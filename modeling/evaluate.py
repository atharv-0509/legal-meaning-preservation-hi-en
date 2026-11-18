"""Aggregate every run in modeling/runs into the results tables (E1-E4).

    python modeling/evaluate.py            # -> reports/results.md, reports/results.json

Metrics are recomputed from the prediction files. Runs over random_s42..s46 are one "family"
(random); their metrics are reported as mean ± std over seeds. OOD splits and language-transfer
runs (split names with "__train-X_test-Y") are their own families.
Headline numbers use human-annotated test pairs only; sanity checks (holdouts) are separate.
The human ceiling (leave-one-out Pearson from the annotations) is printed next to the models.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmp_data import ROOT, RUNS  # noqa: E402
from metrics import agg, evaluate_rows, sanity_metrics  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from common import read_jsonl  # noqa: E402

COLS = [("pearson", "Pearson"), ("spearman", "Spearman"), ("rmse", "RMSE"), ("mae", "MAE"),
        ("over_rate", "Over-score %"), ("decision_macro_f1", "Decision F1")]


def family(split_name: str) -> str:
    return re.sub(r"_s\d+", "", split_name)


def fmt(m, s, pct=False):
    if m != m:
        return "n/a"
    if pct:
        return f"{100 * m:.0f} ± {100 * s:.0f}"
    return f"{m:.3f} ± {s:.3f}" if s else f"{m:.3f}"


def human_ceiling(labeled_path: Path) -> float | None:
    from agreement import human_ceiling as hc
    rows = read_jsonl(labeled_path)
    if not rows:
        return None
    return hc({r["pair_uid"]: r["scores"] for r in rows if r.get("scores")})[0]


def collect(runs: Path, identical_min: float, unrelated_max: float) -> dict:
    """results[family][system] = {"seeds": [...], "test": [per-seed evaluate_rows], "holdout_*": [...]}"""
    res: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for f in sorted(runs.glob("*/*/preds_test.jsonl")):
        system, split_name = f.parent.parent.name, f.parent.name
        fam = family(split_name)
        rows = read_jsonl(f)
        if not rows:
            continue
        r = res[fam][system]
        r["splits"].append(split_name)
        r["test"].append(evaluate_rows(rows))
        r["preds"].append(rows)
        for kind in ("identical", "unrelated"):
            h = f.parent / f"preds_holdout_{kind}.jsonl"
            if h.exists():
                r[f"holdout_{kind}"].append(sanity_metrics([x["pred"] for x in read_jsonl(h)], kind,
                                                           identical_min, unrelated_max))
    return res


def table_overall(res_fam: dict) -> list[str]:
    L = ["| System | runs | " + " | ".join(c for _, c in COLS) + " |", "|---" * (len(COLS) + 2) + "|"]
    order = sorted(res_fam, key=lambda s: -agg([t["overall"]["pearson"] for t in res_fam[s]["test"]])[0]
                   if res_fam[s]["test"] else 0)
    for s in order:
        tests = res_fam[s]["test"]
        cells = [fmt(*agg([t["overall"][k] for t in tests]), pct=(k == "over_rate")) for k, _ in COLS]
        L.append(f"| {s} | {len(tests)} | " + " | ".join(cells) + " |")
    return L


def table_by(res_fam: dict, key: str, metrics=("pearson", "rmse")) -> list[str]:
    groups = sorted({g for s in res_fam.values() for t in s["test"] for g in t[f"by_{key}"]})
    if not groups:
        return []
    head = [f"{g} {m}" for g in groups for m in metrics]
    L = ["| System | " + " | ".join(head) + " |", "|---" * (len(head) + 1) + "|"]
    for s, d in sorted(res_fam.items()):
        cells = []
        for g in groups:
            for m in metrics:
                vals = [t[f"by_{key}"][g][m] for t in d["test"] if g in t[f"by_{key}"] and m in t[f"by_{key}"][g]]
                cells.append(fmt(*agg(vals)))
        L.append(f"| {s} | " + " | ".join(cells) + " |")
    return L


def table_sanity(res_fam: dict) -> list[str]:
    L = ["| System | identical pass % | identical mean pred | unrelated pass % | unrelated mean pred |",
         "|---|---|---|---|---|"]
    for s, d in sorted(res_fam.items()):
        i, u = d.get("holdout_identical", []), d.get("holdout_unrelated", [])
        if not i and not u:
            continue
        L.append(f"| {s} | {fmt(*agg([x['pass_rate'] for x in i]), pct=True)} | {fmt(*agg([x['mean_pred'] for x in i]))} "
                 f"| {fmt(*agg([x['pass_rate'] for x in u]), pct=True)} | {fmt(*agg([x['mean_pred'] for x in u]))} |")
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=str(RUNS))
    ap.add_argument("--labeled", default=str(ROOT / "data" / "processed" / "labeled_pairs.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "results.md"))
    ap.add_argument("--identical-min", type=float, default=9.9)
    ap.add_argument("--unrelated-max", type=float, default=1.1)
    args = ap.parse_args(argv)
    res = collect(Path(args.runs_dir), args.identical_min, args.unrelated_max)
    if not res:
        sys.exit(f"no runs in {args.runs_dir}")
    ceiling = human_ceiling(Path(args.labeled))

    L = ["# Results", "",
         "All numbers are computed from prediction files on **human-annotated test pairs only** "
         "(mean ± std over seeds where there are several runs). Predictions are clipped to [1, 10]. "
         "Decisions: ≥ 7 Preserved, ≥ 2 Partially Preserved, < 2 Not Preserved.", "",
         f"**Human ceiling** (mean leave-one-out Pearson of annotators): "
         f"{'n/a' if ceiling is None else f'{ceiling:.3f}'}", ""]
    fam_order = sorted(res, key=lambda f: (not f.startswith("random"), "__" in f, f))
    for fam in fam_order:
        title = {"random": "E1 — random clause-grouped splits"}.get(fam, fam)
        if fam.startswith("ood_"):
            title = f"E3 — out-of-domain: {fam[4:].replace('_to_', ' → ')}"
        if "__" in fam:
            title = f"E2 — language transfer: {fam}"
        L += [f"## {title}", ""] + table_overall(res[fam]) + [""]
        by_lang = table_by(res[fam], "lang")
        if by_lang:
            L += ["### By language", ""] + by_lang + [""]
        if fam == "random":
            L += ["### By act", ""] + table_by(res[fam], "act_id") + [""]
            L += ["### By variant (MAE and mean signed error; Pearson within a variant has little spread)", ""] + \
                table_by(res[fam], "variant", ("mae", "mean_error")) + [""]
            L += ["### Perturbed pairs by injected error type", ""] + \
                table_by(res[fam], "error_type", ("mae", "mean_error")) + [""]
        san = table_sanity(res[fam])
        if len(san) > 2:
            L += [f"### E4 — sanity checks (identical ≥ {args.identical_min}, unrelated ≤ {args.unrelated_max})", ""] + san + [""]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    summary = {fam: {s: {"splits": d["splits"], "test": d["test"], "holdout_identical": d.get("holdout_identical", []),
                         "holdout_unrelated": d.get("holdout_unrelated", [])} for s, d in sysd.items()}
               for fam, sysd in res.items()}
    Path(args.out).with_suffix(".json").write_text(json.dumps({"human_ceiling": ceiling, "families": summary},
                                                              indent=1, default=str), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwrote {args.out} and {Path(args.out).with_suffix('.json')}")


if __name__ == "__main__":
    main()
