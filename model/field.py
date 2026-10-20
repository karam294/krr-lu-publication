"""Node classification: the research field of a paper, learned from earlier
years and tested on a later one (Session 6, D17).

    python model/field.py --settings   first: choose GraphSAGE's settings, on 2024 only (about 15 minutes)
    python model/field.py              then the models, both rounds (a few minutes)

Run from the repository root after model/build_graph.py. Writes
model/results/field.txt (or field-settings.txt).

Two rounds, the same models in each:
  validation   train on 2022-2023, test on 2024. GraphSAGE's settings (size,
               epochs, dropout) are chosen here (--settings, run first), never
               on 2025.
  test         train on 2022-2024, test on 2025: the result we report.

The models, from the simplest:
  guess        always the largest field of the training years
  0 leak       the field the paper's TOPIC had among the training papers:
               the topic's field is the answer, so wherever the topic was
               seen this is always right. Not a model: it shows why
               build_graph.py takes the topic out.
  1 row        logistic regression on the paper's own row, what the works
               table holds: type, language, open access, number of authors,
               and which venue (one column per venue)
  2 count      over the graph: the field its authors published in most, in
               the training years; else its venue's; else the largest
  3 GraphSAGE  two rounds of message passing over authors, venues,
               institutions and LU-to-LU citations (to_hetero), five seeds

Scores: accuracy, and macro-F1 (every field counts the same).
"""

import argparse
import datetime
import importlib.metadata as md
import itertools
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torch_geometric.transforms as T
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from torch_geometric.nn import SAGEConv, to_hetero

from learning_utils import scores, split_by_year

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "build" / "model" / "lu-graph.pt"
RESULTS = ROOT / "model" / "results"
ROUNDS = [("validation", (2022, 2023), 2024), ("test", (2022, 2023, 2024), 2025)]
SEEDS = range(5)
# The settings tried on the validation round (--settings). The best accuracy on
# 2024 is written to results/field-settings.txt, and the models read it there:
# what is chosen on 2024 is what runs on 2025, on any computer.
GRID = list(itertools.product([32, 64], [100, 200, 400, 800], [0.0, 0.5]))   # hidden, epochs, dropout


def load():
    b = torch.load(GRAPH, weights_only=False)
    data = b["data"]
    venue = np.full(data["paper"].num_nodes, -1)
    p, v = data["paper", "publishedIn", "venue"].edge_index.numpy()
    venue[p] = v
    authors = defaultdict(list)
    for a, p in data["author", "writes", "paper"].edge_index.numpy().T:
        authors[p].append(a)
    return b, data, b["y"].numpy(), b["year"].numpy(), venue, authors


# ---------------------------------------------------------------- 0: the leak
def topic_lookup(topic, y, train, test, largest):
    """The field of the paper's topic, as the training papers show it; the
    largest field for a topic no training paper has."""
    field_of = {topic[i]: y[i] for i in train}
    return np.array([field_of.get(topic[i], largest) for i in test])


# ---------------------------------------------------------------- 1: a table model
def row_model(x, ids, y, train, test):
    """Logistic regression on the paper's row: its features, and one column per
    venue."""
    onehot = OneHotEncoder(handle_unknown="ignore").fit(ids[train])
    rows = lambda i: sparse.hstack([sparse.csr_matrix(x[i]), onehot.transform(ids[i])]).tocsr()
    model = LogisticRegression(max_iter=3000).fit(rows(train), y[train])
    return model.predict(rows(test))


# ---------------------------------------------------------------- 2: a count over the graph
def count_model(y, venue, authors, train, test, largest):
    """For each test paper: the field its authors published in most among the
    training papers; else the field its venue had most; else the largest."""
    by_author, by_venue = defaultdict(Counter), defaultdict(Counter)
    for i in train:
        for a in authors[i]:
            by_author[a][y[i]] += 1
        if venue[i] >= 0:
            by_venue[venue[i]][y[i]] += 1
    out = []
    for i in test:
        votes = Counter()
        for a in authors[i]:
            votes.update(by_author.get(a, {}))
        if not votes:
            votes = by_venue.get(venue[i], Counter())
        out.append(min(votes, key=lambda f: (-votes[f], f)) if votes else largest)   # a tie: the lower id
    return np.array(out)


