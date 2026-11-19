"""Evaluate legal-error type classification: rule baseline vs trained classifiers, over clause-grouped seeds.

    python modeling/error_eval.py                     # -> reports/error_classification.md, reports/tables/errcls*.tsv

Systems:
  majority ("none")     always predicts "none" (floor)
  rules                 modeling/legal_cues.rule_error_type (no training)
  <errcls-* runs>       modeling/error_classifier.py predictions in modeling/runs_err/<system>/random_s*/
Gold labels: "none" for standard simplifications, the injected error type for perturbed pairs (objective,
from src/perturb.py; not LLM-annotator judgements). Aggressive pairs have no known type and are excluded.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from error_classifier import prf, rows_for  # noqa: E402
from legal_cues import ERROR_CLASSES, rule_error_type  # noqa: E402
from lmp_data import ROOT  # noqa: E402
from metrics import agg  # noqa: E402


def fmt(m, s):
    return "n/a" if m != m else f"{m:.3f} ± {s:.3f}"


def collect(splits_root: Path, runs_err: Path, family: str = "random") -> dict:
    """{system: {split_name: (gold, pred, langs)}} on the test rows of every split of the family."""
    res: dict = defaultdict(dict)
    split_dirs = sorted(d for d in splits_root.glob(f"{family}_s*") if d.is_dir() and "__" not in d.name)
    for d in split_dirs:
        test = rows_for(d, "test")
        gold = [r["gold"] for r in test]
        langs = [r["lang"] for r in test]
        res["majority (none)"][d.name] = (gold, ["none"] * len(gold), langs)
        res["rules"][d.name] = (gold, [rule_error_type(r["original"], r["simplification"])[0] for r in test], langs)
    for f in sorted(runs_err.glob(f"*/{family}_s*/errcls_preds_test.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        res[f.parent.parent.name][f.parent.name] = ([r["gold"] for r in rows], [r["pred"] for r in rows],
                                                    [r["lang"] for r in rows])
    return res


def summarise(res: dict) -> dict:
    out = {}
    for system, splits in res.items():
        per = {name: prf(g, p) for name, (g, p, _) in splits.items()}
        by_lang = defaultdict(list)
        for name, (g, p, langs) in splits.items():
            for lg in sorted(set(langs)):
                idx = [i for i, x in enumerate(langs) if x == lg]
                by_lang[lg].append(prf([g[i] for i in idx], [p[i] for i in idx])["macro_f1"])
        pooled_g = [x for g, _, _ in splits.values() for x in g]
        pooled_p = [x for _, p, _ in splits.values() for x in p]
        out[system] = {
            "seeds": len(per), "splits": sorted(per),
            "macro_f1": agg([m["macro_f1"] for m in per.values()]),
            "accuracy": agg([m["accuracy"] for m in per.values()]),
            "per_class_f1": {c: agg([m["per_class"].get(c, {}).get("f1", 0.0) for m in per.values()
                                     if c in m["per_class"]]) for c in ERROR_CLASSES},
            "per_class_pr": {c: (agg([m["per_class"][c]["precision"] for m in per.values() if c in m["per_class"]]),
                                 agg([m["per_class"][c]["recall"] for m in per.values() if c in m["per_class"]]))
                             for c in ERROR_CLASSES},
            "by_lang": {lg: agg(v) for lg, v in by_lang.items()},
            "pooled": prf(pooled_g, pooled_p),
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits", default=str(ROOT / "data" / "splits"))
    ap.add_argument("--runs-err", default=str(ROOT / "modeling" / "runs_err"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "error_classification.md"))
    ap.add_argument("--tables", default=str(ROOT / "reports" / "tables"))
    args = ap.parse_args(argv)
    res = collect(Path(args.splits), Path(args.runs_err))
    if not res:
        sys.exit("no random_s* splits found")
    s = summarise(res)
    order = sorted(s, key=lambda k: -s[k]["macro_f1"][0])
    best = next((k for k in order if k not in ("rules", "majority (none)")), order[0])
    n_test = {name: len(g) for name, (g, _, _) in next(iter(res.values())).items()}
    gold_counts = Counter(x for g, _, _ in next(iter(res.values())).values() for x in g)

    L = ["# Legal-error type classification", "",
         "Task: predict the legal error in a simplification — none, modality (shall↔may), negation, number, "
         "exception_drop or scope. Gold labels are **objective**: \"none\" for the standard simplifications and the "
         "rule-injected error type for perturbed pairs (`src/perturb.py`), not LLM-annotator judgements. Aggressive "
         "pairs have no known type and are excluded. \"none\" means *no injected error*, not *no error*.", "",
         f"Clause-grouped random splits: {', '.join(f'{k} (n={v})' for k, v in n_test.items())}; "
         f"pooled test gold distribution {dict(gold_counts)}. Mean ± std over splits.", "",
         "| System | splits | Macro-F1 | Accuracy | EN macro-F1 | HI macro-F1 |", "|---|---|---|---|---|---|"]
    for k in order:
        d = s[k]
        L.append(f"| {k} | {d['seeds']} | {fmt(*d['macro_f1'])} | {fmt(*d['accuracy'])} | "
                 f"{fmt(*d['by_lang'].get('en', (float('nan'), 0)))} | {fmt(*d['by_lang'].get('hi', (float('nan'), 0)))} |")
    L += ["", "## Per-class F1", "", "| Class | " + " | ".join(order) + " |", "|---" * (len(order) + 1) + "|"]
    for c in ERROR_CLASSES:
        L.append(f"| {c} | " + " | ".join(fmt(*s[k]['per_class_f1'][c]) for k in order) + " |")
    for k in [best, "rules"] if best != "rules" else ["rules"]:
        L += ["", f"## {k}: precision / recall per class (mean over splits)", "",
              "| Class | Precision | Recall |", "|---|---|---|"]
        for c in ERROR_CLASSES:
            (pm, ps), (rm, rs) = s[k]["per_class_pr"][c]
            L.append(f"| {c} | {fmt(pm, ps)} | {fmt(rm, rs)} |")
        conf = s[k]["pooled"]["confusion"]
        L += ["", f"Pooled confusion matrix for {k} (rows = gold, columns = predicted):", "",
              "| gold \\ pred | " + " | ".join(ERROR_CLASSES) + " |", "|---" * (len(ERROR_CLASSES) + 1) + "|"]
        for g in ERROR_CLASSES:
            if g in conf:
                L.append(f"| {g} | " + " | ".join(str(conf[g].get(p, 0)) for p in ERROR_CLASSES) + " |")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    tables = Path(args.tables)
    tables.mkdir(parents=True, exist_ok=True)
    rows = ["System\tSplits\tMacro-F1\tAccuracy\tEN macro-F1\tHI macro-F1"]
    for k in order:
        d = s[k]
        rows.append("\t".join([k, str(d["seeds"]), fmt(*d["macro_f1"]), fmt(*d["accuracy"]),
                               fmt(*d["by_lang"].get("en", (float("nan"), 0))),
                               fmt(*d["by_lang"].get("hi", (float("nan"), 0)))]))
    (tables / "errcls.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    pc = ["Class\t" + "\t".join(order)] + [c + "\t" + "\t".join(fmt(*s[k]["per_class_f1"][c]) for k in order)
                                           for c in ERROR_CLASSES]
    (tables / "errcls_per_class.tsv").write_text("\n".join(pc) + "\n", encoding="utf-8")
    Path(args.out).with_suffix(".json").write_text(json.dumps(s, indent=1, default=str), encoding="utf-8")
    print("\n".join(L[:14 + len(order)]))
    print(f"\nwrote {args.out}, {tables / 'errcls.tsv'}, {tables / 'errcls_per_class.tsv'}")


if __name__ == "__main__":
    main()
