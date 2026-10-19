"""Compare the two routes on the same questions (Session 5, D16): the
materialized graph in Fuseki, and Ontop answering from PostgreSQL.

    python mapping/ontop/compare_routes.py

Run from the repository root, with both endpoints up:
  Fuseki  loaded by python pipeline/run.py               http://127.0.0.1:3030/kr/sparql
  Ontop   prepared by mapping/ontop/prepare_ontop.py     http://127.0.0.1:8080/sparql
and, for part 4, Ontop's own materialization of the same mappings in
build/ontop/materialized.nq (mapping/README.md says how to make it).

Writes mapping/ontop/compare-routes.txt:
  1 answers    every competency question (ontology/cq/) and the query that
               follows the links (mapping/er/follow_links.rq), on both: the
               same answer, row by row?
  2 time       each question's time on each endpoint, the median of 3 runs
               after a first run to warm up
  3 freshness  one value changed in PostgreSQL: which route sees it, and when
  4 graph      the triples Ontop's materialization makes, against the
               pipeline's (Morph-KGC): the same?
"""

import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import requests
from dotenv import load_dotenv
from rdflib import Graph, Namespace
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "compare-routes.txt"
FUSEKI = os.environ.get("FUSEKI_SPARQL", "http://127.0.0.1:3030/kr/sparql")
ONTOP = os.environ.get("ONTOP_SPARQL", "http://127.0.0.1:8080/sparql")
GRAPHS = {"openalex": "graph.nt", "crossref": "crossref.nt", "links": "links.nt", "matches": "matches.nt"}
PAPER = "https://ul.edu.lb/kr/id/work/openalex/W3023054831"
TITLE = f"""PREFIX pub: <https://ul.edu.lb/kr/pub#>
SELECT ?title WHERE {{ GRAPH <https://ul.edu.lb/kr/graph/openalex> {{ <{PAPER}> pub:title ?title }} }}"""


def ask(endpoint, query):
    """(rows, seconds) or (None, the error's first line)."""
    t = time.perf_counter()
    try:
        r = requests.post(endpoint, data={"query": query}, timeout=600,
                          headers={"Accept": "application/sparql-results+json"})
    except requests.ConnectionError:
        sys.exit(f"{endpoint} does not answer: start it first (see this script's docstring).")
    seconds = time.perf_counter() - t
    if not r.ok:
        message = r.text.strip().splitlines()[0] if r.text.strip() else f"HTTP {r.status_code}"
        return None, message.split("Exception: ")[-1][:150]
    data = r.json()
    names = data["head"]["vars"]
    return [tuple(b.get(n, {}).get("value", "") for n in names) for b in data["results"]["bindings"]], seconds


def queries():
    paths = sorted((ROOT / "ontology" / "cq").glob("*.rq")) + [ROOT / "mapping" / "er" / "follow_links.rq"]
    return [(p.name, p.read_text(encoding="utf-8")) for p in paths]


def part_answers_and_time(lines):
    lines += ["1 answers and 2 time: each query on both endpoints (median of 3 runs, after a warm-up run)", "",
              f"  {'query':<18} {'Fuseki':>9} {'Ontop':>9}  answer"]
    same = 0
    for name, query in queries():
        result = {}
        for label, endpoint in (("fuseki", FUSEKI), ("ontop", ONTOP)):
            rows, first = ask(endpoint, query)
            if rows is None:
                result[label] = (None, None, first)
                continue
            runs = [ask(endpoint, query)[1] for _ in range(3)]
            result[label] = (rows, statistics.median(runs), None)
        f_rows, f_time, f_error = result["fuseki"]
        o_rows, o_time, o_error = result["ontop"]
        if f_error:
            verdict = f"Fuseki failed: {f_error}"
        elif o_error:
            verdict = f"Ontop failed: {o_error}"
        elif f_rows == o_rows:
            verdict, same = f"the same ({len(f_rows)} rows)", same + 1
        elif sorted(f_rows) == sorted(o_rows):
            verdict = f"the same rows ({len(f_rows)}), in another order"
        else:
            diff = next((i for i, (a, b) in enumerate(zip(f_rows, o_rows)) if a != b), min(len(f_rows), len(o_rows)))
            verdict = f"DIFFERENT: {len(f_rows)} rows and {len(o_rows)}, first difference at row {diff + 1}"
        show = lambda s: f"{s:8.2f}s" if s is not None else "        -"
        lines.append(f"  {name:<18} {show(f_time)} {show(o_time)}  {verdict}")
    lines += ["", f"  the same answer on both: {same} of {len(queries())} queries", ""]


