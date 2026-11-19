"""Write the six TSV tables the paper and slides read (reports/tables/{e1,e2,e3,e4,diag,dataset}.tsv).

    python modeling/make_tables.py

Inputs are files our own pipeline wrote: reports/results.json (modeling/evaluate.py) and
data/processed/{clauses_final,pairs,labeled_pairs}.jsonl. Headers follow paper/tables.py
EXPECTED_HEADERS on the agent/paper-slides branch. A cell is "n/a" when the run does not exist.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "tables"
BASELINES = ("rougeL", "bleu", "labse", "bertscore")


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def ms(vals: list[float], pct: bool = False, nd: int = 3) -> str:
    vals = [v for v in vals if v is not None and v == v]
    if not vals:
        return "n/a"
    k = 100.0 if pct else 1.0
    m = statistics.mean(vals) * k
    if len(vals) == 1:
        return f"{m:.1f}" if pct else f"{m:.{nd}f}"
    s = statistics.stdev(vals) * k
    return f"{m:.1f} ± {s:.1f}" if pct else f"{m:.{nd}f} ± {s:.{nd}f}"


def is_baseline(system: str) -> bool:
    return system.split("-cal")[0] in BASELINES


def overall(d: dict, key: str) -> list[float]:
    return [t["overall"].get(key) for t in d.get("test", [])]


def group(d: dict, by: str, g: str, key: str) -> list[float]:
    return [t.get(f"by_{by}", {}).get(g, {}).get(key) for t in d.get("test", [])]


def mean_of(vals):
    vals = [v for v in vals if v is not None and v == v]
    return statistics.mean(vals) if vals else float("-inf")


def write(name: str, rows: list[list[str]]):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"{name}.tsv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t").writerows(rows)
    print(f"wrote reports/tables/{name}.tsv ({len(rows) - 1} rows)")


def dataset_table() -> list[list[str]]:
    proc = ROOT / "data" / "processed"
    clauses = _jsonl(proc / "clauses_final.jsonl")
    pairs = _jsonl(proc / "labeled_pairs.jsonl") or _jsonl(proc / "pairs.jsonl")
    rows = [["Act", "Lang", "Clauses", "Pairs", "Mean words", "Mean label"]]
    if not pairs:
        return rows
    by = defaultdict(list)
    for p in pairs:
        by[(p["act_id"], p["lang"])].append(p)
    for (act, lang), ps in sorted(by.items()):
        n_cl = sum(1 for c in clauses if c["act_id"] == act and c.get(f"text_{lang}"))
        words = statistics.mean(len(re.findall(r"\S+", p["original"])) for p in ps)
        labels = [p["label"] for p in ps if p.get("label") is not None]
        rows.append([act.upper(), lang.upper(), str(n_cl), str(len(ps)), f"{words:.1f}",
                     f"{statistics.mean(labels):.2f}" if labels else "n/a"])
    labels = [p["label"] for p in pairs if p.get("label") is not None]
    rows.append(["All", "", str(len(clauses)), str(len(pairs)),
                 f"{statistics.mean(len(re.findall(r'\S+', p['original'])) for p in pairs):.1f}",
                 f"{statistics.mean(labels):.2f}" if labels else "n/a"])
    return rows


def main():
    write("dataset", dataset_table())
    res_path = ROOT / "reports" / "results.json"
    if not res_path.exists():
        sys.exit("reports/results.json missing: run modeling/evaluate.py first (only dataset.tsv written)")
    fams = json.loads(res_path.read_text(encoding="utf-8"))["families"]
    rnd = fams.get("random", {})

    # E1: every system on random clause-grouped splits, best first
    order = sorted(rnd, key=lambda s: -mean_of(overall(rnd[s], "pearson")))
    e1 = [["System", "Pearson", "Spearman", "RMSE", "MAE", "Over-score %"]]
    for s in order:
        d = rnd[s]
        e1.append([s, ms(overall(d, "pearson")), ms(overall(d, "spearman")), ms(overall(d, "rmse")),
                   ms(overall(d, "mae")), ms(overall(d, "over_rate"), pct=True)])
    write("e1", e1)

    models = [s for s in order if not is_baseline(s)]
    best = models[0] if models else None
    da_models = [s for s in models if s.endswith("-da")]
    main_da = da_models[0] if da_models else best

    # E2: per-language results of the best DA model, and zero-shot transfer
    e2 = [["Setting", "Pearson", "RMSE", "Over-score %"]]
    if main_da:
        for lang in ("en", "hi"):
            d = rnd[main_da]
            e2.append([f"{main_da}: test {lang.upper()} (trained on EN+HI)", ms(group(d, "lang", lang, "pearson")),
                       ms(group(d, "lang", lang, "rmse")), ms(group(d, "lang", lang, "over_rate"), pct=True)])
        for fam in sorted(f for f in fams if f.startswith("random__")):
            m = re.search(r"train-(\w+)_test-(\w+)", fam)
            d = fams[fam].get(main_da)
            if m and d:
                e2.append([f"{main_da}: train {m.group(1).upper()} → test {m.group(2).upper()} (zero-shot)",
                           ms(overall(d, "pearson")), ms(overall(d, "rmse")), ms(overall(d, "over_rate"), pct=True)])
    write("e2", e2)

    # E3: out-of-domain splits
    e3 = [["Split", "Pearson", "RMSE", "MAE"]]
    for fam in sorted(f for f in fams if f.startswith("ood_")):
        d = fams[fam].get(main_da) or next(iter(fams[fam].values()))
        e3.append([fam[4:].replace("_to_", " → ").upper(), ms(overall(d, "pearson")), ms(overall(d, "rmse")),
                   ms(overall(d, "mae"))])
    write("e3", e3)

    # E4: sanity holdouts
    e4 = [["System", "Identical >= 9.9 %", "Unrelated <= 1.1 %"]]
    for s in order:
        d = rnd[s]
        i, u = d.get("holdout_identical", []), d.get("holdout_unrelated", [])
        if i or u:
            e4.append([s, ms([x.get("pass_rate") for x in i], pct=True), ms([x.get("pass_rate") for x in u], pct=True)])
    write("e4", e4)

    # Diagnostic set: MAE on perturbed pairs by injected error type
    base = next((s for s in order if is_baseline(s)), None)
    types = sorted({g for s in rnd.values() for t in s.get("test", []) for g in t.get("by_error_type", {}) if g})
    diag = [["Injected error type", "n", "MAE LMP model", "MAE baseline", "MAE LLM judge"]]
    for g in types:
        n = [t.get("by_error_type", {}).get(g, {}).get("n") for t in rnd[best]["test"]] if best else []
        diag.append([g, ms(n, nd=0) if n else "n/a",
                     ms(group(rnd[best], "error_type", g, "mae")) if best else "n/a",
                     (ms(group(rnd[base], "error_type", g, "mae")) + f" ({base})") if base else "n/a",
                     "not run (labels are LLM-produced; circular)"])
    write("diag", diag)


if __name__ == "__main__":
    main()
