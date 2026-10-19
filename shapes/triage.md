# Triage of the first SHACL report (Session 4)

The first draft of the shapes (version 0.1.0) turned every rule into a
Violation. On the real graph it gave **3,636 Violations**. Triage means going
through the report group by group and asking one question: **is the rule
wrong, or the data?** Then one of three decisions:

- **the rule is wrong**: change the rule;
- **the data is wrong**: fix the source and keep the rule;
- **we know about it and accept it for now**: lower the severity, and write
  until when.

No rule was deleted to make the report green. Every decision is also written
next to its rule in `shapes.ttl`, in an `rdfs:comment` that starts with TRIAGE.

## How we ran it

`python shapes/validate.py --shapes <file>` on `build/graph.nt` (578,982
triples) plus `ontology/ontology.ttl`: 579,317 triples, pySHACL 0.40.1, no
inference. Every shape checks something (focus nodes, before anything else):

| Shape | Focus nodes |
|---|---:|
| Every paper (and: has an LU author, with a last author) | 5,211 |
| Every citing paper | 4,160 |
| Every DOI | 5,055 |
| Every authorship | 33,084 |
| Every author | 14,090 |
| Every ORCID | 9,061 |
| Every institution | 3,656 |
| Every venue | 2,216 |
| Every topic | 1,610 |
| Every retraction notice | 1 |

## The first report, and the decision for each group

| Results | Rule | Rule or data? | Decision | Now |
|---:|---|---|---|---|
| 2,101 | Every authorship has an OpenAlex author ID | data incomplete at the source | accept until Session 5 | Warning |
| 1,051 | Every paper's reference list is recorded | rule wrong for some types, source incomplete for the rest | accept, coverage figure | Info |
| 214 | Every paper has a venue | data incomplete at the source | accept until Session 5 | Warning |
| 154 | Every paper has a DOI | rule too strong for the source | accept, re-check at each snapshot | Warning |
| 75 | A paper does not cite itself (new) | data wrong at the source | accept until Session 5 | Warning |
| 20 | An ORCID identifies one author record | data wrong at the source | accept until Session 5 | Warning |
| 12 | Every paper has a topic | data incomplete; not research papers | accept, re-check at each snapshot | Warning |
| 6 | Every paper has an LU author | **rule wrong** | change the rule | Violation (new rule) + Warning |
| 2 | A DOI identifies one paper | data wrong at the source | accept until Session 5 | Warning |
| 1 | A retraction notice is not retracted (new) | data wrong at the source | accept until OpenAlex corrects it | Warning |

### 2,101 authorships with no author ID

What we looked at: the 2,101 authorships (6.4% of 33,084) are on 1,217
papers. Each has the name as printed (D5), so nothing is lost; OpenAlex simply
did not decide who the person is. 311 of them carry an ORCID in the source
table, and 158 of those ORCIDs belong to an author we already have.
Decision: the rule is right (every author is a person), the source is
incomplete. Linking a name to a person is entity resolution: Session 5. A
Warning until then. The rest of the rule (at most one author, an Author, an
IRI ending in A + digits) stays a Violation.

### 1,051 papers with no reference

What we looked at, by type: 537 articles, 148 conference papers, 95
preprints, 92 other, 49 peer reviews, 24 errata, 106 more. An erratum, a
peer review or a list of contributors often cites nothing: for those, the
rule is wrong. An article does cite: there, OpenAlex is incomplete.
Decision: Info, a coverage figure, not an error. Session 5 takes reference
lists from Crossref where the publisher deposited them.

### 214 papers with no venue, 154 with no DOI, 12 with no topic

No venue: 84 conference papers, all 60 peer reviews, 28 preprints, 16
other, 15 articles. No DOI: 99 of the 482 conference papers (proceedings that
register none), 28 articles, 9 preprints, 7 dissertations. No topic: 9 of the
12 are paratext ("List of contributors"), the others a software release,
"Peer-Review Statements" and a chapter called "Conclusions".
Decision: Warnings. Nothing in our pipeline can create a venue, a DOI or a
topic; the counts stay in every report and are re-checked when we take a new
OpenAlex snapshot. Session 5 checks the papers that have a DOI against
Crossref (venue, references).

