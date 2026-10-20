"""Describe the graph with VoID: which classes it has, how many of each, and
which properties link each class to which class or datatype (the layout of
SIB's void-generator). The access layer tells the model this, not the whole
ontology, and checks every query against it. One addition to the template:
each class's superclass in our namespace (pub:Article rdfs:subClassOf
pub:Work), read from the ontology, so the schema can group the kinds of paper.

    python access-layer/make_void.py build/graph.nt build/void.ttl

pipeline/run.py calls write_void() after the SHACL gate.
"""
import sys
from pathlib import Path

import pyoxigraph as ox

from access_layer import DATASET, NS, PFX, ROOT

ONTOLOGY = "urn:ontology"     # the ontology in a graph of its own, so it is not counted as data

QUERY = f"""
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX void-ext: <http://ldf.fi/void-ext#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
CONSTRUCT {{
  <{DATASET}> void:classPartition ?cp .
  ?cp void:class ?c ; void:entities ?n ; void:propertyPartition ?pp .
  ?c rdfs:subClassOf ?super .
  ?pp void:property ?p ; void:triples ?t ; void:classPartition ?op ; void-ext:datatypePartition ?dp .
  ?op void:class ?oc .
  ?dp void-ext:datatype ?dt .
}} WHERE {{
  {{ SELECT ?c (COUNT(DISTINCT ?s) AS ?n) WHERE {{ ?s a ?c FILTER STRSTARTS(STR(?c), "{NS}") }} GROUP BY ?c }}
  BIND (IRI(CONCAT(STR(?c), "-partition")) AS ?cp)
  OPTIONAL {{ GRAPH <{ONTOLOGY}> {{ ?c rdfs:subClassOf ?super FILTER STRSTARTS(STR(?super), "{NS}") }} }}
  OPTIONAL {{
    {{ SELECT ?c ?p (COUNT(*) AS ?t) (SAMPLE(?ocls) AS ?oc) (SAMPLE(DATATYPE(?o)) AS ?dt0) WHERE {{
        ?s a ?c ; ?p ?o . FILTER (?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        OPTIONAL {{ ?o a ?ocls }} }} GROUP BY ?c ?p }}
    BIND (IRI(CONCAT(STR(?c), "-", STRAFTER(STR(?p), "#"))) AS ?pp)
    BIND (IF(BOUND(?oc), IRI(CONCAT(STR(?pp), "-class")), ?unbound) AS ?op)
    BIND (IF(BOUND(?dt0) && !BOUND(?oc), ?dt0, ?unbound) AS ?dt)
    BIND (IF(BOUND(?dt), IRI(CONCAT(STR(?pp), "-datatype")), ?unbound) AS ?dp)
  }}
}}
"""


def write_void(graph_path, out_path, ontology_path=ROOT / "ontology" / "ontology.ttl"):
    store = ox.Store()
    fmt = ox.RdfFormat.N_TRIPLES if str(graph_path).endswith(".nt") else ox.RdfFormat.TURTLE
    store.bulk_load(path=str(graph_path), format=fmt)
    store.bulk_load(path=str(ontology_path), format=ox.RdfFormat.TURTLE, to_graph=ox.NamedNode(ONTOLOGY))
    triples = list(store.query(QUERY))
    Path(out_path).write_bytes(ox.serialize(triples, format=ox.RdfFormat.TURTLE,
                                            prefixes={"void": "http://rdfs.org/ns/void#",
                                                      "void-ext": "http://ldf.fi/void-ext#", PFX: NS,
                                                      "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}))
    return len(triples)


if __name__ == "__main__":
    print(write_void(sys.argv[1], sys.argv[2]), "VoID triples")
