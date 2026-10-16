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