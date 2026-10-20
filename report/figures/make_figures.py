"""The report's two drawn figures, from files of this repository only.

    python report/figures/make_figures.py        (from the repository root; needs matplotlib)

  learning.png      the test round (2025) of model/results/field.txt and coauthors.txt
  architecture.png  from architecture.dot, with Graphviz (nodes placed by hand):
                    neato -n2 -Tpng -Gdpi=200 report/figures/architecture.dot -o report/figures/architecture.png

Every number on learning.png is read from the results files, never typed here.
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "model" / "results"
OUT = Path(__file__).resolve().parent

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e1e0d9"
COUNT, LEARNED, LEAK = "#2a78d6", "#eb6834", "#c3c2b7"   # a count over the graph, a learned model, the leak


def test_round(path):
    """The lines of the test round (train before 2025, test 2025)."""
    text = path.read_text(encoding="utf-8")
    return text.split("\ntest:", 1)[1]


def value(block, label, metric):
    """The number after `metric` on the line that starts with `label`, and its range if it has one."""
    for line in block.splitlines():
        if line.strip().startswith(label):
            m = re.search(metric + r"\s+([\d.]+)(?:\s+\(([\d.]+) to ([\d.]+)\))?", line)
            if m:
                v = float(m.group(1))
                lo, hi = (float(m.group(2)), float(m.group(3))) if m.group(2) else (v, v)
                return v, lo, hi
    raise SystemExit(f"{label!r} with {metric} not found")


def bars(ax, rows, title, metric):
    names = [r[0] for r in rows]
    ys = range(len(rows))[::-1]
    for y, (name, (v, lo, hi), color) in zip(ys, rows):
        ax.barh(y, v, height=0.5, color=color, hatch="////" if color == LEAK else None,
                edgecolor="#fcfcfb" if color != LEAK else "#898781", linewidth=0 if color != LEAK else 0.6)
        if hi > lo:
            ax.plot([lo, hi], [y, y], color=INK, linewidth=1.2)
            ax.plot([lo, lo], [y - 0.12, y + 0.12], color=INK, linewidth=1.2)
            ax.plot([hi, hi], [y - 0.12, y + 0.12], color=INK, linewidth=1.2)
        text = f"{v:.3f}" + (f"  ({lo:.3f} to {hi:.3f})" if hi > lo else "")
        ax.text(max(v, hi) + 0.01 * ax.get_xlim()[1], y, text, va="center", fontsize=8, color=INK)
    ax.set_yticks(list(ys), names, fontsize=8.5, color=INK)
    ax.set_title(title, fontsize=10, color=INK, pad=8, fontweight="bold")
    ax.set_xlabel(metric, fontsize=8.5, color=MUTED)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED, length=0)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")


def learning():
    field = test_round(RESULTS / "field.txt")
    co = test_round(RESULTS / "coauthors.txt")
    f = [("always Medicine", value(field, "guess", "accuracy"), COUNT),
         ("the paper's row (logistic regression)", value(field, "1 ·", "accuracy"), LEARNED),
         ("GraphSAGE, 5 seeds", value(field, "3 · GraphSAGE, the", "accuracy"), LEARNED),
         ("count: its authors' earlier fields", value(field, "2 ·", "accuracy"), COUNT),
         ("the topic kept: the leak, not a model", value(field, "0 ·", "accuracy"), LEAK)]
    c = [("random", value(co, "random", "MRR"), COUNT),
         ("popularity", value(co, "popularity", "MRR"), COUNT),
         ("DistMult, 3 seeds", value(co, "DistMult, the", "MRR"), LEARNED),
         ("common neighbours", value(co, "common neighbours", "MRR"), COUNT),
         ("Adamic-Adar", value(co, "Adamic-Adar", "MRR"), COUNT)]

    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.1), facecolor="#fcfcfb")
    for ax in (a, b):
        ax.set_facecolor("#fcfcfb")
    a.set_xlim(0, 1.0)
    b.set_xlim(0, 0.1)
    bars(a, f, "A. The field of a paper, tested on 2025", "accuracy")
    bars(b, c, "B. New co-authorships, tested on 2025", "MRR (filtered, ties share their places)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=COUNT), plt.Rectangle((0, 0), 1, 1, color=LEARNED),
               plt.Rectangle((0, 0), 1, 1, facecolor=LEAK, hatch="////", edgecolor="#898781", linewidth=0.6)]
    fig.legend(handles, ["a count or a guess (no training)", "a trained model (bar: mean; line: range of the seeds)",
                         "kept only to show the leak"],
               loc="lower center", ncol=3, frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout(rect=(0, 0.08, 1, 1), w_pad=3)
    fig.savefig(OUT / "learning.png", dpi=200, facecolor=fig.get_facecolor())
    print("written:", OUT / "learning.png")


if __name__ == "__main__":
    learning()
