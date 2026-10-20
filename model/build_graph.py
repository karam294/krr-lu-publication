"""Turn our knowledge graph into the shape a graph neural network reads (Session 6):
one table of features per kind of node, one list of links per kind of edge
(PyTorch Geometric's HeteroData), as the course's build_graph.py does.

    python model/build_graph.py

Run from the repository root, after python pipeline/run.py (it reads
build/graph.nt, the OpenAlex graph). About 20 seconds. Writes
build/model/lu-graph.pt and model/results/build-graph.txt.

Every fact the model may see is a SPARQL query below, run on the graph (as in
ontology/run_cqs.py). Nothing comes from the tables directly.

  nodes   paper 5,211, author, venue, institution. Not topic: see the label.
  edges   author writes paper, paper publishedIn venue, paper cites paper (LU
          to LU only), paper withInstitution institution (an affiliation of
          one of its authors)
  x       what a paper is, known the day it is published: its type, its
          language, open access or not, how many authors. The other kinds of
          node have no features: the model learns one vector for each.
  label   the paper's research field: paper pub:hasTopic topic, topic pub:field
          (26 fields). Kept apart, in y. The topic is the answer (its field IS
          the label), so no topic is a node and no hasTopic is an edge. The
          topic of each paper is still saved, apart, for two uses only: the
          leak demonstration of field.py, and coauthors.py, which predicts
          something else.
  year    each paper's publicationYear: the split by time (D17).
"""

import datetime
import importlib.metadata as md
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pyoxigraph as ox
import torch
from torch_geometric.data import HeteroData

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "graph.nt"
OUT = ROOT / "build" / "model" / "lu-graph.pt"
REPORT = ROOT / "model" / "results" / "build-graph.txt"
PREFIX = "PREFIX pub: <https://ul.edu.lb/kr/pub#>\n"

PAPERS = PREFIX + """SELECT ?paper ?year ?type ?oa ?lang (COUNT(?a) AS ?authors) WHERE {
  ?paper pub:publicationYear ?year ; a ?type ; pub:isOpenAccess ?oa .
  OPTIONAL { ?paper pub:language ?lang }
  OPTIONAL { ?paper pub:hasAuthorship ?a }
} GROUP BY ?paper ?year ?type ?oa ?lang"""
WRITES = PREFIX + "SELECT DISTINCT ?author ?paper WHERE { ?paper pub:hasAuthorship ?a . ?a pub:author ?author }"
NAMED = PREFIX + "SELECT (COUNT(*) AS ?n) WHERE { ?paper pub:hasAuthorship ?a . ?a pub:author ?author }"
VENUE = PREFIX + "SELECT ?paper ?venue WHERE { ?paper pub:publishedIn ?venue }"
INSTITUTION = PREFIX + "SELECT DISTINCT ?paper ?inst WHERE { ?paper pub:hasAuthorship ?a . ?a pub:affiliation ?inst }"
CITES = PREFIX + "SELECT ?paper ?cited WHERE { ?paper pub:cites ?cited . ?cited pub:publicationYear ?y }"
# The label, and the topic it comes from: asked separately, kept apart.
LABEL = PREFIX + "SELECT ?paper ?topic ?field WHERE { ?paper pub:hasTopic ?topic . ?topic pub:field ?field }"

LANGUAGES = ["en", "fr", "ar"]          # 4,950 of 5,211 papers; the rest is "other"


def rows(store, query):
    """The answers of a query, each value as plain text (an IRI or a literal's value)."""
    return [[None if t is None else t.value for t in r] for r in store.query(query)]