### 75 papers that cite themselves (a new rule)

75 of the 2,116 citations between our own papers go from a paper to itself:
66 articles, 7 preprints, 1 review, 1 peer review. A paper cannot cite
itself; most likely OpenAlex merged a preprint and its article into one work,
so citing the preprint became citing itself. Decision: the rule is right and
the data is wrong at the source. We do not edit our copy of OpenAlex (D4), so
a Warning until Session 5 checks them against Crossref. Until then CQ6 (most
cited within LU) still counts them.

### 20 ORCIDs on two author records, 2 DOIs on two papers

Same person, two records: "Hala Khalifeh" and "Hala K. Khalife", "ANDREA
GIAMMANCO" and "Andrea Giammanco" (20 ORCIDs, 40 records). Same paper, two
records: 10.4088/pcc.20m02902 (W4206272747, W4205255002) and
10.48327/mtsi.v5i4.2025.728 (W7118513034, W7214706685).
Decision: the rules are right, the data is wrong at the source. Session 5
(entity resolution) links each pair as one; Warnings until then.
The cost of a Warning: a 21st shared ORCID would not stop the gate. The
report shows it (expect 20 and 2), so the count is part of what we check.

### 6 papers with no LU author: the rule was wrong

All 6 (W4284692190, W4367016987, W4382465100, W4394762783, W4394763175,
W4412869153) list exactly 100 authors, the OpenAlex cap. OpenAlex selected
them because of an LU affiliation, so the LU author is past author 100: the
byline is cut. More evidence: 17 of the 19 papers at the cap have no author
labelled last.
Decision: the rule was wrong, because it ignored the cap. New rule (still a
Violation): a paper has an LU author **unless its byline is cut at 100**. A
Violation now means a paper that should not be in our set at all. The 6 stay
visible as a Warning, and a new Info marks the 19 papers at the cap.

### 1 retraction notice flagged as retracted (a new rule)

W4415060141 is the Retraction Note of W4297996152; OpenAlex flags the note
as retracted too (Session 3, CQ8). The rule is right, the data is wrong at
the source. A Warning until OpenAlex corrects it; CQ8 counts 5 retracted
papers, not 6.

### One more triage: a rule that was right but slow

Each shape timed alone on the whole graph (one machine; the seconds change
from laptop to laptop, the proportions do not): the first draft took about
395 seconds, and 330 of them went to one shape, the SPARQL rule "the author
labelled last has the highest order" (0 results). Its query had the constant
"last" in a triple pattern, so rdflib started from all 4,728 authorships
labelled last, for each of the 5,211 papers. Moving "last" into the FILTER
makes it start from the paper's own authorships: 118 seconds, the same
answer. The self-citation rule takes 9 seconds, all the core shapes together
about 60. The whole run after triage: about 185 seconds on that machine.

## After triage (shapes 1.0.0)

**0 Violations, 2,585 Warnings, 1,070 Info. Gate: PASS.** `conforms` is
still False: any result, of any severity, makes it false. The full report is
`shapes/validation-report.txt`.

The rules that held on all the data (0 results) stay Violations, so the gate
stops the first row that breaks them: one class of the 20 per paper; one
title, year (2022 to 2025), date, open access and retraction flag; at most
one DOI, venue, topic, language; 1 to 100 authorships; exactly one first
author, at order 1; at most one last author, and it has the highest order;
every authorship on one paper, with one order, position, name as listed and
corresponding flag; every link (author, institution, venue, topic, cited
paper) an IRI of our scheme, never ".../None"; the value lists of venue
type, institution type and topic domain.

## What the shapes do not check, and why

- **A wrong language.** 9 papers in Latvian (`lv`) and 3 in `ng` are almost
  surely wrong detections, but the code is well formed. Deciding needs the
  title text, not a rule on the value.
