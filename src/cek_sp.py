import io, os, time
import pandas as pd, requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("FIRMS_MAP_KEY")
BASE = "https://firms.modaps.eosdis.nasa.gov"
BBOX = "108.8,-4.3,119.1,4.4"


def coba(sensor, tanggal):
    url = f"{BASE}/api/area/csv/{KEY}/{sensor}/{BBOX}/1/{tanggal}"
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:120]}"
    teks = r.text.strip()
    if not teks or "," not in teks.split("\n")[0]:
        return f"respons aneh: {teks[:120]}"
    try:
        df = pd.read_csv(io.StringIO(teks))
        return f"{len(df):,} titik"
    except Exception as e:
        return f"gagal parse: {e}"


uji = [
    ("VIIRS_SNPP_SP", "2025-09-15"),
    ("VIIRS_SNPP_SP", "2023-09-15"),
    ("VIIRS_SNPP_SP", "2019-09-15"),
    ("MODIS_SP", "2019-09-15"),
    ("MODIS_SP", "2015-10-15"),
    ("MODIS_SP", "2006-10-15"),
]

for sensor, tgl in uji:
    print(f"{sensor:16} {tgl} -> {coba(sensor, tgl)}")
    time.sleep(1)