"""E5: pick >= 15 legally difficult cases for qualitative error analysis.

    python modeling/error_analysis.py --system xlm-roberta-base-da [--family random] [--n 20]

Predictions for the same pair across seeds are averaged. Cases are chosen to cover:
  - every injected error type (perturbed pairs), worst-predicted first
  - every annotator `main_change` category present in the test sets
  - the largest over-scores and under-scores among normal / aggressive simplifications
Writes reports/error_analysis_<system>.md and .csv. The `analysis` column is EMPTY on purpose:
the team writes the legal explanation for each case (never generated text).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmp_data import ROOT, RUNS  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from common import mean, read_jsonl, write_csv  # noqa: E402
from rubric import decision  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system", required=True)
    ap.add_argument("--family", default="random", help="split family, e.g. random, ood_rti_to_cpa")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--runs-dir", default=str(RUNS))
    ap.add_argument("--labeled", default=str(ROOT / "data" / "processed" / "labeled_pairs.jsonl"))
    ap.add_argument("--out-dir", default=str(ROOT / "reports"))
    args = ap.parse_args(argv)

    files = [f for f in Path(args.runs_dir, args.system).glob("*/preds_test.jsonl")
             if re.sub(r"_s\d+", "", f.parent.name) == args.family]
    if not files:
        sys.exit(f"no predictions for {args.system} / {args.family}")
    preds = defaultdict(list)
    for f in files:
        for r in read_jsonl(f):
            preds[r["pair_id"]].append(r["pred"])
    labeled = {r["pair_id"]: r for r in read_jsonl(args.labeled)}
    cases = []
    for pid, ps in preds.items():
        r = labeled.get(pid)
        if r is None:
            continue
        p = mean(ps)
        cases.append(dict(r, pred=round(p, 2), err=round(p - r["label"], 2), n_runs=len(ps)))
    if not cases:
        sys.exit("predictions do not match labeled_pairs.jsonl")

    chosen, seen = [], set()

    def take(rows, k, why):
        for c in sorted(rows, key=lambda c: -abs(c["err"]))[:k]:
            if c["pair_id"] not in seen:
                seen.add(c["pair_id"])
                chosen.append(dict(c, why=why))

    by_et = defaultdict(list)
    for c in cases:
        if c.get("error_type"):
            by_et[c["error_type"]].append(c)
    for et, rows in sorted(by_et.items()):
        take(rows, 2, f"injected {et}")
    by_mc = defaultdict(list)
    for c in cases:
        if c.get("main_change") and c["main_change"] != "none":
            by_mc[c["main_change"]].append(c)
    for mc, rows in sorted(by_mc.items()):
        take(rows, 1, f"annotators: {mc}")
    natural = [c for c in cases if c["variant"] in ("normal", "aggressive")]
    take([c for c in natural if c["err"] > 0], 3, "largest over-score")
    take([c for c in natural if c["err"] < 0], 2, "largest under-score")
    take(cases, max(0, args.n - len(chosen)), "large error")
    chosen = chosen[: max(args.n, 15)]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fields = ["case", "why", "pair_id", "lang", "act_id", "variant", "error_type", "main_change", "label", "label_std",
              "pred", "err", "gold_decision", "pred_decision", "original", "simplification", "analysis"]
    rows = [dict(c, case=i, gold_decision=decision(c["label"]), pred_decision=decision(c["pred"]), analysis="")
            for i, c in enumerate(chosen, 1)]
    write_csv(out / f"error_analysis_{args.system}.csv", rows, fields)
    L = [f"# Error analysis: {args.system} ({args.family})", "",
         f"{len(rows)} cases; predictions averaged over {len(files)} runs. Fill in **Analysis** by hand.", ""]
    for c in rows:
        L += [f"## Case {c['case']} — {c['why']}", "",
              f"`{c['pair_id']}` · gold {c['label']:.2f} (± {c.get('label_std') or 0:.2f}, {c['gold_decision']}) · "
              f"predicted {c['pred']:.2f} ({c['pred_decision']}) · error type: {c.get('error_type') or '—'} · "
              f"annotators' main change: {c.get('main_change') or '—'}", "",
              f"**Original:** {c['original']}", "", f"**Simplification:** {c['simplification']}", "",
              "**Analysis:** [TBD — written by the team]", ""]
    (out / f"error_analysis_{args.system}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {len(rows)} cases to {out}/error_analysis_{args.system}.md/.csv")


if __name__ == "__main__":
    main()
