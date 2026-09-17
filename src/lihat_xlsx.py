import pandas as pd
from pathlib import Path

RAW = Path("data/raw")

for f in sorted(RAW.glob("*.xlsx")):
    print("=" * 70)
    print(f"FILE: {f.name}  ({f.stat().st_size / 1024:.1f} KB)")
    print("=" * 70)

    sheets = pd.read_excel(f, sheet_name=None, header=None, engine="openpyxl")
    print(f"Sheet: {list(sheets.keys())}\n")

    for nama, df in sheets.items():
        print(f"-- sheet '{nama}': {df.shape[0]} baris x {df.shape[1]} kolom")
        with pd.option_context("display.max_columns", None, "display.width", 250):
            print(df.head(12).to_string())
        print()