# data/

Our source: the publications of the Lebanese University (OpenAlex institution
I160368002), 2022-2025, downloaded from OpenAlex on 2026-10-16 (D1).
OpenAlex data is CC0.

The pipeline (pipeline/run.py) reads only `lu.sql` (D4), so a fresh clone needs
no API key and none of the steps before it.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | fetch_openalex.py | the OpenAlex API (OPENALEX_API_KEY in .env) | raw/openalex_works.json, not committed |
| 2 | build_table.py | raw/openalex_works.json | tables/*.csv, 8 tables, not committed |
| 3 | profile_tables.py, look_closer.py, rules_checks.py | tables/*.csv | profile/*.txt, the Session 1 evidence |
| 4 | build_database.py | tables/*.csv | lu.sql, the 8 tables as SQL, committed |

`show_paper.py` prints everything the tables say about one paper (W3023054831);
that paper is written by hand in mapping/one_paper_by_hand.ttl.
`constraint_inventory.csv` holds the 10 rules of Session 1, each with its evidence.

The 8 tables and their grain (one row = ...):

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