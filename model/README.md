# model/

Learning over the knowledge graph (Session 6): one node classification and one
link prediction, each against simple baselines, each trained on earlier years
and tested on a later one (D17, D18). The stack does not serve the models; what
counts is the evaluation, and every number below comes from `results/`.

| File | What it is |
|---|---|
| `build_graph.py` | build/graph.nt (graph/openalex) to PyTorch Geometric, through SPARQL queries; the label taken out |
| `field.py` | node classification: the research field of a paper (D17) |
| `coauthors.py` | link prediction: new co-authorships (D18) |
| `learning_utils.py` | the split by time, and the scores (accuracy, macro-F1, ranks, MRR, Hits@k) |
| `requirements-model.txt` | PyTorch, PyTorch Geometric, PyKEEN, scikit-learn, pinned as the course does |
| `Dockerfile` | the same as a one-shot container: `docker compose --profile learning run --rm model` |
| `results/` | every run's output, with its date and versions: the only numbers the report quotes |

## Run it

From the repository root, after `python pipeline/run.py` (it writes build/graph.nt):

```sh
python -m pip install -r model/requirements-model.txt   # once
python model/build_graph.py                              # seconds  -> results/build-graph.txt
python model/field.py --settings                         # ~15 min  -> results/field-settings.txt (2024 only)
python model/field.py                                    # ~7 min   -> results/field.txt
python model/coauthors.py --settings                     # ~15 min  -> results/coauthors-settings.txt (2024 only)
python model/coauthors.py                                # ~20 min  -> results/coauthors.txt
```

Each `--settings` run tries its settings on the validation round only and writes
the best on its last line (`chosen: ...`); the models read that line. So what was
chosen on 2024 is what runs on 2025, on any computer, and the file shows why.

In Docker, after `docker compose up` has run the pipeline:
`docker compose --profile learning run --rm model` runs build_graph, field and
coauthors, with the settings already in `results/`.

CPU only. Node ids are sorted IRIs and every model has a seed, so a run gives
the same numbers on the same computer. On another, the counts are exact (guess,
leak, the authors' count, the four link baselines); logistic regression,
GraphSAGE and the embeddings may differ, the embeddings by up to 0.02 in MRR.
That is why the settings are chosen, and written down, by the run itself.

coauthors.py prints one warning, from PyTorch: `'pin_memory' argument is set as
true but no accelerator is found`. PyKEEN asks for pinned memory, a speed-up for
copies to a GPU, when it probes the batch size; with no GPU, PyTorch skips it and
computes the same thing. The probe is PyKEEN's default, and the results were made
with it, so it stays.

## The graph the models see (build_graph.py)

Papers 5,211, authors 14,090, venues 2,216, institutions 3,656; edges: author
writes paper, paper publishedIn venue, paper cites paper (LU to LU, 2,116), paper
withInstitution institution. A paper's features are what it is the day it is
published: type, language, open access, number of authors. The other nodes have
no features; the models learn a vector for each.

**The label is taken out.** The field is the topic's field (paper pub:hasTopic
topic, topic pub:field), so the topic is the answer: no topic is a node and no
hasTopic is an edge. field.py shows what leaving it in would do (line 0, below).

## The split: by time (D17, D18)

Our papers have years, so every model trains on the past and is tested on the
future, twice: a **validation** round (train before 2024, test 2024), where every
setting was chosen (`--settings`), and a **test** round (train before 2025, test
2025), the result we report, run with the settings fixed. A random split would
let papers of the same year, by the same authors, teach the model its answer; by
time, the model knows only what was known before.

## Results

### The field of a paper, 2025 (results/field.txt)

1,430 papers, 26 fields; 81% have an author already seen in 2022-2024.
GraphSAGE: hidden 32, 400 epochs, dropout 0.5, the best of 16 settings on 2024
(results/field-settings.txt).

| Model | Accuracy | Macro-F1 |
|---|---|---|
| guess: always Medicine | 0.327 | 0.020 |
| 0 · the topic kept (the leak) | 0.848 | 0.884 |
| 1 · the paper's row: logistic regression on type, language, open access, authors, venue | 0.395 | 0.139 |
| 2 · count over the graph: its authors' earlier fields | **0.549** | **0.350** |
| 3 · GraphSAGE (to_hetero), 5 seeds | 0.517 (0.501 to 0.528) | 0.341 (0.306 to 0.360) |

