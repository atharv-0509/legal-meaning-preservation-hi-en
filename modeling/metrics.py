"""Metrics (pure Python / no scipy needed): Pearson, Spearman, RMSE, MAE, over-scoring rate,
decision accuracy and macro-F1 (Preserved / Partially Preserved / Not Preserved), sanity rates."""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import mean, pearson, spearman, std  # noqa: E402
from rubric import DECISIONS, decision  # noqa: E402

DECISION_NAMES = [name for _, name in DECISIONS]


def macro_f1(gold: list[str], pred: list[str], labels=DECISION_NAMES) -> float:
    f1s = []
    for c in labels:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        if tp + fp + fn == 0:
            continue                                          # class absent in both: skip
        f1s.append(2 * tp / (2 * tp + fp + fn))
    return mean(f1s) if f1s else float("nan")


def regression_metrics(labels: list[float], preds: list[float], over_tol: float = 0.0) -> dict:
    n = len(labels)
    if n == 0:
        return {"n": 0}
    err = [p - y for p, y in zip(preds, labels)]
    gold_d = [decision(y) for y in labels]
    pred_d = [decision(p) for p in preds]
    return {
        "n": n,
        "pearson": pearson(labels, preds) if n > 2 else float("nan"),
        "spearman": spearman(labels, preds) if n > 2 else float("nan"),
        "rmse": math.sqrt(mean(e * e for e in err)),
        "mae": mean(abs(e) for e in err),
        "over_rate": mean(e > over_tol for e in err),      # paper Table 6: % predictions above the human label
        "mean_error": mean(err),
        "decision_acc": mean(g == p for g, p in zip(gold_d, pred_d)),
        "decision_macro_f1": macro_f1(gold_d, pred_d),
    }


def sanity_metrics(preds: list[float], kind: str, identical_min: float = 9.9, unrelated_max: float = 1.1) -> dict:
    if not preds:
        return {"n": 0}
    if kind == "identical":
        return {"n": len(preds), "pass_rate": mean(p >= identical_min for p in preds), "mean_pred": mean(preds),
                "threshold": f">= {identical_min}"}
    return {"n": len(preds), "pass_rate": mean(p <= unrelated_max for p in preds), "mean_pred": mean(preds),
            "threshold": f"<= {unrelated_max}"}


def grouped(rows: list[dict], key: str) -> dict[str, dict]:
    groups = defaultdict(list)
    for r in rows:
        k = r.get(key)
        if k is not None:
            groups[k].append(r)
    return {k: regression_metrics([r["label"] for r in v], [r["pred"] for r in v]) for k, v in sorted(groups.items())}


def evaluate_rows(rows: list[dict]) -> dict:
    out = {"overall": regression_metrics([r["label"] for r in rows], [r["pred"] for r in rows])}
    for key in ("lang", "act_id", "variant", "error_type"):
        out[f"by_{key}"] = grouped(rows, key)
    return out


def agg(values: list[float]) -> tuple[float, float]:
    vals = [v for v in values if v == v]
    if not vals:
        return float("nan"), float("nan")
    return mean(vals), (std(vals, ddof=1) if len(vals) > 1 else 0.0)
