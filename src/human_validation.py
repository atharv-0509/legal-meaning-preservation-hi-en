"""Compare the human validation scores with the LLM labels (and the trained model).

    python src/human_validation.py      # reads data/annotation/human/*.xlsx -> reports/human_validation.md

Reports: agreement among the humans (Krippendorff's alpha, interval), Pearson/Spearman between the
mean human score and the mean LLM label on the same pairs, each LLM annotator vs the humans, and the
transfer model's test predictions vs the humans where those pairs fall in a test split.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agreement import krippendorff_alpha, read_workbook  # noqa: E402
from common import data_paths, pearson, read_jsonl, spearman  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--human-dir", default=None, help="default: data/annotation/human")
    ap.add_argument("--out", default=str(ROOT / "reports" / "human_validation.md"))
    args = ap.parse_args(argv)
    paths = data_paths(None)
    files = sorted(Path(args.human_dir or paths.data / "annotation" / "human").glob("*.xlsx"))
    human = defaultdict(dict)                      # uid -> annotator -> score
    for f in files:
        for r in read_workbook(f):
            if r["lmp"] is not None:
                human[r["pair_uid"]][r["annotator"]] = r["lmp"]
    names = sorted({a for d in human.values() for a in d})
    if not human:
        sys.exit("no filled human workbooks in data/annotation/human/")
    labeled = {p["pair_uid"]: p for p in read_jsonl(paths.processed / "labeled_pairs.jsonl")}
    llm = defaultdict(dict)
    for f in sorted((paths.data / "annotation").glob("llm_*.xlsx")):
        for r in read_workbook(f):
            if r["lmp"] is not None:
                llm[r["pair_uid"]][r["annotator"]] = r["lmp"]

    uids = [u for u in human if u in labeled]
    hm = [mean(human[u].values()) for u in uids]
    lab = [labeled[u]["label"] for u in uids]
    L = ["# Human validation of the LLM labels", "",
         f"Annotators: {', '.join(names)}; pairs scored: {len(uids)} "
         f"(complete ratings: {sum(len(d) for d in human.values())}).", ""]
    if len(names) > 1:
        a = krippendorff_alpha({u: list(human[u].values()) for u in uids}, "interval")
        L.append(f"- **Human–human agreement:** Krippendorff's α (interval) = {a:.3f}")
    L.append(f"- **Mean human score vs LLM label (mean of 2 LLM annotators):** Pearson {pearson(hm, lab):.3f}, "
             f"Spearman {spearman(hm, lab):.3f}")
    for name in sorted({a for d in llm.values() for a in d}):
        xs = [(mean(human[u].values()), llm[u][name]) for u in uids if name in llm.get(u, {})]
        if len(xs) > 2:
            L.append(f"- Human mean vs `{name}`: Pearson {pearson(*zip(*xs)):.3f} (n={len(xs)})")
    for n in names:
        xs = [(human[u][n], labeled[u]["label"]) for u in uids if n in human[u]]
        if len(xs) > 2:
            L.append(f"- `{n}` vs LLM label: Pearson {pearson(*zip(*xs)):.3f} (n={len(xs)})")
    by = defaultdict(list)
    for u, h in zip(uids, hm):
        by[labeled[u]["lang"]].append((h, labeled[u]["label"]))
    for lang, xs in sorted(by.items()):
        if len(xs) > 2:
            L.append(f"- {lang.upper()} pairs: human vs LLM Pearson {pearson(*zip(*xs)):.3f} (n={len(xs)})")
    # transfer model predictions on these pairs, where they are in a random test split
    uid_of = {p["pair_id"]: u for u, p in labeled.items()}
    preds = defaultdict(list)
    for f in (ROOT / "modeling" / "runs" / "xlm-roberta-base-frjudge").glob("random_s*/preds_test.jsonl"):
        for r in read_jsonl(f):
            uid = uid_of.get(r["pair_id"])
            if uid in human:
                preds[uid].append(r["pred"])
    xs = [(mean(human[u].values()), mean(v)) for u, v in preds.items()]
    if len(xs) > 2:
        L.append(f"- Transfer model (test predictions) vs human mean: Pearson {pearson(*zip(*xs)):.3f} (n={len(xs)})")
    L += ["", "Interpretation: Pearson between the human mean and the LLM label is the key number — it says how far "
          "the LLM-produced labels used for training and evaluation track human legal judgement."]
    out = Path(args.out)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
