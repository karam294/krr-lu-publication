# ontology/

YOUR TEAM: your Session 3 work, on your own domain.

- `ontology.ttl`: replace the example with your ontology. Reuse a real
  published vocabulary for your domain (the topic menu names one per area),
  extend it only where it has a gap, and align outward with
  `skos:exactMatch`, `skos:closeMatch` or `rdfs:subClassOf`.
- Competency questions: write them first, as annotations on the ontology
  or in `competency_questions.md`. Every class and property you add must
  answer one of them; the questions are also the first test of your SPARQL.
- Declare the OWL profile (EL, QL, RL or DL) and keep to it. Run a reasoner
  (ELK or HermiT, as in the Session 3 lab) until there is no red class, and
  save the run's output in `ontology/reasoner-run.txt` with the date.
- Give the ontology a version IRI and bump it when you change it.
- The pipeline validates your data together with this file, so a subclass
  declared here reaches the shapes.

In Session 8 an ontology the team cannot defend loses its ontology points.
