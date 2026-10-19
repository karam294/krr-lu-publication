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
## D4. Ship the data as a frozen SQL copy in the repo (2026-10-17)
**Decision.** Commit data/lu.sql: the 8 tables as SQL (21.7 MB), built by
data/build_database.py from the OpenAlex download of 2026-10-16.
The pipeline will load it from step 4 on.
**Alternative.** Download from OpenAlex when the pipeline runs, or commit only a sample.
**Why.** The instructor grades a fresh clone with one command: it has no OpenAlex key,
and a new download would differ from ours (OpenAlex changes daily), so our numbers
would drift. A sample would grade a different dataset than the report describes.
OpenAlex data is CC0, so it may be shared.
**Evidence.** Same row counts as Session 1 in all 8 tables (works 5,211 ... citations
175,896); 0 institutions with country code 'NA', so the 98 empty country codes are
truly empty (data/profile/build_database.txt).

## D5. Keep the name as listed on every authorship; a person only from an OpenAlex ID (2026-10-17)
**Decision.** Every authorship carries pub:nameAsListed, the name printed on the paper.
A person (pub:Author) exists only for an OpenAlex author ID.
**Alternative.** Make a person from the name when the ID is missing, or drop those names.
**Why.** Names repeat and change (D3), so a person named by name would merge different
people. Dropping would lose the only trace of 2,101 authorships (6.4%). Who they are
is a matching question for Session 5.
**Evidence.** 33,084 authorships, all with a name; 2,101 without an author ID
(data/profile/profile_tables.txt).

## D6. Use the RDF stack, not a property graph (2026-10-18)
**Decision.** RDF: IRIs, RDFS and OWL, SHACL, SPARQL in Fuseki, as the template.
**Alternative.** A property graph (Neo4j, queried with Cypher).
**Why.** Crossref must merge with OpenAlex in Session 5 without renaming anything:
global IRIs (D3) do that. "An article is a work" is stated once in the graph, not
listed in every query. We reuse published vocabularies (FaBiO, CiTO) and check data
with SHACL: both are standards a property graph lacks. Neo4j has simpler queries and
suits one team with one source; we have two sources and a schema to reason over.
**Evidence.** Session 2, step 2d: the paper is found as a Work only through
rdfs:subClassOf (ontology/first_schema.ttl, now part of ontology/ontology.ttl).


## D7. Reuse SPAR (FaBiO, CiTO, PRO), FOAF and Dublin Core by alignment (2026-10-18)
**Decision.** The data keeps its pub: words. ontology.ttl places each pub: class or
property under a published one (rdfs:subClassOf, rdfs:subPropertyOf) where meaning,
domain and range agree, and links it with skos:closeMatch where they do not. FaBiO
(with FRBR) and FOAF are imported from local copies so the reasoner checks them.
**Alternative.** Use FaBiO and CiTO terms directly in the data; or SemOpenAlex.
**Why.** FaBiO, CiTO and PRO are the published vocabularies for works, citations and
authorship roles. Using their terms in the data would rewrite the mapping and its test
for no gain in meaning. FaBiO places datasets, reports, reviews and errata at the FRBR
Work level, while an OpenAlex work is an Expression, and FRBR makes the two disjoint:
subClassOf there would make our classes unsatisfiable. Three ranges disagree with our
data (fabio:hasPublicationYear is xsd:gYear, dcterms:language is not text, foaf:name is
not for topics). We found no licence for SemOpenAlex's ontology.
**Evidence.** ontology/LICENCES.md; definitions read in FaBiO 2.3.1, FRBR 1.1.0,
CiTO 2.9.0, PRO 1.6.1.

