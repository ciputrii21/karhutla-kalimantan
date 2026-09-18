"""
Gabungkan semua potongan CSV FIRMS menjadi satu dataset bersih.

Tugasnya:
  - gabung 1071 berkas CSV jadi satu
  - filter ke wilayah Kalimantan (buang Sarawak/Sabah)
  - standarkan kolom
  - tambah kolom bantu: tahun, bulan, musim kebakaran
  - simpan ke data/processed/
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIRMS_DIR = ROOT / "data" / "raw" / "firms"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# Batas administratif Kalimantan (tanpa Malaysia)
LAT_MIN, LAT_MAX = -4.3, 4.2
LON_MIN, LON_MAX = 108.8, 119.0

# Kode provinsi Kalimantan untuk referensi
PROVINSI_KALIMANTAN = [
    "Kalimantan Barat",
    "Kalimantan Tengah",
    "Kalimantan Selatan",
    "Kalimantan Timur",
    "Kalimantan Utara",
]


def musim(bulan):
    """Penanda musim kebakaran Indonesia."""
    if bulan in [6, 7, 8, 9, 10]:
        return "puncak"
    elif bulan in [4, 5, 11]:
        return "transisi"
    else:
        return "basah"


def main():
    berkas = sorted(FIRMS_DIR.glob("*.csv"))
    print(f"Berkas ditemukan: {len(berkas):,}")

    if not berkas:
        raise SystemExit(f"Tidak ada CSV di {FIRMS_DIR}")

    # Cek kolom dari berkas pertama yang tidak kosong
    kolom_standar = None
    for f in berkas:
        if f.stat().st_size > 50:
            kolom_standar = pd.read_csv(f, nrows=0).columns.tolist()
            print(f"Kolom: {kolom_standar}")
            break

    print("\nMenggabungkan... (ini sekitar 1-2 menit)")

    potongan = []
    kosong = 0
    for f in berkas:
        if f.stat().st_size < 50:
            kosong += 1
            continue
        try:
            df = pd.read_csv(f, low_memory=False)
            if len(df):
                potongan.append(df)
        except Exception as e:
            print(f"  Lewati {f.name}: {e}")

    print(f"Potongan kosong: {kosong}")
    print(f"Potongan berisi data: {len(potongan):,}")

    gabung = pd.concat(potongan, ignore_index=True)
    print(f"\nTotal baris sebelum filter: {len(gabung):,}")

    # Filter ke batas Kalimantan
    kal = gabung[
        (gabung["latitude"] >= LAT_MIN) & (gabung["latitude"] <= LAT_MAX) &
        (gabung["longitude"] >= LON_MIN) & (gabung["longitude"] <= LON_MAX)
    ].copy()
    print(f"Setelah filter batas Kalimantan: {len(kal):,}")
    print(f"Titik dibuang (Malaysia dll): {len(gabung) - len(kal):,}")

    # Standarkan tanggal
    kal["tanggal"] = pd.to_datetime(kal["acq_date"], errors="coerce")
    kal["tahun"] = kal["tanggal"].dt.year
    kal["bulan"] = kal["tanggal"].dt.month
    kal["musim"] = kal["bulan"].map(musim)

    # Buang duplikat (potongan yang tumpang tindih)
    sebelum_dedup = len(kal)
    kal = kal.drop_duplicates(
        subset=["latitude", "longitude", "acq_date", "acq_time"]
    )
    print(f"Duplikat dibuang: {sebelum_dedup - len(kal):,}")
    print(f"Total bersih: {len(kal):,}")

    # Laporan singkat
    print("\n--- Titik panas per tahun ---")
    per_tahun = kal.groupby("tahun").size().reset_index(name="jumlah_titik")
    print(per_tahun.to_string(index=False))

    print("\n--- Kolom akhir ---")
    print(kal.dtypes.to_string())

    # Simpan
    keluaran = PROC / "firms_kalimantan_2012_2026.csv"
    kal.to_csv(keluaran, index=False)
    ukuran = keluaran.stat().st_size / 1024 / 1024
    print(f"\nTersimpan: {keluaran}")
    print(f"Ukuran: {ukuran:.1f} MB")
    print(f"Baris: {len(kal):,}")


if __name__ == "__main__":
    main()