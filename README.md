# Your team's knowledge graph system

The starter repository for the Knowledge Representation team project
(Lebanese University, MSc). Every session of the course adds one layer; this
repository is where your team puts its own version of each, on its own
topic and data. You hand it in 48 hours before Session 8; the instructor
clones it fresh, runs one command, and grades what comes up, once.

The labs and slides are at
https://ahmabboud.github.io/course_knowledge_representation/.

It ships with a tiny real example (60 Brunel orders from the course's shared
case), so the whole stack comes up on the first day. Replace the example,
one layer at a time, with your own.

## Start your team's repository

One teammate opens https://github.com/ahmabboud/kr-team-template, presses
**Use this template**, then **Create a new repository**, and adds the
teammates as collaborators. Everyone clones the new repository; nobody
commits to this template.

## Run it

```sh
cp .env.example .env        # then put your Gemini key after GOOGLE_API_KEY=
docker compose up --build
```

On Windows, install Docker Desktop (see the course's `demos/README.md` for
the steps) and use PowerShell: `Copy-Item .env.example .env`, then the same
`docker compose up --build`.

**Expect:** the pipeline prints five steps and `done` (on the example:
1,185 triples, 0 Violation, 189 VoID triples), then the access layer serves
on http://127.0.0.1:8000. Try
`http://127.0.0.1:8000/?question=How%20many%20late%20orders%20are%20there%3F&dataset=https://ul.edu.lb/kr/brunel/`.
The endpoint is at http://127.0.0.1:3030 (dataset `kr`).

Without Docker, the pipeline also runs on its own (Python 3.12, from the
repository root): `pip install -r pipeline/requirements-pipeline.txt`, then
`pip install --no-deps morph-kgc==2.10.0`, then `python pipeline/run.py --no-load`. (On Windows, use `py -3.12` for
`python` when creating the environment, as the course's `demos/README.md` does.)

## What goes where

| Folder | Layer | Session | Replace the example with |
|---|---|---|---|
| `data/` | your source, or a small sample of it | 1, 5 | a sample `example.sql`, or set `DB_URL` in `.env` to your database |
| `ontology/` | the ontology | 3 | your ontology: a reused published vocabulary, competency questions, OWL profile, version IRI |
| `shapes/` | the SHACL shapes | 4 | the shapes for your constraint inventory |
| `mapping/` | the R2RML mapping | 5 | the mapping from your tables to your ontology |
| `pipeline/` | map, gate, describe, load | 4, 5 | usually nothing |
| `model/` | the graph models | 6 | your node classification and link prediction, with baseline and split |
| `access-layer/` | questions in English | 7 | `prompt_rules.txt`, `examples.ttl`, `questions.yaml`, and `NS`/`PFX` in `access_layer.py` |
| `report/` | the technical report | all | your report, from `REPORT.md` |
| `.github/workflows/` | the SHACL gate in CI | 4 | nothing, if `data/example.sql` holds a sample of your data |

## How the stack fits together

```text
data (your tables) --> pipeline: map (mapping/) --> SHACL gate (shapes/ + ontology/)
                                                        |
                                    Violation: stop     |  pass
                                                        v
                                   VoID (build/void.ttl) + load --> Fuseki (kr)
                                                                        ^
                   a question in English --> access layer (Gemini) -----+
```

The endpoint is only ever loaded with data that passes the gate. Change one
row of `data/example.sql` so an order weighs 0 and run the pipeline again: it
stops at step 3 and says why.

## When

Form your team and agree a topic before Session 2, and start your own build
from directly after Session 1, one layer behind each session. Two
checkpoints give you feedback and are not graded: Milestone 1 (end of
Session 4), the ontology and shapes on your own data, and Milestone 2 (end
of Session 6), the graph models with their baseline and a split that does
not leak. Push to your repository for each.

## How it is graded

Handed in 48 hours before Session 8, and graded once (55 percent of the
course grade). The instructor clones it into an empty folder, adds a `.env`,
runs `docker compose up --build`, and gives each layer one mark: works (full
points), partly (half) or missing (none). A layer that cannot be shown
working from this clean checkout is at most partly.

| Layer | Points |
|---|---|
| Ontology | 10 |
| Shapes and validation | 10 |
| Mapping and integration | 9 |
| Learning over the graph | 9 |
| Access layer | 9 |
| Report and open problem | 8 |

Before you hand in, check the five things on the Session 7 checklist, as
the class adjusted it:
one command from a clean checkout; services on 127.0.0.1 only and keys only
in `.env`; the SHACL gate before the endpoint and in CI; the test set's
score recorded with the model and the date; a real unanswerable question
refused, with a reason.

In Session 8 each of you defends the system (30 percent, individual): the
running stack answers one question and refuses one, then each student
answers 2 or 3 questions about parts they did not build. An ontology the team
cannot defend loses its ontology points.

## Rules the course holds you to

- Commit under your own account; one branch and one pull request per person,
  reviewed by a teammate.
- Never commit `.env`, a key or a password.
- Choose an open dataset with a stated licence, and a published ontology to
  reuse; check the licence of the exact feed or item set you use.
- Every third-party ontology, vocabulary and dataset goes in the report with
  its licence.
- Any teammate can be asked about any part, in Session 8.