- **A paper that cites a later paper.** 11 citations between our papers go
  to a paper of a later year (43 by date). Online-first and preprints make
  this normal, so it is not a rule.
- **Institutions with no country** (98): OpenAlex does not know it for every
  institution, and no question of ours needs it.

# Session 5: the Crossref graph (shapes/crossref-shapes.ttl)

The Crossref graph is checked against its own shapes, not against shapes.ttl
(D14): the OpenAlex rules do not hold for Crossref, and are not meant to. A
Crossref record may list no author, or 1,512; its year may fall outside
2022-2025; it has no open-access flag and no type of ours. So the same
question, **is the rule wrong, or the data?**, was asked rule by rule
before the first run, with the counts of data/crossref.sql in hand, and the
first run is the triaged one: 0 Violations, 73 Warnings, 28,182 Info. Each
decision is in the rule's TRIAGE comment; the report is
`shapes/crossref-validation-report.txt`.

| Results | Rule | Rule or data? | Decision | Now |
|---:|---|---|---|---|
| 26,821 | Every Crossref author has an ORCID | coverage of the source (76% have none) | the matcher's job, not an error | Info |
| 1,172 | Every record has references with a DOI | coverage: publishers deposit them by choice | accept | Info |
| 98 | A title has no markup | a fact about Crossref (OpenAlex removes tags) | compare titles without markup | Info |
| 75 | Every record lists an author | coverage: 43 are peer reviews | accept | Info |
| 16 | At most 100 authors | **rule wrong** for Crossref: no cap | keep it as Info: these are the bylines OpenAlex cut | Info |
| 38 | The year is 2022 to 2025 | **rule is OpenAlex's**, not Crossref's | a disagreement between the sources (CQ10) | Warning |
| 10 | A reference has a well-formed DOI | data wrong at the source (publisher's deposit) | accept, we do not repair the source (D4) | Warning |
| 7 | A notice updates another record | data as deposited: 6 versions or editions, 1 removal | accept | Warning |
| 6 | Every record has a date | data incomplete at the source | accept | Warning |
| 5 | A record does not cite itself | data wrong at the source | accept | Warning |
| 4 | A reference's DOI has no space | data wrong at the source | accept | Warning |
| 2 | Two authors of a record do not share an ORCID | data wrong at the source | accept; one of the two authorships is linked to the wrong person | Warning |
| 1 | Every record has a title | data incomplete: the DOI of a whole journal issue | accept | Warning |
| 707 | A reference's DOI is ASCII (new in 1.0.1) | data wrong at the source: typographic hyphens | accept | Warning |

The last rule came later, from comparing the two routes (D16): Ontop and
Morph-KGC made the same graph but for 707 triples, the references whose DOI
has a typographic hyphen (U+2010) or a dash where a DOI has "-". Morph-KGC
writes the character percent-encoded, Ontop as it is. No rule had looked at the
characters of a cited DOI, only at its start. Since then the Crossref report has
780 Warnings.

Every other rule held on all the data (0 results) and is a Violation, so the
gate stops the first row that breaks it: a record is a pub:Work named
.../work/crossref/{DOI}, with exactly one DOI, at most one title, year, date
and venue name, ISSNs written 0000-000X, authorships of our scheme; an
authorship belongs to one record, with one position and one name; a person
is named by a well-formed ORCID, and one ORCID is one person.

Two things were learned on the way:

- **Targeting.** The first idea, `sh:targetClass pub:Work`, would have
  targeted the notices outside our papers too: a correction of one of our
  papers is typed pub:Erratum by the mapping, but it is not a record we
  downloaded, so it has no pub:doi and would have broken "exactly one DOI".
  The target is `sh:targetSubjectsOf pub:doi`: the records.
- **Cost.** pySHACL runs a SPARQL rule once per focus node. The ORCID rule
  asked per record was by far the slowest rule: a record with 1,512 authors
  makes over 2 million pairs of authorships. Asked per person (a few
  authorships each), it takes about a third of that time, with the same 2
  results. The time of the whole run is the report's "validated in" line.

What the second source already says about Session 4's decisions (the
competency questions, `ontology/cq_answers.txt`):

