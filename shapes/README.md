# shapes/

The rules our graphs must obey, checked with SHACL before anything reaches
the endpoint (Session 4). Each graph has its own shapes (D14, D15): the OpenAlex
graph `shapes.ttl`, the Crossref graph `crossref-shapes.ttl`, the links by key
`links-shapes.ttl`, the matcher's links `matches-shapes.ttl`. The link shapes
see the triples of the graphs a link joins, as the pipeline gives them.

| File | What it is |
|---|---|
| `shapes.ttl` | the shapes of the OpenAlex graph, version 1.0.1 (after triage, with the Session 5 evidence); every changed rule has a TRIAGE comment |
| `validate.py` | runs the shapes and prints the report as a work queue; `pipeline/run.py` uses it as its gate |
| `triage.md` | the first report (3,636 Violations) and the decision for each group |
| `shapes-v0.ttl` | the first draft (0.1.0): every rule a Violation, kept as evidence |
| `validation-report-v0.txt` | the first draft's report: 3,636 Violations |
| `validation-report.txt` | the report after triage: 0 Violations, 2,585 Warnings, 1,070 Info |
| `crossref-shapes.ttl` | the shapes of the Crossref graph (Session 5), version 1.0.0, each rule not a Violation with its TRIAGE comment |
| `crossref-validation-report.txt` | its report: 0 Violations, 73 Warnings, 28,182 Info |
| `links-shapes.ttl`, `links-validation-report.txt` | the links by key: their two ends exist, of one kind; 0 results |
| `matches-shapes.ttl`, `matches-validation-report.txt` | the matcher's links: one to one, same paper, the same ORCID on both sides; 0 Violations, 60 Warnings |

Run it, from the repository root:

```sh
python pipeline/run.py --no-load        # map both sources, then the gate on each graph;
                                        # writes build/shacl-report.txt (both reports)
python shapes/validate.py               # the gate alone, on build/graph.nt (2 to 4 minutes)
python shapes/validate.py --shapes shapes/crossref-shapes.ttl --data build/crossref.nt --data ontology/ontology.ttl
                                        # the gate alone, on the Crossref graph
```

The link graphs are checked by the pipeline only, because their shapes need
some triples of the other graphs (pipeline/run.py, CONTEXT): their reports are
build/shacl-report-links.txt and build/shacl-report-matches.txt.

The gate fails (exit code 1) on any Violation, and on a shape with 0 focus
nodes: a shape that targets nothing checks nothing, and would pass forever.
Warnings and Info are reported and do not stop it.

## Severity: what each one makes the pipeline do

- **Violation**: a rule that holds on all our data today. The first row that
  breaks it is new and unknown: the gate stops, the endpoint is not loaded.
- **Warning**: a rule that is right, broken by data we know about and cannot
  fix today (the source). Its TRIAGE comment says why, and until when.
- **Info**: a coverage figure (no reference list, a byline cut at 100), not
  an error.

Our gate runs on the whole graph, in CI and in the stack, not on a sample.
So every known problem of the source has to be a Warning with an until-when,
or the gate would never pass (D9).

## Why SHACL and not OWL, rule by rule

OWL works in an open world: a missing value is unknown, not false, so a
reasoner never reports a missing DOI. A "max one" in OWL makes the reasoner
conclude that two values are the same thing (two papers with one DOI become
one paper) instead of listing them. SHACL works on the graph we have, closed
world, and gives the list of nodes to fix. So: rules about what the **data**
must contain are shapes; what follows from the **meaning** (Session 3) stays
in the ontology.

| Rule | Shape | Kind | Severity | Why SHACL, and not OWL |
|---|---|---|---|---|
| Exactly one author labelled first, at order 1 | PaperShape (qualified value shapes) | core | Violation | a count of authorships with a given value; OWL's qualified cardinality would never report a paper with none |
| An LU author, unless the byline is cut at 100 | LUAuthorShape (`sh:or`, path of two steps) | core | Violation, Warning for the 6 | "at least one" in OWL is satisfied by an unknown author; we need the list of papers without one |
| A DOI identifies one paper | DoiShape (`^doi`, max 1) | core | Warning | OWL 2 can state it (`owl:hasKey` on pub:doi), but the reasoner then concludes that the two papers are one, and says nothing; we want them listed |
| Every authorship has an author ID | AuthorshipShape | core | Warning | OWL: an unknown author exists. D5 keeps the name; the shape counts the gap |
| An ORCID identifies one author | OrcidShape (`^orcid`, max 1) | core | Warning | as for the DOI: `owl:hasKey` would merge the two records silently; merging is Session 5's job, done on purpose |
| At most 100 authors; exactly 100 is flagged | PaperShape | core | Violation, Info | a number of values; OWL cardinality cannot raise an Info |
| Every paper has a topic, a venue, a DOI | PaperShape (min 1) | core | Warning | open world: missing is unknown to OWL, never an error |
| Every paper's reference list is recorded | PaperShape (`cites` min 1) | core | Info | as above |
| A retraction notice is not retracted | RetractionNoticeShape | core | Warning | the "if" is the target class; OWL could make this an inconsistency, which stops the reasoner instead of listing one paper |
| A paper does not cite itself | NoSelfCitationShape | SPARQL | Warning | compares a value with the node itself: no core keyword does; OWL's irreflexive property would make the whole graph inconsistent over 75 errors |
| The last author has the highest order | LastAuthorShape | SPARQL | Violation | compares an authorship with the other authorships of the paper: other nodes |
| One class of the 20; year 2022 to 2025; a valid date; booleans; value lists; the IRIs of our scheme | Paper, Authorship, Author, Institution, Venue, Topic shapes | core | Violation | datatypes, ranges, patterns and lists are checks of values; OWL ranges only add types (Session 3: domain and range are not constraints) |

What stays in OWL: the class tree and the alignment with FaBiO, FOAF, PRO
and CiTO; domains and ranges (they add types, for queries); the disjointness
of a person and an organization, which the reasoner checks on the ontology
itself (Session 3). The shapes use the ontology's `rdfs:subClassOf`, so
`sh:targetClass pub:Work` checks all 20 kinds of paper: the two layers work
on the same graph.

## SPARQL only when no core keyword can say it

pySHACL runs a SPARQL rule once per focus node: 4,160 and 5,211 small
queries on the OpenAlex graph. Timed alone on the whole graph: the
self-citation rule 9 s, the last-author rule 118 s (330 s in the first draft,
see its TRIAGE comment), all the core shapes together about 60 s. So
everything core SHACL can state is core.

The Crossref shapes have three SPARQL rules (a record citing itself, a notice
updating itself, an ORCID on two authors of one record): 3,714, 61 and 4,450
queries. The last one is asked per person, not per record, because a record
can have 1,512 authors (triage.md, Session 5). The two SPARQL rules of the
matcher's links are asked per OpenAlex paper (5,211 each): pySHACL parses the
query again for each focus node, so fewer focus nodes is what makes them fast.
