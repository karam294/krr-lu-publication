# Technical report: <your system's name>

At most 16 pages, the open problem included. It documents what was
deployed, not what was planned. Section 9 and the
references feed the "Report and open problem" mark; sections 3 to 7 are
what the instructor reads while checking each layer. Quote only numbers that a file in this repository holds.

## 1. Problem framing and scope

The questions the system answers, tied to the competency questions and
measurable. What was left out, and why.

## 2. Data understanding and constraint discovery

The source, its licence, and what one row means. The constraint inventory:
each constraint with the evidence in your data, and the ones you found false
in the data, reported rather than dropped.

## 3. Ontology

The published vocabulary you reused and why it fits; the alignment outward;
the competency questions; the OWL profile; the reasoner run; the version IRI.
Every class and property answers a competency question.

## 4. Constraint validation with SHACL

The shapes against the inventory; for each constraint, why SHACL and not OWL
(or the reverse); the triage of every failure (data defect or wrong
constraint); the gate in CI, with a red run it blocked.

## 5. Operational data integration

The mapping; materialized and virtualized over the same data, and which one
the deployed system uses, argued on freshness, latency and workload; entity
resolution across two sources, with precision and recall on a labelled sample.

## 6. Prediction and evaluation honesty

The graph built from the ontology; the node classification and link
prediction models; the split (temporal where time matters) and why it does
not leak; the baseline; several seeds and the spread. A model that loses to
the baseline, reported as such with an explanation, is a result, not a failure.

## 7. Access layer

The grounding (VoID, examples), the check and repair loop, the refusal path
on a real unanswerable question, and the score of your test set before and
after one improvement, with the model and the date.

## 8. Deployment and reproducibility

The stack (`docker-compose.yml`), how it comes up from a clean checkout with
one command, provenance, the ontology's version, and what a clean checkout
test surfaced.

## 9. Open problem, at most 2 pages

One open problem from Session 7, stated as a question, connected to a
decision or limitation in your own system, with a position of your own, and
at least three primary sources you read.

## Licences

| Ontology, vocabulary or dataset | Licence | Where used |
|---|---|---|
|  |  |  |
