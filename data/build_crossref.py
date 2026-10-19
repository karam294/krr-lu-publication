"""Turn the Crossref answers into 4 tables, frozen as data/crossref.sql (Session 5).

    python data/build_crossref.py

Reads data/raw/crossref_works.jsonl (data/fetch_crossref.py) and writes
data/crossref.sql, committed like data/lu.sql (D4, D11): the pipeline and the
entity resolution read it, so a fresh clone needs no download. The counts it
prints are also saved in data/profile/build_crossref.txt.

We keep only what we use, every value as text, as in data/lu.sql. No abstracts:
Crossref says almost none of its metadata is under copyright, except some
abstracts.

  cr_works       one DOI we asked for (found or not)
  cr_authors     one author of one Crossref record, in the order Crossref lists them
  cr_references  one reference with a DOI, of one Crossref record
  cr_updates     one notice (retraction, correction...) and the DOI it updates
"""

import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "crossref_works.jsonl"

TABLES = {
    "cr_works": ["doi", "found", "title", "type", "venue", "issn", "publisher", "published",
                 "reference_count", "cited_by_count", "language"],
    "cr_authors": ["doi", "author_order", "sequence", "given", "family", "name", "orcid", "affiliation"],
    "cr_references": ["doi", "ref_order", "ref_doi"],
    "cr_updates": ["notice_doi", "updated_doi", "update_type"],
}


def first(values):
    """Crossref gives titles and venues as lists; we keep the first one."""
    return values[0].strip() if values else None


def date(message):
    """The earliest publication date Crossref knows: YYYY, YYYY-MM or YYYY-MM-DD."""
    parts = (message.get("published") or message.get("issued") or {}).get("date-parts") or [[]]
    parts = [p for p in parts[0] if p is not None]
    return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(parts)) or None


def text(value):
    return None if value is None else str(value)


def rows_of(rec):
    """The rows one Crossref answer gives, table by table."""
    doi = rec["doi"]
    out = {name: [] for name in TABLES}
    if rec["status"] != 200:
        out["cr_works"].append([doi, "False"] + [None] * 9)
        return out
    m = rec["message"]
    out["cr_works"].append([doi, "True", first(m.get("title")), m.get("type"), first(m.get("container-title")),
                            " ".join(m.get("ISSN", [])) or None, m.get("publisher"), date(m),
                            text(m.get("reference-count")), text(m.get("is-referenced-by-count")),
                            m.get("language")])
    for i, a in enumerate(m.get("author", []), 1):
        orcid = a.get("ORCID")
        orcid = orcid.rstrip("/").rsplit("/", 1)[-1] if orcid else None      # https://orcid.org/0000-... -> 0000-...
        aff = " | ".join(x["name"] for x in a.get("affiliation", []) if x.get("name")) or None
        out["cr_authors"].append([doi, str(i), a.get("sequence"), a.get("given"), a.get("family"),
                                  a.get("name"), orcid, aff])
    for i, ref in enumerate(m.get("reference", []), 1):
        if ref.get("DOI"):
            out["cr_references"].append([doi, str(i), ref["DOI"].strip().lower()])
    for u in m.get("update-to", []):        # this record is a notice that updates another one
        if u.get("DOI"):
            out["cr_updates"].append([doi, u["DOI"].strip().lower(), u.get("type")])
    for u in m.get("updated-by", []):       # this record is updated by a notice
        if u.get("DOI"):
            out["cr_updates"].append([u["DOI"].strip().lower(), doi, u.get("type")])
    return out


def main():
    con = sqlite3.connect(":memory:")
    for name, cols in TABLES.items():
        con.execute(f'CREATE TABLE "{name}" ({", ".join(f"{c} TEXT" for c in cols)})')
    seen = set()
    with RAW.open(encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:        # a line cut off by a stop of the download
                continue
            if rec["doi"] in seen:              # asked twice (a resumed run): keep the first answer
                continue
            seen.add(rec["doi"])
            for name, rows in rows_of(rec).items():
                con.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" * len(TABLES[name]))})', rows)
    # A notice listed both ways (update-to on the notice, updated-by on the paper) counts once.
    con.execute("""DELETE FROM cr_updates WHERE rowid NOT IN
                   (SELECT MIN(rowid) FROM cr_updates GROUP BY notice_doi, updated_doi, update_type)""")

    q = lambda sql: con.execute(sql).fetchone()[0]
    lu = sqlite3.connect(":memory:")
    lu.executescript((HERE / "lu.sql").read_text(encoding="utf-8"))
    ours = {d for (d,) in lu.execute("SELECT doi FROM works WHERE doi IS NOT NULL")}
    found = q("SELECT COUNT(*) FROM cr_works WHERE found = 'True'")
    missing = q("SELECT COUNT(*) FROM cr_works WHERE found = 'False'")
    to_ours = sum(1 for (d,) in con.execute("SELECT ref_doi FROM cr_references") if d in ours)
    types = con.execute("SELECT type, COUNT(*) FROM cr_works WHERE found = 'True' GROUP BY 1 ORDER BY 2 DESC")
    updates = con.execute("SELECT update_type, COUNT(*) FROM cr_updates GROUP BY 1 ORDER BY 2 DESC")
    lines = [
        f"DOIs asked: {q('SELECT COUNT(*) FROM cr_works'):,}",
        f"  found in Crossref: {found:,}",
        f"  not in Crossref:   {missing:,}",
        f"cr_authors: {q('SELECT COUNT(*) FROM cr_authors'):,} rows, "
        f"{q('SELECT COUNT(*) FROM cr_authors WHERE orcid IS NOT NULL'):,} with an ORCID, "
        f"{q('SELECT COUNT(*) FROM cr_authors WHERE affiliation IS NOT NULL'):,} with an affiliation",
        f"cr_references: {q('SELECT COUNT(*) FROM cr_references'):,} rows (references with a DOI), "
        f"from {q('SELECT COUNT(DISTINCT doi) FROM cr_references'):,} records",
        f"  pointing to one of our own DOIs: {to_ours:,}",
        f"cr_updates: {q('SELECT COUNT(*) FROM cr_updates'):,} rows; by type: "
        + (", ".join(f"{t} {n}" for t, n in updates) or "none"),
        "Crossref types: " + ", ".join(f"{t} {n:,}" for t, n in types),
    ]
    out = HERE / "crossref.sql"
    with open(out, "w", encoding="utf-8") as f:
        for line in con.iterdump():
            f.write(line + "\n")
    lines.append(f"written: data/crossref.sql, {out.stat().st_size / 1e6:.1f} MB")
    print("\n".join(lines))
    (HERE / "profile" / "build_crossref.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
