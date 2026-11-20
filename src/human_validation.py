"""Compare the human validation scores with the LLM labels and the trained models.

    python src/human_validation.py      # reads data/annotation/human/*.xlsx

Writes reports/human_validation.md, reports/human_validation.json and reports/tables/human.tsv, which the
paper and slides read. With no filled workbook it writes {"status": "pending"} and exits 0, so the paper
build can always call it; the paper then says that human validation has not been scored.

Reports: agreement among the humans (Krippendorff's alpha, interval); Pearson / Spearman / MAE between the
mean human score and the LLM label (the mean of the two LLM annotators) on the same pairs, and the mean
LLM - human difference (bias); each LLM
annotator vs the humans; the legal expert (workbook `legal_expert`) separately from the three authors; the
breakdown by language and variant; and the test predictions of the principal system and of MuRIL vs the
humans, on the pairs that fall in a random test split (mean over the seeds in which they do), next to the
same models vs the LLM label on those same pairs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agreement import krippendorff_alpha, read_workbook  # noqa: E402
from common import data_paths, pearson, read_jsonl, spearman  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXPERT = "legal_expert"
MODELS = [("XLM-R principal system", "xlm-roberta-base-frjudge-da"),      # FrJUDGE -> ours, with DA
          ("MuRIL", "muril-base-cased-frjudge-5s-da")]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def compare(pairs: list[tuple[float, float]]) -> dict:
    """Pearson / Spearman / MAE / mean(a - b) for a list of (a, b) pairs."""
    if len(pairs) < 3:
        return {"n": len(pairs)}
    a, b = zip(*pairs)
    return {"n": len(pairs), "pearson": pearson(list(a), list(b)), "spearman": spearman(list(a), list(b)),
            "mae": sum(abs(x - y) for x, y in pairs) / len(pairs), "bias": sum(x - y for x, y in pairs) / len(pairs)}


def fmt(v, d=3):
    return "n/a" if v is None or v != v else f"{v:.{d}f}"


def write_pending(args, n_files: int) -> None:
    Path(args.json).write_text(json.dumps({"status": "pending", "workbooks": n_files}, indent=1) + "\n",
                               encoding="utf-8")
    Path(args.out).write_text("# Human validation\n\nNo human scores yet: the workbooks in "
                              "`data/annotation/human/` are empty.\n", encoding="utf-8")
    table = Path(args.tables) / "human.tsv"
    if table.exists():
        table.unlink()
    print(f"no filled human workbooks ({n_files} found, all empty): wrote status 'pending' to {args.json}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--human-dir", default=None, help="default: data/annotation/human")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--runs", default=str(ROOT / "modeling" / "runs"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "human_validation.md"))
    ap.add_argument("--json", default=str(ROOT / "reports" / "human_validation.json"))
    ap.add_argument("--tables", default=str(ROOT / "reports" / "tables"))
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    files = sorted(Path(args.human_dir or paths.data / "annotation" / "human").glob("*.xlsx"))
    human = defaultdict(dict)                      # uid -> annotator -> score
    for f in files:
        for r in read_workbook(f):
            if r["lmp"] is not None:
                human[r["pair_uid"]][r["annotator"]] = r["lmp"]
    labeled = {p["pair_uid"]: p for p in read_jsonl(paths.processed / "labeled_pairs.jsonl")}
    uids = [u for u in human if u in labeled]
    if not uids:
        write_pending(args, len(files))
        return
    names = sorted({a for u in uids for a in human[u]})
    team = [n for n in names if n != EXPERT]
    llm = defaultdict(dict)
    for f in sorted((paths.data / "annotation").glob("llm_*.xlsx")):
        for r in read_workbook(f):
            if r["lmp"] is not None:
                llm[r["pair_uid"]][r["annotator"]] = r["lmp"]

    hmean = {u: mean(human[u].values()) for u in uids}
    rows = []                                      # (name, stats) for the table
    res = {"status": "scored", "annotators": names, "n_pairs": len(uids),
           "n_ratings": sum(len(human[u]) for u in uids)}
    if len(names) > 1:
        res["alpha_humans"] = krippendorff_alpha({u: list(human[u].values()) for u in uids}, "interval")
    if len(team) > 1:
        res["alpha_team"] = krippendorff_alpha({u: [human[u][n] for n in team if n in human[u]] for u in uids},
                                               "interval")
    # LLM labels vs humans: (LLM, human) so that bias = LLM - human
    rows.append(("LLM label vs humans", compare([(labeled[u]["label"], hmean[u]) for u in uids])))
    for name in sorted({a for d in llm.values() for a in d}):
        rows.append((f"LLM annotator {name.rsplit('_', 1)[-1].upper()} vs humans",
                     compare([(llm[u][name], hmean[u]) for u in uids if name in llm.get(u, {})])))
    if EXPERT in names and team:
        both = [u for u in uids if EXPERT in human[u] and any(n in human[u] for n in team)]
        rows.append(("Authors vs legal expert",
                     compare([(mean(human[u][n] for n in team if n in human[u]), human[u][EXPERT]) for u in both])))
        rows.append(("LLM label vs legal expert", compare([(labeled[u]["label"], human[u][EXPERT]) for u in both])))
    for n in names:
        res.setdefault("per_annotator", {})[n] = compare([(labeled[u]["label"], human[u][n]) for u in uids if n in human[u]])
    # trained models on the pairs that are in a random test split
    uid_of = {p["pair_id"]: u for u, p in labeled.items()}
    for label, system in MODELS:
        preds = defaultdict(list)
        for f in (Path(args.runs) / system).glob("random_s*/preds_test.jsonl"):
            for r in read_jsonl(f):
                u = uid_of.get(r["pair_id"])
                if u in hmean:
                    preds[u].append(r["pred"])
        on = [u for u in preds]
        rows.append((f"{label} vs humans", compare([(mean(preds[u]), hmean[u]) for u in on])))
        rows.append((f"{label} vs LLM label (same pairs)", compare([(mean(preds[u]), labeled[u]["label"]) for u in on])))
    res["comparisons"] = [{"name": n, **s} for n, s in rows]
    by_lang, by_var = defaultdict(list), defaultdict(list)
    for u in uids:
        by_lang[labeled[u]["lang"]].append((labeled[u]["label"], hmean[u]))
        by_var[labeled[u]["variant"]].append((labeled[u]["label"], hmean[u]))
    res["by_lang"] = {k: compare(v) for k, v in sorted(by_lang.items())}
    res["by_variant"] = {k: {"n": len(v), "llm_mean": mean(x for x, _ in v), "human_mean": mean(y for _, y in v)}
                         for k, v in sorted(by_var.items())}

    Path(args.json).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tsv = ["Comparison\tn\tPearson\tSpearman\tMAE\tBias (1st − 2nd)"]
    for n, s in rows:
        tsv.append("\t".join([n, str(s["n"]), fmt(s.get("pearson")), fmt(s.get("spearman")), fmt(s.get("mae"), 2),
                              f"{s['bias']:+.2f}" if "bias" in s else "n/a"]))
    Path(args.tables).mkdir(parents=True, exist_ok=True)
    (Path(args.tables) / "human.tsv").write_text("\n".join(tsv) + "\n", encoding="utf-8")

    L = ["# Human validation of the LLM labels", "",
         f"Annotators: {', '.join(names)}; pairs scored: {len(uids)} (ratings: {res['n_ratings']}).", ""]
    if "alpha_humans" in res:
        L.append(f"- **Human–human agreement:** Krippendorff's α (interval) = {res['alpha_humans']:.3f}"
                 + (f" (three authors only: {res['alpha_team']:.3f})" if "alpha_team" in res else ""))
    L += ["", "| Comparison | n | Pearson | Spearman | MAE | Bias (1st − 2nd) |", "|---|---|---|---|---|---|"]
    L += ["| " + " | ".join(line.split("\t")) + " |" for line in tsv[1:]]
    L += ["", "By language (LLM label vs human mean): " + "; ".join(
        f"{k.upper()} Pearson {fmt(v.get('pearson'))} (n={v['n']})" for k, v in res["by_lang"].items()),
          "", "By variant (mean score, LLM label / humans): " + "; ".join(
        f"{k} {fmt(v['llm_mean'], 2)} / {fmt(v['human_mean'], 2)} (n={v['n']})" for k, v in res["by_variant"].items()),
          "", "Bias > 0 means the first score is higher (more lenient) than the second. Model rows use only the pairs "
          "that fall in a random test split (mean prediction over those seeds), so their n is smaller."]
    Path(args.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
