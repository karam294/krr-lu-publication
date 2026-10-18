"""Run every competency question (ontology/cq/*.rq) on the graph and save the answers.

    python ontology/run_cqs.py        after pipeline/run.py (it reads build/graph.nt)

The answers go to ontology/cq_answers.txt: the evidence that the graph answers
each question, and the numbers the report may quote.
"""
import datetime
from pathlib import Path

import pyoxigraph as ox

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ontology" / "cq_answers.txt"


def show(term):
    """A value as text: the number or string of a literal, the last part of an IRI."""
    if term is None:
        return ""
    if isinstance(term, ox.Literal):
        return term.value
    return str(term.value).rsplit("/", 1)[-1].rsplit("#", 1)[-1]


store = ox.Store()
store.load(path=str(ROOT / "build" / "graph.nt"), format=ox.RdfFormat.N_TRIPLES)
lines = [f"Competency questions on build/graph.nt ({len(store):,} triples), run {datetime.date.today()}", ""]

for path in sorted((ROOT / "ontology" / "cq").glob("*.rq")):
    query = path.read_text(encoding="utf-8")
    question = query.splitlines()[0].lstrip("# ")
    results = store.query(query)
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