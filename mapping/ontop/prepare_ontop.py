"""Prepare the virtualized route (Session 5, D16): our tables in PostgreSQL, and
Ontop's mapping and connection, so Ontop can answer SPARQL from the database.

    docker compose --profile virtual up -d postgres      first: the database
    python mapping/ontop/prepare_ontop.py                 then this (about a minute)
    docker compose --profile virtual up -d --build ontop  then the endpoint

Run from the repository root. Needs POSTGRES_PASSWORD in .env (the database's
password, which docker-compose.yml gives PostgreSQL; never committed).

  1 tables    the same tables the pipeline maps (pipeline/run.py, step 1:
              data/lu.sql, data/crossref.sql, the links of mapping/er), copied
              from build/sources.sqlite into PostgreSQL, every value as text
  2 keys      a primary key on each table that has one, and indexes on the
              columns the mappings join on. Ontop reads the keys from the
              database to write shorter SQL: without them it cannot tell that
              two rows with the same work_id are one row.
  3 mapping   build/ontop/mapping.ttl: our four mappings in one file (Ontop
              takes one), each triples map given the named graph its file
              stands for (rr:graph), so a query with GRAPH or FROM sees the
              same four graphs as on Fuseki
  4 connect   build/ontop/ontop.properties: how the Ontop container reaches
              PostgreSQL. It holds the password, so it stays in build/ (never
              committed).
"""

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from rdflib import Graph, Namespace, URIRef
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "ontop"
sys.path.insert(0, str(ROOT / "pipeline"))
import run  # noqa: E402  (pipeline/run.py: the same source tables, the same mappings)

RR = Namespace("http://www.w3.org/ns/r2rml#")
GRAPH = "https://ul.edu.lb/kr/graph/"

# The key of each table: the grain of its rows (data/README.md, D3).
KEYS = {
    "works": "work_id", "authors": "author_id", "institutions": "institution_id",
    "sources": "source_id", "topics": "topic_id",
    "authorships": "work_id, author_order", "affiliations": "work_id, author_order, institution_id",
    "citations": "citing_work_id, cited_work_id",
    "cr_works": "doi", "cr_authors": "doi, author_order", "cr_references": "doi, ref_order",
    "er_matches": "openalex_authorship",
}
# Other columns the mappings and the queries join on.
INDEXES = ["works (doi)", "authorships (author_id)", "authors (orcid)", "citations (cited_work_id)",
           "cr_authors (orcid)", "cr_references (ref_doi)", "cr_updates (notice_doi)",
           "cr_updates (updated_doi)", "er_links (kind)"]


def main():
    load_dotenv(ROOT / ".env")
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        sys.exit("Set POSTGRES_PASSWORD in .env (see .env.example), then start PostgreSQL: "
                 "docker compose --profile virtual up -d postgres")
    host = "127.0.0.1"                  # docker-compose.yml publishes it on this computer only
    engine = create_engine(f"postgresql+psycopg2://kr:{password}@{host}:5432/lu")
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        sys.exit(f"PostgreSQL is not answering on {host}:5432: docker compose --profile virtual up -d postgres")

    # 1 the same tables as the pipeline, from our data (not DB_URL)
    os.environ.pop("DB_URL", None)
    run.BUILD.mkdir(exist_ok=True)
    run.source()
    src = sqlite3.connect(run.BUILD / "sources.sqlite")
    tables = [t for (t,) in src.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for table in tables:
        df = pd.read_sql(f'SELECT * FROM "{table}"', src)
        df.to_sql(table, engine, if_exists="replace", index=False, chunksize=10_000, method="multi")
        print(f"  {table:<14} {len(df):>8,} rows")
    print(f"1 tables: {len(tables)} copied into PostgreSQL ({host}:5432, database lu)")

    # 2 keys and indexes
    with engine.begin() as c:
        for table, key in KEYS.items():
            c.execute(text(f"ALTER TABLE {table} ADD PRIMARY KEY ({key})"))
        for index in INDEXES:
            c.execute(text(f"CREATE INDEX ON {index}"))
        for table in tables:
            c.execute(text(f"ANALYZE {table}"))
    print(f"2 keys: {len(KEYS)} primary keys, {len(INDEXES)} indexes")

    # 3 one mapping file, each map in the graph of its file
    combined = Graph()
    combined.bind("rr", RR)
    for name, mapping, _, _ in run.GRAPHS:
        g = Graph().parse(ROOT / mapping, format="turtle", publicID=f"https://ul.edu.lb/kr/mapping/{name}")
        for subject_map in set(g.objects(None, RR.subjectMap)):
            g.add((subject_map, RR.graph, URIRef(GRAPH + name)))
        combined += g
    OUT.mkdir(parents=True, exist_ok=True)
    combined.serialize(OUT / "mapping.ttl", format="turtle", encoding="utf-8")
    print(f"3 mapping: {len(run.GRAPHS)} mappings, {len(combined)} triples -> build/ontop/mapping.ttl")

    # 4 the connection, as the Ontop container sees PostgreSQL (the service name)
    (OUT / "ontop.properties").write_text(
        "# Written by mapping/ontop/prepare_ontop.py. Holds the password: never commit it.\n"
        "# autosave: when PostgreSQL refuses one query, the next ones still run. Without\n"
        "# it the connection stays in a failed transaction, and every later query fails\n"
        "# too (found by compare_routes.py).\n"
        "jdbc.url=jdbc:postgresql://postgres:5432/lu?autosave=always\n"
        "jdbc.user=kr\n"
        f"jdbc.password={password}\n"
        "jdbc.driver=org.postgresql.Driver\n"
        "# A column of a view whose type Ontop cannot infer gives a plain string,\n"
        "# as in the materialized graph.\n"
        "ontop.inferDefaultDatatype=true\n", encoding="utf-8")
    print("4 connect: build/ontop/ontop.properties")
    print("next: docker compose --profile virtual up -d --build ontop")


if __name__ == "__main__":
    main()