def part_freshness(lines):
    load_dotenv(ROOT / ".env")
    engine = create_engine(f"postgresql+psycopg2://kr:{os.environ['POSTGRES_PASSWORD']}@127.0.0.1:5432/lu")
    mark = " [changed in PostgreSQL]"
    lines.append("3 freshness: the title of W3023054831, changed in PostgreSQL, then changed back")
    try:
        with engine.begin() as c:
            c.execute(text("UPDATE works SET title = title || :m WHERE work_id = 'W3023054831'"), {"m": mark})
        for label, endpoint in (("Fuseki", FUSEKI), ("Ontop", ONTOP)):
            rows, _ = ask(endpoint, TITLE)
            seen = "sees the change" if rows and rows[0][0].endswith(mark) else "does not see it"
            lines.append(f"  {label:<7} {seen}: {rows[0][0] if rows else rows}")
    finally:
        with engine.begin() as c:
            c.execute(text("UPDATE works SET title = replace(title, :m, '') WHERE work_id = 'W3023054831'"), {"m": mark})
    prov = Graph().parse(ROOT / "build" / "provenance.ttl")
    PROV = Namespace("http://www.w3.org/ns/prov#")
    run = next(prov.subjects(PROV.endedAtTime, None))
    start, end = (datetime.fromisoformat(str(prov.value(run, p))) for p in (PROV.startedAtTime, PROV.endedAtTime))
    lines += [f"  The materialized graph sees a change after the next pipeline run (map, SHACL gate, load):",
              f"  the last one took {(end - start).seconds // 60} min {(end - start).seconds % 60} s "
              "(build/provenance.ttl). Ontop sees it at the next query, and nothing checks it first.", ""]


def part_graph(lines):
    path = ROOT / "build" / "ontop" / "materialized.nq"
    lines.append("4 graph: Ontop's materialization of the same four mappings, against the pipeline's (Morph-KGC)")
    if not path.exists():
        lines += ["  skipped: no build/ontop/materialized.nq (mapping/README.md says how to make it)", ""]
        return
    import pyoxigraph as ox
    morph, ontop = ox.Store(), ox.Store()
    for name, filename in GRAPHS.items():
        morph.bulk_load(path=str(ROOT / "build" / filename), format=ox.RdfFormat.N_TRIPLES,
                        to_graph=ox.NamedNode(f"https://ul.edu.lb/kr/graph/{name}"))
    ontop.bulk_load(path=str(path), format=ox.RdfFormat.N_QUADS)
    a, b = set(morph), set(ontop)
    lines.append(f"  Morph-KGC {len(a):,} triples, Ontop {len(b):,}; only in Morph-KGC {len(a - b):,}, "
                 f"only in Ontop {len(b - a):,}")
    if a - b:
        # The usual reason: a character that is not ASCII in a key. R2RML lets an IRI keep it;
        # Morph-KGC writes it percent-encoded, Ontop as it is.
        decoded = lambda q: tuple(unquote(str(t)) if isinstance(t, ox.NamedNode) else str(t)
                                  for t in (q.subject, q.predicate, q.object, q.graph_name))
        explained = {decoded(q) for q in a - b} == {decoded(q) for q in b - a}
        by_graph = sorted({str(q.graph_name).rsplit("/", 1)[-1].rstrip(">") for q in a - b})
        lines.append(f"  in graph/{', graph/'.join(by_graph)}; " + (
            "all of them the same triple once percent-encoding is undone: a character that is not ASCII "
            "in a key, which Morph-KGC writes encoded and Ontop as it is" if explained else "see the examples"))
        for q in sorted(a - b, key=str)[:2]:
            lines.append(f"    Morph-KGC  {q.object}")
        for q in sorted(b - a, key=str)[:2]:
            lines.append(f"    Ontop      {q.object}")
    lines.append("")


def main():
    lines = [f"The two routes compared, {datetime.now().date()}: Fuseki ({FUSEKI}, the materialized graph) "
             f"and Ontop ({ONTOP}, answers from PostgreSQL)", ""]
    part_answers_and_time(lines)
    part_freshness(lines)
    part_graph(lines)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"written: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
