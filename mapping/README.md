# mapping/

From the source tables to RDF, in R2RML (W3C, 2012): one mapping and one named
graph per source (D10, D14), and per kind of link between them (D15).

| File | What it is |
|---|---|
| `mapping.ttl` | OpenAlex: the 8 tables of data/lu.sql to triples (Session 2) -> graph/openalex |
| `crossref.ttl` | Crossref: the 4 tables of data/crossref.sql to triples (Session 5) -> graph/crossref |
| `links.ttl` | the links by key of er/links_by_key.csv (same DOI, same ORCID) -> graph/links |
| `matches.ttl` | the matcher's links of er/authorship_links.csv -> graph/matches |
| `one_paper_by_hand.ttl` | one paper (W3023054831) written by hand, before the mapping |
| `check_one_paper.py` | the test: every hand-written triple must come out of the mapping (CI runs it) |
| `er/` | entity resolution: which records of the two sources are the same thing (its own README) |

`pipeline/run.py` runs each mapping with Morph-KGC into its own file
(build/graph.nt, crossref.nt, links.nt, matches.nt), checks each against its
own shapes, and loads each into its own named graph. The link mappings read
the two CSV files of er/, which the pipeline loads as the tables er_links and
er_matches. The sizes are at the top of `ontology/cq_answers.txt`.

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
checking (D3): `er/` makes the links, `links.ttl` and `matches.ttl` turn them
into `owl:sameAs` (and `pub:author`) in graph/links and graph/matches (D15).

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

## Materialized, or virtualized? (D16)

**The deployed system materializes**: pipeline/run.py writes every triple once
with Morph-KGC, checks it with SHACL, and loads it into Fuseki. The same four
mappings also run **virtualized**: Ontop keeps no graph, and turns each SPARQL
query into SQL on PostgreSQL. That route is not part of the stack; it is here
to compare the two on the same questions, and to keep the mappings honest.

| File | What it is |
|---|---|
| `ontop/prepare_ontop.py` | our tables into PostgreSQL, with their keys; Ontop's mapping (the four in one file, each in its named graph) and connection, in build/ontop/ |
| `ontop/Dockerfile` | Ontop 5.5.0 and the PostgreSQL driver, pinned and checksummed |
| `ontop/compare_routes.py` | every competency question on both endpoints: the same answer? how long? then a change in the database, and the two graphs triple by triple |
| `ontop/compare-routes.txt` | its result, the evidence of D16 |

Run it, from the repository root (POSTGRES_PASSWORD in .env, Fuseki loaded by
python pipeline/run.py):

```sh
docker compose --profile virtual up -d postgres
python mapping/ontop/prepare_ontop.py                  # about a minute
docker compose --profile virtual up -d --build ontop   # http://127.0.0.1:8080/sparql
docker compose --profile virtual run --rm ontop /opt/ontop/ontop materialize \
    -m build/ontop/mapping.ttl -p build/ontop/ontop.properties -f nquads -o build/ontop/materialized.nq
python mapping/ontop/compare_routes.py                 # writes ontop/compare-routes.txt
```

If prepare_ontop.py cannot connect:

- **Password authentication failed.** PostgreSQL reads POSTGRES_PASSWORD only
  the first time it starts, when it creates its data in the volume
  postgres-data; later it keeps that password, whatever .env says. To use the
  password now in .env, start it fresh (prepare_ontop.py copies the tables again):
  `docker compose --profile virtual rm -sf postgres ontop`, then
  `docker volume rm krr-lu-publication_postgres-data` (the name starts with the
  folder's name: `docker volume ls`), then `docker compose --profile virtual up -d postgres`.
- **Port 5432 is already allocated.** Another PostgreSQL container on this
  computer uses it: `docker ps --filter "publish=5432"` names it, `docker stop`
  it while this route runs.

What the comparison showed (compare-routes.txt):

- **The same graph, from two engines.** Ontop's materialization of our four
  mappings and Morph-KGC's have the same number of triples, and differ only
  where a key has a character that is not ASCII: R2RML lets an IRI keep it,
  Morph-KGC percent-encodes it. These were 707 reference DOIs with a
  typographic hyphen, which no shape had seen: crossref-shapes.ttl 1.0.1 now
  flags them.
- **One change to the mapping.** Ontop refused a view of mapping.ttl, a
  subquery without a name (`FROM (SELECT ...) WHERE`): SQL requires one,
  SQLite does not. With `AS typed`, the same file serves both engines.
- **The same answers, where Ontop answers.** 12 of the 16 queries give the
  same rows, in the same order. Ontop cannot answer 4: an EXISTS it does not
  support in that form (cq08_sources), and the title and venue comparisons of
  CQ10, whose regular expression (`\p{L}`, a letter in any script) PostgreSQL
  does not know, or which Ontop cannot turn into SQL at all.
- **Freshness.** A title changed in PostgreSQL is in Ontop's next answer;
  Fuseki shows it only after the next pipeline run, minutes later, once the
  SHACL gate has checked it.
