# Technical report: a knowledge graph of Lebanese University's publications

Karam Jammal · Knowledge Representation, MSc, Lebanese University, 2026 ·
repository karam294/krr-lu-publication · October 2026

The system describes what Lebanese University (LU) published from 2022 to
2025, as OpenAlex records it: 5,211 papers, their 33,084 authorships, the
institutions and venues around them, checked against Crossref as a second
source. It says what its data means (an OWL ontology aligned with FaBiO and
FOAF), refuses data that breaks its rules (a SHACL gate before every load),
learns honestly (models trained on earlier years and tested on a later one,
against counts that beat them), and answers questions in English with a
checked SPARQL query, or says it cannot. This report documents what is
deployed. Every number it quotes is in a file of the repository, named next
to it; the decisions D1 to D21 are in `report/decisions.md`.

## 1. Problem framing and scope

**The questions.** LU's research office (R), a researcher or a dean (D) and
this project (P) ask ten competency questions, written before the ontology
(`ontology/competency_questions.md`). Each is a SPARQL file in `ontology/cq/`,
and `ontology/run_cqs.py` writes their answers to `ontology/cq_answers.txt`,
so each question is measurable: it has an answer, and anyone can rerun it.

| # | Asked by | The question, shortly | The answer on our graph (cq_answers.txt) |
|---|---|---|---|
| CQ1 | R | papers per year, by type, open access | 1,272 papers in 2022 to 1,431 in 2025; open access 898 to 1,102 |
| CQ2 | D | who publishes most; first, last, corresponding | Pascale Salameh, 283 papers, 109 as last author |
| CQ3 | R | co-authoring countries and institutions | CNRS (FR) on 659 papers, then the Lebanese American University, 495 |
| CQ4 | R | where LU publishes | 2,028 journals carry 4,085 papers; 103 conferences, 212 |
| CQ5 | R | fields and domains, by year | Health Sciences leads every year, 436 papers in 2022, 543 in 2025 |
| CQ6 | D | LU papers citing LU papers | 2,116 citations; the most cited paper, 22 times |
| CQ7 | R | languages | English 4,748, French 114, Arabic 88 |
| CQ8 | R | retractions | 6 flagged by OpenAlex; Crossref has a notice retracting 2, and says 2 others are notices themselves |
| CQ9 | P | authorships with no person; shared ORCIDs | 2,101, then 1,790 after the ORCID links, 1,449 of them matched |
| CQ10 | P | does Crossref agree on title, year, venue? | same title for 4,882 of 4,887 pairs, same year for 4,697 |

The same graph serves two more users: the access layer, which turns a
question in English into one query (section 7), and the learning layer, which
predicts a paper's research field and new co-authorships (section 6).

**Scope.** Papers whose OpenAlex record has an LU affiliation (institution
I160368002) and a publication year from 2022 to 2025, downloaded on
2026-10-16; and, for the 5,055 distinct DOIs among them, their Crossref
records, downloaded on 2026-10-19. Both are frozen in the repository as SQL
(D4, D11), so a clean checkout grades the dataset this report describes.

**Left out, and why.**

- *OpenAlex's xpac records* (repository copies, DataCite datasets): OpenAlex
  calls them lower quality; they would add near-duplicates. With them, 2024
  has 1,398 papers instead of 1,288 (D1).
- *Abstracts*: the one part of Crossref's metadata that may be under
  copyright (`ontology/LICENCES.md`); no question needs them.
- *Citation counts, funding, contact details, nationality, students*: no
  source we use holds them. The access layer refuses such questions (section 7).
- *Facts that change over time*: an author's affiliation is the one printed
  on each paper (an authorship), never a fact about the person.

## 2. Data understanding and constraint discovery

**The sources.** OpenAlex is an open index of scholarly works, under CC0. Its
API gave 5,211 papers, which `data/build_table.py` cut into 8 tables and
`data/build_database.py` froze as `data/lu.sql` (21.7 MB, D4). Crossref is
where publishers register DOIs; it found 4,886 of our 5,055 DOIs, and the 169
others are registered elsewhere, mostly DataCite (112 Zenodo, 26 arXiv,
`data/profile/build_crossref.txt`). Crossref states that almost none of its
metadata is subject to copyright, except some abstracts, which we do not keep.

**What one row means** (`data/README.md`). The grain decides the graph: an
authorship is one author on one paper, so it becomes a node of its own
(pub:Authorship), which carries what is true only on that paper: the
position in the byline, the name as printed, the affiliations given.

