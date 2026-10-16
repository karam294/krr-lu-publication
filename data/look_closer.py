from pathlib import Path
import pandas as pd

T = Path(__file__).resolve().parent / "tables"
works = pd.read_csv(T / "works.csv", dtype=str)
authorships = pd.read_csv(T / "authorships.csv", dtype=str)

# Finding 7: what are the 20 types, and how many papers each?
print(works["type"].value_counts())

# Finding 5: which papers share a DOI?
shared = works[works["doi"].notna() & works["doi"].duplicated(keep=False)]
print(shared[["work_id", "doi", "type", "title"]])

# Finding 1: how many papers hit the 100-author limit?
authors_per_paper = authorships.groupby("work_id").size()
print("papers with 100 authors listed:", (authors_per_paper == 100).sum())
