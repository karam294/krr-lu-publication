# access-layer/

Questions in English over LU's publications (Session 7): Gemini writes one
SPARQL query from the graph's description and a few examples; the layer checks
it, sends it back for repair if it uses words the graph does not have, runs it,
and returns the rows as the evidence. When the graph holds no such fact, it
refuses and says what is missing. It is measured on a test set, before and
after one improvement (D20).

| File | What it is |
|---|---|
| `access_layer.py` | the layer: the schema from VoID, the examples, the prompt, the call to Gemini, the check, the loop |
| `make_void.py` | the graph's description (build/void.ttl), which the pipeline writes at step 5 |
| `prompt_rules.txt` | the rules in the prompt: how our graph names things, when to refuse (version 67d7c6d8) |
| `prompt_rules-before.txt` | the first rules (version e6f4871f), kept so their score can be replayed |
| `examples.ttl` | 8 example queries, one pattern each (the SHACL layout sparql-llm uses) |
| `questions.yaml` | the test set: 14 questions with their right query, 4 to refuse; none is an example |
| `evaluate.py` | the score, in three settings, the way TEXT2SPARQL scores |
| `ask.py` | one question: each query tried, its problems, the rows |
| `serve.py` | on port 8000: the page (`ui.html`), what it asks (`/ask`), and the TEXT2SPARQL contract |
| `ui.html` | the page: type a question, see the answer, the query that computed it, each try and its problems |
| `llm-cache.json` | every answer Gemini gave in the recorded runs: the scores replay without a key |
| `results/` | the scores: `score-before.txt`, `score-fixed.txt`, `score-after.txt` |

## How a question is answered

1. **The schema.** `build/void.ttl` says which classes the graph has, how many
   of each, and which property links which class to which. The 20 kinds of
   paper (pub:Article, pub:Review, ...) share their properties, so the prompt
   lists them once, as pub:Work: 36 lines.
2. **The prompt.** The rules, the schema, the 3 examples whose questions share
   the most words with this one, and the question.
3. **The check.** Is it valid SPARQL? Does it use only classes and properties
   the graph has? If not, the problems go back to Gemini as a hint, up to twice.
4. **The run.** Every query is asked of graph/openalex and the ontology only:
   the layer adds the two FROM lines itself (D19). In Fuseki's default graph,
   the union of all six graphs, Crossref's records would be counted too.
5. **The refusal.** Gemini replies `REFUSE: <what is missing>` when the graph
   holds no such fact; the layer also refuses when no valid query comes after
   two repairs.

## Why the FROM lines: one check (D19)

On Fuseki, 2026-10-20, from the repository root:

```sh
python -c "import sys; sys.path.insert(0, 'access-layer'); import access_layer as A; print(A.run(A.open_store(), 'SELECT (COUNT(?p) AS ?n) WHERE { ?p pub:publicationYear 2024 }'))"
```

with `SPARQL_ENDPOINT=http://127.0.0.1:3030/kr/sparql` gives **1,288** papers for
2024, as CQ1 does (ontology/cq_answers.txt). The same query sent to Fuseki as it
is, without the FROM lines, gives **2,543**: the union counts the Crossref
records of 2024 too.

## Run it

From `access-layer/`, with `GOOGLE_API_KEY` in `.env`, after `python pipeline/run.py`:

```sh
python ask.py "How many conference papers are there?"                 # on build/graph.nt, in memory
SPARQL_ENDPOINT=http://127.0.0.1:3030/kr/sparql python ask.py "..."   # the same, on Fuseki
LLM_MODE=replay python evaluate.py                                    # the recorded score, no key, no network
LLM_MODE=replay RULES_FILE=prompt_rules-before.txt python evaluate.py # the score of the first rules
LLM_MODE=record python evaluate.py --save results/score-new.txt       # a new run, recorded
```