- **The retraction notice flagged as retracted** (W4415060141, a Warning):
  Crossref agrees it is a notice (cq08_sources). And it finds a second one
  that no rule could see: OpenAlex types W4308586991 as an article and flags
  it retracted; Crossref says it is the retraction notice of another paper,
  10.3892/ijo.2014.2638, not one of ours.
- **214 papers with no venue** (a Warning): Crossref names a venue for 105
  of the 212 that have a Crossref record (cq10_venues).
- **Bylines cut at 100** (an Info, and the 6 papers without an LU author): 16
  Crossref records list more than 100 authors.

The links between the two graphs come next; with them, the Session 4
Warnings that wait for Session 5 (the self-citations, the duplicate DOIs and
ORCIDs, the authorships without an author) are re-checked, and their TRIAGE
comments in shapes.ttl say what the links changed.

# Session 5: the links (shapes/links-shapes.ttl, shapes/matches-shapes.ttl)

A link is right only if it fits the graphs it joins, so the link shapes see
some triples of the source graphs too: the classes of both ends, the
authorships of each paper, the people and their ORCIDs (pipeline/run.py,
CONTEXT). The reports: `shapes/links-validation-report.txt`,
`shapes/matches-validation-report.txt`.

**The links by key** (graph/links, 9,293 triples): every rule held on the first
run, so every rule is a Violation. Both ends of each link exist and are of one
kind (a paper and a paper, a person and a person); each OpenAlex record is the
same as at most one Crossref record or person; a link by ORCID never gives an
authorship a second person; every person named by ORCID has a well-formed one.

**The matcher's links** (graph/matches, 30,848 triples), first run: 8
Violations, 52 Warnings.

| Results | Rule | Rule or data? | Decision | Now |
|---:|---|---|---|---|
| 52 | Both sources give a matched person the same ORCID | mostly the sources disagree; a few times the matcher is wrong | a person decides; listed in match_authorships.txt | Warning |
| 8 | A Crossref author is matched to one OpenAlex authorship | **rule wrong** for a paper OpenAlex has twice | expect 8 | Warning (was a Violation) |
| 0 | A matched pair is on one paper (the links by key say which) | | | Violation |
| 0 | An OpenAlex authorship is matched to one Crossref author | | | Violation |

- **52 ORCID disagreements.** 42 have the same name on both sides (Dany
  Azar): one person with two ORCIDs, so one source is wrong, or the person has
  two ORCID records. A few are the matcher's mistakes: Norma and Najah A. R.
  Ghamrawi (3 papers), Nigar and Najwaa Kirmani, two people each time with one
  family name and one first initial. The matcher's own measurement sees one of
  the 52 (mapping/er/README.md), so this rule is what finds the rest.
- **8 Crossref authors matched twice.** They are the 8 authors of
  10.4088/pcc.20m02902, which OpenAlex has twice (W4205255002 and W4206272747,
  linked in graph/links): each record's authors are matched to the same
  Crossref authors, rightly. The rule was right for every other paper and too
  strong for this one; a Warning, and a ninth result would be a new problem.

What the links settle among Session 4's Warnings (`ontology/cq_answers.txt`),
written in shapes.ttl's TRIAGE comments (version 1.0.1). The Warnings stay:
shapes.ttl checks graph/openalex alone, which is unchanged (D4).

- **2 DOIs on two records, 20 ORCIDs on two records**: all linked as one
  paper, one person (cq09; link_by_key.txt).
- **2,101 authorships with no person**: 311 get one by ORCID; 1,790 are left,
  1,449 of them matched to a Crossref author, and Crossref names only 1 of
  those by an ORCID (cq09).
- **75 self-citations**: for 43 the Crossref record has references, and only 4
  list the paper itself (cq06_sources): Crossref does not confirm them.
- **1,051 papers with no reference**: Crossref has references for 20 (cq06_sources).
