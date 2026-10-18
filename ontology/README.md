# ontology/

| File | What it is |
|---|---|
| ontology.ttl | Our ontology, version 1.0.0, OWL 2 DL: every pub: term with its meaning, its competency question and its place in FaBiO, FOAF, PRO, CiTO, Dublin Core (D7) |
| imports/ | Unchanged local copies of FaBiO 2.3.1, FRBR 1.1.0 and FOAF, CC BY (LICENCES.md) |
| catalog-v001.xml | Tells Protégé and ROBOT to load the imports from imports/ |
| competency_questions.md | The ten questions the graph must answer |
| cq/, run_cqs.py, cq_answers.txt | The questions as SPARQL, the runner, and their answers on the full graph |
| LICENCES.md | The licence of everything reused |

Bump the version IRI (1.0.0, 1.0.1, ...) on every change to ontology.ttl.