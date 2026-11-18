"""Loading split files and writing prediction files (shared by every modelling script).

Split dirs (from src/split.py): train.jsonl, dev.jsonl, test.jsonl, train_da.jsonl, dev_da.jsonl,
meta.json; holdouts in data/splits/holdout_{identical,unrelated}.jsonl.

Prediction files: modeling/runs/<system>/<split_name>/preds_<set>.jsonl, one row per pair:
    pair_id, clause_id, act_id, lang, variant, error_type, main_change, label, pred, pred_raw
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import read_jsonl, write_jsonl  # noqa: E402

RUNS = ROOT / "modeling" / "runs"
SPLITS = ROOT / "data" / "splits"
KEEP = ["pair_id", "clause_id", "act_id", "lang", "variant", "error_type", "main_change", "label"]
OPTIONAL = ["main_change_pred", "explanation"]           # LLM judge extras


def load_split(split_dir: Path, name: str, langs=None) -> list[dict]:
    rows = read_jsonl(Path(split_dir) / f"{name}.jsonl")
    if langs:
        rows = [r for r in rows if r.get("lang") in langs]
    return rows


def holdout_files(split_dir: Path) -> dict[str, Path]:
    """Holdouts live next to the split dirs (data/splits/holdout_*.jsonl) or inside the split dir."""
    out = {}
    for kind in ("identical", "unrelated"):
        for cand in (Path(split_dir) / f"holdout_{kind}.jsonl", Path(split_dir).parent / f"holdout_{kind}.jsonl"):
            if cand.exists():
                out[f"holdout_{kind}"] = cand
                break
    return out


def run_dir(system: str, split_name: str, runs: Path | None = None) -> Path:
    d = (runs or RUNS) / system / split_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_preds(path: Path, rows: list[dict], preds_raw, lo: float = 1.0, hi: float = 10.0) -> None:
    out = []
    for r, p in zip(rows, preds_raw):
        o = {k: r.get(k) for k in KEEP}
        o.update({k: r[k] for k in OPTIONAL if r.get(k) is not None})
        o["pred_raw"] = float(p)
        o["pred"] = float(min(hi, max(lo, p)))
        out.append(o)
    write_jsonl(path, out)


def write_json(path: Path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
