"""Run every competency question (ontology/cq/*.rq) on the graph and save the answers.

    python ontology/run_cqs.py        after pipeline/run.py (it reads build/graph.nt,
                                      crossref.nt, links.nt and matches.nt)

The graphs are loaded as the endpoint holds them: each source and each kind of
link in its own named graph (graph/openalex, graph/crossref, graph/links,
graph/matches), and the default graph is their union, as in Fuseki
(fuseki/config.ttl). So a question gives the same answer here and on the
endpoint. The questions about OpenAlex name their graph (FROM); the ones that
compare the sources or follow the links (CQ6 and CQ8 both sources, CQ9, CQ10)
name each graph they use (FROM NAMED, GRAPH).

The answers go to ontology/cq_answers.txt: the evidence that the graph answers
each question, and the numbers the report may quote.
"""
import datetime
import re
from pathlib import Path

import pyoxigraph as ox

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontology" / "cq_answers.txt"
GRAPHS = {"openalex": "graph.nt", "crossref": "crossref.nt", "links": "links.nt", "matches": "matches.nt"}


def show(term):
    """A value as text: the number or string of a literal, the last part of an IRI."""
    if term is None:
        return ""
    if isinstance(term, ox.Literal):
        return term.value
    return str(term.value).rsplit("/", 1)[-1].rsplit("#", 1)[-1]


store = ox.Store()
sizes = []
for name, filename in GRAPHS.items():
    graph = ox.NamedNode(f"https://ul.edu.lb/kr/graph/{name}")
    store.bulk_load(path=str(ROOT / "build" / filename), format=ox.RdfFormat.N_TRIPLES, to_graph=graph)
    n = next(iter(store.query(f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{graph.value}> {{ ?s ?p ?o }} }}")))["n"]
    sizes.append(f"graph/{name} {int(n.value):,} triples (build/{filename})")
lines = [f"Competency questions, run {datetime.date.today()}, on", *[f"  {s}" for s in sizes], ""]

for path in sorted((ROOT / "ontology" / "cq").glob("*.rq")):
    query = path.read_text(encoding="utf-8")
    question = query.splitlines()[0].lstrip("# ")
    # The union as default graph only for a query that names no graph: pyoxigraph
    # ignores FROM when it is asked for the union (Fuseki honours both).
    names_graph = re.search(r"^\s*FROM\b", query, re.MULTILINE | re.IGNORECASE)
    results = store.query(query, use_default_graph_as_union=not names_graph)
    names = [v.value for v in results.variables]
    rows = [[show(row[name]) for name in names] for row in results]
    widths = [max(len(n), *(len(r[i][:60]) for r in rows)) if rows else len(n) for i, n in enumerate(names)]
    lines += [f"== {path.name}  {question}",
              "   " + "  ".join(n.ljust(w) for n, w in zip(names, widths))]
    lines += ["   " + "  ".join(v[:60].ljust(w) for v, w in zip(r, widths)) for r in rows]
    lines += [f"   ({len(rows)} rows)", ""]

OUT.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print("written:", OUT.relative_to(ROOT))
