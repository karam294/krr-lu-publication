"""Provenance of one pipeline run, in PROV-O (W3C Recommendation, 2013): which
files went in, which programs ran, when, and which named graphs came out.

pipeline/run.py calls write_provenance() after the SHACL gate, so only a graph
that passed the gate gets provenance; the file goes to build/provenance.ttl
and is loaded into the named graph https://ul.edu.lb/kr/graph/provenance.
Regenerated on every run: do not edit it.

PROV-O has three kinds of thing:
  entity    a thing: data/lu.sql, the mapping, the ontology, the shapes, a graph
  activity  something that happened: this run of the pipeline
  agent     who or what is responsible: the programs; OpenAlex for the data

Provenance is per named graph, not per triple: a few dozen triples describe
the 578,982 of the data graph.
"""

import hashlib
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef

PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")
VOID = Namespace("http://rdfs.org/ns/void#")
ID = "https://ul.edu.lb/kr/id/"
GRAPH = "https://ul.edu.lb/kr/graph/"

# The OpenAlex download behind data/lu.sql (data/README.md, D1).
SNAPSHOT_DATE = "2026-10-16"
SNAPSHOT_QUERY = ("https://api.openalex.org/works?filter=authorships.institutions.id:I160368002,"
                  "publication_year:2022-2025")


def sha256(path):
    """The file's checksum, with Windows line endings read as Unix ones: git
    may check a file out with \\r\\n on Windows and \\n on Linux (CI), and the
    same file must get the same checksum on both."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(t):
    return Literal(t.isoformat(), datatype=XSD.dateTime)


def write_provenance(root, out, n_triples, started, ended, gate_summary):
    root = Path(root)
    g = Graph()
    for p, ns in (("prov", PROV), ("dcterms", DCT), ("void", VOID), ("xsd", XSD), ("rdfs", RDFS), ("owl", OWL)):
        g.bind(p, ns)

    def entity(iri, title, path=None):
        e = URIRef(iri)
        g.add((e, RDF.type, PROV.Entity))
        g.add((e, DCT.title, Literal(title)))
        if path is not None:
            g.add((e, DCT.identifier, Literal(sha256(path))))
        return e

    def program(iri, label, path=None):
        a = URIRef(iri)
        g.add((a, RDF.type, PROV.SoftwareAgent))
        g.add((a, RDFS.label, Literal(label)))
        if path is not None:
            g.add((a, DCT.identifier, Literal(sha256(path))))
        return a

    # Where the data comes from: one OpenAlex download, frozen as data/lu.sql (D4).
    openalex = URIRef("https://openalex.org/")
    g.add((openalex, RDF.type, PROV.Organization))
    g.add((openalex, RDFS.label, Literal("OpenAlex")))
    snapshot = entity(f"{ID}snapshot/openalex/{SNAPSHOT_DATE}", "OpenAlex works of LU (I160368002), 2022 to 2025")
    g.add((snapshot, DCT.source, URIRef(SNAPSHOT_QUERY)))
    g.add((snapshot, DCT.created, Literal(SNAPSHOT_DATE, datatype=XSD.date)))
    g.add((snapshot, PROV.wasAttributedTo, openalex))
    g.add((snapshot, DCT.license, URIRef("https://creativecommons.org/publicdomain/zero/1.0/")))
    sql = entity(f"{ID}file/lu.sql", "data/lu.sql", root / "data" / "lu.sql")
    g.add((sql, PROV.wasDerivedFrom, snapshot))

    # What the run read: the mapping, the ontology (by its version IRI), the shapes.
    mapping = entity(f"{ID}file/mapping.ttl", "mapping/mapping.ttl", root / "mapping" / "mapping.ttl")
    onto = Graph().parse(root / "ontology" / "ontology.ttl")
    onto_iri = onto.value(predicate=RDF.type, object=OWL.Ontology)
    onto_version = onto.value(onto_iri, OWL.versionIRI) or onto_iri
    ontology = entity(onto_version, "ontology/ontology.ttl", root / "ontology" / "ontology.ttl")
    shapes_graph = Graph().parse(root / "shapes" / "shapes.ttl")
    shapes_iri = shapes_graph.value(predicate=RDF.type, object=OWL.Ontology)
    shapes = entity(shapes_iri, "shapes/shapes.ttl", root / "shapes" / "shapes.ttl")
    g.add((shapes, OWL.versionInfo, shapes_graph.value(shapes_iri, OWL.versionInfo)))

    # Who ran: our pipeline, Morph-KGC for the mapping, pySHACL for the gate.
    run_py = program(f"{ID}software/pipeline/run.py", "pipeline/run.py", root / "pipeline" / "run.py")
    morph = program(f"{ID}software/morph-kgc/{version('morph-kgc')}", f"Morph-KGC {version('morph-kgc')}")
    pyshacl = program(f"{ID}software/pyshacl/{version('pyshacl')}", f"pySHACL {version('pyshacl')}")

    # The run itself.
    run = URIRef(f"{ID}run/pipeline/{started.strftime('%Y%m%dT%H%M%SZ')}")
    g.add((run, RDF.type, PROV.Activity))
    g.add((run, RDFS.label, Literal("Pipeline run: map, SHACL gate, provenance")))
    g.add((run, PROV.startedAtTime, stamp(started)))
    g.add((run, PROV.endedAtTime, stamp(ended)))
    for used in (sql, mapping, ontology, shapes):
        g.add((run, PROV.used, used))
    for agent in (run_py, morph, pyshacl):
        g.add((run, PROV.wasAssociatedWith, agent))
    g.add((run, RDFS.comment, Literal(f"SHACL gate passed: {gate_summary}")))

    # What came out: one named graph for the data, one for the ontology.
    data = entity(f"{GRAPH}openalex", "LU publications from OpenAlex, mapped to RDF")
    g.add((data, PROV.wasDerivedFrom, sql))
    g.add((data, PROV.wasGeneratedBy, run))
    g.add((data, PROV.generatedAtTime, stamp(ended)))
    g.add((data, VOID.triples, Literal(n_triples)))
    schema = entity(f"{GRAPH}ontology", "The ontology, as loaded")
    g.add((schema, PROV.wasDerivedFrom, ontology))
    g.add((schema, PROV.wasGeneratedBy, run))

    g.serialize(out, format="turtle", encoding="utf-8")
    return len(g)
