# Decision log

## D1. Leave out OpenAlex's xpac records (2026-10-16)
**Decision.** Download with OpenAlex's default, which excludes xpac records.
**Alternative.** Add include_xpac=true, as LU's institution page counts.
**Why.** OpenAlex says xpac records (repository copies, DataCite datasets) are lower quality.
They would add near-duplicates and messier fields.
**Evidence.** LU papers in 2024: 1,288 by default, 1,398 with include_xpac=true.
Our download for 2022-2025: 5,211 papers (data/fetch_openalex.py).

## D2. Keep all 20 work types for now (2026-10-17)
**Decision.** Keep every type; store the type on each paper.
**Alternative.** Keep only articles, reviews and conference papers.
**Why.** It is what OpenAlex records for LU. Decide per step where the small types
(errata, peer reviews, paratext) matter, e.g. in Step 6.
**Evidence.** 20 types; article 3,873, conference-paper 482, preprint 210 ... (data/profile/look_closer.txt).
## D3. Name every thing by kind, source and key (2026-10-17)
**Decision.** Every thing gets the IRI https://ul.edu.lb/kr/id/{kind}/{source}/{key},
with the key exactly as the source wrote it:
- paper: .../work/openalex/W4206272747 (also cited papers outside our 5,211)
- author: .../author/openalex/A...
- authorship (one author on one paper): .../authorship/openalex/{work_id}-{author_order}
- institution: .../institution/openalex/I160368002
- venue (journal, conference): .../venue/openalex/S...
- topic: .../topic/openalex/T...
Words (classes and properties, e.g. title) live apart, in https://ul.edu.lb/kr/pub#.
**Alternative.** Name papers by DOI and authors by ORCID, or by row number.
**Why.** Row numbers change with every download. DOI and ORCID are not keys in our data:
some are missing and a few are shared. Named by DOI, the OpenAlex and Crossref records
of one paper would merge on load, before we check that they agree (Session 5).
Names change and repeat, so a name is never part of an IRI. An authorship has no ID
of its own, so its key is paper + byline position, the grain of authorships.csv.
**Evidence.** 154 papers without a DOI; 5,057 DOIs but only 5,055 distinct.
9,081 author records with an ORCID, 9,061 distinct. 14,090 authors, 13,955 distinct names
(data/profile/profile_tables.txt, data/constraint_inventory.csv).