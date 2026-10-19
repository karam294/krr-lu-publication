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