# ---------------------------------------------------------------- 3: GraphSAGE
class SAGE(torch.nn.Module):
    """Two GraphSAGE layers and a score per field. (-1, -1): sizes read from the data."""

    def __init__(self, n_fields, hidden, dropout):
        super().__init__()
        self.conv1 = SAGEConv((-1, -1), hidden)
        self.conv2 = SAGEConv((-1, -1), hidden)
        # A module, not torch.nn.functional.dropout(h, p, self.training): to_hetero
        # traces forward() once, and would freeze that call in training mode, so
        # the model would drop half its signal while being tested too.
        self.dropout = torch.nn.Dropout(dropout)
        self.score = torch.nn.Linear(hidden, n_fields)

    def forward(self, x, edge_index):  # the name edge_index matters to to_hetero
        h = self.dropout(self.conv1(x, edge_index).relu())
        h = self.conv2(h, edge_index).relu()
        return self.score(h)


class FieldModel(torch.nn.Module):
    """A learned vector for each author, venue and institution (they have no
    features), then SAGE copied once per kind of edge by to_hetero. The vectors
    start at zero: a node no training paper reaches stays zero, "unknown",
    instead of a random vector."""

    def __init__(self, data, n_fields, hidden, dropout):
        super().__init__()
        self.vectors = torch.nn.ModuleDict({k: torch.nn.Embedding(data[k].num_nodes, hidden)
                                            for k in ("author", "venue", "institution")})
        for e in self.vectors.values():
            torch.nn.init.zeros_(e.weight)
        self.gnn = to_hetero(SAGE(n_fields, hidden, dropout), data.metadata(), aggr="sum")

    def forward(self, data):
        x = {"paper": data["paper"].x, **{k: e.weight for k, e in self.vectors.items()}}
        return self.gnn(x, data.edge_index_dict)["paper"]


def gnn_model(graph, y, train, test, n_fields, seed, hidden, epochs, dropout):
    """Train on the training papers' labels only; predict the test papers. The
    graph holds every paper, as the year being predicted has them (its papers,
    their authors and venues), but no test label ever reaches the loss."""
    torch.manual_seed(seed)
    model = FieldModel(graph, n_fields, hidden, dropout)
    model(graph)                                   # one pass to size the layers
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    target = torch.tensor(y)
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        torch.nn.functional.cross_entropy(model(graph)[train], target[train]).backward()
        opt.step()
    model.eval()                                   # dropout off
    with torch.no_grad():
        return model(graph)[test].argmax(1).numpy(), sum(q.numel() for q in model.parameters())


def line(name, s, note=""):
    return f"  {name:<42} accuracy {s['accuracy']:.3f}  macro-F1 {s['macro-F1']:.3f}{note}"


def header(b, y):
    versions = ", ".join(f"{p} {md.version(p)}" for p in ("torch", "torch-geometric", "scikit-learn"))
    return [f"python model/field.py   ({versions}, {datetime.date.today()}; CPU)",
            f"{int((y >= 0).sum()):,} papers with a field, {len(b['fields'])} fields."]


def settings():
    """GraphSAGE on the validation round only, for each setting, two seeds; the
    best is written last, as the line field.py reads."""
    b, data, y, year, venue, authors = load()
    graph = T.ToUndirected()(data)
    train, test = split_by_year(year, y, *ROUNDS[0][1:])
    lines = header(b, y) + ["settings of GraphSAGE, validation round only (train 2022-2023, test 2024), "
                            "seeds 0 and 1, mean:"]
    tried = []
    for hidden, epochs, dropout in GRID:
        runs = [scores(y[test], gnn_model(graph, y, train, test, len(b["fields"]), s, hidden, epochs, dropout)[0])
                for s in (0, 1)]
        acc, f1 = np.mean([r["accuracy"] for r in runs]), np.mean([r["macro-F1"] for r in runs])
        tried.append((-round(acc, 3), hidden, epochs, dropout))
        lines.append(f"  hidden {hidden:>2}, {epochs:>3} epochs, dropout {dropout}   accuracy {acc:.3f}  macro-F1 {f1:.3f}")
        print(lines[-1], flush=True)
    _, hidden, epochs, dropout = min(tried)        # the best accuracy; a tie: smaller, then shorter, then less dropout
    lines.append(f"chosen: hidden {hidden}, epochs {epochs}, dropout {dropout}")
    return "field-settings.txt", lines