| Table | One row is | Rows |
|---|---|---:|
| works | one paper | 5,211 |
| authorships | one author on one paper | 33,084 |
| affiliations | one institution of one authorship | 51,737 |
| authors | one OpenAlex author | 14,090 |
| institutions, sources, topics | one institution, venue, topic | 3,656, 2,216, 1,610 |
| citations | one paper citing another | 175,896 |
| Crossref: cr_works, cr_authors, cr_references, cr_updates | one record, author, reference, notice | 5,055, 35,468, 149,936, 63 |

**What the profile showed** (`data/profile/profile_tables.txt`). Names are not
keys: 14,090 authors carry 13,955 distinct names. DOIs and ORCIDs almost are:
5,057 DOIs, 5,055 distinct; 9,081 author records with an ORCID, 9,061
distinct. So every thing is named by its source's own key, never by a name or
a DOI (D3): `https://ul.edu.lb/kr/id/{kind}/{source}/{key}`.

**The constraint inventory** (`data/constraint_inventory.csv`): ten rules, each
with its evidence in the data. Eight are false in the data, and are reported,
not dropped; section 4 says what the shapes do with each.

| Rule | Evidence | Holds? |
|---|---|---|
| Exactly one author labelled first, at order 1 | 0 exceptions in 5,211 | yes |
| At most 100 authors per paper | 19 papers at exactly 100, the OpenAlex cap | yes, but the cap cuts bylines |
| Every LU paper lists an LU author | 6 do not: all 6 list 100 authors, the LU one was cut | no |
| A DOI identifies one paper | 2 DOIs each on two records of the same paper | no |
| An ORCID identifies one author record | 20 ORCIDs on two records | no |
| Every authorship has an author ID | 2,101 of 33,084 have none (6.4%) | no |
| Every paper has a topic, a venue, a DOI | 12, 214 and 154 have none | no |
| Every paper's reference list is recorded | 1,051 have none (20%) | no |

## 3. Ontology

**What is reused, and why.** The ontology (`ontology/ontology.ttl`, 26
classes, 7 object and 23 datatype properties of our own, pub:) is aligned with
the SPAR ontologies, the published vocabularies for bibliographic works:
FaBiO 2.3.1 with FRBR 1.1.0, CiTO 2.9.0 and PRO 1.6.1, and with FOAF and
Dublin Core (D7). FaBiO and FOAF are imported from local copies
(`ontology/imports/`, found through `catalog-v001.xml`), so the reasoner checks
our axioms together with theirs. The data keeps its pub: words: using FaBiO's
terms in the data would rewrite the mapping and its test for no gain in
meaning, and the alignment says the same thing once, in the ontology.

**The alignment outward**, one rule: a pub: term goes under a published one
(rdfs:subClassOf, rdfs:subPropertyOf) only where meaning, domain and range
agree, and is linked by skos:closeMatch where they do not.

| Ours | Relation | Published |
|---|---|---|
| pub:Work, and its 20 kinds (Article, Review, ConferencePaper, Preprint, ...) | subClassOf | fabio:Expression; fabio:Article, fabio:ReviewArticle, fabio:ConferencePaper, fabio:Preprint, ... |
| pub:Author, pub:Institution | subClassOf | foaf:Person, foaf:Organization |
| pub:Authorship; pub:hasAuthorship, pub:author, pub:affiliation | subClassOf; subPropertyOf | pro:RoleInTime; pro:isDocumentContextFor, pro:isHeldBy, pro:relatesToOrganization |
| pub:cites, pub:title, pub:hasTopic | subPropertyOf | cito:cites, dcterms:title, fabio:hasSubjectTerm |
| pub:Dataset, pub:Report, pub:Erratum, pub:PeerReview, pub:BookReview | closeMatch | fabio:Dataset, fabio:Report, fabio:Erratum, fabio:Review, fabio:BookReview |
| pub:publicationYear, pub:language, pub:name | closeMatch | fabio:hasPublicationYear (an xsd:gYear), dcterms:language (not text), foaf:name (not for topics) |

The closeMatch rows are decisions, not gaps. FaBiO places datasets, reports,
reviews and errata at FRBR's Work level, while an OpenAlex work is an
Expression, and FRBR makes the two disjoint. We first wrote
`pub:Dataset rdfs:subClassOf fabio:Dataset`: both reasoners found pub:Dataset
unsatisfiable (D8), so it became a closeMatch. pub:Venue has no superclass:
FaBiO splits venues by kind, OpenAlex gives one source with a type.