## D8. Declare OWL 2 DL; check with ELK and HermiT through ROBOT (2026-10-18)
**Decision.** ontology.ttl is written for OWL 2 DL and checked by two reasoners, ELK
(fast) and HermiT (complete), through ROBOT 1.9.10 in a Docker service run on demand:
docker compose --profile tools run --rm reasoner. The run is saved in
ontology/reasoner-run.txt.
**Alternative.** OWL 2 EL only (drop the boolean and date ranges), or checking by hand
in Protégé.
**Why.** Our file is OWL 2 DL; it would be EL but for its xsd:boolean and xsd:date
ranges, which say what the values are and are worth keeping. HermiT reads every
axiom, while ELK alone misses axioms outside EL (Session 3, slide 39). A scripted run
can be repeated by anyone from a clean checkout; a Protégé session cannot.
**Evidence.** ontology/reasoner-run.txt: both reasoners consistent, no unsatisfiable
class; our file passes the OWL 2 DL check; the 976 violations with the imports come
from FaBiO's own Dublin Core declarations. With pub:Dataset rdfs:subClassOf
fabio:Dataset both reasoners found pub:Dataset unsatisfiable (step 3.5), which is why
D7 links it with skos:closeMatch instead.   

## D9. Validate the whole graph; the severity says what the pipeline does (2026-10-19)
**Decision.** The SHACL gate checks the whole graph (578,982 triples and the
ontology), in CI and in the stack, against shapes/shapes.ttl. A Violation, or a
shape with 0 focus nodes, stops the pipeline before the endpoint is loaded. A
rule that is right but broken by known problems of the source is a Warning,
with a TRIAGE comment that says why and until when; a coverage figure is Info.
**Alternative.** Validate a small sample in CI (the course lab: seconds, not
minutes); or keep every broken rule a Violation until the source is fixed.
**Why.** A sample can miss the one bad row, and the whole graph takes about two
minutes on a laptop, which CI affords. Known problems kept as Violations would
keep the gate red forever, and a gate that is always red is ignored. A shape
that targets nothing passes forever: the template's order shape did, on our
graph, from Session 2 to Session 4. So the gate counts focus nodes first.
**Evidence.** shapes/triage.md: first draft 3,636 Violations; after triage 0
Violations, 2,585 Warnings, 1,070 Info. The cost: a Warning does not stop a new
case of a known problem (a 21st shared ORCID); the counts in
shapes/validation-report.txt show it.

## D10. One named graph per source; provenance of every run in PROV-O (2026-10-19)
**Decision.** The pipeline empties the endpoint (DROP ALL), then loads the mapped
OpenAlex data into the named graph https://ul.edu.lb/kr/graph/openalex, the
ontology into .../graph/ontology and the run's provenance into
.../graph/provenance. Fuseki's default graph is the union of the named graphs
(fuseki/config.ttl), so a query without GRAPH sees everything, as before. On every
run that passes the gate, pipeline/provenance.py writes in PROV-O: the OpenAlex
download (2026-10-16), data/lu.sql and its checksum, the mapping, the ontology by
its version IRI (1.0.0), the shapes, the programs and their versions, and the start
and end of the run.
**Alternative.** Everything in the default graph (Sessions 2 and 3); or one named
graph per table (the course lab).
**Why.** Provenance is recorded per graph: 51 triples describe 578,982. In the
default graph nothing says which source a triple came from. Session 5 adds Crossref
as a second graph and Session 6 predicted links as a third; a triple's graph then
says who said it. Our questions cross tables (a paper, its authors, their
institutions), and what we must trace is the source, not the table. DROP ALL first,
so no graph from an older run or a manual upload stays behind. Checksums read
Windows line endings as Unix ones, so a laptop and CI give the same value.
**Evidence.** pipeline/where_from.rq: the title of W3023054831 is in graph/openalex,
derived from data/lu.sql (its sha256), from the 2026-10-16 download, made by one run
(its end time; pipeline/run.py, Morph-KGC 2.10.0, pySHACL 0.40.1).


