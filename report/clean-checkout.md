# The clean-checkout test (report section 8)

What the instructor does, done before the hand-in: clone the repository into
an empty folder, add a `.env` from `.env.example` with a key and nothing else,
run one command, and check each layer.

## Run 1: without Docker, as CI runs it (2026-10-20, commit af4dfb5)

A fresh `git clone` into an empty folder on Linux, Python 3.12, the pinned
requirements; no network for the data.

| Step | Command | Result |
|---|---|---|
| map and gate | `python pipeline/run.py --no-load` | exit 0 in 6 min 54 s; four graphs mapped (578,982, 341,926, 9,293 and 30,848 triples); 0 Violation in each; 140 PROV-O triples; 1251 VoID triples; `done` |
| the mapping's test | `python mapping/check_one_paper.py` | 81 hand-written triples, 0 missing: "the mapping reproduces the hand-written paper" |
| the competency questions | `python ontology/run_cqs.py` | `git diff ontology/cq_answers.txt`: only the date line changes; every answer the same |
| the access layer's score | `LLM_MODE=replay python evaluate.py` (from `access-layer/`) | the lines of `results/score-after.txt`, identical but for the header (`LLM_MODE replay`, `build/graph.nt`); no key, no network |
| tracked files | `git status --short` | nothing: the run writes only to `build/`, which is not committed |

## Run 2: with Docker, as the instructor runs it

Windows 11, Docker Desktop (WSL 2), 2026-10-20, commit af4dfb5: `git clone`
into a new folder, `copy .env.example .env`, the Gemini key added and nothing
else, then `docker compose up --build`.

| Check | Result |
|---|---|
| the images | built in 6 s, from Docker's cache of the same Dockerfiles; a computer without that cache first downloads the base images and installs the packages, a few minutes more |
| the pipeline | the same lines as run 1: four graphs, 0 Violation in each (OpenAlex validated in 125 s, the matcher's links in 65 s), 140 PROV-O triples, 1251 VoID triples, the six graphs loaded, `done` |
| `docker compose ps -a` | pipeline `Exited (0)` about 7 minutes after it was created; fuseki and access-layer `Up`, on 127.0.0.1:3030 and 127.0.0.1:8000 |
| the page | "How many papers did Maha Hoteit write?": 92, live from Gemini, with the query and its two FROM lines (the right query of `questions.yaml` gives 92) |
| tracked files | `git status --short`: nothing |
| CI | the latest run of the SHACL gate on GitHub Actions: green |

What it surfaced: the README gave the Windows commands for PowerShell only, and
`Copy-Item` does not exist in Command Prompt, where the test was started. The
README now gives both (`copy .env.example .env` in Command Prompt).

## What earlier tests surfaced, now fixed

| What happened | Why | Fix |
|---|---|---|
| `prepare_ontop.py`: password authentication failed | PostgreSQL keeps the password of its first start, in its volume | written in mapping/README.md: remove the volume to use a new password |
| port 5432 already allocated | another PostgreSQL container on the same computer | written in mapping/README.md: `docker ps --filter publish=5432`, stop it |
| `docker compose logs access-layer` printed nothing | Python buffers what it prints when not on a terminal | `PYTHONUNBUFFERED=1` in access-layer/Dockerfile |
| two runs of the gate gave two reports | pySHACL lists a node's messages in no fixed order | shapes/validate.py prints, for each group, the message of its first focus node |
| two computers chose different GraphSAGE settings | the settings were close, and floating point differs | the run writes its choice (`chosen:`) and the models read it (D17) |
