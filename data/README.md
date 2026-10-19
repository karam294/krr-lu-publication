# data/

Two sources (D11):

- **OpenAlex**, the first source: the publications of the Lebanese University
  (OpenAlex institution I160368002), 2022-2025, downloaded on 2026-10-16 (D1).
  OpenAlex data is CC0. Frozen as `lu.sql` (D4).
- **Crossref**, the second source (Session 5): the Crossref record of each of
  our 5,055 distinct DOIs, downloaded on 2026-10-19. Crossref says almost none of
  its metadata is subject to copyright; we keep no abstracts. Frozen as
  `crossref.sql`.

The pipeline (pipeline/run.py) reads only `lu.sql` and `crossref.sql`, so a
fresh clone needs no API key and none of the steps before them.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | fetch_openalex.py | the OpenAlex API (OPENALEX_API_KEY in .env) | raw/openalex_works.json, not committed |
| 2 | build_table.py | raw/openalex_works.json | tables/*.csv, 8 tables, not committed |
| 3 | profile_tables.py, look_closer.py, rules_checks.py | tables/*.csv | profile/*.txt, the Session 1 evidence |
| 4 | build_database.py | tables/*.csv | lu.sql, the 8 tables as SQL, committed |
| 5 | fetch_crossref.py | lu.sql (the DOIs), the Crossref API (no key) | raw/crossref_works.jsonl, not committed |
| 6 | build_crossref.py | raw/crossref_works.jsonl | crossref.sql, 4 tables, committed; profile/build_crossref.txt |

`show_paper.py` prints everything the tables say about one paper (W3023054831);
that paper is written by hand in mapping/one_paper_by_hand.ttl.
`constraint_inventory.csv` holds the 10 rules of Session 1, each with its evidence.

The 8 OpenAlex tables and their grain (one row = ...):

| Table | One row is | Rows |
|---|---|---|
| works | one paper | 5,211 |
| authorships | one author on one paper | 33,084 |
| affiliations | one institution of one authorship | 51,737 |
| authors | one OpenAlex author | 14,090 |
| institutions | one institution | 3,656 |
| sources | one venue (journal, conference, repository) | 2,216 |
| topics | one OpenAlex topic | 1,610 |
| citations | one paper citing another | 175,896 |

The 4 Crossref tables (crossref.sql), every value as text:

| Table | One row is | Rows |
|---|---|---|
| cr_works | one DOI we asked for: found (4,886) or not in Crossref (169) | 5,055 |
| cr_authors | one author of one Crossref record, in Crossref's order | 35,468 |
| cr_references | one reference that has a DOI, of one Crossref record | 149,936 |
| cr_updates | one notice (correction, retraction, new version...) and the DOI it updates | 63 |

The 169 DOIs not in Crossref are registered elsewhere, mostly with DataCite:
112 Zenodo (10.5281), 26 arXiv (10.48550), 7 figshare (10.6084), 24 others.
