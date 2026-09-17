"""
Bersihkan data luas karhutla SiPongi (provinsi dan kabupaten/kota).

Tugasnya:
  - ubah format lebar (tahun jadi kolom) ke format panjang
  - tangani angka format Indonesia: titik ribuan, koma desimal
  - tangani sel bertipe campur (sebagian angka, sebagian teks)
  - buang baris agregat "Total" supaya tidak dobel hitung
  - tandai nol yang mencurigakan, bukan menghapusnya
  - pisahkan subset Kalimantan

Sumber data: SIPONGI KEMENHUT
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# Kode wilayah BPS untuk lima provinsi di Kalimantan
KODE_KALIMANTAN = {"61", "62", "63", "64", "65"}

TAHUN_PARSIAL = 2026  # data input baru sampai Juli 2026


def parse_angka(nilai):
    """
    '16.910,00' -> 16910.0
    '0,00'      -> 0.0
    0           -> 0.0   (sel yang sudah bertipe angka)
    kosong      -> NA
    """
    if pd.isna(nilai):
        return pd.NA
    if isinstance(nilai, (int, float)):
        return float(nilai)

    teks = str(nilai).strip()
    if teks in {"", "-", "nan", "None"}:
        return pd.NA

    teks = teks.replace(".", "").replace(",", ".")
    teks = re.sub(r"[^\d.\-]", "", teks)
    if teks in {"", ".", "-"}:
        return pd.NA
    try:
        return float(teks)
    except ValueError:
        return pd.NA


def bersihkan(path, nama_wilayah):
    raw = pd.read_excel(path, sheet_name=0, header=0, engine="openpyxl")

    kolom = list(raw.columns)
    kol_kode, kol_nama = kolom[0], kolom[1]
    kol_tahun = kolom[2:]

    df = raw.rename(columns={kol_kode: "kode_wilayah", kol_nama: nama_wilayah})

    tidy = df.melt(
        id_vars=["kode_wilayah", nama_wilayah],
        value_vars=kol_tahun,
        var_name="tahun",
        value_name="luas_mentah",
    )

    tidy["tahun"] = pd.to_numeric(tidy["tahun"], errors="coerce").astype("Int64")
    tidy["luas_ha"] = tidy["luas_mentah"].map(parse_angka).astype("Float64")

    # kode wilayah terbaca sebagai desimal (61.0) karena ada baris tanpa kode
    tidy["kode_wilayah"] = (
        tidy["kode_wilayah"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    tidy[nama_wilayah] = (
        tidy[nama_wilayah].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )

    tidy = tidy.drop(columns=["luas_mentah"])

    # buang baris agregat "Total" supaya tidak dobel hitung
    bukan_total = ~tidy[nama_wilayah].str.upper().str.strip().eq("TOTAL")
    tidy = tidy[bukan_total].copy()

    # penanda kualitas, bukan penghapusan
    tidy["nilai_nol"] = tidy["luas_ha"] == 0
    tidy["tahun_parsial"] = tidy["tahun"] == TAHUN_PARSIAL

    return tidy.sort_values([nama_wilayah, "tahun"]).reset_index(drop=True)


def laporan(tidy, nama_wilayah, judul):
    print("=" * 66)
    print(judul)
    print("=" * 66)

    print(f"\nBaris          : {len(tidy):,}")
    print(f"Jumlah wilayah : {tidy[nama_wilayah].nunique()}")
    print(f"Rentang tahun  : {tidy['tahun'].min()} - {tidy['tahun'].max()}")

    kosong = int(tidy["luas_ha"].isna().sum())
    print(f"Nilai kosong   : {kosong:,}")

    print("\n--- Jumlah nilai nol per tahun ---")
    print("(nol yang banyak menandakan data tidak terinput, bukan tidak ada kebakaran)")
    per_tahun = tidy.groupby("tahun").agg(
        total_wilayah=(nama_wilayah, "count"),
        jumlah_nol=("nilai_nol", "sum"),
        total_ha=("luas_ha", "sum"),
    )
    per_tahun["persen_nol"] = (
        per_tahun["jumlah_nol"] / per_tahun["total_wilayah"] * 100
    ).round(1)
    per_tahun["total_ha"] = per_tahun["total_ha"].round(0)
    with pd.option_context("display.width", 200):
        print(per_tahun.to_string())

    print("\n--- 10 tahun-wilayah dengan luas terbesar ---")
    top = tidy.nlargest(10, "luas_ha")[[nama_wilayah, "tahun", "luas_ha"]]
    top["luas_ha"] = top["luas_ha"].round(0)
    print(top.to_string(index=False))
    print()


if __name__ == "__main__":
    # --- provinsi ---
    prov = bersihkan(RAW / "luas_provinsi.xlsx", "provinsi")
    laporan(prov, "provinsi", "LUAS KARHUTLA PER PROVINSI (SELURUH INDONESIA)")

    prov.to_csv(PROC / "luas_provinsi_long.csv", index=False)

    kal = prov[prov["kode_wilayah"].isin(KODE_KALIMANTAN)].copy()
    kal.to_csv(PROC / "luas_kalimantan_provinsi.csv", index=False)

    print("=" * 66)
    print("SUBSET KALIMANTAN")
    print("=" * 66)
    if len(kal):
        pivot = kal.pivot(index="provinsi", columns="tahun", values="luas_ha").round(0)
        with pd.option_context("display.width", 250, "display.max_columns", None):
            print(pivot.to_string())
    else:
        print("Kosong. Cek kode wilayah:", sorted(prov["kode_wilayah"].unique())[:10])
    print()

    # --- kabupaten/kota ---
    kab_path = RAW / "luas_kabupaten.xlsx"
    if kab_path.exists():
        kab = bersihkan(kab_path, "kabupaten")
        kab["kode_provinsi"] = kab["kode_wilayah"].str[:2]
        laporan(kab, "kabupaten", "LUAS KARHUTLA PER KABUPATEN/KOTA")

        kab.to_csv(PROC / "luas_kabupaten_long.csv", index=False)

        kab_kal = kab[kab["kode_provinsi"].isin(KODE_KALIMANTAN)].copy()
        kab_kal.to_csv(PROC / "luas_kalimantan_kabupaten.csv", index=False)

        print(f"Kabupaten di Kalimantan: {kab_kal['kabupaten'].nunique()}")
        print("\n--- 15 kabupaten Kalimantan dengan luas kumulatif terbesar ---")
        rekap = (
            kab_kal.groupby("kabupaten")["luas_ha"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .round(0)
        )
        print(rekap.to_string())
    else:
        print("luas_kabupaten.xlsx belum ada, bagian kabupaten dilewati.")

    print("\nTersimpan di data/processed/")
