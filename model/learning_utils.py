"""Small helpers the Session 6 scripts share: the split by time, and the scores.
The same style as the course's demos/session-06-learning/learning_utils.py.
"""

import numpy as np
from sklearn.metrics import accuracy_score, f1_score


# ---------------------------------------------------------------- the split
def split_by_year(year, y, train_years, test_year):
    """Train on the papers of the train years, test on the papers of one later
    year: the model never sees a paper from its test year, or after it, with
    its label (D17). Papers without a label (y = -1) are in neither. Returns
    (train, test), two arrays of paper positions."""
    year, y = np.asarray(year), np.asarray(y)
    labelled = y >= 0
    train = np.flatnonzero(labelled & np.isin(year, train_years))
    test = np.flatnonzero(labelled & (year == test_year))
    assert year[train].max() < test_year, "a training paper is not older than the test year"
    return train, test


# ---------------------------------------------------------------- classification scores
def scores(y_true, y_pred):
    """Accuracy (the share right) and macro-F1 (the F1 of each field, averaged
    with every field counting the same: small fields matter as much as
    Medicine, so always answering Medicine scores badly)."""
    return {"accuracy": accuracy_score(y_true, y_pred),
            "macro-F1": f1_score(y_true, y_pred, average="macro", zero_division=0)}


# ---------------------------------------------------------------- ranking scores
def realistic_rank(scores_, true, candidates):
    """The rank of the true answer among the candidates (a boolean mask, the
    true one included), 1 = first. Ties share the middle of their places: with
    a count, hundreds of candidates often tie, and putting the right one first
    (or last) among them would flatter (or punish) the model by luck."""
    s = scores_[true]
    higher = np.sum((scores_ > s) & candidates)
    ties = np.sum((scores_ == s) & candidates) - 1
    return 1 + higher + ties / 2


def mrr(ranks):
    """Mean reciprocal rank: the average of 1/rank. Rank 1 counts 1, rank 10 counts 0.1."""
    return float(np.mean(1.0 / np.asarray(ranks, dtype=float)))


def hits_at_k(ranks, k):
    """The share of right answers ranked in the top k."""
    return float(np.mean(np.asarray(ranks) <= k))
