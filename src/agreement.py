"""Step 7: read annotated workbooks -> agreement report, aggregated labels, adjudication list.

    python src/agreement.py            # main round  -> labeled_pairs.jsonl, annotations.jsonl,
                                       #                reports/agreement.md, reports/adjudicate.csv
    python src/agreement.py --pilot    # pilot round -> reports/agreement_pilot.md, adjudicate_pilot.csv
                                       #                (pilot scores are discarded: no labels written)

The LMP score is RECOMPUTED from bracket + error counts (rubric.lmp_score); the lmp_score cell in
the sheet is ignored, so the spreadsheet program used does not matter.

Reported: Krippendorff's alpha (interval on LMP; nominal on bracket), mean pairwise Pearson,
the leave-one-out human ceiling (each annotator vs. the mean of the others), per-annotator
leniency, and scores by language / variant (variant comes from pairs.jsonl, never the workbook).
"""
from __future__ import annotations

import argparse
import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_paths, mean, pearson, read_jsonl, std, write_csv, write_jsonl  # noqa: E402
from rubric import ERROR_COLS, lmp_score, normalise_bracket  # noqa: E402


# --------------------------------------------------------------------------- reading
def _num(v):
    if v is None or str(v).strip() == "":
        return 0
    try:
        return int(float(v))
    except ValueError:
        return 0


