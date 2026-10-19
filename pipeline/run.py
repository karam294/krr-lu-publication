"""The graph pipeline: source tables -> graphs -> SHACL gate -> provenance -> VoID -> endpoint.

    python pipeline/run.py              all steps, loads the endpoint at the end
    python pipeline/run.py --no-load    the first five steps only (no Fuseki needed)

Run from the repository root. In the stack, docker compose runs it once, as
the "pipeline" service, before the access layer starts.

Four named graphs (GRAPHS below), each with its own mapping, its own shapes and
its own file: one per source (D10, D14), and one per kind of link between them
(D15): the links by key, and the matcher's links.

  1 source       DB_URL if set (your database, with the tables of both
                 sources and of mapping/er), otherwise our data: data/lu.sql,
                 data/crossref.sql and the two CSV files of mapping/er loaded
                 into build/sources.sqlite
  2 map          each mapping with Morph-KGC:
                 mapping/mapping.ttl  -> build/graph.nt     (OpenAlex)
                 mapping/crossref.ttl -> build/crossref.nt  (Crossref)
                 mapping/links.ttl    -> build/links.nt     (links by key)
                 mapping/matches.ttl  -> build/matches.nt   (the matcher's links)
  3 validate     each graph + ontology/ontology.ttl against its own shapes
                 (shapes/validate.py). A link is checked with the triples of the
                 graphs it joins (CONTEXT below). Any Violation, or a shape that
                 checks nothing, in any graph stops here (exit 1), so bad data
                 never reaches the endpoint; the reports go to
                 build/shacl-report.txt (all) and build/shacl-report-{graph}.txt
  4 provenance   what this run used and made, in PROV-O -> build/provenance.ttl
                 (pipeline/provenance.py)
  5 describe     VoID of the OpenAlex graph -> build/void.ttl (the access layer
                 reads it)
  6 load         empty the endpoint, then one named graph each: graph/openalex,
                 graph/crossref, graph/links, graph/matches, graph/ontology,
                 graph/provenance. Fuseki's default graph is their union
                 (fuseki/config.ttl).
"""

import argparse
import csv
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

# One named graph per source, and one per kind of link: its name, its mapping,
# its shapes, its file in build/.
GRAPHS = (
    ("openalex", "mapping/mapping.ttl", "shapes/shapes.ttl", "graph.nt"),
    ("crossref", "mapping/crossref.ttl", "shapes/crossref-shapes.ttl", "crossref.nt"),
    ("links", "mapping/links.ttl", "shapes/links-shapes.ttl", "links.nt"),
    ("matches", "mapping/matches.ttl", "shapes/matches-shapes.ttl", "matches.nt"),
)
SOURCE_FILES = ("graph.nt", "crossref.nt")

# A link is right only if it fits the graphs it joins, so its shapes see some
# triples of those graphs too: the predicates named here, taken from both source
# graphs, and whole link graphs. Only these: the whole sources would take minutes.
TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PUB = "https://ul.edu.lb/kr/pub#"
CONTEXT = {
    "links": {"predicates": (TYPE, PUB + "author"), "graphs": ()},
    "matches": {"predicates": (TYPE, PUB + "hasAuthorship", PUB + "author", PUB + "orcid", PUB + "isOpenAccess"),
                "graphs": ("links.nt",)},
}

# The links of mapping/er, as tables for the link mappings (mapping/links.ttl,
# mapping/matches.ttl). links_by_key.csv's columns left and right are SQL words,
# so they become left_node and right_node.
ER_TABLES = (
    ("er_links", "mapping/er/links_by_key.csv", ["kind", "left_node", "right_node", "rule", "evidence"]),
    ("er_matches", "mapping/er/authorship_links.csv",
     ["openalex_authorship", "crossref_authorship", "score", "name", "initial", "position"]),
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
    for table, path, columns in ER_TABLES:
        with open(ROOT / path, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))[1:]          # the first row is the header
        con.execute(f"CREATE TABLE {table} ({', '.join(c + ' TEXT' for c in columns)})")
        con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(columns))})", rows)
    con.commit()
    con.close()
    step(1, "source: our data, data/lu.sql, data/crossref.sql and the links of mapping/er")
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


def context(name):
    """The triples of other graphs that the shapes of graph/{name} look at, as N-Triples."""
    spec = CONTEXT.get(name)
    if spec is None:
        return ""
    wanted = {f"<{p}>" for p in spec["predicates"]}
    lines = []
    for filename in SOURCE_FILES:
        with open(BUILD / filename, encoding="utf-8") as f:
            lines += [line for line in f if line.split(" ", 2)[1] in wanted]
    for filename in spec["graphs"]:
        lines += (BUILD / filename).read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(lines)


def gate(name, graph_path, shapes_file):
    """Validate one graph against its shapes; return the counts per severity,
    the shapes that checked nothing, and the report lines."""
    sys.path.insert(0, str(ROOT / "shapes"))
    from validate import check
    data = Graph().parse(graph_path, format="nt").parse(ROOT / "ontology" / "ontology.ttl")
    size = len(data)
    data.parse(data=context(name), format="nt")
    extra = f", with {len(data) - size:,} triples of the graphs it links" if len(data) > size else ""
    shapes = Graph().parse(ROOT / shapes_file)
    counts, empty, lines = check(data, shapes)
    step(3, f"validate: graph/{name} against {shapes_file}{extra}: {counts['Violation']:,} Violation, "
            f"{counts['Warning']:,} Warning, {counts['Info']:,} Info")
    print("\n".join(lines), flush=True)
    head = f"== graph/{name} ({size:,} triples with the ontology{extra}) against {shapes_file}"
    return counts, empty, [head] + lines + [""]


def stop_if_failed(results):
    report = [line for _, _, lines in results.values() for line in lines]
    (BUILD / "shacl-report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    for name, (_, _, lines) in results.items():          # and one file per graph
        (BUILD / f"shacl-report-{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
    for name, mapping, _, filename in GRAPHS:
        files[name], sizes[name] = materialize(db_url, name, mapping, filename)
    results = {name: gate(name, files[name], shapes) for name, _, shapes, _ in GRAPHS}
    stop_if_failed(results)
    record_provenance(sizes, results, started)
    describe(files["openalex"])
    if not a.no_load:
        load(files)
    print("done")


if __name__ == "__main__":
    main()