## D11. Crossref as the second source, frozen like OpenAlex (2026-10-19)
**Decision.** The second source is Crossref: the record of each of our 5,055 distinct
DOIs, downloaded once (data/fetch_crossref.py) and frozen as data/crossref.sql, 4 tables
(data/build_crossref.py), as D4 did for OpenAlex. We keep only what we use, and no
abstracts.
**Alternative.** ORCID (people only); DataCite (only our 169 DOIs that are not in
Crossref); Semantic Scholar (another aggregator, partly built from the same sources).
**Why.** Crossref is where publishers register most DOIs, so it does not depend on
OpenAlex's own processing, and the DOI is a key both sources share. Per paper it gives
the authors in printed order, some with an ORCID, the references, the venue, and the
notices (retractions, corrections): what the Session 4 Warnings need. Frozen, so the
graph, the matcher and their numbers rebuild from a clean checkout without the network.
**Evidence.** data/profile/build_crossref.txt: 4,886 of 5,055 DOIs found; 35,468 authors,
8,647 with an ORCID; 149,936 references with a DOI; 63 notices. The 169 not found are
registered elsewhere, mostly with DataCite: 112 Zenodo, 26 arXiv, 7 figshare, 24 others.

## D12. A person known only by an ORCID gets an IRI of its own (2026-10-19)
**Decision.** An authorship that OpenAlex gave no author ID, but an ORCID, is linked
to the person with that ORCID: the OpenAlex author record that carries it (158
authorships), or else a person named by the ORCID itself,
https://ul.edu.lb/kr/id/author/orcid/{ORCID} (153 authorships, 123 people). D5 said: a
person only from an OpenAlex ID. This adds a second identifier, one that names one
person.
**Alternative.** Keep D5 as it was (2,101 authorships without a person); or also match
the other 1,790 to people by name.
**Why.** ORCID gives one identifier to one person, to name that person across systems:
it is a key, so linking by it needs no guessing. The IRI follows D3: kind author,
source orcid, key the ORCID. A name is not a key: two people can share one, and one
person writes theirs in several ways (part 2 of mapping/er/README.md), so the 1,790
keep their name as listed (D5) and no person.
**Evidence.** mapping/er/link_by_key.txt.

## D13. Keep an author link from a score of 4 (2026-10-19)
**Decision.** mapping/er/match_authorships.py keeps a link between an OpenAlex
authorship and a Crossref author when its score is 4 or more: 30,848 links.
**Alternative.** A threshold of 8 (30,697 links); or a rule that refuses every link
whose first initials differ.
**Why.** On the 3,681 Crossref authors of half B whose true match is known by ORCID,
4 and 8 have the same precision, 0.9997, and 4 finds more: recall 0.9995 against
0.9957. The 151 links between 4 and 8 are mostly a byline in another order in Crossref
(W4399056955: initials, positions one or two places apart). A person checked 20 of
them: 19 are the same person (the wrong one: Bilal Alhayani and Bilal Öztürk). The one
miss left on half B is an author OpenAlex does not have: Crossref's author 121 of
W4382465100, past the 100-author cap. The weakness we keep, with its size: when the
family name and the position agree, a different first initial does not cancel the
link (28 links, most with a score of 9.1), and 2 of the 4 checked are two people (Tatiana and Fadi
Abou-Mrad; Y. Satou and H. Sato). Refusing all of them would also drop right ones
(Filippos and Phil Aravanopoulos).
**Evidence.** mapping/er/match_authorships.txt; mapping/er/hand_sample.csv.

