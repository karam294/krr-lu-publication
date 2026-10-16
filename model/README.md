# model/

YOUR TEAM: your Session 6 work, on your own graph.

- Start from `build/graph.nt` (written by `pipeline/run.py`): convert it to
  PyTorch Geometric as the course's `build_graph.py` does, with the label
  taken out of the features.
- A node classification model and a link prediction model, each against a
  simple baseline (a table model; a count), with a split that does not leak:
  by time if your data has dates, by group otherwise. Several seeds, and the
  spread.
- Save every run's output in `model/results/` with the date and versions,
  and quote only those numbers in the report.

The stack does not have to serve the model; the results and the evaluation
are what the rubric scores ("Prediction and evaluation honesty").
