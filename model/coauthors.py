"""Link prediction: which researchers will write together for the first time?
Learned from the years before, tested on the new co-authorships of a later
year (Session 6, D18).

    python model/coauthors.py --settings   first: choose the embedding, on 2024 only (about 15 minutes)
    python model/coauthors.py              then the models, both rounds (about 10 minutes)

Run from the repository root after python pipeline/run.py (it reads
build/graph.nt). Writes model/results/coauthors.txt (or coauthors-settings.txt).

Two rounds, the same models in each:
  validation   facts before 2024, the new pairs of 2024. The embedding and its
               size are chosen here (--settings, run first), never on 2025.
  test         facts before 2025, the new pairs of 2025: the result we report.

A co-authorship is two authors on one paper of at most 25 authors (CAP): a
byline of 100 says little about who works with whom, and one such paper would
add 4,950 pairs. A new pair is one first seen in the test year, between two
authors who both had a co-author before it (an author with none cannot be
ranked by anything).

For each new pair (a, b), and again for (b, a), every model ranks all
candidate authors as a's partner, and we keep the rank of b. Filtered: a's
earlier co-authors and its other new partners are not counted against the
model. Ties share the middle of their places (learning_utils.realistic_rank).
Scores: MRR, Hits@10 and Hits@100, for all the queries and split by whether
the two already had a co-author in common.

The models, from the simplest:
  random              every candidate equally likely
  popularity          the authors with the most co-authors first
  common neighbours   how many co-authors a and the candidate share
  Adamic-Adar         the same, but a shared co-author who has few co-authors
                      counts more (Adamic and Adar 2003; Liben-Nowell and
                      Kleinberg 2007, on co-authorship)
  embedding           a knowledge graph embedding (PyKEEN) of the years before:
                      who wrote with whom, at which institution, in which
                      venue, on which topic. Three seeds. Which one (TransE,
                      DistMult or RotatE) and its size: the best MRR on 2024.
                      Co-authorship is symmetric: DistMult's score is, RotatE
                      can learn it (a half turn), TransE cannot (h + r = t and
                      t + r = h leave r = 0).
"""

import argparse
import datetime
import importlib.metadata as md
import itertools
import math
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyoxigraph as ox
import torch

ROOT = Path(__file__).resolve().parents[1]
# PyKEEN keeps a cache through PyStow: keep it in build/, not in the home folder
os.environ.setdefault("PYSTOW_HOME", str(ROOT / "build" / "model" / "pystow"))

from pykeen.models import DistMult, RotatE, TransE  # noqa: E402
from pykeen.training import SLCWATrainingLoop  # noqa: E402
from pykeen.triples import TriplesFactory  # noqa: E402

from learning_utils import hits_at_k, mrr, realistic_rank  # noqa: E402

GRAPH = ROOT / "build" / "graph.nt"
RESULTS = ROOT / "model" / "results"
ROUNDS = [("validation", 2024), ("test", 2025)]
CAP = 25
SEEDS = range(3)
EMBEDDINGS = {"TransE": TransE, "DistMult": DistMult, "RotatE": RotatE}
DIMS = (64, 128)
# The embeddings and sizes tried on the validation round (--settings). The best
# MRR on 2024 is written to results/coauthors-settings.txt, and the models read
# it there: what is chosen on 2024 is what runs on 2025, on any computer.
EPOCHS, BATCH, LR = 100, 1024, 0.005
PREFIX = "PREFIX pub: <https://ul.edu.lb/kr/pub#>\n"

# One row per authorship: its author, paper, year and byline size; the
# institution, venue and topic when the graph has them.
AUTHORSHIPS = PREFIX + """SELECT ?author ?paper ?year ?size ?inst ?venue ?topic WHERE {
  { SELECT ?paper (COUNT(?x) AS ?size) WHERE { ?paper pub:hasAuthorship ?x } GROUP BY ?paper }
  ?paper pub:publicationYear ?year ; pub:hasAuthorship ?a .
  ?a pub:author ?author .
  OPTIONAL { ?a pub:affiliation ?inst }
  OPTIONAL { ?paper pub:publishedIn ?venue }
  OPTIONAL { ?paper pub:hasTopic ?topic }
}"""


def short(iri):
    return iri.rsplit("/", 1)[-1]


def read_graph():
    store = ox.Store()
    store.bulk_load(path=str(GRAPH), format=ox.RdfFormat.N_TRIPLES)
    rows = [[None if t is None else t.value for t in r] for r in store.query(AUTHORSHIPS)]
    return sorted(rows, key=lambda r: tuple(v or "" for v in r))      # the same order on every computer


