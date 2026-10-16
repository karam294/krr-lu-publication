import os
import requests
from dotenv import load_dotenv
import json #save the file as json 
from pathlib import Path #new to bnuild teh folder path 
import requests


load_dotenv()
key = os.environ["OPENALEX_API_KEY"]

URL = "https://api.openalex.org/works"
params = {
    "filter": "authorships.institutions.id:I160368002,publication_year:2022-2025",
    "per_page": 100,
    "select": "id,doi,title,publication_year,publication_date,type,language,"
              "primary_location,authorships,primary_topic,open_access,"
              "referenced_works,biblio,is_retracted",
    "api_key": key,
}


# ... load_dotenv(), key, URL and params stay exactly as they are ...

works = []        # every paper from every page ends up in this list
cursor = "*"      # "*" = start at the first page

while cursor:     # repeat as long as OpenAlex gives us a next page
    r = requests.get(URL, params={**params, "cursor": cursor}, timeout=60)
    r.raise_for_status()
    data = r.json()
    works.extend(data["results"])            # add this page's 100 papers to the list
    cursor = data["meta"]["next_cursor"]     # None after the last page, which ends the loop
    print(f"{len(works)} of {data['meta']['count']} downloaded")

out = Path("data/raw/openalex_works.json")
out.parent.mkdir(parents=True, exist_ok=True)          # create data/raw/ if it doesn't exist yet
with open(out, "w", encoding="utf-8") as f:
    json.dump(works, f, ensure_ascii=False)            # write the whole list to the file

print(f"saved {len(works)} works to {out}; OpenAlex says {data['meta']['count']}")