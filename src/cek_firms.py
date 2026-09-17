"""
Cek ketersediaan data FIRMS untuk wilayah Kalimantan.
Dijalankan sekali di awal proyek untuk memastikan:
  - MAP_KEY valid dan berapa sisa kuota
  - sensor apa saja yang tersedia dan rentang tanggalnya
  - berapa banyak titik panas di Kalimantan saat ini
  - apakah query tanggal lampau berfungsi
"""

import io
import os
import sys
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("FIRMS_MAP_KEY")
if not KEY:
    sys.exit("FIRMS_MAP_KEY tidak ditemukan. Cek file .env")

BASE = "https://firms.modaps.eosdis.nasa.gov"

# Kotak pembatas Kalimantan: barat, selatan, timur, utara
# Catatan: kotak ini ikut menangkap sebagian Sarawak dan Sabah (Malaysia).
# Nanti dipotong pakai batas provinsi.
BBOX = "108.8,-4.3,119.1,4.4"

SENSOR = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "MODIS_NRT",
]


def garis(judul):
    print()
    print("=" * 62)
    print(judul)
    print("=" * 62)


def cek_kuota():
    garis("1. STATUS MAP_KEY")
    url = f"{BASE}/mapserver/mapkey_status/?MAP_KEY={KEY}"
    try:
        r = requests.get(url, timeout=30)
        print("Status HTTP:", r.status_code)
        print(r.text[:400])
    except Exception as e:
        print("Gagal:", e)


def cek_ketersediaan():
    garis("2. SENSOR YANG TERSEDIA")
    url = f"{BASE}/api/data_availability/csv/{KEY}/all"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            print("Status:", r.status_code)
            print(r.text[:400])
            return
        df = pd.read_csv(io.StringIO(r.text))
        with pd.option_context("display.width", 200, "display.max_columns", None):
            print(df.to_string(index=False))
    except Exception as e:
        print("Gagal:", e)


def ambil(sensor, hari=1, tanggal=None):
    """Ambil titik panas untuk bbox Kalimantan."""
    url = f"{BASE}/api/area/csv/{KEY}/{sensor}/{BBOX}/{hari}"
    if tanggal:
        url += f"/{tanggal}"
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    teks = r.text.strip()
    if not teks or teks.lower().startswith("invalid"):
        return None, f"Respons tidak terduga: {teks[:200]}"
    try:
        return pd.read_csv(io.StringIO(teks)), None
    except Exception as e:
        return None, f"Gagal parse CSV: {e} | awal respons: {teks[:200]}"


def cek_terkini():
    garis("3. DATA TERKINI (1 HARI TERAKHIR)")
    total = {}
    contoh = None
    for s in SENSOR:
        df, err = ambil(s, hari=1)
        if err:
            print(f"{s:20} -> {err}")
        else:
            print(f"{s:20} -> {len(df):,} titik")
            total[s] = len(df)
            if contoh is None and len(df):
                contoh = df
        time.sleep(1)

    if contoh is not None:
        print("\n--- Kolom yang tersedia ---")
        print(", ".join(contoh.columns))
        print("\n--- 5 baris pertama ---")
        with pd.option_context("display.width", 220, "display.max_columns", None):
            print(contoh.head().to_string(index=False))
    return total


def cek_riwayat():
    garis("4. UJI QUERY TANGGAL LAMPAU")
    uji = [
        ("2026-08-15", "puncak musim 2026"),
        ("2025-09-15", "musim 2025"),
        ("2023-09-15", "musim 2023"),
        ("2019-09-15", "El Nino 2019"),
        ("2015-10-15", "El Nino 2015 (MODIS saja)"),
    ]
    for tgl, ket in uji:
        sensor = "MODIS_NRT" if tgl < "2020" else "VIIRS_SNPP_NRT"
        df, err = ambil(sensor, hari=1, tanggal=tgl)
        if err:
            print(f"{tgl}  {ket:28} -> {err[:80]}")
        else:
            print(f"{tgl}  {ket:28} -> {len(df):,} titik  ({sensor})")
        time.sleep(1)


def ringkas_spasial():
    garis("5. SEBARAN TITIK PANAS 7 HARI TERAKHIR")
    df, err = ambil("VIIRS_SNPP_NRT", hari=7)
    if err:
        print(err)
        return
    print(f"Total: {len(df):,} titik\n")

    if "acq_date" in df.columns:
        print("--- Per tanggal ---")
        print(df["acq_date"].value_counts().sort_index().to_string())

    if "confidence" in df.columns:
        print("\n--- Tingkat kepercayaan ---")
        print(df["confidence"].value_counts().to_string())

    if "frp" in df.columns:
        print("\n--- Fire Radiative Power ---")
        print(df["frp"].describe().round(2).to_string())

    if {"latitude", "longitude"}.issubset(df.columns):
        print("\n--- Rentang koordinat ---")
        print(f"Lintang : {df['latitude'].min():.3f} s/d {df['latitude'].max():.3f}")
        print(f"Bujur   : {df['longitude'].min():.3f} s/d {df['longitude'].max():.3f}")

    os.makedirs("data/raw", exist_ok=True)
    keluaran = "data/raw/contoh_7hari.csv"
    df.to_csv(keluaran, index=False)
    print(f"\nTersimpan: {keluaran}")


if __name__ == "__main__":
    cek_kuota()
    cek_ketersediaan()
    cek_terkini()
    cek_riwayat()
    ringkas_spasial()
    print("\nSelesai.")
