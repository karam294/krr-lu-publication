"""Entity resolution, part 1: records that share a key (Session 5).

    python mapping/er/link_by_key.py

Run from the repository root. Reads data/lu.sql and data/crossref.sql; writes
mapping/er/links_by_key.csv (one link per row) and mapping/er/link_by_key.txt
(what it found). No guessing here: two records are linked only when they carry
the same identifier, a DOI or an ORCID. The matcher for records without a shared
key is match_authorships.py.

  1 paper:  an OpenAlex paper and the Crossref record of its DOI. Checked: the
            two titles must agree, or the DOI is suspect.
  2 paper:  two OpenAlex records with the same DOI (Session 4: 2 DOIs).
  3 author: two OpenAlex author records with the same ORCID (Session 4: 20).
  4 author: an authorship OpenAlex gave no author ID, but with an ORCID: the
            author record that has this ORCID, or else a person known only by
            the ORCID (D12).
"""

import csv
import html
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from sources import ER, load


def title_key(s):
    """A title reduced for comparison: tags and entities out, accents off, lower case,
    letters and digits of any script kept."""
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"\w+", s))


def main():
    con = load()
    links, lines = [], []

    # 1 OpenAlex paper <-> Crossref record of the same DOI
    sims = Counter()
    suspect = []
    for wid, doi, t_oa, t_cr in con.execute(
            "SELECT w.work_id, w.doi, w.title, c.title FROM works w JOIN cr_works c ON c.doi = w.doi "
            "WHERE c.found = 'True' ORDER BY w.work_id"):
        sim = SequenceMatcher(None, title_key(t_oa), title_key(t_cr)).ratio() if t_cr else None
        band = ("no Crossref title" if sim is None else "same" if sim == 1 else
                "close (0.9 or more)" if sim >= 0.9 else "different (below 0.9)")
        sims[band] += 1
        if sim is not None and sim < 0.9:
            suspect.append((round(sim, 2), wid, doi, t_oa, t_cr))
        links.append(["paper", f"work/openalex/{wid}", f"work/crossref/{doi}", "same DOI",
                      "" if sim is None else f"{sim:.3f}"])
    n_papers = sum(sims.values())
    lines.append(f"1 OpenAlex paper <-> Crossref record, same DOI: {n_papers:,} links "
                 f"({con.execute('SELECT COUNT(*) FROM works WHERE doi IS NOT NULL').fetchone()[0]:,} "
                 "OpenAlex papers have a DOI)")
    lines.append("  titles: " + ", ".join(f"{k} {v:,}" for k, v in sims.most_common()))
    for sim, wid, doi, a, b in sorted(suspect):
        lines.append(f"  title differs ({sim}): {wid} {doi}\n      OpenAlex: {a[:90]}\n      Crossref: {(b or '')[:90]}")

    # 2 two OpenAlex records with one DOI
    for doi, ids in con.execute("SELECT doi, GROUP_CONCAT(work_id) FROM works WHERE doi IS NOT NULL "
                                "GROUP BY doi HAVING COUNT(*) > 1 ORDER BY doi"):
        a, b = sorted(ids.split(","))
        found = con.execute("SELECT found FROM cr_works WHERE doi = ?", (doi,)).fetchone()[0] == "True"
        links.append(["paper (two OpenAlex records)", f"work/openalex/{a}", f"work/openalex/{b}", "same DOI", ""])
        lines.append(f"2 two OpenAlex records, one DOI: {a} = {b} ({doi}; "
                     + ("one Crossref record for both)" if found else "not in Crossref)"))

    # 3 two OpenAlex author records with one ORCID
    groups = con.execute("SELECT orcid, GROUP_CONCAT(author_id) FROM authors WHERE orcid IS NOT NULL "
                         "GROUP BY orcid HAVING COUNT(*) > 1 ORDER BY orcid").fetchall()
    for orcid, ids in groups:
        ids = sorted(ids.split(","))
        for other in ids[1:]:
            links.append(["author (two OpenAlex records)", f"author/openalex/{ids[0]}", f"author/openalex/{other}",
                          "same ORCID", orcid])
    lines.append(f"3 two OpenAlex author records, one ORCID: {len(groups)} ORCIDs, "
                 f"{sum(len(i.split(',')) for _, i in groups)} records")

    # 4 authorships with no OpenAlex author ID, but an ORCID
    known = dict(con.execute("SELECT orcid, MIN(author_id) FROM authors WHERE orcid IS NOT NULL GROUP BY orcid"))
    rows = con.execute("SELECT work_id, author_order, orcid FROM authorships "
                       "WHERE author_id IS NULL AND orcid IS NOT NULL ORDER BY work_id, CAST(author_order AS INT)").fetchall()
    to_known = to_new = 0
    new_people = defaultdict(int)
    for wid, order, orcid in rows:
        if orcid in known:
            links.append(["authorship -> author", f"authorship/openalex/{wid}-{order}",
                          f"author/openalex/{known[orcid]}", "same ORCID", orcid])
            to_known += 1
        else:
            links.append(["authorship -> person by ORCID", f"authorship/openalex/{wid}-{order}",
                          f"author/orcid/{orcid}", "same ORCID", orcid])
            to_new += 1
            new_people[orcid] += 1
    total = con.execute("SELECT COUNT(*) FROM authorships WHERE author_id IS NULL").fetchone()[0]
    lines.append(f"4 authorships with no OpenAlex author ID: {total:,}; with an ORCID: {len(rows)}")
    lines.append(f"  -> an OpenAlex author with this ORCID: {to_known}")
    lines.append(f"  -> a person known only by the ORCID: {to_new} authorships, {len(new_people)} people")
    lines.append(f"  still without a person: {total - len(rows):,}")

    with open(ER / "links_by_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "left", "right", "rule", "evidence"])
        w.writerows(links)
    lines.append(f"written: mapping/er/links_by_key.csv, {len(links):,} links")
    text = "\n".join(lines)
    print(text)
    (ER / "link_by_key.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
