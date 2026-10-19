# mapping/er/: entity resolution across OpenAlex and Crossref

Two sources describe the same papers and the same authors (D11). Entity
resolution decides which records are the same real thing, and measures how
often it is wrong. Every number below is in one of the files of this folder.

| File | What it is |
|---|---|
| `sources.py` | loads data/lu.sql and data/crossref.sql into one database in memory |
| `link_by_key.py` | part 1: records that share an identifier (a DOI, an ORCID) |
| `links_by_key.csv`, `link_by_key.txt` | its links, and what it found |
| `match_authorships.py` | part 2: the matcher for authors, who share no identifier |
| `authorship_links.csv`, `match_authorships.txt` | its links, and its measurement |
| `hand_sample.csv` | 40 links checked by a person (the column `same`) |
| `follow_links.rq` | a query that follows both kinds of link for one paper, on the endpoint |

Run, from the repository root:

```sh
python mapping/er/link_by_key.py          # a few seconds
python mapping/er/match_authorships.py    # about a minute
```

## Part 1: records that share an identifier (no guessing)

1. **A paper in both sources**: an OpenAlex paper and the Crossref record of its
   DOI, 4,887 links. The DOI is a key both sources share. Checked by the titles:
   4,870 the same once accents, case and markup are removed, 15 close, 1 different
   (W4205255002, a second OpenAlex record of a paper, with a longer title).
2. **Two OpenAlex records, one DOI** (Session 4): W4205255002 = W4206272747,
   one Crossref record for both; W7118513034 = W7214706685, a DOI Crossref does
   not have.
3. **Two OpenAlex author records, one ORCID** (Session 4): 20 ORCIDs, 40
   records, linked in pairs.
4. **Authorships OpenAlex gave no author ID** (Session 4: 2,101): 311 carry an
   ORCID. 158 link to the OpenAlex author with that ORCID; 153 to a person known
   only by the ORCID, 123 people (D12). 1,790 are left with a name only.
5. **An OpenAlex author and the Crossref person of the same ORCID**: 3,827
   author records, 3,812 ORCIDs (of the 4,450 that Crossref gives).

## Part 2: which Crossref author is which OpenAlex authorship?

The same paper lists its authors in both sources, but with no shared key:
OpenAlex writes "Rim Fayad", Crossref given "Rim", family "Fayad", sometimes in
another order or with only initials. The method is Fellegi and Sunter's (1969),
as in the course's lab:

- **Blocking**: compare only the authors of the same paper (962,298 pairs).
- **Three fields**, each with an outcome: the name (same, family in name, family
  close, different), the first initial (same, different), the position in the
  author list (same, near: one or two places, far).
- **Weights** log2(m/u). m: how often an outcome happens for two records of the
  same person; u: for two different people. Here m and u are **counted, not
  stated**, on labelled pairs: the pairs where both sources give an ORCID (same
  ORCID: same person). The ORCID is never a field of the matcher.
- **One-to-one**: within a paper, the best pairs first, each author at most once;
  a link is kept if its score is 4 or more (the threshold, D13): 30,848 links.

**Measured honestly**: the papers are split in two halves; the weights are
counted on half A, the matcher is measured on half B, on the 3,681 Crossref
authors of half B whose true match is known by ORCID. The results, threshold by
threshold, and each field alone, are in `match_authorships.txt`.

**What the ORCID labels cannot check.** They exist only where both sources have
an ORCID, and those authors are the easy ones. So a person also checked 40 links
with no ORCID on both sides (`hand_sample.csv`), drawn when the threshold was 8:
20 with a score from 4 to 8, which a threshold of 8 drops, and 20 with 8 or more
whose names are not plainly the same.

**Where the two sources give two different ORCIDs.** 52 of the kept links join
an OpenAlex authorship and a Crossref author whose ORCIDs differ (listed at the
end of `match_authorships.txt`). 42 have the same name on both sides: one person
with two ORCIDs, so one source is wrong or the person has two ORCID records. A
few are the matcher's mistakes: Norma and Najah A. R. Ghamrawi (3 papers), Nigar
and Najwaa Kirmani, two people each time with one family name and one first
initial. The measurement above sees only one of the 52 (Heeba Anis): it can only
measure a link where Crossref's ORCID is on exactly one OpenAlex authorship of
the paper. The pipeline flags all 52 (shapes/matches-shapes.ttl).

**What decided the threshold** (D13). On half B, thresholds 4 and 8 have the
same precision, 0.9997; 4 has the higher recall, 0.9995 against 0.9957. In the
hand sample, 19 of the 20 links from 4 to 8 are the same person: most are a
byline in another order in Crossref. So the threshold is 4. The weakness we
keep: when the family name and the position agree, a different first initial
does not cancel the link (28 links, most with a score of 9.1); 2 of the 4
checked are two different people.

## How the links reach the graph (D15)

The two CSV files are the links; pipeline/run.py loads them as two tables and
maps them like the sources, each into a named graph of its own:

| Links | Mapping | Named graph | Shapes |
|---|---|---|---|
| `links_by_key.csv`: by DOI and ORCID, no guessing | `mapping/links.ttl` | graph/links | `shapes/links-shapes.ttl` |
| `authorship_links.csv`: the matcher's, score 4 or more | `mapping/matches.ttl` | graph/matches | `shapes/matches-shapes.ttl` |

A link is `owl:sameAs` (kinds 1, 2, 3, 5 and the matcher's) or `pub:author`
(kind 4), always from OpenAlex to Crossref. The records stay two nodes, each in
its source's graph: a wrong link is removed by changing this folder, never by
editing a source. And a query chooses how sure it must be: graph/links only,
or graph/matches too (ontology/cq/cq09.rq does both, step by step).

### Labelling the hand sample (how it was done, and how to redo it)

Open `hand_sample.csv` in VS Code or Notepad (not Excel: it can change the
file's format when it saves). Each line is one link: the OpenAlex name and its
position, the Crossref given and family names and their position, the score.
Decide whether the two are **the same person on that paper**, and write `y` or
`n` after the last comma, for example `...,15.6,y`. If you cannot tell, leave it
empty. Then run `match_authorships.py` again: it prints how many of each group
are the same person, and keeps your labels.
