"""Validate the graph against our SHACL shapes, and print the report as a
work queue: how many nodes each shape checks, then one line per shape and
problem, with a count and examples.

    python shapes/validate.py                         # build/graph.nt + ontology, shapes/shapes.ttl
    python shapes/validate.py --shapes my-draft.ttl   # another shapes file
    python shapes/validate.py --save shapes/validation-report.txt

Run from the repository root, after python pipeline/run.py --no-load (which
writes build/graph.nt). pipeline/run.py uses check() below as its gate.

The gate fails (exit 1) when
  - any result has severity Violation, or
  - a shape has 0 focus nodes: it checks nothing, so "no Violation" would
    mean nothing (the targeting trap, Session 4).
Warnings and Info are printed but do not stop the gate. SHACL itself says
conforms = False as soon as there is any result, of any severity.
"""

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from pyshacl import validate
from rdflib import RDF, RDFS, Graph, Namespace

ROOT = Path(__file__).resolve().parents[1]
SH = Namespace("http://www.w3.org/ns/shacl#")
SEVERITY = {SH.Violation: "Violation", SH.Warning: "Warning", SH.Info: "Info"}
ORDER = {"Violation": 0, "Warning": 1, "Info": 2}


def short(node):
    """A readable name: the key at the end of one of our IRIs."""
    s = str(node)
    for base in ("https://ul.edu.lb/kr/id/", "https://ul.edu.lb/kr/pub#", "https://ul.edu.lb/kr/shapes#",
                 "http://www.w3.org/ns/shacl#"):
        if s.startswith(base):
            s = s[len(base):]
    return s.replace("/openalex/", "/")


def path_text(shapes, path):
    """sh:resultPath as text: a property, a sequence (a b), or ^inverse."""
    if path is None:
        return None
    inverse = shapes.value(path, SH.inversePath)
    if inverse is not None:
        return "^" + short(inverse)
    if (path, RDF.first, None) in shapes:
        return "(" + " ".join(short(p) for p in shapes.items(path)) + ")"
    return short(path)


def focus_nodes(data, shapes, shape):
    """The nodes a node shape targets: by class (with subclasses, through the
    rdfs:subClassOf triples of the ontology), as subject or object of a
    property, or named one by one."""
    nodes = set()
    for cls in shapes.objects(shape, SH.targetClass):
        for sub in data.transitive_subjects(RDFS.subClassOf, cls):
            nodes.update(data.subjects(RDF.type, sub))
    for p in shapes.objects(shape, SH.targetSubjectsOf):
        nodes.update(data.subjects(p, None))
    for p in shapes.objects(shape, SH.targetObjectsOf):
        nodes.update(data.objects(None, p))
    nodes.update(shapes.objects(shape, SH.targetNode))
    return nodes


def check(data, shapes):
    """Validate; return (results per severity, shapes with 0 focus nodes, the
    report as text lines)."""
    lines = []
    labels = {s: str(shapes.value(s, RDFS.label) or short(s)) for s in shapes.subjects(RDF.type, SH.NodeShape)}
    targeted = [s for s in labels if any(shapes.triples((s, t, None)) for t in
                (SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.targetNode))]
    empty = []
    for s in sorted(targeted, key=lambda s: labels[s]):
        n = len(focus_nodes(data, shapes, s))
        if n == 0:
            empty.append(labels[s])
        flag = "   <- targets nothing: this shape checks nothing" if n == 0 else ""
        lines.append(f"  focus nodes {n:>7,}  {labels[s]}{flag}")

    t0 = time.time()
    # No inference: the graph is checked as it is. conforms is SHACL's own
    # answer (False as soon as there is any result); the gate looks at severities.
    conforms, report, _ = validate(data, shacl_graph=shapes, inference="none")
    secs = time.time() - t0

    groups, messages = defaultdict(list), {}
    for r in report.subjects(RDF.type, SH.ValidationResult):
        sev = SEVERITY.get(report.value(r, SH.resultSeverity), "?")
        src = report.value(r, SH.sourceShape)
        parent = shapes.value(predicate=SH.property, object=src)  # a property shape's node shape
        shape = labels.get(parent if parent is not None else src, short(src))
        comp = short(report.value(r, SH.sourceConstraintComponent)).replace("ConstraintComponent", "")
        path = path_text(shapes, shapes.value(src, SH.path)) if parent is not None else None
        key = (sev, shape, f"{comp} on {path}" if path else comp, src)  # one line per rule
        groups[key].append(report.value(r, SH.focusNode))
        messages.setdefault(key, report.value(r, SH.resultMessage))

    by_sev = Counter()
    for (sev, _, _, _), nodes in groups.items():
        by_sev[sev] += len(nodes)
    lines.append(f"\nvalidated in {secs:.0f} s. conforms (SHACL): {conforms}. "
                 + ", ".join(f"{by_sev[s]:,} {s}" for s in ORDER))
    for key, nodes in sorted(groups.items(), key=lambda kv: (ORDER.get(kv[0][0], 3), -len(kv[1]))):
        sev, shape, what, _ = key
        ex = ", ".join(short(n) for n in sorted(set(nodes), key=str)[:3])
        lines.append(f"  {sev:<9} {len(nodes):>6,}  {shape} · {what}   e.g. {ex}")
        lines.append(f"                    {messages[key]}")
    return by_sev, empty, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shapes", default=str(ROOT / "shapes" / "shapes.ttl"))
    ap.add_argument("--data", action="append", help="data file (repeat to merge several); "
                    "default build/graph.nt and ontology/ontology.ttl")
    ap.add_argument("--save", help="also write the report to this file")
    a = ap.parse_args()

    files = a.data or [str(ROOT / "build" / "graph.nt"), str(ROOT / "ontology" / "ontology.ttl")]
    data = Graph()
    for f in files:
        if not Path(f).exists():
            sys.exit(f"{f} not found: run python pipeline/run.py --no-load first.")
        data.parse(f)
    shapes = Graph().parse(a.shapes)

    counts, empty, lines = check(data, shapes)
    violations = counts["Violation"]
    head = [f"data: {len(data):,} triples from {', '.join(Path(f).name for f in files)}",
            f"shapes: {Path(a.shapes).name}"]
    if violations or empty:
        why = [f"{violations:,} Violation"] if violations else []
        why += [f"{len(empty)} shape(s) with 0 focus nodes"] if empty else []
        tail = f"\nGATE: FAIL, {' and '.join(why)}. Exit code 1."
    else:
        tail = "\nGATE: PASS, no Violation, every shape checks something."
    text = "\n".join(head + lines + [tail])
    print(text)
    if a.save:
        Path(a.save).write_text(text + "\n", encoding="utf-8")
    sys.exit(1 if violations or empty else 0)


if __name__ == "__main__":
    main()
