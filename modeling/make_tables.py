"""Write the TSV tables the paper and slides read (reports/tables/*.tsv).

    python modeling/make_tables.py

Inputs are files our own pipeline wrote: reports/results.json (modeling/evaluate.py), the per-run
prediction files in modeling/runs/, data/splits/ and data/processed/. Nothing is typed by hand.

The systems shown are DECLARED below, not chosen by test score (Codex review, finding 8): the principal
system is the FrJUDGE-pretrained cross-encoder fine-tuned with DA (the configuration used for every
experiment E1-E4), compared with the same backbone trained from scratch with DA, and LaBSE-cal as the
generic baseline. A missing run is an error, never silently replaced by another system.
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
RUNS = ROOT / "modeling" / "runs"
SPLITS = ROOT / "data" / "splits"
BASELINES = ("rougeL", "bleu", "labse", "bertscore")

PRINCIPAL = "xlm-roberta-base-frjudge-da"      # FrJUDGE -> ours, with DA (all of E1-E4)
SCRATCH = "xlm-roberta-base-da"                # same backbone and settings, no FrJUDGE pre-training
BASELINE = "labse-cal"                         # declared generic baseline (best mapping of LaBSE)
SEEDS = (42, 43, 44)
E1_ORDER = [PRINCIPAL, "xlm-roberta-base-frjudge", SCRATCH, "xlm-roberta-base", "muril-base-cased-da",
            "muril-base-cased", "labse-cal", "labse", "bertscore-cal", "bertscore", "bleu-cal", "bleu",
            "rougeL-cal", "rougeL"]
NAMES = {PRINCIPAL: "XLM-R, FrJUDGE→ours, DA", "xlm-roberta-base-frjudge": "XLM-R, FrJUDGE→ours, no DA",
         SCRATCH: "XLM-R from scratch, DA", "xlm-roberta-base": "XLM-R from scratch, no DA",
         "muril-base-cased-da": "MuRIL from scratch, DA", "muril-base-cased": "MuRIL from scratch, no DA"}


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def ms(vals, pct: bool = False, nd: int = 3) -> str:
    vals = [v for v in vals if v is not None and v == v]
    if not vals:
        return "n/a"
    k = 100.0 if pct else 1.0
    m = statistics.mean(vals) * k
    if len(vals) == 1:
        return f"{m:.1f}" if pct else f"{m:.{nd}f}"
    s = statistics.stdev(vals) * k
    return f"{m:.1f} ± {s:.1f}" if pct else f"{m:.{nd}f} ± {s:.{nd}f}"


def name(s: str) -> str:
    return NAMES.get(s, s)


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = sum((a - mx) ** 2 for a in x) ** 0.5
    sy = sum((b - my) ** 2 for b in y) ** 0.5
    return sxy / (sx * sy) if sx and sy else None


def rmse(x, y):
    return (sum((a - b) ** 2 for a, b in zip(x, y)) / len(x)) ** 0.5 if x else None


def write(key: str, rows: list[list[str]]):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"{key}.tsv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t").writerows(rows)
    print(f"wrote reports/tables/{key}.tsv ({len(rows) - 1} rows)")


def require(fams: dict, fam: str, system: str) -> dict:
    d = fams.get(fam, {}).get(system)
    if not d or not d.get("test"):
        sys.exit(f"missing results: system {system!r} in family {fam!r} (run the experiments first)")
    return d


def overall(d, key):
    return [t["overall"].get(key) for t in d["test"]]


def group(d, by, g, key):
    return [t.get(f"by_{by}", {}).get(g, {}).get(key) for t in d["test"]]


def preds(system: str, split: str) -> list[dict]:
    return _jsonl(RUNS / system / split / "preds_test.jsonl")


# ----------------------------------------------------------------------------- tables
def dataset_table() -> list[list[str]]:
    proc = ROOT / "data" / "processed"
    clauses = _jsonl(proc / "clauses_final.jsonl")
    pairs = _jsonl(proc / "labeled_pairs.jsonl") or _jsonl(proc / "pairs.jsonl")
    rows = [["Act", "Lang", "Clauses", "Pairs", "Mean words", "Mean label"]]
    by = defaultdict(list)
    for p in pairs:
        by[(p["act_id"], p["lang"])].append(p)
    words = lambda ps: statistics.mean(len(re.findall(r"\S+", p["original"])) for p in ps)
    for (act, lang), ps in sorted(by.items()):
        n_cl = sum(1 for c in clauses if c["act_id"] == act and c.get(f"text_{lang}"))
        labels = [p["label"] for p in ps if p.get("label") is not None]
        rows.append([act.upper(), lang.upper(), str(n_cl), str(len(ps)), f"{words(ps):.1f}",
                     f"{statistics.mean(labels):.2f}" if labels else "n/a"])
    if pairs:
        labels = [p["label"] for p in pairs if p.get("label") is not None]
        rows.append(["All", "", str(len(clauses)), str(len(pairs)), f"{words(pairs):.1f}",
                     f"{statistics.mean(labels):.2f}" if labels else "n/a"])
    return rows


def variant_lookup() -> list[dict]:
    """Privileged diagnostic: predict each test pair by its VARIANT's mean training label (uses the answer
    key, so it is not a deployable baseline). Shows how much of the correlation the construction explains."""
    out = []
    for s in SEEDS:
        tr, te = _jsonl(SPLITS / f"random_s{s}" / "train.jsonl"), _jsonl(SPLITS / f"random_s{s}" / "test.jsonl")
        means = {v: statistics.mean(r["label"] for r in tr if r["variant"] == v) for v in {r["variant"] for r in tr}}
        y = [r["label"] for r in te]
        p = [means[r["variant"]] for r in te]
        out.append({"pearson": pearson(p, y), "spearman": None, "rmse": rmse(p, y),
                    "mae": sum(abs(a - b) for a, b in zip(p, y)) / len(y), "over": sum(a > b for a, b in zip(p, y)) / len(y)})
    return out


def main():
    write("dataset", dataset_table())
    res_path = ROOT / "reports" / "results.json"
    if not res_path.exists():
        sys.exit("reports/results.json missing: run modeling/evaluate.py first (only dataset.tsv written)")
    fams = json.loads(res_path.read_text(encoding="utf-8"))["families"]

    # E1: fixed, declared order (not sorted by test score)
    rnd = fams.get("random", {})
    require(fams, "random", PRINCIPAL), require(fams, "random", SCRATCH), require(fams, "random", BASELINE)
    e1 = [["System", "Pearson", "Spearman", "RMSE", "MAE", "Over-score %"]]
    for s in E1_ORDER:
        d = rnd.get(s)
        if d and d.get("test"):
            e1.append([name(s), ms(overall(d, "pearson")), ms(overall(d, "spearman")), ms(overall(d, "rmse")),
                       ms(overall(d, "mae")), ms(overall(d, "over_rate"), pct=True)])
    vl = variant_lookup()
    e1.append(["Variant-mean lookup (uses answer key; diagnostic, not a system)", ms([x["pearson"] for x in vl]),
               "n/a", ms([x["rmse"] for x in vl]), ms([x["mae"] for x in vl]), ms([x["over"] for x in vl], pct=True)])
    write("e1", e1)

    # E2: RTI clauses present in BOTH languages (bilingual_s*), DA, both systems
    e2 = [["System", "Setting", "Pearson", "RMSE", "Over-score %"]]
    for s in (PRINCIPAL, SCRATCH):
        d = require(fams, "bilingual", s)
        for lang in ("en", "hi"):
            e2.append([name(s), f"train EN+HI, test {lang.upper()}", ms(group(d, "lang", lang, "pearson")),
                       ms(group(d, "lang", lang, "rmse")), ms(group(d, "lang", lang, "over_rate"), pct=True)])
        for tr, te in (("en", "hi"), ("hi", "en")):
            dz = require(fams, f"bilingual__train-{tr}_test-{te}", s)
            e2.append([name(s), f"train {tr.upper()} → test {te.upper()} (zero-shot)", ms(overall(dz, "pearson")),
                       ms(overall(dz, "rmse")), ms(overall(dz, "over_rate"), pct=True)])
    write("e2", e2)

    # E3: unseen act (DA partners restricted to the training act), both systems
    e3 = [["System", "Split", "Pearson", "RMSE", "MAE"]]
    for s in (PRINCIPAL, SCRATCH):
        for fam, label in (("ood_cpa_to_rti", "CPA → RTI"), ("ood_rti_to_cpa", "RTI → CPA")):
            d = require(fams, fam, s)
            e3.append([name(s), label, ms(overall(d, "pearson")), ms(overall(d, "rmse")), ms(overall(d, "mae"))])
    write("e3", e3)

    # E4: per-language counts and pass rates, computed from the holdout prediction files
    hid, hun = _jsonl(SPLITS / "holdout_identical.jsonl"), _jsonl(SPLITS / "holdout_unrelated.jsonl")
    n = lambda rows, lang: sum(1 for r in rows if r["lang"] == lang)
    e4 = [["System", f"Identical ≥ 9.9 %: EN (n={n(hid, 'en')})", f"Identical ≥ 9.9 %: HI (n={n(hid, 'hi')})",
           f"Unrelated ≤ 1.1 %: EN (n={n(hun, 'en')})", f"Unrelated ≤ 1.1 %: HI (n={n(hun, 'hi')})"]]
    for s in [PRINCIPAL, "xlm-roberta-base-frjudge", SCRATCH, BASELINE, "labse", "bertscore", "bleu", "rougeL"]:
        cells = []
        for kind, ok in (("identical", lambda p: p >= 9.9), ("unrelated", lambda p: p <= 1.1)):
            for lang in ("en", "hi"):
                rates = []
                for d in sorted(RUNS.glob(f"{s}/random_s*")):
                    rows = [r for r in _jsonl(d / f"preds_holdout_{kind}.jsonl") if r["lang"] == lang]
                    if rows:
                        rates.append(sum(ok(r["pred"]) for r in rows) / len(rows))
                cells.append(ms(rates, pct=True) if rates else "not evaluated")
        e4.append([name(s)] + cells)
    write("e4", e4)

    # Diagnostic set: MAE on perturbed pairs by injected error type (principal vs baseline)
    dp, db = rnd[PRINCIPAL], rnd[BASELINE]
    types = sorted({g for t in dp["test"] for g in t.get("by_error_type", {}) if g})
    diag = [["Injected error type", "n per test split", f"MAE {name(PRINCIPAL)}", f"MAE {BASELINE}"]]
    for g in types:
        diag.append([g, ms(group(dp, "error_type", g, "n"), nd=0), ms(group(dp, "error_type", g, "mae")),
                     ms(group(db, "error_type", g, "mae"))])
    write("diag", diag)

    # Within-variant behaviour of the principal system (finding 9): MAE, mean signed error, Pearson
    var = [["Variant", "n per test split", "Mean label", f"MAE {name(PRINCIPAL)}",
            f"Mean signed error {name(PRINCIPAL)}", f"Within-variant Pearson {name(PRINCIPAL)}"]]
    for v in ("normal", "aggressive", "perturbed"):
        ns, labs, maes, mses, rs = [], [], [], [], []
        for s in SEEDS:
            rows = [r for r in preds(PRINCIPAL, f"random_s{s}") if r["variant"] == v]
            if not rows:
                continue
            y, p = [r["label"] for r in rows], [r["pred"] for r in rows]
            ns.append(len(rows)), labs.append(statistics.mean(y))
            maes.append(sum(abs(a - b) for a, b in zip(p, y)) / len(y))
            mses.append(sum(a - b for a, b in zip(p, y)) / len(y))
            rs.append(pearson(p, y))
        var.append([v, ms(ns, nd=0), ms(labs, nd=2), ms(maes), ms(mses), ms(rs)])
    write("variant", var)


def followup_tables():
    """Generalisation follow-up (19 Nov evening) and legal-error type classification, from their own reports."""
    gpath = ROOT / "reports" / "generalization_followup.json"
    if gpath.exists():
        fams = json.loads(gpath.read_text(encoding="utf-8"))["families"]
        frj = ROOT / "modeling" / "runs_frj"
        rows = [  # (system, label, FrJUDGE pre-training metrics file)
            ("xlm-roberta-base-frjudge-da", "XLM-R, original pre-training (3 seeds)",
             # E1 used the lmp-transfer pre-training (frjudge_s42_transfer), E2/E3 the lmp-e23-fixed one (frjudge_s42)
             (frj / "xlm-roberta-base-frjudge-pretrain" / "frjudge_s42_transfer" / "metrics.json",
              frj / "xlm-roberta-base-frjudge-pretrain" / "frjudge_s42" / "metrics.json")),
            ("xlm-roberta-base-frjudge-5s-da", "XLM-R, re-run pre-training (5 seeds)",
             frj / "xlm-roberta-base-frjudge-pretrain" / "frjudge_s42_5s" / "metrics.json"),
            ("muril-base-cased-frjudge-5s-da", "MuRIL (5 seeds)",
             frj / "muril-base-cased-frjudge-pretrain" / "frjudge_s42" / "metrics.json"),
        ]
        t = [["System (FrJUDGE→ours, DA)", "FrJUDGE", "E1", "E1 HI", "E2 EN", "E2 HI", "E3 C→R", "E3 R→C"]]
        for sysname, label, mpath in rows:
            paths = mpath if isinstance(mpath, tuple) else (mpath,)
            pres = [json.loads(m.read_text(encoding="utf-8"))["test"]["overall"]["pearson"] for m in paths if m.exists()]
            cell = lambda fam, key=None, g=None: (ms(group(fams[fam][sysname], key, g, "pearson")) if key else
                                                  ms(overall(fams[fam][sysname], "pearson"))) \
                if sysname in fams.get(fam, {}) else "n/a"
            t.append([label, " / ".join(f"{x:.3f}" for x in pres) or "n/a", cell("random"), cell("random", "lang", "hi"),
                      cell("bilingual", "lang", "en"), cell("bilingual", "lang", "hi"),
                      cell("ood_cpa_to_rti"), cell("ood_rti_to_cpa")])
        write("followup", t)
    epath = ROOT / "reports" / "error_classification.json"
    if epath.exists():
        e = json.loads(epath.read_text(encoding="utf-8"))
        order = [("rules", "Rules (no training)"), ("majority (none)", "Majority (\"none\")"),
                 ("errcls-muril-base-cased", "MuRIL"), ("errcls-muril-base-cased-aug", "MuRIL + augmentation"),
                 ("errcls-xlm-roberta-base-aug", "XLM-R + augmentation"),
                 ("errcls-muril-base-cased-augcue", "MuRIL + augmentation + cues")]
        t = [["System", "Macro-F1", "Acc.", "Mod.", "Neg.", "Num.", "Exc.", "Scope"]]
        for key, label in order:
            d = e.get(key)
            if not d:
                continue
            pc = d["per_class_f1"]
            t.append([label, f"{d['macro_f1'][0]:.3f} ± {d['macro_f1'][1]:.3f}",
                      f"{d['accuracy'][0]:.3f}"] +
                     [f"{pc[c][0]:.2f}" for c in ("modality", "negation", "number", "exception_drop", "scope")])
        write("errcls_main", t)


if __name__ == "__main__":
    main()
    followup_tables()
