"""The access layer on the web: a page to ask a question and see the answer,
and the TEXT2SPARQL contract, at one address.

    python serve.py                       serves on http://127.0.0.1:8000

    GET /                                 the page (ui.html): type a question, see the answer,
                                          the query that computed it, each try and its problems
    GET /ask?question=...                 what the page asks: the whole result, as JSON
    GET /?question=...&dataset=https://ul.edu.lb/kr/lu/
                                          the TEXT2SPARQL contract, unchanged:
                                          {"dataset": "...", "question": "...", "query": "SELECT ..."}

A refusal comes back, in the contract, as a query that returns nothing, with
the reason in a comment, so a harness still gets valid SPARQL. When Gemini
cannot be reached or a run fails, both say why, and the server keeps serving.
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from access_layer import RULES_ID, answer, load_examples, model_name, open_store

DATASET = os.environ.get("DATASET_ID", "https://ul.edu.lb/kr/lu/")  # as in questions.yaml
STORE, EXAMPLES = open_store(), load_examples()
PAGE = (Path(__file__).resolve().parent / "ui.html").read_bytes()
MAX_ROWS = 200                                   # the page shows at most this many rows


def run_question(question):
    """answer(), but a failure (no key, Gemini busy, the daily limit) becomes a
    message instead of stopping the server."""
    try:
        return answer(question, STORE, EXAMPLES), None
    except SystemExit as e:                      # the layer's own messages (access_layer.ask_model)
        return None, str(e)
    except Exception as e:                       # anything else: say what, keep serving
        return None, f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"


def query_for(question):
    r, error = run_question(question)
    if error:
        return f"# ERROR: {error}\nSELECT * WHERE {{ FILTER(false) }}"
    if r["refused"]:
        reason = r["refused"].replace("\n", " ")
        return f"# {reason}\nSELECT * WHERE {{ FILTER(false) }}"
    return r["query"]


def ask_json(question):
    """Everything the page shows: the answer (rows), the query, each try and its problems."""
    t = time.time()
    r, error = run_question(question)
    out = {"question": question, "model": model_name(), "rules": RULES_ID, "error": error}
    if r:
        rows = r["rows"]
        if isinstance(rows, bool):               # an ASK query
            rows = [{"answer": "yes" if rows else "no"}]
        rows = rows or []
        columns = list(dict.fromkeys(k for row in rows for k in row))
        out.update(query=r["query"], refused=r["refused"], attempts=r["attempts"], columns=columns,
                   rows=rows[:MAX_ROWS], total=len(rows))
    out["seconds"] = round(time.time() - t, 1)
    return out


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, kind="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", f"{kind}; charset=utf-8")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def do_GET(self):
        url = urlparse(self.path)
        args = parse_qs(url.query)
        question = args.get("question", [""])[0].strip()
        if url.path == "/ask":
            if not question:
                return self.send(400, {"error": "give ?question=..."})
            return self.send(200, ask_json(question))
        if url.path == "/favicon.ico":            # no icon: say so quietly
            self.send_response(204)
            return self.end_headers()
        if url.path != "/":
            return self.send(404, {"error": "not found"})
        if not question:                         # no question: the page
            return self.send(200, PAGE, "text/html")
        dataset = args.get("dataset", [DATASET])[0]
        if dataset != DATASET:
            return self.send(400, {"error": f"give ?question=... and dataset={DATASET}"})
        self.send(200, {"dataset": dataset, "question": question, "query": query_for(question)})

    def log_message(self, fmt, *args):
        print("  " + fmt % args, flush=True)


def main():
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    shown = "127.0.0.1" if host == "0.0.0.0" else host     # in Docker the port is published on 127.0.0.1
    print(f"the page:   http://{shown}:{port}/", flush=True)
    print(f"the TEXT2SPARQL contract on http://{shown}:{port}/?question=...&dataset={DATASET}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
