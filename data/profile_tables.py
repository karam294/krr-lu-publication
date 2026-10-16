from pathlib import Path
import pandas as pd

TABLES = Path(__file__).resolve().parent / "tables"

for path in sorted(TABLES.glob("*.csv")):
    df = pd.read_csv(path, dtype=str)      # everything as text: we measure first, interpret later
    print(f"\n== {path.stem}: {len(df):,} rows")
    for col in df.columns:
        empty = df[col].isna().sum()        # how many cells are empty
        distinct = df[col].nunique()        # how many different values
        print(f"   {col:20} empty {empty:>7,}   distinct {distinct:>7,}")