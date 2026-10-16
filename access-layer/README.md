# access-layer/

The course's Session 7 access layer: a question in English becomes a SPARQL
query over your endpoint, grounded in `build/void.ttl` and a few examples,
checked, repaired up to twice, or refused. Gemini only (`GOOGLE_API_KEY` in
`.env`).

YOUR TEAM changes:

- `access_layer.py`: `NS` and `PFX`, your ontology's namespace and prefix;
- `prompt_rules.txt`: how things are named in your data, and what the
  subclasses are;
- `examples.ttl`: 6 to 10 example queries, in the SHACL vocabulary;
- `questions.yaml`: your test set, with gold queries and at least three
  questions to refuse; never the same questions as the examples.

Measure (with the stack up, from this folder):

```sh
SPARQL_ENDPOINT=http://127.0.0.1:3030/kr/sparql python evaluate.py
SPARQL_ENDPOINT=http://127.0.0.1:3030/kr/sparql LLM_MODE=record python evaluate.py > ../report/access-layer-score.txt
```

On Windows PowerShell, set the variables first, for example
`$env:SPARQL_ENDPOINT="http://127.0.0.1:3030/kr/sparql"`, then run
`python evaluate.py` (add `$env:LLM_MODE="record"` to record).

`LLM_MODE=record` saves every answer in `llm-cache.json`; commit it with the
score, and `LLM_MODE=replay` reproduces the score without the network.
The free tier limits requests a minute and a day: the scripts wait 4 s
between calls.