def read_workbook(path: Path) -> list[dict]:
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=False, read_only=True)
    if "Annotate" not in wb.sheetnames:
        raise ValueError(f"{path}: no 'Annotate' sheet")
    annotator = path.stem
    if "meta" in wb.sheetnames:
        for k, v in wb["meta"].iter_rows(values_only=True):
            if k == "annotator" and v:
                annotator = str(v)
    rows = list(wb["Annotate"].iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    out = []
    for vals in rows[1:]:
        r = dict(zip(header, vals))
        if not r.get("pair_uid"):
            continue
        errors = {c: _num(r.get(c)) for c in ERROR_COLS}
        bracket = normalise_bracket(r.get("bracket"))
        simp = r.get("simplicity")
        out.append({
            "pair_uid": str(r["pair_uid"]).strip(), "annotator": annotator, "bracket": bracket, **errors,
            "lmp": lmp_score(bracket, errors),
            "simplicity": int(str(simp).strip()[0]) if simp and str(simp).strip()[:1].isdigit() else None,
            "main_change": (str(r.get("main_change")).strip() if r.get("main_change") else None),
            "comment": r.get("comment"), "minutes": r.get("minutes"), "file": path.name,
        })
    return out


# --------------------------------------------------------------------------- agreement
def krippendorff_alpha(units: dict[str, list], metric: str = "interval") -> float:
    """Krippendorff's alpha with missing data. units: uid -> list of values (one per coder)."""
    data = [[v for v in vals if v is not None] for vals in units.values()]
    data = [vals for vals in data if len(vals) >= 2]
    if not data:
        return float("nan")
    delta = (lambda a, b: (a - b) ** 2) if metric == "interval" else (lambda a, b: float(a != b))
    n = sum(len(v) for v in data)
    d_o = 0.0
    for vals in data:
        m = len(vals)
        d_o += sum(delta(a, b) for i, a in enumerate(vals) for j, b in enumerate(vals) if i != j) / (m - 1)
    d_o /= n
    allv = [v for vals in data for v in vals]
    if metric == "interval":
        s1, s2 = sum(allv), sum(v * v for v in allv)
        d_e = 2 * (n * s2 - s1 * s1) / (n * (n - 1))
    else:
        c = Counter(allv)
        d_e = (n * n - sum(k * k for k in c.values())) / (n * (n - 1))
    return 1.0 - d_o / d_e if d_e > 0 else float("nan")


def human_ceiling(by_uid: dict[str, dict[str, float]]) -> tuple[float, dict]:
    """Leave-one-out: Pearson of each annotator with the mean of the other annotators of the same
    items. With many independent annotators its mean approximates a ceiling; with two annotators it is
    just their correlation and is not an upper bound on predicting their mean (it is reported as agreement)."""
    annotators = sorted({a for d in by_uid.values() for a in d})
    per = {}
    for a in annotators:
        xs, ys = [], []
        for d in by_uid.values():
            if a in d and len(d) >= 2:
                xs.append(d[a])
                ys.append(mean(v for b, v in d.items() if b != a))
        per[a] = (pearson(xs, ys), len(xs))
    vals = [r for r, n in per.values() if n >= 3 and r == r]
    return (mean(vals) if vals else float("nan")), per


def pairwise_pearson(by_uid) -> dict:
    annotators = sorted({a for d in by_uid.values() for a in d})
    out = {}
    for a, b in itertools.combinations(annotators, 2):
        xs = [(d[a], d[b]) for d in by_uid.values() if a in d and b in d]
        if len(xs) >= 3:
            out[(a, b)] = (pearson([x for x, _ in xs], [y for _, y in xs]), len(xs))
    return out


def fmt(x, nd=3):
    return "n/a" if x is None or x != x else f"{x:.{nd}f}"


# --------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--min-annotators", type=int, default=2, help="pairs with fewer complete ratings get no label")
    ap.add_argument("--adjudicate-range", type=float, default=4, help="flag pairs whose max-min score >= this")
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    folder = paths.pilot if args.pilot else paths.annotation
    suffix = "_pilot" if args.pilot else ""
    files = sorted(p for p in folder.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        sys.exit(f"no workbooks in {folder}")
    pairs = {p["pair_uid"]: p for p in read_jsonl(paths.pairs)}

    ann, incomplete = [], Counter()
    for f in files:
        rows = read_workbook(f)
        for r in rows:
            if r["lmp"] is None:
                incomplete[r["annotator"]] += 1
            else:
                ann.append(r)
        print(f"{f.name}: {len(rows)} rows, {sum(r['lmp'] is not None for r in rows)} complete")
    unknown = {r["pair_uid"] for r in ann} - set(pairs)
    if unknown:
        print(f"WARNING: {len(unknown)} pair_uids not in pairs.jsonl (e.g. {sorted(unknown)[:3]})")

    by_uid: dict[str, dict[str, float]] = defaultdict(dict)
    rows_by_uid = defaultdict(list)
    for r in ann:
        by_uid[r["pair_uid"]][r["annotator"]] = r["lmp"]
        rows_by_uid[r["pair_uid"]].append(r)

    alpha_lmp = krippendorff_alpha({u: list(d.values()) for u, d in by_uid.items()}, "interval")
    alpha_br = krippendorff_alpha({u: [r["bracket"] for r in rs] for u, rs in rows_by_uid.items()}, "nominal")
    ceiling, per_ceiling = human_ceiling(by_uid)
    pw = pairwise_pearson(by_uid)
    multi = [u for u, d in by_uid.items() if len(d) >= 2]
    annotators = sorted({r["annotator"] for r in ann})

    # ---- report
    L = [f"# Annotation agreement{' (pilot)' if args.pilot else ''}", "",
         f"Workbooks: {', '.join(f.name for f in files)}", "",
         f"- Complete ratings: {len(ann)}; incomplete rows: {dict(incomplete) or 0}",
         f"- Pairs with >= 2 ratings: {len(multi)} / {len(by_uid)}",
         f"- **Krippendorff's alpha (interval, LMP 1-10): {fmt(alpha_lmp)}** (JUDGEBERT/FrJUDGE reported 0.10)",
         f"- Krippendorff's alpha (nominal, bracket): {fmt(alpha_br)}",
         f"- **Inter-annotator agreement** (mean leave-one-out Pearson; with two annotators this is their "
         f"correlation, not an upper bound on predicting their mean): {fmt(ceiling)}", "",
         "## Annotators", "", "| annotator | n | mean LMP | std | LOO Pearson | % Accurate | % Off-track |",
         "|---|---|---|---|---|---|---|"]
    for a in annotators:
        rs = [r for r in ann if r["annotator"] == a]
        sc = [r["lmp"] for r in rs]
        acc = sum(r["bracket"] == "Accurate (7-10)" for r in rs) / len(rs)
        off = sum(r["bracket"] == "Off-track (1)" for r in rs) / len(rs)
        L.append(f"| {a} | {len(rs)} | {fmt(mean(sc), 2)} | {fmt(std(sc), 2)} | {fmt(per_ceiling[a][0])} "
                 f"| {acc:.0%} | {off:.0%} |")
    L += ["", "Large differences in mean LMP indicate lenient vs. strict annotators (as in FrJUDGE).", "",
          "## Pairwise Pearson", "", "| pair | r | n |", "|---|---|---|"]
    L += [f"| {a}-{b} | {fmt(r)} | {n} |" for (a, b), (r, n) in pw.items()]
    L += ["", "## Mean LMP by language and variant (from pairs.jsonl)", "", "| lang | variant | n pairs | mean | std |",
          "|---|---|---|---|---|"]
    groups = defaultdict(list)
    for u, d in by_uid.items():
        p = pairs.get(u)
        if p:
            groups[(p["lang"], p["variant"])].append(mean(d.values()))
            if p.get("error_type"):
                groups[(p["lang"], f"perturbed:{p['error_type']}")].append(mean(d.values()))
    for (lang, var), xs in sorted(groups.items()):
        L.append(f"| {lang} | {var} | {len(xs)} | {fmt(mean(xs), 2)} | {fmt(std(xs), 2)} |")

    # ---- adjudication list (no variant / error type: adjudicators stay blind)
    adj = []
    for u, rs in rows_by_uid.items():
        sc = [r["lmp"] for r in rs]
        brs = {r["bracket"] for r in rs}
        if len(sc) >= 2 and (max(sc) - min(sc) >= args.adjudicate_range or
                             {"Accurate (7-10)", "Off-track (1)"} <= brs):
            p = pairs.get(u, {})
            adj.append({"pair_uid": u, "original": p.get("original"), "simplification": p.get("simplification"),
                        "scores": "; ".join(f"{r['annotator']}={r['lmp']}" for r in rs),
                        "brackets": "; ".join(f"{r['annotator']}={r['bracket']}" for r in rs),
                        "comments": " | ".join(f"{r['annotator']}: {r['comment']}" for r in rs if r["comment"]),
                        "range": max(sc) - min(sc), "decision": "", "note": ""})
    adj.sort(key=lambda r: -r["range"])
    L += ["", f"## Adjudication", "", f"{len(adj)} pairs with score range >= {args.adjudicate_range} or "
          f"Accurate-vs-Off-track disagreement -> reports/adjudicate{suffix}.csv"]
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / f"agreement{suffix}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    write_csv(paths.reports / f"adjudicate{suffix}.csv", adj,
              ["pair_uid", "range", "scores", "brackets", "original", "simplification", "comments", "decision", "note"])
    print("\n".join(L[4:11]))
    print(f"wrote {paths.reports / ('agreement' + suffix + '.md')} and adjudicate{suffix}.csv ({len(adj)} rows)")

    if args.pilot:
        print("pilot: scores discarded (no labels written). Update the guidelines change log, then run the main round.")
        return

    # ---- labels
    write_jsonl(paths.annotations, ann)
    labeled, missing = [], 0
    for u, p in pairs.items():
        rs = rows_by_uid.get(u, [])
        if len(rs) < args.min_annotators:
            missing += 1
            continue
        sc = [r["lmp"] for r in rs]
        mc = Counter(r["main_change"] for r in rs if r["main_change"])
        top = mc.most_common()
        if top and (len(top) == 1 or top[0][1] > top[1][1]):
            main_change = top[0][0]
        elif top:
            main_change = "tie:" + "/".join(sorted(k for k, c in top if c == top[0][1]))
        else:
            main_change = None
        simp = [r["simplicity"] for r in rs if r["simplicity"] is not None]
        labeled.append(dict(p, label=round(mean(sc), 4), label_std=round(std(sc), 4),
                            scores={r["annotator"]: r["lmp"] for r in rs}, n_annotators=len(rs),
                            main_change=main_change, simplicity=round(mean(simp), 3) if simp else None,
                            **{f"mean_{c}": round(mean(r[c] for r in rs), 3) for c in ERROR_COLS}))
    write_jsonl(paths.labeled, labeled)
    print(f"wrote {paths.labeled}: {len(labeled)} labelled pairs ({missing} pairs with < {args.min_annotators} ratings)")


if __name__ == "__main__":
    main()
