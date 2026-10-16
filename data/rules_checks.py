from pathlib import Path
import pandas as pd

T = Path(__file__).resolve().parent / "tables"
works = pd.read_csv(T / "works.csv", dtype=str)
authorships = pd.read_csv(T / "authorships.csv", dtype=str)
affiliations = pd.read_csv(T / "affiliations.csv", dtype=str)
n = len(works)

# Rule A: each paper has exactly one author labelled "first", and that author is at order 1
firsts = authorships[authorships["author_position"] == "first"]
per_paper = firsts.groupby("work_id").size()
print("A. exactly one first author:", (per_paper == 1).sum(), "of", n)
print("   no first author:", n - len(per_paper), "| more than one:", (per_paper > 1).sum())
print("   'first' author not at order 1:", (firsts["author_order"] != "1").sum())

# Rule B: every LU paper has at least one author affiliated with LU (I160368002)
lu_papers = affiliations.loc[affiliations["institution_id"] == "I160368002", "work_id"].nunique()
print("B. papers with an LU-affiliated author:", lu_papers, "of", n)
# Why do 6 papers have no LU affiliation? Are they the ones cut at 100 authors?
lu_set = set(affiliations.loc[affiliations["institution_id"] == "I160368002", "work_id"])
missing = works[~works["work_id"].isin(lu_set)].copy()
authors_per_paper = authorships.groupby("work_id").size()
missing["n_authors"] = missing["work_id"].map(authors_per_paper)
print(missing[["work_id", "type", "n_authors", "title"]].to_string())