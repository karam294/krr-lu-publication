"""The graph pipeline: source tables -> graph -> SHACL gate -> VoID -> endpoint.

    python pipeline/run.py              all steps, loads the endpoint at the end
    python pipeline/run.py --no-load    the first four steps only (no Fuseki needed)

Run from the repository root. In the stack, docker compose runs it once, as
the "pipeline" service, before the access layer starts.

  1 source     DB_URL if set (your database), otherwise our data:
               data/lu.sql loaded into build/lu.sqlite
  2 map        mapping/mapping.ttl with Morph-KGC -> build/graph.nt
  3 validate   build/graph.nt + ontology/ontology.ttl against shapes/shapes.ttl
               (shapes/validate.py); any Violation, or a shape that checks
               nothing, stops here (exit 1), so bad data never reaches the
               endpoint; the report goes to build/shacl-report.txt
  4 describe   VoID of the graph -> build/void.ttl (the access layer reads it)
  5 load       ontology and graph into the endpoint (FUSEKI_URL, dataset kr)
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FUSEKI = os.environ.get("FUSEKI_URL", "http://127.0.0.1:3030")
DATASET = os.environ.get("FUSEKI_DATASET", "kr")


def step(n, text):
    print(f"{n} {text}", flush=True)


def source():
    url = os.environ.get("DB_URL")
    if url:
        step(1, f"source: {url.split('@')[-1]}")  # never print a password
        return url
    db = BUILD / "lu.sqlite"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript((ROOT / "data" / "lu.sql").read_text(encoding="utf-8"))
    con.close()
    step(1, "source: our data, data/lu.sql")
    return f"sqlite:///{db}"


def materialize(db_url):
    import morph_kgc
    cfg = (f"[CONFIGURATION]\nlogging_level=WARNING\n\n"
           f"[source]\nmappings={ROOT / 'mapping' / 'mapping.ttl'}\ndb_url={db_url}\n")
    graph = morph_kgc.materialize(cfg)
    out = BUILD / "graph.nt"
    graph.serialize(out, format="nt", encoding="utf-8")
    step(2, f"map: {len(graph):,} triples -> build/graph.nt")
    return out


def gate(graph_path):
    sys.path.insert(0, str(ROOT / "shapes"))
    from validate import check
    data = Graph().parse(graph_path, format="nt").parse(ROOT / "ontology" / "ontology.ttl")
    shapes = Graph().parse(ROOT / "shapes" / "shapes.ttl")
    counts, empty, lines = check(data, shapes)
    (BUILD / "shacl-report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    step(3, f"validate: {counts['Violation']:,} Violation, {counts['Warning']:,} Warning, "
            f"{counts['Info']:,} Info -> build/shacl-report.txt")
    print("\n".join(lines), flush=True)
    if counts["Violation"]:
        sys.exit(f"SHACL gate: {counts['Violation']:,} Violation, so the endpoint is not loaded. "
                 "Read build/shacl-report.txt.")
    if empty:
        sys.exit(f"SHACL gate: {', '.join(empty)} checks nothing (0 focus nodes), so the endpoint is not loaded.")
    return counts


def describe(graph_path):
    sys.path.insert(0, str(ROOT / "access-layer"))
    from make_void import write_void
    n = write_void(graph_path, BUILD / "void.ttl")
    step(4, f"describe: {n} VoID triples -> build/void.ttl")


def load(graph_path):
    base = f"{FUSEKI}/{DATASET}"
    for _ in range(30):  # the endpoint may still be starting
        try:
            if requests.get(f"{FUSEKI}/$/ping", timeout=5).ok:
                break
        except requests.ConnectionError:
            pass
        time.sleep(2)
    else:
        sys.exit(f"The endpoint at {FUSEKI} did not answer within a minute.")
    ont = (ROOT / "ontology" / "ontology.ttl").read_bytes()
    r1 = requests.put(f"{base}/data?default", data=graph_path.read_bytes(),
                      headers={"Content-Type": "application/n-triples"}, timeout=300)
    r2 = requests.post(f"{base}/data?default", data=ont, headers={"Content-Type": "text/turtle"}, timeout=60)
    for r in (r1, r2):
        if not r.ok:
            sys.exit(f"Loading the endpoint failed ({r.status_code}): {r.text[:200]}")
    step(5, f"load: graph and ontology -> {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-load", action="store_true")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    graph = materialize(source())
    gate(graph)
    describe(graph)
    if not a.no_load:
        load(graph)
    print("done")


if __name__ == "__main__":
    main()