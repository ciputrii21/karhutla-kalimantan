"""
Tarik data titik panas VIIRS SNPP untuk wilayah Kalimantan, 2012 sampai sekarang.

Sifatnya bisa dilanjutkan: setiap potongan 5 hari disimpan sebagai berkas
terpisah. Kalau proses terhenti, jalankan ulang dan dia melewati potongan
yang sudah ada.

API FIRMS membatasi 5 hari per permintaan, jadi 14 tahun butuh sekitar
1.070 permintaan. Siapkan waktu sekitar 30 sampai 45 menit.

Sumber: NASA FIRMS (VIIRS S-NPP 375m)
"""

import io
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

KEY = os.getenv("FIRMS_MAP_KEY")
if not KEY:
    sys.exit("FIRMS_MAP_KEY tidak ditemukan. Cek file .env")

BASE = "https://firms.modaps.eosdis.nasa.gov"
BBOX = "108.8,-4.3,119.1,4.4"      # Kalimantan (ikut menangkap sebagian Malaysia)
LANGKAH = 5                         # batas maksimum API
JEDA = 1.0                          # detik antar permintaan
BATAS_ULANG = 3

MULAI = date(2012, 1, 20)           # VIIRS SNPP mulai beroperasi
SELESAI = date.today() - timedelta(days=1)

# Data Standard Processing tertinggal beberapa bulan dari hari ini.
# Untuk tanggal terbaru dipakai Near Real Time.
AMBANG_NRT = date.today() - timedelta(days=90)

KELUAR = ROOT / "data" / "raw" / "firms"
KELUAR.mkdir(parents=True, exist_ok=True)


def sensor_untuk(tanggal):
    return "VIIRS_SNPP_NRT" if tanggal >= AMBANG_NRT else "VIIRS_SNPP_SP"


def ambil(tanggal, hari):
    """Satu permintaan. Kembalikan (DataFrame atau None, pesan error atau None)."""
    sensor = sensor_untuk(tanggal)
    url = f"{BASE}/api/area/csv/{KEY}/{sensor}/{BBOX}/{hari}/{tanggal.isoformat()}"

    for percobaan in range(1, BATAS_ULANG + 1):
        try:
            r = requests.get(url, timeout=90)
        except Exception as e:
            if percobaan == BATAS_ULANG:
                return None, f"koneksi gagal: {e}"
            time.sleep(5 * percobaan)
            continue

        if r.status_code == 429:
            time.sleep(30)
            continue

        if r.status_code != 200:
            if percobaan == BATAS_ULANG:
                return None, f"HTTP {r.status_code}: {r.text[:120]}"
            time.sleep(5 * percobaan)
            continue

        teks = r.text.strip()
        if not teks:
            return pd.DataFrame(), None

        baris_awal = teks.split("\n")[0]
        if "latitude" not in baris_awal.lower():
            return None, f"respons tidak terduga: {teks[:120]}"

        try:
            return pd.read_csv(io.StringIO(teks)), None
        except Exception as e:
            return None, f"gagal parse: {e}"

    return None, "gagal setelah beberapa percobaan"


def main():
    potongan = []
    kursor = MULAI
    while kursor <= SELESAI:
        potongan.append(kursor)
        kursor += timedelta(days=LANGKAH)

    total = len(potongan)
    print(f"Rentang     : {MULAI} sampai {SELESAI}")
    print(f"Potongan    : {total} permintaan @ {LANGKAH} hari")
    print(f"Ambang NRT  : {AMBANG_NRT}")
    print(f"Folder      : {KELUAR}")
    print()

    sudah = 0
    baru = 0
    kosong = 0
    gagal = []
    titik_total = 0
    awal = time.time()

    for i, tanggal in enumerate(potongan, 1):
        berkas = KELUAR / f"{tanggal.isoformat()}.csv"

        if berkas.exists():
            sudah += 1
            if i % 100 == 0 or i == total:
                print(f"[{i}/{total}] dilewati (sudah ada)")
            continue

        df, err = ambil(tanggal, LANGKAH)

        if err:
            gagal.append((tanggal.isoformat(), err))
            print(f"[{i}/{total}] {tanggal} GAGAL: {err[:70]}")
        else:
            df.to_csv(berkas, index=False)
            baru += 1
            n = len(df)
            titik_total += n
            if n == 0:
                kosong += 1

            if i % 20 == 0 or n > 3000:
                lewat = time.time() - awal
                sisa = (total - i) * (lewat / max(baru, 1))
                print(
                    f"[{i}/{total}] {tanggal} -> {n:,} titik "
                    f"| total {titik_total:,} | sisa ~{sisa/60:.0f} menit"
                )

        time.sleep(JEDA)

    print()
    print("=" * 60)
    print("SELESAI")
    print("=" * 60)
    print(f"Sudah ada sebelumnya : {sudah}")
    print(f"Baru diunduh         : {baru}")
    print(f"Potongan kosong      : {kosong}")
    print(f"Total titik baru     : {titik_total:,}")
    print(f"Gagal                : {len(gagal)}")

    if gagal:
        print("\n--- Potongan yang gagal (jalankan ulang untuk mencoba lagi) ---")
        for tgl, e in gagal[:20]:
            print(f"  {tgl}: {e[:80]}")
        if len(gagal) > 20:
            print(f"  ... dan {len(gagal) - 20} lainnya")

    berkas_ada = sorted(KELUAR.glob("*.csv"))
    print(f"\nTotal berkas di folder: {len(berkas_ada)} dari {total} potongan")

    if len(berkas_ada) == total and not gagal:
        print("Lengkap. Lanjut ke penggabungan.")
    else:
        print("Belum lengkap. Jalankan ulang script ini untuk melanjutkan.")


if __name__ == "__main__":
    main()
