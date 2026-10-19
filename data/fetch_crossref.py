"""Download the Crossref record of every DOI in our data: the second source (Session 5).

    python data/fetch_crossref.py

Reads the DOIs from data/lu.sql, asks the Crossref REST API for each one
(https://api.crossref.org/works/{doi}), and writes each answer as one line of
data/raw/crossref_works.jsonl (not committed). If it stops (network, laptop
asleep), run it again: the DOIs already saved are skipped.

Crossref needs no key. If you put CROSSREF_MAILTO=your address in .env, it is
sent with each request (Crossref's "polite pool"); without it the script works
the same. One request at a time, with a short pause between two: our 5,055
DOIs take about 30 to 45 minutes. Leave it running.
"""

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
OUT = HERE / "raw" / "crossref_works.jsonl"
URL = os.environ.get("CROSSREF_URL", "https://api.crossref.org/works/")   # another server only for tests
PAUSE = 0.1           # seconds between two requests, on top of Crossref's answer time


def our_dois():
    """Every distinct DOI of data/lu.sql (5,055: two DOIs are on two records each)."""
    con = sqlite3.connect(":memory:")
    con.executescript((HERE / "lu.sql").read_text(encoding="utf-8"))
    return [d for (d,) in con.execute("SELECT DISTINCT doi FROM works WHERE doi IS NOT NULL ORDER BY doi")]


def saved():
    """The answers already in the file. A line cut off by a stop is skipped (its DOI is asked again)."""
    if not OUT.exists():
        return []
    out = []
    with OUT.open(encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def ask(session, doi, params):
    """One DOI. Returns the answer, retrying when Crossref is busy or the network fails."""
    for attempt in range(6):
        try:
            r = session.get(URL + quote(doi, safe="/"), params=params, timeout=60)
        except requests.RequestException as e:
            wait = 5 * 2 ** attempt
            print(f"  {doi}: {type(e).__name__}, trying again in {wait} s", flush=True)
            time.sleep(wait)
            continue
        if r.status_code in (429, 500, 502, 503, 504):     # too many requests, or Crossref busy
            wait = 5 * 2 ** attempt
            print(f"  {doi}: Crossref answered {r.status_code}, trying again in {wait} s", flush=True)
            time.sleep(wait)
            continue
        return r
    sys.exit(f"Crossref did not answer for {doi}. Run the script again later: it starts where it stopped.")


def main():
    load_dotenv()
    mailto = os.environ.get("CROSSREF_MAILTO")
    params = {"mailto": mailto} if mailto else {}
    session = requests.Session()
    session.headers["User-Agent"] = "krr-lu-publication/1.0 (Knowledge Representation course project)"

    dois = our_dois()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = {rec["doi"] for rec in saved()}
    todo = [d for d in dois if d not in done]
    print(f"{len(dois):,} DOIs in data/lu.sql, {len(done):,} already saved, {len(todo):,} to ask"
          + (" (polite pool)" if mailto else ""), flush=True)

    found = missing = 0
    if OUT.exists() and OUT.stat().st_size and not OUT.read_bytes().endswith(b"\n"):
        with OUT.open("a", encoding="utf-8") as f:
            f.write("\n")                      # end a line cut off by a stop
    with OUT.open("a", encoding="utf-8") as f:
        for i, doi in enumerate(todo, 1):
            r = ask(session, doi, params)
            if r.status_code == 200:
                rec = {"doi": doi, "status": 200, "message": r.json()["message"]}
                found += 1
            elif r.status_code < 500:           # 404: not a Crossref DOI (DataCite, arXiv...) or unknown
                rec = {"doi": doi, "status": r.status_code}
                missing += 1
            else:
                sys.exit(f"Unexpected answer {r.status_code} for {doi}: {r.text[:200]}")
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()                           # saved at once: a stop loses nothing
            if i % 100 == 0 or i == len(todo):
                print(f"{i:,} of {len(todo):,} asked: {found:,} found, {missing:,} not in Crossref", flush=True)
            time.sleep(PAUSE)

    statuses = [rec["status"] for rec in saved()]
    print(f"saved: {len(statuses):,} answers in data/raw/crossref_works.jsonl, "
          f"{statuses.count(200):,} found, {len(statuses) - statuses.count(200):,} not in Crossref")


if __name__ == "__main__":
    main()
