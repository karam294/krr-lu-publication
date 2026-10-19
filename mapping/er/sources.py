"""Both sources in one database, for entity resolution (Session 5).

load() reads data/lu.sql (OpenAlex, 8 tables) and data/crossref.sql (Crossref,
4 tables whose names start with cr_) into one SQLite database in memory, with
the indexes the matchers need. Nothing is written to disk.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ER = Path(__file__).resolve().parent

INDEXES = [
    "works(doi)", "works(work_id)", "authorships(work_id)", "authorships(orcid)", "authors(orcid)",
    "cr_works(doi)", "cr_authors(doi)", "cr_references(doi)", "citations(citing_work_id)",
]


def load():
    con = sqlite3.connect(":memory:")
    for name in ("lu.sql", "crossref.sql"):
        con.executescript((ROOT / "data" / name).read_text(encoding="utf-8"))
    for i, target in enumerate(INDEXES):
        con.execute(f"CREATE INDEX i{i} ON {target}")
    return con
