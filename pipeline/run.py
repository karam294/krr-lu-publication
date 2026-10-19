"""The graph pipeline: source tables -> graphs -> SHACL gate -> provenance -> VoID -> endpoint.

    python pipeline/run.py              all steps, loads the endpoint at the end
    python pipeline/run.py --no-load    the first five steps only (no Fuseki needed)

Run from the repository root. In the stack, docker compose runs it once, as
the "pipeline" service, before the access layer starts.

Two sources, one named graph each (D10, D14), each with its own mapping, its
own shapes and its own file (SOURCES below).

  1 source       DB_URL if set (your database, with the tables of both
                 sources), otherwise our data: data/lu.sql and
                 data/crossref.sql loaded into build/sources.sqlite
  2 map          each source's mapping with Morph-KGC:
                 mapping/mapping.ttl  -> build/graph.nt     (OpenAlex)
                 mapping/crossref.ttl -> build/crossref.nt  (Crossref)
  3 validate     each graph + ontology/ontology.ttl against its own shapes
                 (shapes/validate.py): shapes/shapes.ttl for OpenAlex,
                 shapes/crossref-shapes.ttl for Crossref. Any Violation, or a
                 shape that checks nothing, in either graph stops here (exit 1),
                 so bad data never reaches the endpoint; both reports go to
                 build/shacl-report.txt
  4 provenance   what this run used and made, in PROV-O -> build/provenance.ttl
                 (pipeline/provenance.py)
  5 describe     VoID of the OpenAlex graph -> build/void.ttl (the access layer
                 reads it)
  6 load         empty the endpoint, then one named graph each:
                 graph/openalex, graph/crossref, graph/ontology, graph/provenance.
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

# One named graph per source: its name, its mapping, its shapes, its file in build/.
SOURCES = (
    ("openalex", "mapping/mapping.ttl", "shapes/shapes.ttl", "graph.nt"),
    ("crossref", "mapping/crossref.ttl", "shapes/crossref-shapes.ttl", "crossref.nt"),
)


def step(n, text):
    print(f"{n} {text}", flush=True)


def source():
    url = os.environ.get("DB_URL")
    if url:
        step(1, f"source: {url.split('@')[-1]}")  # never print a password
        return url
    db = BUILD / "sources.sqlite"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    for sql in ("lu.sql", "crossref.sql"):
        con.executescript((ROOT / "data" / sql).read_text(encoding="utf-8"))
    con.close()
    step(1, "source: our data, data/lu.sql and data/crossref.sql")
    return f"sqlite:///{db}"


def materialize(db_url, name, mapping, filename):
    import morph_kgc
    cfg = (f"[CONFIGURATION]\nlogging_level=WARNING\n\n"
           f"[source]\nmappings={ROOT / mapping}\ndb_url={db_url}\n")
    graph = morph_kgc.materialize(cfg)
    out = BUILD / filename
    graph.serialize(out, format="nt", encoding="utf-8")
    step(2, f"map: graph/{name}, {len(graph):,} triples ({mapping}) -> build/{filename}")
    return out, len(graph)


def gate(name, graph_path, shapes_file):
    """Validate one graph against its shapes; return the counts per severity,
    the shapes that checked nothing, and the report lines."""
    sys.path.insert(0, str(ROOT / "shapes"))
    from validate import check
    data = Graph().parse(graph_path, format="nt").parse(ROOT / "ontology" / "ontology.ttl")
    shapes = Graph().parse(ROOT / shapes_file)
    counts, empty, lines = check(data, shapes)
    step(3, f"validate: graph/{name} against {shapes_file}: {counts['Violation']:,} Violation, "
            f"{counts['Warning']:,} Warning, {counts['Info']:,} Info")
    print("\n".join(lines), flush=True)
    head = f"== graph/{name} ({len(data):,} triples with the ontology) against {shapes_file}"
    return counts, empty, [head] + lines + [""]


def stop_if_failed(results):
    report = [line for _, _, lines in results.values() for line in lines]
    (BUILD / "shacl-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    failed = []
    for name, (counts, empty, _) in results.items():
        if counts["Violation"]:
            failed.append(f"graph/{name}: {counts['Violation']:,} Violation")
        if empty:
            failed.append(f"graph/{name}: {', '.join(empty)} checks nothing (0 focus nodes)")
    if failed:
        sys.exit("SHACL gate: " + "; ".join(failed) + ". The endpoint is not loaded. "
                 "Read build/shacl-report.txt.")


def record_provenance(sizes, results, started):
    graphs = {name: (sizes[name], ", ".join(f"{counts[s]:,} {s}" for s in ("Violation", "Warning", "Info")))
              for name, (counts, _, _) in results.items()}
    n = write_provenance(ROOT, BUILD / "provenance.ttl", graphs, started, now())
    step(4, f"provenance: {n} PROV-O triples -> build/provenance.ttl")


def describe(graph_path):
    sys.path.insert(0, str(ROOT / "access-layer"))
    from make_void import write_void
    n = write_void(graph_path, BUILD / "void.ttl")
    step(5, f"describe: {n} VoID triples -> build/void.ttl")


def load(files):
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
    parts = [(name, path, "application/n-triples") for name, path in files.items()]
    parts += [("ontology", ROOT / "ontology" / "ontology.ttl", "text/turtle; charset=utf-8"),
              ("provenance", BUILD / "provenance.ttl", "text/turtle; charset=utf-8")]
    for name, path, ctype in parts:
        r = requests.put(f"{base}/data", params={"graph": GRAPH + name}, data=Path(path).read_bytes(),
                         headers={"Content-Type": ctype}, timeout=300)
        ok(r, f"graph/{name}")
    step(6, f"load: {', '.join('graph/' + name for name, _, _ in parts)} -> {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-load", action="store_true")
    a = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    started = now()
    db_url = source()
    files, sizes = {}, {}
    for name, mapping, _, filename in SOURCES:
        files[name], sizes[name] = materialize(db_url, name, mapping, filename)
    results = {name: gate(name, files[name], shapes) for name, _, shapes, _ in SOURCES}
    stop_if_failed(results)
    record_provenance(sizes, results, started)
    describe(files["openalex"])
    if not a.no_load:
        load(files)
    print("done")


if __name__ == "__main__":
    main()