![The class hierarchy in Protégé, with FaBiO and FRBR imported: our pub:Work and its 20 kinds of paper (in bold, the classes of our file) among FaBiO's other kinds of expression (plain)](figures/protege-classes.png)

**Every term answers a competency question.** Each class and property carries
pub:answersCQ, and `ontology/competency_questions.md` lists the question of
every term; a term with no question is deleted. pub:Authorship exists for CQ2
(first, last, corresponding author are facts of one paper, not of a person)
and CQ3 (the affiliation given on that paper).

**The profile and the reasoner run** (D8, `ontology/reasoner-run.txt`). Our
file is OWL 2 DL; it would be OWL 2 EL but for its xsd:boolean and xsd:date
ranges, which say what the values are and are kept. ROBOT 1.9.10 runs ELK
(fast, EL only) and HermiT (complete), in a container run on demand
(`docker compose --profile tools run --rm reasoner`): both find the ontology
consistent, with no unsatisfiable class. Our own file passes ROBOT's OWL 2 DL
check; with the imports, 976 violations remain, 4 on Dublin Core terms our file
uses and FaBiO declares another way, the rest inside FaBiO itself.


**The version.** The ontology IRI is `https://ul.edu.lb/kr/pub`; its version
IRI `https://ul.edu.lb/kr/pub/1.1.0`, with owl:priorVersion 1.0.0. Version
1.1.0 added three words for Crossref (pub:updates, pub:venueName, pub:issn,
D14). A new word is a minor version, a word removed or changed in meaning a
major one (`ontology/README.md`). Each pipeline run records the version it
loaded (section 8).

**What stays out of OWL.** Domains and ranges add types; they do not reject
data. Rules about what the data must contain are shapes (section 4).

## 4. Constraint validation with SHACL

**One rule: data in SHACL, meaning in OWL.** OWL reasons in an open world: a
missing DOI is unknown, never an error, and a "max one" makes the reasoner
conclude that two papers with one DOI are one paper, silently. SHACL checks
the graph we have and lists the nodes to fix. So each rule of the inventory is
a shape (`shapes/README.md` gives the reason rule by rule):

| Rule | Shape | Severity | Why SHACL, not OWL |
|---|---|---|---|
| One first author, at order 1 | PaperShape, qualified value shapes | Violation | a count of authorships with a value; OWL's qualified cardinality never reports a paper with none |
| An LU author, unless the byline is cut at 100 | LUAuthorShape, sh:or, a path of two steps | Violation; Warning for the 6 | OWL's "at least one" is satisfied by an unknown author |
| A DOI, an ORCID identifies one record | `^pub:doi`, `^pub:orcid` max 1 | Warning | owl:hasKey would merge the two records and say nothing |
| A topic, a venue, a DOI, an author ID | min 1 | Warning | missing is unknown to OWL |
| A paper does not cite itself | SPARQL constraint | Warning | an irreflexive property would make the whole graph inconsistent over 75 errors |
| The last author has the highest order | SPARQL constraint | Violation | compares a node with other nodes |
| One class of the 20; year 2022 to 2025; booleans, value lists, IRIs of our scheme | core | Violation | checks of values; an OWL range only adds a type |

The shapes use the ontology's rdfs:subClassOf, so `sh:targetClass pub:Work`
checks all 20 kinds of paper: the two layers read the same graph.

**Triage** (`shapes/triage.md`). The first draft (`shapes/shapes-v0.ttl`) made
every rule a Violation and gave 3,636 Violations on the whole graph. Each group
got one question, *is the rule wrong, or the data?*, and one of three
decisions: change the rule; fix the source; or accept for now, as a Warning
whose TRIAGE comment in `shapes.ttl` says why and until when. No rule was
deleted to make the report green.

| Results | Rule | Rule or data? | Now |
|---:|---|---|---|
| 2,101 | an authorship has an author ID | the source is incomplete; Session 5 links 311 by ORCID | Warning |
| 1,051 | a reference list is recorded | wrong for errata and peer reviews, incomplete for the rest | Info |
| 214, 154, 12 | a venue, a DOI, a topic | the source is incomplete | Warning |
| 75 | no self-citation | wrong at the source: Crossref confirms 4 (cq06_sources) | Warning |
| 20, 2 | one record per ORCID, per DOI | wrong at the source; linked as one in graph/links | Warning |
| 6 | an LU author | **the rule was wrong**: it ignored the cap of 100 | new rule, a Violation |
| 1 | a retraction notice is not retracted | wrong at the source (W4415060141) | Warning |

After triage the OpenAlex graph gives **0 Violations, 2,585 Warnings, 1,070
Info** (`shapes/validation-report.txt`). The other three graphs have shapes
of their own, because the OpenAlex rules do not hold for them (a Crossref
record may list 1,512 authors and has no open-access flag): Crossref 0
Violations, 780 Warnings, 28,182 Info; the links by key 0 results; the
matcher's links 0 Violations, 60 Warnings (D14, D15). The severity says what
the pipeline does: a Violation stops it, a Warning is a known problem of the
source, an Info a coverage figure.

**The gate.** `pipeline/run.py` validates every graph whole, 578,982 triples
for OpenAlex, with the ontology, not a sample, which could miss the one bad row
(D9). It stops before the endpoint on any Violation, and on any shape with 0
focus nodes: a shape that targets nothing passes forever, as the template's
order shape did on our graph from Session 2 to Session 4. The same steps run on
GitHub Actions on every push and pull request (`.github/workflows/shacl-gate.yml`),
with the mapping's test (section 5). **The red run it blocked**: pull request
#N (branch `demo/red-gate`) changes one value of `data/lu.sql`, the year of
paper W3023054831, from 2022 to 2030, as a bad row from a new download would.
The gate finds exactly 1 Violation ("Every paper · MaxInclusive on
publicationYear: a paper has one publication year, from 2022 to 2025"), the run
fails, and the pull request was closed without merging. Run locally, the same
change stops the pipeline at step 3: "SHACL gate: graph/openalex: 1 Violation.
The endpoint is not loaded."

**What it cost, and what it does not check.** pySHACL runs a SPARQL rule once
per focus node: the last-author rule took 330 s of a 395 s run, until the
constant "last" moved into the FILTER (118 s, the same answer). Not checked,
on purpose: a wrong language code (9 papers in `lv`) is well formed; a paper
citing a later paper is normal with online-first; 98 institutions have no
country and no question needs one. The cost of a Warning: a 21st shared ORCID
would not stop the gate; the report's counts show it.

## 5. Operational data integration

**The mapping.** Four R2RML mappings, one per named graph: `mapping/mapping.ttl`
(OpenAlex, 578,982 triples), `crossref.ttl` (341,926), `links.ttl` (9,293) and
`matches.ttl` (30,848), run by Morph-KGC 2.10.0. One paper, W3023054831, was
written by hand first (`mapping/one_paper_by_hand.ttl`, 81 triples);
`mapping/check_one_paper.py` checks, in CI, that the mapping makes every one of
them. The two sources keep their own nodes: an OpenAlex paper is
`.../work/openalex/W...`, its Crossref record `.../work/crossref/{DOI}`, and they
become one paper only through a link, after checking (D3).

**Materialized or virtualized** (D16, `mapping/ontop/compare-routes.txt`). The
same four mappings also run virtualized: Ontop 5.5.0 answers SPARQL from the
tables in PostgreSQL, and `compare_routes.py` asks both routes every
competency question.

| | Materialized (deployed): Morph-KGC, SHACL, Fuseki | Virtualized: Ontop over PostgreSQL |
|---|---|---|
| Freshness | a change is visible after the next pipeline run (the last took 5 min 8 s) | at the next query, with no check first |
| Latency | seconds, on every question | seconds, on the 12 it answers |
| Workload | all 16 queries | 12 of 16: an EXISTS form and three queries of CQ10 fail |
| The graph | 961,049 triples | 961,049; 707 differ only by the encoding of a non-ASCII DOI |

The deployed system materializes. Freshness does not argue for Ontop: our
sources are frozen downloads (D4, D11), and a change Ontop showed at once
would have passed no SHACL gate, which needs a stored graph. Latency does not
decide. The workload decides: the access layer sends queries a model writes,
which may use the property paths (`*`, `+`) Ontop does not support, and the
learning layer reads the whole graph. The comparison still paid: the 707 triples were reference DOIs
with a typographic hyphen, which no shape had seen (now a Warning), and one
view needed a name to run on both engines.

**Entity resolution** (`mapping/er/README.md`). Part 1 links records that share
a key, with no guessing (`link_by_key.txt`): 4,887 OpenAlex papers to the
Crossref record of their DOI; the 2 pairs of OpenAlex records of one paper and
the 20 of one person; 311 authorships with no author ID, by their ORCID (D12);
and 3,827 author records to the Crossref person of their ORCID. Part 2 matches
authors, who share no key. It follows Fellegi and Sunter: blocking on the paper
(962,298 pairs), three compared fields (the name, the first initial, the
position in the byline), weights log2(m/u) with m and u *counted* on half A of
the papers, on the pairs whose two sides carry an ORCID, which is never a field
of the matcher; then one to one per paper, kept from a score of 4 (D13).

| Measured on half B: 3,681 Crossref authors whose true match is known by ORCID | Precision | Recall |
|---|---:|---:|
| threshold 4 (deployed), 30,848 links on all papers | 0.9997 | 0.9995 |
| threshold 8 | 0.9997 | 0.9957 |
| position only | 0.9910 | 0.9908 |

The ORCID labels exist only where both sources have an ORCID, the easy cases,
so a person also checked 40 links without one (`hand_sample.csv`): 19 of the
20 links scored 4 to 8 are the same person, and 17 of 19 above 8 whose names
are not plainly equal. The weakness kept, with its size: when the family name
and the position agree, a different first initial does not cancel a link (28
links; 2 of the 4 checked are two people). The matcher's shapes flag the 52
links whose two sources give the person two different ORCIDs.

**The links in the graph** (D15). Links are owl:sameAs in two named graphs,
graph/links (by key) and graph/matches (guessed, with a measured precision);
the records are never merged, so a triple still says which source said it,
and a wrong link is removed without touching a source. A query chooses how
sure it must be: CQ9 counts with both. What integration found: Crossref
confirms 4 of the 75 self-citations, names a venue for 105 papers OpenAlex
gives none, and shows one "retracted article" to be itself a retraction notice
(W4308586991, cq08_sources).

## 6. Prediction and evaluation honesty

**The graph the models see** (`model/build_graph.py`,
`model/results/build-graph.txt`). Read from graph/openalex through SPARQL:
5,211 papers, 14,090 authors, 2,216 venues, 3,656 institutions; edges author
writes paper (30,904), paper publishedIn venue, paper cites paper (LU to LU,
2,116), paper withInstitution institution. A paper's features are what it is
on the day it is published: its kind, language, open access, number of
authors. The other nodes have none; the models learn a vector for each.

**Two tasks, both split by time** (D17, D18). Our papers have years, so every
model trains on the past and is tested on the future, twice: a validation
round (train 2022 to 2023, test 2024), where every setting is chosen, and a
test round (train 2022 to 2024, test 2025), run with those settings, the
result reported. The settings are chosen by the run itself (`--settings`) and
written on the last line of a results file that the models read: two
computers ranked them differently, and settings typed into the code would
disagree with their evidence.

- *Node classification: the field of a paper* (26 OpenAlex fields). The label
  is the field of the paper's topic, so the topic is taken out of the graph:
  no topic node, no hasTopic edge. Models: always the largest field; a
  logistic regression on the paper's own row; a count of its authors' earlier
  fields; GraphSAGE (PyTorch Geometric, to_hetero), the best of 16 settings on
  2024, five seeds.
- *Link prediction: new co-authorships.* For each pair of authors who first
  write together in the test year, the partner is ranked, both ways, among all
  authors with a co-author before that year (about 9,100 candidates in 2025),
  filtered, with ties sharing the middle of their places: with a count,
  thousands of candidates tie at 0, and the right one's rank must not depend
  on the order of a list. Models: random, popularity, common neighbours,
  Adamic-Adar; and an embedding (PyKEEN) of the knowledge graph of the years
  before, DistMult of dimension 128, the best MRR of six on 2024, three seeds.

![The test round, 2025. A: the field of a paper. B: new co-authorships. Drawn by report/figures/make_figures.py from model/results/](figures/learning.png)

| 2025 | Score | Spread over seeds |
|---|---|---|
| field: the topic kept, a lookup (the leak) | accuracy 0.848; 1.000 on the 78% whose topic it has seen | |
| field: the paper's row (logistic regression) | accuracy 0.395, macro-F1 0.139 | |
| field: count of the authors' earlier fields | **accuracy 0.549**, macro-F1 0.350 | none: a count |
| field: GraphSAGE | accuracy 0.517, macro-F1 0.341 | 0.501 to 0.528; macro-F1 0.306 to 0.360 |
| co-authors: Adamic-Adar | **MRR 0.072**, Hits@10 0.169 | none |
| co-authors: DistMult | MRR 0.046, Hits@10 0.101 | MRR 0.046 for all three; Hits@10 0.100 to 0.103 |

**Why the split does not leak.** The test papers and pairs did not exist when
the model was trained; the label's source, the topic, is not in the graph;
nothing is tuned on 2025. The leak line shows what we avoided: kept, the topic
makes a lookup right on every paper whose topic it has seen.

**Both models lose to a count, and that is the result.** The graph matters:
the paper's own row gets 0.395, its neighbours 0.517 to 0.549, because 81% of
the 2025 papers share an author with an earlier paper and authors stay in
their field. But counting the authors' earlier fields, one step of label
propagation, beats GraphSAGE, which sees its neighbours' features but never
their labels: what Huang et al. (2021) found on standard benchmarks. For
co-authorships, Adamic-Adar beats the embedding on every score of 2025. Where
the counts are blind, on the half of the new pairs that share no earlier
co-author (MRR 0.000), popularity does best (0.017), not the embedding (0.006
to 0.007). On 2024 the embedding led only on Hits@100 (0.469 to 0.480 against
0.448). We report this rather than tune on 2025 until the models win.

**What the numbers do not show** (`model/README.md`). The label is itself a
model's output: OpenAlex assigns topics from a paper's title, abstract,
citations and journal name, so part of what the models learn is OpenAlex's rule.
Titles are left out, to measure what the graph adds. One test year is one
draw; on another computer the embeddings may move by up to 0.02 in MRR. The
predictions stay out of the knowledge graph: a guess no shape can check, which
a query on the default graph would count as a fact (D21).

## 7. Access layer

**Grounding.** Gemini (gemini-3.5-flash-lite, temperature 0) writes one SPARQL
query from a prompt the layer builds (`access-layer/access_layer.py`): the
rules (`prompt_rules.txt`: how our graph names things, when to refuse), the
schema, the three examples of `examples.ttl` (eight in all) whose questions
share the most words with the question, and the question. The schema is the
VoID description of graph/openalex (`build/void.ttl`, 1,251 triples, written by
the pipeline's step 5): which classes the graph has, how many of each, which
property links which class to which. The 20 kinds of paper share their
properties, so the prompt lists them once, as pub:Work: 36 lines.

**Check and repair.** The reply is parsed (rdflib) and its pub: words are
checked against the VoID; a class also counts when it is the superclass of
one the graph has (pub:Work).
On a problem, the problems go back to Gemini as a hint, listing the real
words, up to twice. The layer then writes the graphs the query may read, FROM
graph/openalex and graph/ontology (D19): asked of Fuseki's default graph, the
union of six, a count of 2024's papers is 2,543, because each paper also counts
through its Crossref record; with the FROM lines, 1,288, as CQ1. A rule could be
forgotten by the model; a FROM the layer writes cannot, and the query it returns
gives the same answer on any endpoint.

**The refusal.** Gemini replies `REFUSE: <what is missing>` when no class or
property holds the fact asked for, and the layer refuses too when no valid
query comes after two repairs. "What is the email address of Maha Hoteit?" is
refused with "email address": a plausible wrong number would be trusted; a
refusal says what the graph lacks.

**The test set and the score** (`questions.yaml`, `evaluate.py`,
`results/`). 14 questions with their right query and 4 to refuse (an h-index,
funding, an email, students), none of them an example. Each answer is the set
of values its query returns, compared with the right query's set (F1); a
refusal scores 0 where the graph can answer. Three settings: schema only; with
examples; with examples and the check and repair, which the stack runs. Model
gemini-3.5-flash-lite, run on 2026-10-20 on Fuseki.

| Mean F1 on 14 questions | before (`score-fixed.txt`, rules e6f4871f) | after (`score-after.txt`, rules 67d7c6d8) |
|---|---:|---:|
| schema | 0.929 | 0.913 |
| examples | 0.702 | 0.750 |
| examples and repair (deployed) | 0.702 | 0.750 |
| wrong refusals (deployed) | 3 | 0 |
| right refusals of 4 (schema; deployed) | 4; 4 | 3; 4 |

**One improvement, measured** (D20). The first score's largest loss: with
examples, Gemini refused three answerable questions (retractions, ORCIDs, a
title by DOI) with the reason the rule had given as an example of a missing
fact ("citation counts"). The new rule lists the facts the graph holds
instead. Before it, a bug of the template was fixed (`with_prefixes` declared
both of our prefixes or none, so a query that declared pub: but not rdfs: failed),
and the first answers were replayed with the fix (`score-fixed.txt`), so the two
scores differ by the rule alone. Its cost: in the schema setting the h-index
question is now answered, and two counts gained a filter "has an LU author",
wrong for the 6 papers whose byline is cut at 100. One run of 14 questions,
where one question moves the mean by about 0.07: kept, because the deployed
setting improves and refuses nothing it should answer.

**Repeatable without a key.** Every answer Gemini gave is in
`llm-cache.json`, keyed by the model and the exact prompt, so
`LLM_MODE=replay python evaluate.py` gives the same lines on Fuseki and on
`build/graph.nt`, from a clean checkout and without the network (section 8).

**What the check does not catch.** A valid query that answers another
question: the LU filter passes every check. And extra columns (a title next to
a count), which the set score counts against the answer. In the recorded runs
the repair loop answered one question after a repair, and that repair was
caused by the prefix bug (`score-before.txt`); after the fix, no test question
needed one.

**The page and the contract** (`serve.py`, `ui.html`). On
http://127.0.0.1:8000/ a question typed in English gets the answer (one value
in large type, or a table; OpenAlex things link to openalex.org), the query
that computed it, each try with its problems, and the model, the rules and
the time. The same server keeps the TEXT2SPARQL contract (`/?question=...&dataset=`),
returning the query with its FROM lines; a refusal comes back as a query that
returns nothing, the reason in a comment.

![The page refusing a question the graph cannot answer: OpenAlex records no author's nationality, and the reason says what is there instead (2026-10-20)](figures/page.png)

## 8. Deployment and reproducibility

**The stack** (`docker-compose.yml`). `docker compose up --build` builds and
starts three services: Fuseki 5.5.0 (TDB2, one dataset, its default graph the
union of the named graphs), the pipeline, which runs once, and the access
layer, which starts only when the pipeline has exited successfully. Three more
run on demand, from the same checkout, by a profile: the reasoner (`tools`),
the learning layer (`learning`), and PostgreSQL with Ontop (`virtual`). Every
port listens on 127.0.0.1 only; the Gemini key and the PostgreSQL password live
only in `.env`, which `.gitignore` and `.dockerignore` keep out of the
repository and the images. Versions are pinned: Python packages in the
requirements files, Fuseki, ROBOT and Ontop by version and checksum in their
Dockerfiles.

![The deployed system: the sources, the pipeline and its gate, the endpoint, the access layer; on demand, the reasoner, the models and the virtualized route](figures/architecture.png)

**The pipeline** (`pipeline/run.py`): (1) the sources into SQLite, (2) map
each graph, (3) the SHACL gate, (4) provenance, (5) the VoID, (6) empty the
endpoint (DROP ALL), then load six named graphs: openalex, crossref, links,
matches, ontology, provenance. Emptying first means no graph from an older run
or a manual upload stays behind.

**Provenance** (D10, `pipeline/provenance.py`). Every run that passes the gate
writes, in PROV-O, what it used and made: each graph with its size and its
gate result, the file it was derived from with its sha256 checksum, the
download behind that file (OpenAlex, 2026-10-16; Crossref, 2026-10-19), the
mappings, the shapes and the ontology by its version IRI (1.1.0), the programs
and their versions, and the start and end of the run (140 triples).
`pipeline/where_from.rq` follows a title back to its graph, file, download and
run.

**The clean-checkout test** (`report/clean-checkout.md`), on 2026-10-20 at
commit af4dfb5, twice: a fresh clone into an empty folder, a `.env` made from
`.env.example` with a key and nothing else, one command. With Docker Desktop on
Windows, as the instructor will run it: the pipeline maps the four graphs with
0 Violations and exits with code 0 after about 7 minutes, the access layer
comes up, and the page answers in English, live ("How many papers did Maha
Hoteit write?": 92, the right query's answer). Without Docker, as CI runs it:
the same pipeline lines in 6 min 54 s; the mapping's test passes; the ten
competency questions give the answers of `cq_answers.txt`; the access layer's
score, replayed without a key, is `score-after.txt` line for line. Neither run
changes a tracked file. What it surfaced: the README gave the Windows commands
for PowerShell only, and the test was started in Command Prompt, where
`Copy-Item` does not exist; the README now gives both. And the images built in
seconds only because Docker had them cached: on a computer without the cache,
the first build takes a few minutes more. Earlier tests surfaced what is now
fixed and written down: PostgreSQL keeps the password of its first start
(`mapping/README.md`); a port already taken by another container; `docker
compose logs` empty until Python printed unbuffered; and pySHACL's messages in
no fixed order, which made two reports of the same graph differ.

**Continuous integration.** The SHACL gate and the mapping's test on every
push (section 4).

## 9. Open problem: do published improvements hold in a fair test?

*Open problem 5 of Session 7: do reported gains in knowledge graph completion,
and in learning on graphs, still hold in a fair comparison?*

**Where it appears in our system.** Session 6 was this question on our own
data. A graph neural network and a knowledge graph embedding, the methods the
literature reports gains for, both lost to a count once the comparison was
fair: a split by time, settings chosen on a validation year only, and, for the
ranking, ties shared. The access layer met it again at a smaller scale:
a gain of 0.048 in mean F1 on 14 questions, where one question moves the mean
by about 0.07.

**What the literature found.** Kadlec, Bajgar and Kleindienst (2017)
reimplemented DistMult, a simple early embedding, tuned it, and found it
beat almost every model published on FB15k: gains credited to new
architectures came, at least partly, from tuning and training objectives.
Ruffinelli, Broscheit and Gemulla (ICLR 2020) trained the classic models
(RESCAL, TransE, DistMult, ComplEx, ConvE) with a modern training method and
a large search of its settings: the gaps between models shrank or reversed,
and RESCAL, the first, was competitive with the newest; the training method
and its settings mattered more than the model. Sun et al. (ACL 2020) found
that several recent models' high scores came from the evaluation itself: when
many candidates tie with the right answer, a protocol that ranks the right one
first among its ties gives ConvKB an MRR of 0.407 on FB15k-237 and CapsE 0.511;
placed at random among its ties, the right answer gives them 0.243 and 0.150.
They recommend the random protocol. Huang et al. (ICLR 2021) showed that on
standard node classification benchmarks a simple model plus label propagation
matches or beats graph neural networks, with far fewer parameters.

**What we did about it.** Each finding has a counterpart in our evaluation.
Against Kadlec and Ruffinelli: the settings of GraphSAGE and of the embedding
were searched (16 and 6), on 2024 only, and the choice is written by the run
and read by the models. Against Sun: our ranking gives the right partner the
middle place of its ties (1 + higher + ties/2, the expected rank under their
random protocol), which matters most for the counts, whose scores tie by the
thousands. Against Huang: the count of the authors' earlier fields is one step
of label propagation, and it is the strongest model we have. And one thing our
data needs that their benchmarks do not: a split by time, because in a
bibliography the past predicts the future, and a random split would let a
paper's co-authors of the same year teach the model its answer.

**What we could not do.** Our baselines are counts with nothing to tune, but
our models had a small search: 16 settings on two seeds, 6 embeddings on one,
where Ruffinelli's search was far larger, so a better-trained embedding might
still close the gap; we cannot rule it out. We have one test year; a fair
test would move the origin (test 2023, 2024, 2025, each trained on the years
before) and report the spread over years, not only over seeds. We give ranges
over seeds but no significance test, which would need the score of each query,
which we do not keep. And the access layer's score is one run on 14
questions; a second live run would show how much it moves by itself.

**Our position.** A published gain is a hypothesis about a comparison, and it
holds only for the comparison that made it. On a new graph, the question is
not which model is newest but which simple baseline it has to beat, under a
split that matches how the system will be used. For a research office asking
who will publish with whom, "authors who share co-authors" is a better
predictor than our embedding, costs nothing to train, and explains itself.
We would adopt a learned model only once it beats that count on more than one
test year, by more than the spread of its seeds.

## Licences

| Ontology, vocabulary or dataset | Licence | Where used |
|---|---|---|
| OpenAlex data, downloaded 2026-10-16 | CC0 | `data/lu.sql`, graph/openalex |
| Crossref metadata, downloaded 2026-10-19 | almost none under copyright, except some abstracts, which we keep none of (Crossref REST API documentation) | `data/crossref.sql`, graph/crossref |
| FaBiO 2.3.1 (SPAR) | CC BY 4.0 | imported, local copy |
| FRBR core 1.1.0 (SPAR) | CC BY 4.0 | imported through FaBiO |
| FOAF (SPAR's copy) | CC BY 1.0 | imported, local copy |
| CiTO 2.9.0, PRO 1.6.1 (SPAR) | CC BY 4.0 | referenced (cito:cites, pro:RoleInTime) |
| DCMI Metadata Terms | CC BY 4.0 | referenced (dcterms:title) |
| SKOS, OWL 2, RDF Schema, SHACL, R2RML, PROV-O, VoID (W3C) | W3C Software and Document License | the ontology, the shapes, the mappings, the provenance and the VoID |

`ontology/LICENCES.md` gives the versions and how each is used.

## References

- Fellegi, I. P. and Sunter, A. B. (1969). A theory for record linkage. *Journal of the American Statistical Association*, 64(328).
- Huang, Q., He, H., Singh, A., Lim, S.-N. and Benson, A. R. (2021). Combining label propagation and simple models out-performs graph neural networks. *ICLR 2021*.
- Kadlec, R., Bajgar, O. and Kleindienst, J. (2017). Knowledge base completion: baselines strike back. *Proceedings of the 2nd Workshop on Representation Learning for NLP*, ACL.
- Ruffinelli, D., Broscheit, S. and Gemulla, R. (2020). You CAN teach an old dog new tricks! On training knowledge graph embeddings. *ICLR 2020*.
- Sun, Z., Vashishth, S., Sanyal, S., Talukdar, P. and Yang, Y. (2020). A re-evaluation of knowledge graph completion methods. *ACL 2020*.
- Peroni, S. and Shotton, D. (2012). FaBiO and CiTO: ontologies for describing bibliographic resources and citations. *Journal of Web Semantics*, 17.
- W3C (2012). R2RML: RDB to RDF Mapping Language. W3C (2017). Shapes Constraint Language (SHACL). W3C (2013). PROV-O: The PROV Ontology. W3C (2011). Describing Linked Datasets with the VoID Vocabulary.