def coauthor_pairs(rows):
    """Each pair of authors on a paper of at most CAP authors, with the first
    year they wrote together."""
    on_paper, year, size = defaultdict(set), {}, {}
    for author, paper, y, n, *_ in rows:
        on_paper[paper].add(author)
        year[paper], size[paper] = int(y), int(n)
    first = {}
    for paper, authors in on_paper.items():
        if size[paper] <= CAP:
            for pair in itertools.combinations(sorted(authors), 2):
                first[pair] = min(first.get(pair, 9999), year[paper])
    return first


class Round:
    """One round: what is known before `year`, and the new pairs of `year`."""

    def __init__(self, first, year):
        self.past = defaultdict(set)
        for (a, b), y in first.items():
            if y < year:
                self.past[a].add(b)
                self.past[b].add(a)
        self.cands = sorted(self.past)                     # the authors with a co-author before the year
        self.index = {a: i for i, a in enumerate(self.cands)}
        self.new = defaultdict(set)
        for (a, b), y in first.items():
            if y == year and a in self.index and b in self.index:
                self.new[a].add(b)
                self.new[b].add(a)
        self.queries = [(a, b) for a in sorted(self.new) for b in sorted(self.new[a])]
        self.shared = np.array([bool(self.past[a] & self.past[b]) for a, b in self.queries])

    def mask(self, a, b):
        """The candidates for the query (a, b): everyone but a, its earlier
        co-authors and its other new partners (filtered); b is in."""
        m = np.ones(len(self.cands), bool)
        m[[self.index[c] for c in self.past[a] | self.new[a] | {a}]] = False
        m[self.index[b]] = True
        return m

    def ranks(self, scorer):
        """The rank of b for every query. The queries are sorted by a, so each
        author's scores are computed once."""
        out, last, s = [], None, None
        for a, b in self.queries:
            if a != last:
                last, s = a, scorer(a)
            out.append(realistic_rank(s, self.index[b], self.mask(a, b)))
        return np.array(out)

    # ------------------------------------------------------------ the baselines
    def degree(self):
        d = np.array([len(self.past[c]) for c in self.cands], float)
        return lambda a: d

    def neighbours(self, adamic):
        def score(a):
            s = np.zeros(len(self.cands))
            for n in self.past[a]:
                w = 1.0 if not adamic else (1 / math.log(len(self.past[n])) if len(self.past[n]) > 1 else 0.0)
                for m in self.past[n]:
                    s[self.index[m]] += w
            return s
        return score


def kg_triples(rows, first, before):
    """The knowledge graph the embedding learns from: every fact of the years
    before `before`. Co-authorship both ways (it is symmetric)."""
    out = set()
    for (a, b), y in first.items():
        if y < before:
            out |= {(short(a), "coauthorWith", short(b)), (short(b), "coauthorWith", short(a))}
    for author, _, y, _, inst, venue, topic in rows:
        if int(y) < before:
            if inst:
                out.add((short(author), "affiliatedWith", short(inst)))
            if venue:
                out.add((short(author), "publishesIn", short(venue)))
            if topic:
                out.add((short(author), "worksOn", short(topic)))
    return sorted(out)


def embedding(triples, rnd, name, dim, seed):
    """Train the embedding on the triples; return a scorer for the round's
    candidates: author -> a score for each candidate as its co-author."""
    tf = TriplesFactory.from_labeled_triples(np.array(triples))
    model = EMBEDDINGS[name](triples_factory=tf, embedding_dim=dim, random_seed=seed)
    loop = SLCWATrainingLoop(model=model, triples_factory=tf,
                             optimizer=torch.optim.Adam(model.get_grad_params(), lr=LR))
    loop.train(triples_factory=tf, num_epochs=EPOCHS, batch_size=BATCH, use_tqdm=False)
    model.eval()
    rel = tf.relation_to_id["coauthorWith"]
    cand_ids = np.array([tf.entity_to_id[short(c)] for c in rnd.cands])

    def score(a):
        with torch.no_grad():
            return model.score_t(torch.tensor([[tf.entity_to_id[short(a)], rel]]))[0].numpy()[cand_ids]
    return score, tf.num_triples


