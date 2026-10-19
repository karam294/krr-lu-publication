"""Provenance of one pipeline run, in PROV-O (W3C Recommendation, 2013): which
files went in, which programs ran, when, and which named graphs came out.

pipeline/run.py calls write_provenance() after the SHACL gate, so only graphs
that passed the gate get provenance; the file goes to build/provenance.ttl
and is loaded into the named graph https://ul.edu.lb/kr/graph/provenance.
Regenerated on every run: do not edit it.

PROV-O has three kinds of thing:
  entity    a thing: data/lu.sql, data/crossref.sql, a mapping, the ontology,
            a shapes file, a graph
  activity  something that happened: this run of the pipeline
  agent     who or what is responsible: the programs; OpenAlex and Crossref
            for the data

Provenance is per named graph, not per triple: a few dozen triples describe
the 578,982 of graph/openalex and the 341,926 of graph/crossref (D10, D14).
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

# The Crossref download behind data/crossref.sql (data/README.md, D11): one
# request per DOI of data/lu.sql, https://api.crossref.org/works/{doi}.
CROSSREF_DATE = "2026-10-19"
CROSSREF_API = "https://api.crossref.org/works"


def sha256(path):
    """The file's checksum, with Windows line endings read as Unix ones: git
    may check a file out with \\r\\n on Windows and \\n on Linux (CI), and the
    same file must get the same checksum on both."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def stamp(t):
    return Literal(t.isoformat(), datatype=XSD.dateTime)


def write_provenance(root, out, graphs, started, ended):
    """graphs: for each source graph that passed the gate, its name ("openalex",
    "crossref") -> (number of triples, the gate's counts as text)."""
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

    def organization(iri, label):
        o = URIRef(iri)
        g.add((o, RDF.type, PROV.Organization))
        g.add((o, RDFS.label, Literal(label)))
        return o

    def shapes_file(path):
        sg = Graph().parse(path)
        iri = sg.value(predicate=RDF.type, object=OWL.Ontology)
        e = entity(iri, str(path.relative_to(root)).replace("\\", "/"), path)
        g.add((e, OWL.versionInfo, sg.value(iri, OWL.versionInfo)))
        return e

    # Where the data comes from: one OpenAlex download, frozen as data/lu.sql (D4).
    openalex = organization("https://openalex.org/", "OpenAlex")
    snapshot = entity(f"{ID}snapshot/openalex/{SNAPSHOT_DATE}", "OpenAlex works of LU (I160368002), 2022 to 2025")
    g.add((snapshot, DCT.source, URIRef(SNAPSHOT_QUERY)))
    g.add((snapshot, DCT.created, Literal(SNAPSHOT_DATE, datatype=XSD.date)))
    g.add((snapshot, PROV.wasAttributedTo, openalex))
    g.add((snapshot, DCT.license, URIRef("https://creativecommons.org/publicdomain/zero/1.0/")))
    sql = entity(f"{ID}file/lu.sql", "data/lu.sql", root / "data" / "lu.sql")
    g.add((sql, PROV.wasDerivedFrom, snapshot))

    # And one Crossref download, of the DOIs of data/lu.sql, frozen as data/crossref.sql (D11).
    crossref = organization("https://www.crossref.org/", "Crossref")
    cr_snapshot = entity(f"{ID}snapshot/crossref/{CROSSREF_DATE}",
                         "Crossref records of the 5,055 distinct DOIs of data/lu.sql")
    g.add((cr_snapshot, DCT.source, URIRef(CROSSREF_API)))
    g.add((cr_snapshot, DCT.created, Literal(CROSSREF_DATE, datatype=XSD.date)))
    g.add((cr_snapshot, PROV.wasAttributedTo, crossref))
    g.add((cr_snapshot, DCT.rights, Literal("Crossref: almost none of its metadata is subject to copyright, "
                                            "except some abstracts; we keep no abstracts.")))
    cr_sql = entity(f"{ID}file/crossref.sql", "data/crossref.sql", root / "data" / "crossref.sql")
    g.add((cr_sql, PROV.wasDerivedFrom, cr_snapshot))

    # What the run read: the mappings, the ontology (by its version IRI), the shapes.
    mapping = entity(f"{ID}file/mapping.ttl", "mapping/mapping.ttl", root / "mapping" / "mapping.ttl")
    cr_mapping = entity(f"{ID}file/crossref.ttl", "mapping/crossref.ttl", root / "mapping" / "crossref.ttl")
    onto = Graph().parse(root / "ontology" / "ontology.ttl")
    onto_iri = onto.value(predicate=RDF.type, object=OWL.Ontology)
    onto_version = onto.value(onto_iri, OWL.versionIRI) or onto_iri
    ontology = entity(onto_version, "ontology/ontology.ttl", root / "ontology" / "ontology.ttl")
    shapes = shapes_file(root / "shapes" / "shapes.ttl")
    cr_shapes = shapes_file(root / "shapes" / "crossref-shapes.ttl")

    # Who ran: our pipeline, Morph-KGC for the mappings, pySHACL for the gate.
    run_py = program(f"{ID}software/pipeline/run.py", "pipeline/run.py", root / "pipeline" / "run.py")
    morph = program(f"{ID}software/morph-kgc/{version('morph-kgc')}", f"Morph-KGC {version('morph-kgc')}")
    pyshacl = program(f"{ID}software/pyshacl/{version('pyshacl')}", f"pySHACL {version('pyshacl')}")

    # The run itself.
    run = URIRef(f"{ID}run/pipeline/{started.strftime('%Y%m%dT%H%M%SZ')}")
    g.add((run, RDF.type, PROV.Activity))
    g.add((run, RDFS.label, Literal("Pipeline run: map, SHACL gate, provenance")))
    g.add((run, PROV.startedAtTime, stamp(started)))
    g.add((run, PROV.endedAtTime, stamp(ended)))
    for used in (sql, cr_sql, mapping, cr_mapping, ontology, shapes, cr_shapes):
        g.add((run, PROV.used, used))
    for agent in (run_py, morph, pyshacl):
        g.add((run, PROV.wasAssociatedWith, agent))

    # What came out: one named graph per source, each from its own file and
    # checked by its own shapes; and the ontology.
    made_from = {"openalex": (sql, shapes, "LU publications from OpenAlex, mapped to RDF"),
                 "crossref": (cr_sql, cr_shapes, "The Crossref records of our DOIs, mapped to RDF")}
    for name, (n_triples, gate_summary) in graphs.items():
        source_file, checked_by, title = made_from[name]
        data = entity(f"{GRAPH}{name}", title)
        g.add((data, PROV.wasDerivedFrom, source_file))
        g.add((data, PROV.wasGeneratedBy, run))
        g.add((data, PROV.generatedAtTime, stamp(ended)))
        g.add((data, VOID.triples, Literal(n_triples)))
        g.add((data, RDFS.comment, Literal(f"SHACL gate passed against {g.value(checked_by, DCT.title)}: "
                                           f"{gate_summary}")))
    schema = entity(f"{GRAPH}ontology", "The ontology, as loaded")
    g.add((schema, PROV.wasDerivedFrom, ontology))
    g.add((schema, PROV.wasGeneratedBy, run))

    g.serialize(out, format="turtle", encoding="utf-8")
    return len(g)