def main():
    if not GRAPH.exists():
        raise SystemExit("build/graph.nt not found: run python pipeline/run.py first.")
    store = ox.Store()
    store.bulk_load(path=str(GRAPH), format=ox.RdfFormat.N_TRIPLES)

    # 1 papers, in a fixed order (sorted IRIs): the same ids on every computer,
    # so a training seed gives the same run (the course's build_graph.py does the same)
    papers = sorted(rows(store, PAPERS))
    paper_id = {p[0]: i for i, p in enumerate(papers)}
    year = np.array([int(p[1]) for p in papers])
    types = sorted({p[2] for p in papers})

    # 2 what the model may see about a paper (x): type, language, open access, authors
    x = np.zeros((len(papers), len(types) + len(LANGUAGES) + 3), dtype=np.float32)
    for i, (_, _, t, oa, lang, n) in enumerate(papers):
        x[i, types.index(t)] = 1
        x[i, len(types) + (LANGUAGES.index(lang) if lang in LANGUAGES else len(LANGUAGES))] = 1
        x[i, -2] = 1.0 if oa == "true" else 0.0
        x[i, -1] = math.log1p(int(n))
    columns = [t.rsplit("#", 1)[-1] for t in types] + LANGUAGES + ["other language", "open access", "log(1 + authors)"]

    # 3 the other nodes and the edges, each node kind in sorted order too
    def table(pairs):
        ids = {iri: i for i, iri in enumerate(sorted({b for _, b in pairs}))}
        return ids, [(paper_id[a], ids[b]) for a, b in pairs]
    writes = sorted(rows(store, WRITES))
    author_id = {iri: i for i, iri in enumerate(sorted({a for a, _ in writes}))}
    venue_id, published_in = table(sorted(rows(store, VENUE)))
    inst_id, with_inst = table(sorted(rows(store, INSTITUTION)))
    cites = [(paper_id[a], paper_id[b]) for a, b in sorted(rows(store, CITES))]

    data = HeteroData()
    data["paper"].x = torch.tensor(x)
    for kind, ids in (("author", author_id), ("venue", venue_id), ("institution", inst_id)):
        data[kind].num_nodes = len(ids)          # no features: the model learns a vector per node
    edges = {("author", "writes", "paper"): [(author_id[a], paper_id[p]) for a, p in writes],
             ("paper", "publishedIn", "venue"): published_in,
             ("paper", "cites", "paper"): cites,
             ("paper", "withInstitution", "institution"): with_inst}
    for kind, pairs in edges.items():
        data[kind].edge_index = torch.tensor(np.array(pairs).T, dtype=torch.long).contiguous()

    # 4 the label, kept apart: the field of the paper's topic (-1: OpenAlex gives no topic)
    label = {p: (t, f) for p, t, f in rows(store, LABEL)}
    fields = sorted({f for _, f in label.values()})
    topics = sorted({t for t, _ in label.values()})
    y = np.array([fields.index(label[p[0]][1]) if p[0] in label else -1 for p in papers])
    topic = np.array([topics.index(label[p[0]][0]) if p[0] in label else -1 for p in papers])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"data": data, "y": torch.tensor(y), "year": torch.tensor(year), "fields": fields,
                "columns": columns, "paper_iri": [p[0] for p in papers],
                "names": {"author": sorted(author_id, key=author_id.get), "venue": sorted(venue_id, key=venue_id.get),
                          "institution": sorted(inst_id, key=inst_id.get)},
                # NOT features. The topic is the label's source: field.py uses it only to show the leak;
                # coauthors.py uses it as a link, since it predicts co-authors, not fields.
                "topic": torch.tensor(topic), "topics": topics}, OUT)

    # 5 what was built, for model/results/build-graph.txt
    named = int(rows(store, NAMED)[0][0])
    versions = ", ".join(f"{p} {md.version(p)}" for p in ("pyoxigraph", "torch", "torch-geometric"))
    count = Counter(year[y >= 0])
    top = Counter(fields[v] for v in y[y >= 0]).most_common(3)
    lines = [f"python model/build_graph.py   ({versions}, {datetime.date.today()})",
             f"read build/graph.nt: {len(store):,} triples (graph/openalex)",
             "nodes: " + ", ".join(f"{k} {data[k].num_nodes:,}" for k in ("paper", "author", "venue", "institution")),
             "edges: " + ", ".join(f"{r} {len(p):,}" for (_, r, _), p in edges.items()),
             f"  writes: one per author and paper; {named:,} authorships name an author, "
             f"{named - len(writes):,} of them an author already on that paper",
             f"paper features ({len(columns)}): " + ", ".join(columns),
             f"label: the field of the paper's topic, {len(fields)} fields; {int((y >= 0).sum()):,} papers have one, "
             f"{int((y < 0).sum())} have no topic (not used)",
             "  taken out of what the model sees: pub:hasTopic and the topics (the topic's field is the label)",
             "  largest: " + ", ".join(f"{f} {n:,}" for f, n in top),
             "papers with a label, by year: " + ", ".join(f"{y_} {count[y_]:,}" for y_ in sorted(count)),
             f"written: {OUT.relative_to(ROOT).as_posix()}"]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