def chosen():
    """The settings --settings chose on 2024 (the last line of field-settings.txt)."""
    path = RESULTS / "field-settings.txt"
    found = re.search(r"^chosen: hidden (\d+), epochs (\d+), dropout ([\d.]+)$",
                      path.read_text(encoding="utf-8") if path.exists() else "", re.MULTILINE)
    if not found:
        raise SystemExit("No settings chosen yet: run python model/field.py --settings first (2024 only).")
    return int(found[1]), int(found[2]), float(found[3])


def models():
    b, data, y, year, venue, authors = load()
    graph = T.ToUndirected()(data)                 # messages flow both ways along every link
    x, topic, fields = data["paper"].x.numpy(), b["topic"].numpy(), b["fields"]
    hidden, epochs, dropout = chosen()
    lines = header(b, y) + [f"GraphSAGE: hidden {hidden}, {epochs} epochs, dropout {dropout} (chosen on 2024: "
                            f"results/field-settings.txt), seeds {SEEDS.start}-{SEEDS.stop - 1}.", ""]
    for name, train_years, test_year in ROUNDS:
        train, test = split_by_year(year, y, train_years, test_year)
        largest = Counter(y[train]).most_common(1)[0][0]
        yt = y[test]
        trained_authors = {a for i in train for a in authors[i]}
        known = np.array([any(a in trained_authors for a in authors[i]) for i in test])
        seen_topic = np.isin(topic[test], topic[train])
        lines.append(f"{name}: train {train_years[0]}-{train_years[-1]} ({len(train):,} papers), test {test_year} "
                     f"({len(test):,} papers; {known.mean():.0%} have an author from the training years)")
        lines.append(line(f"guess: always {fields[largest]}", scores(yt, np.full(len(test), largest))))
        leak = topic_lookup(topic, y, train, test, largest)
        lines.append(line("0 · the topic kept (the leak)", scores(yt, leak),
                          f"   on the {seen_topic.mean():.0%} whose topic is in training: accuracy "
                          f"{np.mean(leak[seen_topic] == yt[seen_topic]):.3f}"))
        lines.append(line("1 · the paper's row (logistic regression)",
                          scores(yt, row_model(x, venue[:, None], y, train, test))))
        lines.append(line("2 · count: its authors' earlier fields",
                          scores(yt, count_model(y, venue, authors, train, test, largest))))
        runs = []
        for seed in SEEDS:
            pred, n_params = gnn_model(graph, y, train, test, len(fields), seed, hidden, epochs, dropout)
            runs.append(scores(yt, pred))
            lines.append(line(f"3 · GraphSAGE, seed {seed}", runs[-1]))
            print(lines[-1], flush=True)
        acc, f1 = [r["accuracy"] for r in runs], [r["macro-F1"] for r in runs]
        lines.append(f"  {f'3 · GraphSAGE, the {len(SEEDS)} seeds':<42} accuracy {np.mean(acc):.3f} ({min(acc):.3f} to "
                     f"{max(acc):.3f})  macro-F1 {np.mean(f1):.3f} ({min(f1):.3f} to {max(f1):.3f})")
        lines += [f"  ({n_params:,} parameters)", ""]
    return "field.txt", lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", action="store_true", help="choose GraphSAGE's settings on 2024 only")
    name, lines = settings() if ap.parse_args().settings else models()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"written: model/results/{name}")


if __name__ == "__main__":
    main()
