"""Entity resolution, part 2: which Crossref author is which OpenAlex authorship? (Session 5)

    python mapping/er/match_authorships.py

Run from the repository root (about a minute). Reads data/lu.sql and
data/crossref.sql. Writes mapping/er/authorship_links.csv (the links),
mapping/er/match_authorships.txt (the measurement), and, the first time only,
mapping/er/hand_sample.csv (40 links for a person to label: see the README).

A paper is in both sources (link_by_key.py, by DOI), but its authors carry no
shared key: OpenAlex writes "Rim Fayad", Crossref writes given "Rim", family
"Fayad", and the two lists may be in a different order. The method is
Fellegi and Sunter's (1969), the one of the course's lab:

1 Block: compare only the authors of the same paper (962,298 pairs instead of
  every OpenAlex authorship with every Crossref author).
2 Compare three fields; each gives an outcome:
    name      same / family in name / family close / different
    initial   same / different        (the first letter of the given name)
    position  same / near (1 or 2 places apart) / far
3 Each outcome adds a weight log2(m/u): m is how often it happens for two
  records of the same person, u for two different people. Here m and u are
  not stated by hand: they are counted on labelled pairs, the pairs where both
  sources give an ORCID (same ORCID: same person; two different ORCIDs: two
  people). The ORCID itself is never a field of the matcher.
4 Within a paper, link the best pairs first, each author at most once
  (one-to-one), and keep a link if its score reaches the threshold.

Measured honestly: the papers are split in two halves, the weights are counted
on half A only and the matcher is measured on half B only.
"""

import csv
import hashlib
import html
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict

from sources import ER, load

