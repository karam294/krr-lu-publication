"""Check that the mapping reproduces the paper written by hand (Session 2, step 4d).

Every triple of mapping/one_paper_by_hand.ttl must be in build/graph.nt. For the
same subjects the graph may hold more only where the hand file was short on
purpose: the paper's other references (pub:cites).

    python mapping/check_one_paper.py        after pipeline/run.py
"""
import sys
from pathlib import Path

from rdflib import Graph, URIRef

ROOT = Path(__file__).resolve().parents[1]
CITES = URIRef("https://ul.edu.lb/kr/pub#cites")

hand = Graph().parse(ROOT / "mapping" / "one_paper_by_hand.ttl")
subjects = {f"<{s}>" for s in hand.subjects()}

# Read only the lines of the big graph whose subject is one of ours.
with open(ROOT / "build" / "graph.nt", encoding="utf-8") as f:
    lines = [line for line in f if line.split(" ", 1)[0] in subjects]
mapped = Graph().parse(data="".join(lines), format="nt")

missing = set(hand) - set(mapped)
extra = set(mapped) - set(hand)
other = [t for t in extra if t[1] != CITES]

print(f"hand-written: {len(hand)} triples; mapped, same subjects: {len(mapped)}")
print(f"missing from the mapping: {len(missing)}")
for t in sorted(missing):
    print("   ", *t)
print(f"extra in the mapping: {len(extra)} ({len(extra) - len(other)} other references, {len(other)} anything else)")
for t in sorted(other):
    print("   ", *t)
if missing or other:
    sys.exit("The mapping does not reproduce the hand-written paper.")
print("OK: the mapping reproduces the hand-written paper.")