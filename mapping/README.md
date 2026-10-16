# mapping/

YOUR TEAM: your Session 5 work, on your own source.

- `mapping.ttl`: replace the example with the R2RML mapping from your tables
  to your ontology. One triples map per table or view, and one IRI template
  per kind of thing (the course's IRI convention, Session 2).
- Materialized and virtualized: the pipeline materializes the graph with
  Morph-KGC. Run the same data virtualized (Ontop, as in the Session 5 lab)
  and say in the report which one your deployed system uses, argued on
  freshness, latency and workload.
- Entity resolution across two sources: link records that name the same real
  thing, and measure it on a small labelled sample, with precision and
  recall. Keep the sample, the matcher and the result in `mapping/er/`.
- Quote only numbers that a file in this repository holds.
