"""The graph pipeline: source tables -> graph -> SHACL gate -> provenance -> VoID -> endpoint.

    python pipeline/run.py              all steps, loads the endpoint at the end
    python pipeline/run.py --no-load    the first five steps only (no Fuseki needed)

Run from the repository root. In the stack, docker compose runs it once, as
the "pipeline" service, before the access layer starts.

  1 source       DB_URL if set (your database), otherwise our data:
                 data/lu.sql loaded into build/lu.sqlite
  2 map          mapping/mapping.ttl with Morph-KGC -> build/graph.nt
  3 validate     build/graph.nt + ontology/ontology.ttl against shapes/shapes.ttl
                 (shapes/validate.py); any Violation, or a shape that checks
                 nothing, stops here (exit 1), so bad data never reaches the
                 endpoint; the report goes to build/shacl-report.txt
  4 provenance   what this run used and made, in PROV-O -> build/provenance.ttl
                 (pipeline/provenance.py)
  5 describe     VoID of the graph -> build/void.ttl (the access layer reads it)
  6 load         empty the endpoint, then one named graph each (D10):
                 graph/openalex (the data), graph/ontology, graph/provenance.
                 Fuseki's default graph is their union (fuseki/config.ttl).
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from rdflib import Graph

from provenance import GRAPH, now, write_provenance

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
    return out, len(graph)


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


def record_provenance(n_triples, started, counts):
    summary = ", ".join(f"{counts[s]:,} {s}" for s in ("Violation", "Warning", "Info"))
    n = write_provenance(ROOT, BUILD / "provenance.ttl", n_triples, started, now(), summary)
    step(4, f"provenance: {n} PROV-O triples -> build/provenance.ttl")


def describe(graph_path):
    sys.path.insert(0, str(ROOT / "access-layer"))
    from make_void import write_void
    n = write_void(graph_path, BUILD / "void.ttl")
    step(5, f"describe: {n} VoID triples -> build/void.ttl")


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

    def ok(r, what):
        if not r.ok:
            sys.exit(f"Loading the endpoint failed at {what} ({r.status_code}): {r.text[:200]}")

    # Start from an empty endpoint: no graph from an older run or a manual upload stays behind.
    ok(requests.post(f"{base}/update", data={"update": "DROP ALL"}, timeout=120), "DROP ALL")
    parts = (("openalex", graph_path, "application/n-triples"),
             ("ontology", ROOT / "ontology" / "ontology.ttl", "text/turtle; charset=utf-8"),
             ("provenance", BUILD / "provenance.ttl", "text/turtle; charset=utf-8"))
    for name, path, ctype in parts:
        r = requests.put(f"{base}/data", params={"graph": GRAPH + name}, data=Path(path).read_bytes(),
                         headers={"Content-Type": ctype}, timeout=300)
        ok(r, f"graph/{name}")
    step(6, f"load: graph/openalex, graph/ontology, graph/provenance -> {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-load", action="store_true")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    started = now()
    graph, n_triples = materialize(source())
    counts = gate(graph)
    record_provenance(n_triples, started, counts)
    describe(graph)
    if not a.no_load:
        load(graph)
    print("done")


if __name__ == "__main__":
    main()