On 2024 (validation) the order is the same: row 0.383, GraphSAGE 0.531 (0.519
to 0.537), count 0.551.

### New co-authorships, 2025 (results/coauthors.txt)

1,623 new pairs between 9,150 authors who had a co-author before 2025, ranked
both ways (3,246 queries, about 9,100 candidates each); half (1,588) share an
earlier co-author. The embedding: DistMult, dimension 128, the best MRR of six on
2024 (results/coauthors-settings.txt).

| Model | MRR | Hits@10 | Hits@100 | MRR, shared co-author | MRR, none |
|---|---|---|---|---|---|
| random | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| popularity | 0.025 | 0.029 | 0.144 | 0.032 | 0.017 |
| common neighbours | 0.069 | 0.164 | 0.374 | 0.140 | 0.000 |
| Adamic-Adar | **0.072** | **0.169** | **0.382** | **0.146** | 0.000 |
| DistMult (PyKEEN), 3 seeds | 0.046 (all three) | 0.101 (0.100 to 0.103) | 0.354 to 0.357 | 0.087 to 0.089 | 0.006 to 0.007 |

On 2024 (validation): Adamic-Adar MRR 0.098, DistMult 0.084 (0.079 to 0.091);
but on Hits@100 DistMult was ahead, 0.469 to 0.480 against 0.448.

## What the numbers say

- **The leak is real.** With the topic, a lookup is right on every paper whose
  topic it has seen (1.000 on 78% of 2025): a score that high is a leak, not a model.
- **The graph matters for the field.** The paper's own row gets 0.395; what its
  neighbours know gets 0.517 (GraphSAGE) to 0.549 (the count). Most papers share
  an author with an earlier paper, and authors stay in their field.
- **But both graph models lose to a count.** For the field, counting the authors'
  earlier fields (one step of label propagation) beats GraphSAGE, which sees its
  neighbours' features but never their labels: a known result (Huang et al. 2021,
  "Combining Label Propagation and Simple Models Out-performs Graph Neural
  Networks", ICLR). For co-authorships, Adamic-Adar beats the embedding on
  every score of 2025 (MRR 0.072 against 0.046).
- **Where the counts are blind.** Half the new pairs share no earlier co-author:
  common neighbours and Adamic-Adar give the right partner 0, behind everyone
  they can score (MRR 0.000).
  There popularity does best (0.017): authors with many co-authors keep finding
  new ones. The embedding gets 0.006 to 0.007, so on 2025 it wins nowhere; on
  2024 it led only on Hits@100.
- **Losing to a baseline is the result.** We report it, with the reason, rather
  than tune the models on 2025 until they win.

## What the numbers do not show

- **The label is a model's output.** OpenAlex assigns topics automatically, from a
  paper's title, abstract, citations and journal name
  ([OpenAlex help: Topics](https://help.openalex.org/hc/en-us/articles/24736129405719-Topics)).
  So "the field" is OpenAlex's guess, not a fact checked by a person, and two of
  its inputs, the venue and the citations, are in our graph: part of what the
  models learn is OpenAlex's own rule.
- **Titles are left out.** The words of a title would be the strongest feature
  for a field; the models leave them out to measure what the graph adds.
- **Open access can change after publication** (a copy deposited later): a paper
  feature that is not quite known on day one.
- **Author records are not perfect.** 20 ORCIDs have two OpenAlex author records
  (CQ9): a pair counted "new" may be one person split in two; and 2,101
  authorships name no author, so they are in no co-authorship.
- **One year of test, few seeds.** 2025 is one draw. The gaps between the graph
  models and the counts are larger than the spread of the seeds; the gaps between
  the embeddings in `--settings` (one seed) are not, and two computers rank them
  differently.
- **Settings from 2024 may not carry over.** The 2025 knowledge graph is larger
  (145,174 triples against 103,743), trained for the same 100 epochs.
