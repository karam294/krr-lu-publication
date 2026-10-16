import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent                     # the data/ folder
works = json.loads((HERE / "raw" / "openalex_works.json").read_text(encoding="utf-8"))

def short(iri):
    """'https://openalex.org/W123' -> 'W123'  (None stays None)"""
    return iri.rsplit("/", 1)[-1] if iri else None

out = HERE / "tables"
out.mkdir(exist_ok=True)

# ---- table 1: works (one row = one paper) ----
rows = []
for w in works:
    source = (w.get("primary_location") or {}).get("source") or {}
    topic = w.get("primary_topic") or {}
    rows.append({
        "work_id": short(w["id"]),
        "doi": (w["doi"] or "").replace("https://doi.org/", "") or None,
        "title": w["title"],
        "publication_year": w["publication_year"],
        "publication_date": w["publication_date"],
        "type": w["type"],
        "language": w["language"],
        "source_id": short(source.get("id")),
        "topic_id": short(topic.get("id")),
        "is_oa": (w.get("open_access") or {}).get("is_oa"),
        "is_retracted": w.get("is_retracted"),
    })
df = pd.DataFrame(rows)
df.to_csv(out / "works.csv", index=False, encoding="utf-8")
print("works:", df.shape)

# ---- tables 2 and 3: authorships and affiliations ----
authorship_rows = []
affiliation_rows = []
for w in works:
    work_id = short(w["id"])
    for order, a in enumerate(w["authorships"], start=1):
        author = a.get("author") or {}
        authorship_rows.append({
            "work_id": work_id,
            "author_order": order,
            "author_position": a.get("author_position"),
            "author_id": short(author.get("id")),
            "author_name": author.get("display_name"),
            "orcid": short(author.get("orcid")),
            "is_corresponding": a.get("is_corresponding"),
        })
        for inst in a.get("institutions") or []:
            affiliation_rows.append({
                "work_id": work_id,
                "author_order": order,
                "institution_id": short(inst.get("id")),
            })
pd.DataFrame(authorship_rows).to_csv(out / "authorships.csv", index=False, encoding="utf-8")
pd.DataFrame(affiliation_rows).to_csv(out / "affiliations.csv", index=False, encoding="utf-8")
print("authorships:", len(authorship_rows), " affiliations:", len(affiliation_rows))
# ---- tables 4-8: one row per journal, topic, author, institution; and citations ----
sources, topics, authors, institutions = {}, {}, {}, {}   # dict: id -> details, so each thing is kept once
citation_rows = []

for w in works:
    work_id = short(w["id"])

    s = (w.get("primary_location") or {}).get("source")
    if s and s.get("id"):
        sources[short(s["id"])] = {"source_id": short(s["id"]), "name": s.get("display_name"),
                                   "issn_l": s.get("issn_l"), "type": s.get("type"),
                                   "publisher": s.get("host_organization_name")}

    t = w.get("primary_topic")
    if t and t.get("id"):
        topics[short(t["id"])] = {"topic_id": short(t["id"]), "name": t.get("display_name"),
                                  "subfield": (t.get("subfield") or {}).get("display_name"),
                                  "field": (t.get("field") or {}).get("display_name"),
                                  "domain": (t.get("domain") or {}).get("display_name")}

    for a in w["authorships"]:
        au = a.get("author") or {}
        if au.get("id"):
            authors[short(au["id"])] = {"author_id": short(au["id"]), "name": au.get("display_name"),
                                        "orcid": short(au.get("orcid"))}
        for i in a.get("institutions") or []:
            if i.get("id"):
                institutions[short(i["id"])] = {"institution_id": short(i["id"]), "name": i.get("display_name"),
                                                "country_code": i.get("country_code"), "type": i.get("type")}

    for ref in w.get("referenced_works") or []:
        citation_rows.append({"citing_work_id": work_id, "cited_work_id": short(ref)})

for name, table in [("sources", sources), ("topics", topics), ("authors", authors), ("institutions", institutions)]:
    pd.DataFrame(list(table.values())).to_csv(out / f"{name}.csv", index=False, encoding="utf-8")
    print(f"{name}:", len(table))
pd.DataFrame(citation_rows).to_csv(out / "citations.csv", index=False, encoding="utf-8")
print("citations:", len(citation_rows))