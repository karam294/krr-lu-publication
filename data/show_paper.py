from pathlib import Path
import pandas as pd
pd.set_option("display.max_colwidth", None)
T = Path(__file__).resolve().parent / "tables"
works = pd.read_csv(T / "works.csv", dtype=str)
authorships = pd.read_csv(T / "authorships.csv", dtype=str)
affiliations = pd.read_csv(T / "affiliations.csv", dtype=str)
institutions = pd.read_csv(T / "institutions.csv", dtype=str)
sources = pd.read_csv(T / "sources.csv", dtype=str)
topics = pd.read_csv(T / "topics.csv", dtype=str)
citations = pd.read_csv(T / "citations.csv", dtype=str)

# Pick one small, complete paper: an article with 3 authors, a DOI, a venue,
# a topic and at least one reference. Sorted by ID, so it is the same paper every run.
n_authors = authorships.groupby("work_id").size()
n_refs = citations.groupby("citing_work_id").size()
ok = (works["type"].eq("article") & works["doi"].notna() & works["source_id"].notna()
      & works["topic_id"].notna() & works["work_id"].map(n_authors).eq(3)
      & works["work_id"].map(n_refs).gt(0))
paper = works[ok].sort_values("work_id").iloc[0]
w = paper["work_id"]

print("== works (1 row)")
print(paper.to_string())

print("\n== authorships")
print(authorships[authorships["work_id"] == w].to_string(index=False))

aff = affiliations[affiliations["work_id"] == w]
print("\n== affiliations")
print(aff.to_string(index=False))

print("\n== institutions of these authors")
print(institutions[institutions["institution_id"].isin(aff["institution_id"])].to_string(index=False))

print("\n== venue")
print(sources[sources["source_id"] == paper["source_id"]].to_string(index=False))

print("\n== topic")
print(topics[topics["topic_id"] == paper["topic_id"]].to_string(index=False))

refs = citations[citations["citing_work_id"] == w]
print(f"\n== citations: {len(refs)} references, the first 3")
print(refs.head(3).to_string(index=False))