On Windows PowerShell, set each variable first (`$env:LLM_MODE="replay"`), then
run the command. `LLM_MODE`: live (the default) asks Gemini; record asks and
saves each answer in `llm-cache.json`, and reuses an answer already saved for the
same prompt, so a run cut short starts again where it stopped; replay answers
only from the cache. `LLM_DELAY` (default 4 s) is the pause between calls; on
"too many requests", "busy" (503) or no answer within 90 s the layer waits and
tries again, four times in all.

In the stack (`docker compose up --build`), or with `python serve.py` from this
folder, the layer serves on port 8000:

- **http://127.0.0.1:8000/**, the page: type a question (or click one of the
  five examples) and see the answer: one value in large type, or a table; under
  it, the query that computed it (with the FROM lines the layer added), and each
  try with the problems the check found. A refusal says what the graph lacks;
  if Gemini cannot be reached, the page says why and the server keeps serving.
  Values that are OpenAlex things link to their page on openalex.org.
- **/ask?question=...**, what the page asks: the whole result as JSON (the
  rows, the query, the tries, the model, the rules, the seconds).
- **/?question=...&dataset=https://ul.edu.lb/kr/lu/**, the TEXT2SPARQL
  contract, unchanged: `{"dataset": "...", "question": "...", "query": "PREFIX pub: ... FROM <.../graph/openalex> ..."}`.
  A refusal comes back as a query that returns nothing, the reason in a comment
  (`# REFUSE: ...`).

With `LLM_MODE=replay`, the page answers the 18 recorded questions of the test
set without a key (the five examples on the page are among them).

## The score (results/)

Model gemini-3.5-flash-lite, 2026-10-20, on Fuseki. Each question's answer is a
set of values, compared with the set the right query returns (F1); a refusal
scores 0 on a question the graph can answer. Settings: **schema** (rules and
schema only), **examples** (plus 3 examples), **repair** (plus the check and up
to 2 repairs: what the stack runs).

| Mean F1 on 14 questions | before (`score-fixed`) | after (`score-after`) |
|---|---|---|
| schema | 0.929 | 0.913 |
| examples | 0.702 | 0.750 |
| repair (deployed) | 0.702 | 0.750 |
| wrong refusals (examples, repair) | 3 | 0 |
| right refusals, of 4 (schema; examples and repair) | 4; 4 | 3; 4 |

- **`score-before.txt`**, the first run, had a bug: `with_prefixes` added both
  of our prefixes or none, so a query that declared pub: but not rdfs: was
  rejected (question 2 in the examples setting: 0.631). Fixed, the same answers
  replayed give **`score-fixed.txt`**: the before of the improvement.
- **The improvement (D20)** is one rule. The first rules gave examples of what
  the graph lacks ("for example citation counts, ..."); with examples in the
  prompt, Gemini refused three answerable questions (retractions, ORCIDs, a
  title by DOI) with exactly that reason. The new rule lists what the graph does
  hold: the three are answered, and in the setting we deploy the four questions
  to refuse are still refused.
- **What it cost.** In the schema setting Gemini now tries to answer the h-index
  question; with examples it added a filter "has an LU author" to two counts that
  were right before. A gain of 0.048 on 14 questions, where one question moves
  the mean by about 0.07: one run, real but small.

## What the score does not show

- **Two mistakes no check catches.** Gemini adds "has an LU author" to counts of
  LU papers: valid, plausible and wrong, because 6 papers list no LU author (the
  byline OpenAlex cuts at 100, shapes/validation-report.txt). And it returns
  columns nobody asked for (titles, counts), which the set score counts against
  it. A next improvement would aim at these, one at a time.
- **One run.** Gemini at temperature 0 is close to repeatable, not exactly; a
  second live run (`LLM_MODE=live`) would show how much the numbers move.
- **The examples hurt before they helped.** With the first rules, the schema
  alone scored best (0.929): examples changed what Gemini did in ways the test
  set saw.
- **Only OpenAlex.** Questions that need Crossref, or the links between the
  sources, are for the hand-written competency questions (ontology/cq/), not
  for this layer (D19).
- **Privacy.** The question and the prompt go to Google; on the free tier they
  may be used to improve its products. Ask only about this graph.