def line(name, r, shared):
    return (f"  {name:<24} MRR {mrr(r):.3f}  Hits@10 {hits_at_k(r, 10):.3f}  Hits@100 {hits_at_k(r, 100):.3f}"
            f"   shared co-author: MRR {mrr(r[shared]):.3f}  none: MRR {mrr(r[~shared]):.3f}")


def header(first):
    versions = ", ".join(f"{p} {md.version(p)}" for p in ("pykeen", "torch", "pyoxigraph"))
    return [f"python model/coauthors.py   ({versions}, {datetime.date.today()}; CPU)",
            f"co-authorships: {len(first):,} pairs of authors on papers of at most {CAP} authors. "
            f"Embeddings: {EPOCHS} epochs, batch {BATCH}, learning rate {LR}."]


def describe(name, year, rnd):
    return (f"{name}: facts before {year}; {len(rnd.cands):,} candidate authors; {len(rnd.queries) // 2:,} new "
            f"pairs in {year}, ranked both ways: {len(rnd.queries):,} queries, {int(rnd.shared.sum()):,} with a "
            f"co-author in common")


def settings(rows, first):
    """The three embeddings at two sizes, validation round only, seed 0."""
    name, year = ROUNDS[0]
    rnd, triples = Round(first, year), kg_triples(rows, first, year)
    lines = header(first) + [describe(name, year, rnd), "the embeddings, validation round only, seed 0:"]
    tried = []
    for order, (model, dim) in enumerate(itertools.product(EMBEDDINGS, DIMS)):
        score, _ = embedding(triples, rnd, model, dim, 0)
        r = rnd.ranks(score)
        tried.append((-round(mrr(r), 3), dim, order, model))
        lines.append(line(f"{model}, dimension {dim}", r, rnd.shared))
        print(lines[-1], flush=True)
    _, dim, _, model = min(tried)                  # the best MRR; a tie: the smaller, then the first listed
    lines.append(f"chosen: {model}, dimension {dim}")
    return "coauthors-settings.txt", lines


def chosen():
    """The embedding --settings chose on 2024 (the last line of coauthors-settings.txt)."""
    path = RESULTS / "coauthors-settings.txt"
    found = re.search(r"^chosen: (\w+), dimension (\d+)$",
                      path.read_text(encoding="utf-8") if path.exists() else "", re.MULTILINE)
    if not found or found[1] not in EMBEDDINGS:
        raise SystemExit("No embedding chosen yet: run python model/coauthors.py --settings first (2024 only).")
    return found[1], int(found[2])


def models(rows, first):
    model, dim = chosen()
    lines = header(first) + [f"{model}: dimension {dim} (chosen on 2024: results/coauthors-settings.txt), "
                             f"seeds {SEEDS.start}-{SEEDS.stop - 1}.", ""]
    for name, year in ROUNDS:
        rnd, triples = Round(first, year), kg_triples(rows, first, year)
        lines.append(describe(name, year, rnd))
        n = rnd.mask(*rnd.queries[0]).sum()
        lines.append(line("random", np.array([(rnd.mask(a, b).sum() + 1) / 2 for a, b in rnd.queries]), rnd.shared))
        lines.append(line("popularity", rnd.ranks(rnd.degree()), rnd.shared))
        lines.append(line("common neighbours", rnd.ranks(rnd.neighbours(adamic=False)), rnd.shared))
        lines.append(line("Adamic-Adar", rnd.ranks(rnd.neighbours(adamic=True)), rnd.shared))
        print("\n".join(lines[-5:]), flush=True)
        runs = []
        for seed in SEEDS:
            score, n_triples = embedding(triples, rnd, model, dim, seed)
            runs.append(rnd.ranks(score))
            lines.append(line(f"{model}, seed {seed}", runs[-1], rnd.shared))
            print(lines[-1], flush=True)
        m, h = [mrr(r) for r in runs], [hits_at_k(r, 10) for r in runs]
        lines.append(f"  {f'{model}, the {len(SEEDS)} seeds':<24} MRR {np.mean(m):.3f} ({min(m):.3f} to {max(m):.3f})  "
                     f"Hits@10 {np.mean(h):.3f} ({min(h):.3f} to {max(h):.3f})")
        lines += [f"  ({model} learned from {n_triples:,} triples; about {n:,} candidates per query)", ""]
    return "coauthors.txt", lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", action="store_true", help="choose the embedding on 2024 only")
    rows = read_graph()
    first = coauthor_pairs(rows)
    name, lines = settings(rows, first) if ap.parse_args().settings else models(rows, first)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"written: model/results/{name}")


if __name__ == "__main__":
    main()