## D14. Crossref in a named graph of its own, checked by its own shapes (2026-10-19)
**Decision.** mapping/crossref.ttl maps data/crossref.sql into graph/crossref, with the
same pub: words and the IRI scheme of D3 (.../work/crossref/{DOI}, a person by ORCID as
in D12), checked against shapes/crossref-shapes.ttl, with its own provenance (the
Crossref download of 2026-10-19, data/crossref.sql and its checksum). Ontology 1.1.0
adds three words: pub:updates (a notice and the paper it updates), pub:venueName and
pub:issn. The venue stays two values of the record, not a node. Crossref's types get no
class, except its notices: a retraction is a pub:Retraction; a correction, erratum or
corrigendum a pub:Erratum. The default graph is now the union of two sources, so every
competency question names its graph (FROM).
**Alternative.** Crossref's triples in graph/openalex, checked by shapes.ttl; a venue
node per ISSN; Crossref's types mapped to our 20 classes.
**Why.** In its own graph a triple says which source said it (D10), and the two records
of a paper stay two nodes until a checked link joins them (D3). The OpenAlex rules do
not hold for Crossref: a record may list no author or 1,512, have a year outside
2022-2025, and has no open-access flag. Crossref gives no venue identifier, and the
ISSNs it lists for one journal change from record to record (Medicine: 0025-7974 and
1536-5964 on some records, 1536-5964 alone on others): a node per ISSN would split one
journal, a node per name would merge two. Crossref's journal-article covers OpenAlex's
article, review, editorial and letter: as a class it would contradict ours where it is
only coarser. Without FROM, a count of papers on the default graph counts each paper
twice, once per source.
**Evidence.** shapes/crossref-validation-report.txt: 0 Violations, 73 Warnings, 28,182
Info. ontology/cq_answers.txt, CQ10, on the 4,887 pairs of an OpenAlex paper and the
Crossref record of its DOI: the same title for 4,882, the same year for 4,697, the same
venue (by ISSN or by name) for 4,175; cq08_sources: of the 6 papers OpenAlex flags as
retracted, Crossref has a notice retracting 2 and says 2 others are retraction notices
themselves. ontology/reasoner-run.txt (1.1.0): consistent, no unsatisfiable class.


## D15. Links as owl:sameAs in two named graphs: by key, and by the matcher (2026-10-19)
**Decision.** The links of mapping/er enter the graph through two mappings, each into
a named graph of its own. graph/links holds the links by key (mapping/links.ttl):
owl:sameAs for 4,887 papers, the 2 pairs of OpenAlex records of one paper, the 20
pairs of author records of one person and 3,827 author records to the Crossref person
of their ORCID; and pub:author for the 311 authorships OpenAlex left without a person
(D12). graph/matches holds the matcher's 30,848 links (mapping/matches.ttl), owl:sameAs
between an OpenAlex authorship and a Crossref author. The records are never merged:
each stays a node in its source's graph, and a link is written from OpenAlex to
Crossref. Each link graph has its own shapes, which also see the triples of the
graphs it joins: both ends exist and are of one kind; a match is one to one, on one
paper, and the two sources give the matched person the same ORCID.
**Alternative.** Merge the two records of a paper into one node; put all links in one
graph; or skos:exactMatch, or a node per link with its score, instead of owl:sameAs.
**Why.** Merged, a triple no longer says which source said it (D10), and a wrong link
cannot be undone without rebuilding the sources. In two graphs the certainty of a link
is said once, in the provenance of its graph: by key, no guessing; by the matcher,
guessed, with its precision and recall in match_authorships.txt. So a query chooses:
graph/links only when it must not guess, graph/matches too when a measured precision
of 0.9997 is enough (cq09 shows both). owl:sameAs is the standard word for "the same
thing"; no reasoner runs on the data, so it merges nothing. A score per link would
need a node per link; it stays in the CSV, the graph's evidence.
**Evidence.** mapping/er/link_by_key.txt; shapes/links-validation-report.txt: 0
results; shapes/matches-validation-report.txt: 0 Violations, 60 Warnings: 8 for the 8
authors of a paper OpenAlex has twice, 52 for matched people whose ORCIDs differ
between the sources, most with the same name (listed in match_authorships.txt).
ontology/cq_answers.txt: cq09, of 2,101 authorships with no person, 1,790 are left
after the links by ORCID, the matcher links 1,449 of those, and Crossref names 1 of
them by an ORCID; cq06_sources, Crossref confirms 4 of the 75 self-citations.
