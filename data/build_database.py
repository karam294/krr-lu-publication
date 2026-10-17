import sqlite3
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
TABLES = ["works", "authorships", "affiliations", "authors",
          "institutions", "sources", "topics", "citations"]

con = sqlite3.connect(":memory:")      # a database that lives only while the script runs
for name in TABLES:
    # dtype=str: keep every value as text, exactly as in the CSV.
    # keep_default_na=False, na_values=[""]: only an empty cell counts as missing
    # (pandas would otherwise read the text "NA", Namibia's country code, as missing).
    df = pd.read_csv(HERE / "tables" / f"{name}.csv", dtype=str,
                     keep_default_na=False, na_values=[""])
    df.to_sql(name, con, index=False)
    print(f"{name}: {len(df):,} rows")

# The first SQL question of the project, asked to the new database.
na = con.execute("SELECT COUNT(*) FROM institutions WHERE country_code = 'NA'").fetchone()[0]
print("institutions with country code 'NA' (Namibia):", na)

out = HERE / "lu.sql"
with open(out, "w", encoding="utf-8") as f:
    for line in con.iterdump():       # the whole database written out as SQL text
        f.write(line + "\n")
print(f"written: data/lu.sql, {out.stat().st_size / 1e6:.1f} MB")