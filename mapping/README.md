# mapping/

From the source tables to RDF, in R2RML (W3C, 2012), one mapping per source,
one named graph per source (D10, D14).

| File | What it is |
|---|---|
| `mapping.ttl` | OpenAlex: the 8 tables of data/lu.sql to triples (Session 2) -> graph/openalex |
| `crossref.ttl` | Crossref: the 4 tables of data/crossref.sql to triples (Session 5) -> graph/crossref |
| `one_paper_by_hand.ttl` | one paper (W3023054831) written by hand, before the mapping |
| `check_one_paper.py` | the test: every hand-written triple must come out of the mapping (CI runs it) |
| `er/` | entity resolution: which records of the two sources are the same thing (its own README) |

`pipeline/run.py` runs each mapping with Morph-KGC into its own file
(build/graph.nt, build/crossref.nt), checks each against its own shapes, and
loads each into its own named graph. The sizes are in the first line of
`ontology/cq_answers.txt`.

## One IRI scheme for both sources (D3)

`https://ul.edu.lb/kr/id/{kind}/{source}/{key}`, the key as the source writes it:

| Thing | OpenAlex | Crossref |
|---|---|---|
| paper | .../work/openalex/W3023054831 | .../work/crossref/10.1007%2Fs00205-021-01737-1 (the DOI; its slash written %2F) |
| authorship | .../authorship/openalex/{work}-{position} | .../authorship/crossref/{DOI}-{position} |
| person | .../author/openalex/A... | .../author/orcid/{ORCID} (Crossref has no person ID, D12) |
| venue | .../venue/openalex/S... | none: the name and ISSNs stay values of the record (D14) |

So the OpenAlex paper and the Crossref record of the same DOI are two nodes,
each in its own graph. They become one paper only through a link, made after
checking (D3): `er/` makes the links, and the next step loads them.

## What each source says

Both mappings use the same pub: words (ontology 1.1.0). Crossref adds three
(D14): pub:updates (a notice and the paper it retracts or corrects),
pub:venueName and pub:issn (the venue as the record states it). Left out of
Crossref on purpose: its types (journal-article covers OpenAlex's article,
review, editorial and letter), its counts, publisher and language.

Two R2RML habits matter in both files:

- a view (`rr:sqlQuery`) only on columns that are never empty: Morph-KGC
  writes an empty cell of a view as the text "None" (Session 2);
- one value per view row: cr_works.issn holds up to three ISSNs, so the
  view gives one row per ISSN (`<#CrossrefIssns>`).

## Materialized, or virtualized?

Today the pipeline materializes: it writes every triple once, checks it with
SHACL and loads it into Fuseki. The same mappings can also be answered
without copying the data (virtualized, with Ontop, as in the Session 5 lab).
Which route the deployed system takes, argued on freshness, latency and
workload, is decided later in Session 5.
