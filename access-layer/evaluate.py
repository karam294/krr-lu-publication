"""Score the access layer on the test set, in three settings, the way
TEXT2SPARQL scores it: for each question, the set of values the query
returns against the set the right query returns (precision, recall, F1).

    python evaluate.py                      the three settings
    python evaluate.py --setting repair     one setting only
    python evaluate.py --questions my_questions.yaml   add your own questions
    python evaluate.py --save results/score-before.txt also write it all to a file

Run from access-layer/. A question not answered right (F1 below 1) is
printed with the query the layer ran, so the score file shows each mistake.

Settings: schema (the schema only), examples (plus the 3 closest example
queries), repair (plus the check and up to 2 repairs). A refusal scores 0 on
a question the graph can answer, and counts as right on one it cannot.
"""
import argparse
import datetime
import os
import re
import statistics
from pathlib import Path

from access_layer import CHECKS, RULES_FILE, RULES_ID, answer, load_examples, model_name, open_store, run
from questions_utils import load_questions
from score_utils import answer_set, set_f1

SETTINGS = {"schema": dict(use_examples=False, repair=False),
            "examples": dict(use_examples=True, repair=False),
            "repair": dict(use_examples=True, repair=True)}


def evaluate(questions, store, examples, setting, checks, verbose=True):
    f1s, refused_right, refused_wrong, repaired, lines = [], 0, 0, 0, []
    for q in questions:
        r = answer(q["question"], store, examples, checks=checks, **SETTINGS[setting])
        tries = len(r["attempts"])
        repaired += tries > 1 and r["refused"] is None
        if q["refuse"]:
            ok = r["refused"] is not None
            refused_right += ok
            lines.append(f"  {q['id']:>2}  {'refused, right' if ok else 'answered, should refuse':24} {q['question']}")
            continue
        if r["refused"]:
            refused_wrong += 1
            f1 = 0.0
        else:
            f1 = set_f1(answer_set(r["rows"]), answer_set(run(store, q["gold"])))
        f1s.append(f1)
        lines.append(f"  {q['id']:>2}  F1 {f1:.2f}  tries {tries}{'  refused' if r['refused'] else ''}".ljust(33) + q["question"])
        if f1 < 1:                                 # the mistake, for the score file: what the layer ran or said
            query = re.sub(r"(?m)^PREFIX .*$|FROM\s*<[^>]*>", "", r["query"] or "")    # the layer's own lines
            said = r["refused"] or re.sub(r"\s+", " ", query).strip()
            lines.append(f"        {said[:300]}")
    n_refuse = sum(1 for q in questions if q["refuse"])
    summary = (f"{setting:9} mean F1 {statistics.fmean(f1s):.3f} on {len(f1s)} answerable questions; "
               f"refused {refused_right} of {n_refuse} it should; refused {refused_wrong} it should not; "
               f"{repaired} answered after a repair")
    if verbose:
        OUT.extend(lines)
    OUT.append(summary)
    return statistics.fmean(f1s)


class Lines(list):
    """Every line of the run: printed as it comes, and kept for --save."""
    def append(self, line):
        print(line, flush=True)
        super().append(line)

    def extend(self, lines):
        for line in lines:
            self.append(line)


OUT = Lines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setting", choices=list(SETTINGS))
    ap.add_argument("--questions", action="append", default=[])
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--save", help="also write the run to this file (UTF-8)")
    a = ap.parse_args()
    checks = list(CHECKS)
    questions = load_questions("questions.yaml")
    for extra in a.questions:
        questions += load_questions(extra)
    store, examples = open_store(), load_examples()
    where = store if isinstance(store, str) else "build/graph.nt, in memory"
    OUT.append(f"python evaluate.py   ({datetime.date.today()}; model {model_name()}; rules {RULES_ID} "
               f"({RULES_FILE.name}); "
               f"LLM_MODE {os.environ.get('LLM_MODE', 'live')}; graph: {where})")
    OUT.append(f"{len(questions)} questions; {len(examples)} examples; checks: {', '.join(c.__name__ for c in checks)}")
    for s in ([a.setting] if a.setting else list(SETTINGS)):
        OUT.append(f"\n{s}:")
        evaluate(questions, store, examples, s, checks, verbose=not a.quiet)
    if a.save:
        Path(a.save).parent.mkdir(parents=True, exist_ok=True)
        Path(a.save).write_text("\n".join(OUT) + "\n", encoding="utf-8")
        print(f"written: {a.save}")


if __name__ == "__main__":
    main()