THRESHOLD = 4           # the score a link must reach: D13, chosen from match_authorships.txt
DRAWN_AT = 8            # the threshold when hand_sample.csv was drawn (its two groups are split there)
SHOWN = (0, 4, 8, 12, 16)
SPECIAL = str.maketrans({"ı": "i", "ø": "o", "ł": "l", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe"})
TITLES = {"dr", "prof", "pr", "md", "phd", "mr", "mrs", "ms", "mme", "obe", "jr", "sr"}   # not part of a name


# ------------------------------------------------------------------ comparing two names
def tokens(s):
    """A name as a list of lower-case words, accents and titles off:
    'Dr. Özçelık-Ünal, T.' -> ['ozcelik', 'unal', 't']."""
    s = html.unescape(s or "").translate(SPECIAL)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    return [t for t in re.findall(r"[^\W_]+", s) if t not in TITLES]


def jaro_winkler(a, b):
    """Similarity of two words, from 0 to 1 (the course lab's function)."""
    if a == b:
        return 1.0
    reach = max(len(a), len(b)) // 2 - 1
    ma, mb = [False] * len(a), [False] * len(b)
    m = 0
    for i, ca in enumerate(a):
        for j in range(max(0, i - reach), min(len(b), i + reach + 1)):
            if not mb[j] and b[j] == ca:
                ma[i] = mb[j] = True
                m += 1
                break
    if not m:
        return 0.0
    sa = [c for c, f in zip(a, ma) if f]
    sb = [c for c, f in zip(b, mb) if f]
    t = sum(x != y for x, y in zip(sa, sb)) / 2
    jaro = (m / len(a) + m / len(b) + (m - t) / m) / 3
    prefix = next((k for k in range(min(4, len(a), len(b))) if a[k] != b[k]), min(4, len(a), len(b)))
    return jaro + prefix * 0.1 * (1 - jaro)


def name_outcome(oa_name, given, family):
    o, fam, giv = tokens(oa_name), tokens(family), tokens(given)
    if not o or not fam:
        return "name unknown"
    if set(o) == set(fam + giv) or "".join(o) in ("".join(giv + fam), "".join(fam + giv)):
        return "name same"
    compact_fam = "".join(fam)
    if all(t in o for t in fam) or (len(compact_fam) >= 4 and compact_fam in "".join(o)):
        return "family in name"         # 'El Gerges' and 'ElGerges' are one family name
    if max(jaro_winkler(a, b) for a in o for b in fam + ["".join(fam)]) >= 0.9:
        return "family close"
    return "name different"


def initial_outcome(oa_name, given, family):
    o, fam, giv = tokens(oa_name), tokens(family), tokens(given)
    if not o or not giv:
        return "initial unknown"
    rest = [t for t in o if t not in fam] or o
    return "initial same" if giv[0][0] in {t[0] for t in rest} else "initial different"


def position_outcome(i, j):
    d = abs(i - j)
    return "position same" if d == 0 else "position near" if d <= 2 else "position far"


# ------------------------------------------------------------------ the data
def half(work_id):
    """Half A (0) or half B (1) of the papers, fixed by the paper's ID."""
    return int(hashlib.sha256(work_id.encode()).hexdigest(), 16) % 2


def read(con):
    oa = defaultdict(list)          # (work_id, doi) -> OpenAlex authorships
    for wid, doi, order, name, orcid, aid in con.execute(
            "SELECT w.work_id, w.doi, CAST(a.author_order AS INT), a.author_name, a.orcid, a.author_id "
            "FROM authorships a JOIN works w ON w.work_id = a.work_id "
            "JOIN cr_works c ON c.doi = w.doi AND c.found = 'True'"):
        oa[(wid, doi)].append({"order": order, "name": name, "orcid": orcid, "author_id": aid})
    cr = defaultdict(list)          # doi -> Crossref authors
    for doi, order, given, family, name, orcid in con.execute(
            "SELECT doi, CAST(author_order AS INT), given, family, name, orcid FROM cr_authors"):
        cr[doi].append({"order": order, "given": given, "family": family or name, "orcid": orcid})
    return oa, cr


def compare(oa, cr):
    pairs = []
    for (wid, doi), authorships in oa.items():
        for a in authorships:
            for c in cr.get(doi, []):
                out = (name_outcome(a["name"], c["given"], c["family"]),
                       initial_outcome(a["name"], c["given"], c["family"]),
                       position_outcome(a["order"], c["order"]))
                pairs.append({"wid": wid, "doi": doi, "a": a, "c": c, "out": out,
                              "label": (a["orcid"] == c["orcid"]) if a["orcid"] and c["orcid"] else None})
    return pairs


def weights(pairs):
    """m and u of every outcome, counted on the labelled pairs of half A."""
    n, count = Counter(), {True: Counter(), False: Counter()}
    for p in pairs:
        if p["label"] is not None and half(p["wid"]) == 0:
            n[p["label"]] += 1
            for o in p["out"]:
                count[p["label"]][o] += 1
    table = {}
    for o in sorted({o for p in pairs for o in p["out"]}):
        m = (count[True][o] + 0.5) / (n[True] + 1)       # + 0.5: an outcome never seen is not impossible
        u = (count[False][o] + 0.5) / (n[False] + 1)
        table[o] = (m, u, 0.0 if o.endswith("unknown") else math.log2(m / u))
    return table, n


def assign(pairs, table, fields=(0, 1, 2)):
    """One-to-one within each paper, best score first."""
    by_paper = defaultdict(list)
    for p in pairs:
        p_score = sum(table[o][2] for k, o in enumerate(p["out"]) if k in fields)
        by_paper[p["wid"]].append((p_score, p))
    links = {}
    for wid, lst in by_paper.items():
        lst.sort(key=lambda x: -x[0])
        used_a, used_c = set(), set()
        for s, p in lst:
            if p["a"]["order"] in used_a or p["c"]["order"] in used_c:
                continue
            used_a.add(p["a"]["order"])
            used_c.add(p["c"]["order"])
            links[(wid, p["c"]["order"])] = (s, p)
    return links


def measure(oa, cr, links, threshold):
    """On half B: every Crossref author with an ORCID that is on exactly one OpenAlex
    authorship of the same paper. Its true match is known."""
    population, right, wrong, missed = 0, 0, [], []
    for (wid, doi), authorships in oa.items():
        if half(wid) != 1:
            continue
        orcids = Counter(a["orcid"] for a in authorships if a["orcid"])
        for c in cr.get(doi, []):
            if not c["orcid"] or orcids[c["orcid"]] != 1:
                continue
            population += 1
            s, p = links.get((wid, c["order"]), (None, None))
            if s is not None and s >= threshold:
                if p["a"]["orcid"] == c["orcid"]:
                    right += 1
                else:
                    wrong.append((s, wid, p["a"], c))
            else:
                missed.append((s, wid, c))
    found = right + len(wrong)
    return {"population": population, "found": found, "right": right, "wrong": wrong, "missed": missed,
            "precision": right / found if found else 0.0, "recall": right / population if population else 0.0}


# ------------------------------------------------------------------ the person's sample
def hand_sample(links):
    """40 links a person can check, none with an ORCID on both sides (the ORCID labels
    cannot check them): 20 with a score from 4 to DRAWN_AT, which a threshold of DRAWN_AT
    drops, and 20 with DRAWN_AT or more whose names are not plainly the same."""
    unlabelled = [(s, p) for s, p in links.values() if p["label"] is None]
    unlabelled.sort(key=lambda x: (x[1]["wid"], x[1]["c"]["order"]))
    low = [x for x in unlabelled if 4 <= x[0] < DRAWN_AT]
    high = [x for x in unlabelled if x[0] >= DRAWN_AT and x[1]["out"][0] != "name same" and
            (x[1]["out"][0] == "family close" or x[1]["out"][1] != "initial same")]
    rnd = random.Random(2026)
    return sorted(rnd.sample(low, min(20, len(low))) + rnd.sample(high, min(20, len(high))), key=lambda x: -x[0])


def label_results(links):
    """Precision on the person's labels, when hand_sample.csv has them."""
    path = ER / "hand_sample.csv"
    if not path.exists():
        return None
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    done = [r for r in rows if r["same"].strip().lower() in ("y", "n")]
    if not done:
        return None
    out = []
    for name, keep in ((f"score {DRAWN_AT} or more, names not plainly the same", lambda x: x >= DRAWN_AT),
                       (f"score 4 to {DRAWN_AT}", lambda x: 4 <= x < DRAWN_AT)):
        part = [r for r in done if keep(float(r["score"]))]
        yes = sum(r["same"].strip().lower() == "y" for r in part)
        out.append(f"  {name}: {yes} of {len(part)} are the same person")
    return f"hand-labelled sample: {len(done)} of {len(rows)} pairs labelled\n" + "\n".join(out)


# ------------------------------------------------------------------ run
def main():
    con = load()
    oa, cr = read(con)
    pairs = compare(oa, cr)
    table, n = weights(pairs)
    links = assign(pairs, table)
    lines = [f"papers in both sources: {len(oa):,}; pairs compared (same paper only): {len(pairs):,}",
             f"labelled pairs (an ORCID on both sides): {sum(p['label'] is not None for p in pairs):,}, "
             f"of which same person {sum(p['label'] is True for p in pairs):,}",
             f"weights counted on half A: {n[True]:,} pairs of the same person, {n[False]:,} of two people", ""]
    lines.append(f"  {'outcome':<18} {'m':>8} {'u':>8} {'weight':>7}")
    for o, (m, u, w) in table.items():
        lines.append(f"  {o:<18} {m:8.4f} {u:8.4f} {w:+7.1f}")

    lines += ["", "measured on half B (Crossref authors whose true match is known by ORCID):"]
    for t in SHOWN:
        r = measure(oa, cr, links, t)
        lines.append(f"  threshold {t:>2}: {r['found']:,} links, {r['right']:,} right: precision {r['precision']:.4f}, "
                     f"recall {r['recall']:.4f}  ({len(r['wrong'])} wrong, {len(r['missed'])} missed of "
                     f"{r['population']:,})")
    lines += ["", f"each field alone or together, threshold {THRESHOLD}, half B:"]
    for label, fields in (("name and initial", (0, 1)), ("position only", (2,)), ("all three", (0, 1, 2))):
        r = measure(oa, cr, assign(pairs, table, fields), THRESHOLD)
        lines.append(f"  {label:<17} precision {r['precision']:.4f}, recall {r['recall']:.4f}  "
                     f"({len(r['wrong'])} wrong, {len(r['missed'])} missed)")
    r = measure(oa, cr, links, THRESHOLD)
    lines += ["", f"the mistakes at threshold {THRESHOLD}, half B:"]
    for s, wid, a, c in r["wrong"]:
        lines.append(f"  wrong  {wid}: OpenAlex {a['order']} {a['name']!r} ORCID {a['orcid']} <-> Crossref "
                     f"{c['order']} {c['given']!r} {c['family']!r} ORCID {c['orcid']} (score {s:.1f})")
    for s, wid, c in r["missed"][:10]:
        lines.append(f"  missed {wid}: Crossref {c['order']} {c['given']!r} {c['family']!r} "
                     f"(best score {'none' if s is None else f'{s:.1f}'})")
    if len(r["missed"]) > 10:
        lines.append(f"  ... and {len(r['missed']) - 10} more missed")

    # The links themselves, all papers, both halves.
    kept = sorted((p["wid"], p["a"]["order"], p["doi"], p["c"]["order"], s, p["out"])
                  for s, p in links.values() if s >= THRESHOLD)
    with open(ER / "authorship_links.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["openalex_authorship", "crossref_authorship", "score", "name", "initial", "position"])
        for wid, ao, doi, co, s, out in kept:
            w.writerow([f"{wid}-{ao}", f"{doi}-{co}", f"{s:.1f}", *out])
    unidentified = sum(1 for wid, ao, doi, co, s, out in kept
                       if any(a["order"] == ao and a["author_id"] is None for a in oa[(wid, doi)]))
    zone = sum(1 for s, p in links.values() if 4 <= s < DRAWN_AT)
    lines += ["", f"links kept (score {THRESHOLD} or more, all papers): {len(kept):,}, of "
              f"{sum(len(v) for v in oa.values()):,} OpenAlex authorships on papers in both sources; "
              f"{unidentified:,} of them are authorships OpenAlex gave no author ID",
              f"of which with a score from 4 to {DRAWN_AT}: {zone:,}",
              f"of which the first initials differ and the names are not the same: "
              f"{sum(1 for s, p in links.values() if s >= THRESHOLD and p['out'][1] == 'initial different' and p['out'][0] != 'name same'):,}"]

    sample_path = ER / "hand_sample.csv"
    if not sample_path.exists():
        with open(sample_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["paper", "openalex_position", "openalex_name", "crossref_position", "crossref_given",
                        "crossref_family", "score", "same"])
            for s, p in hand_sample(links):
                w.writerow([p["wid"], p["a"]["order"], p["a"]["name"], p["c"]["order"], p["c"]["given"],
                            p["c"]["family"], f"{s:.1f}", ""])
        lines.append("written: mapping/er/hand_sample.csv, 40 pairs to label (column 'same': y or n)")
    labels = label_results(links)
    if labels:
        lines += ["", labels]
    lines.append(f"written: mapping/er/authorship_links.csv, {len(kept):,} links")
    text = "\n".join(lines)
    print(text)
    (ER / "match_authorships.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
