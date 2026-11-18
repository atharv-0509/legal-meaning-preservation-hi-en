"""Generic semantic-similarity baselines (E1), scored on every split's test set and the holdouts.

    python modeling/baselines.py --metrics rougeL bleu labse bertscore --splits data/splits/random_s* data/splits/ood_*

  rougeL, bleu   our Devanagari-aware tokeniser (src/common.py); no extra dependencies
  labse          cosine similarity of sentence-transformers/LaBSE embeddings
  bertscore      BERTScore F1 (simplification vs. original), multilingual model (default xlm-roberta-large)

Normalisation to the 1-10 LMP scale (needed for RMSE/MAE; Pearson/Spearman are unaffected):
  <metric>         naive: clip the raw score to [0, 1] and map linearly to [1, 10]
  <metric>-cal     calibrated: least-squares line label ~ score fitted on that split's human TRAIN pairs
Raw scores are cached in modeling/cache/ so each pair is scored once across splits.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmp_data import ROOT, holdout_files, load_split, run_dir, write_json, write_preds  # noqa: E402
from metrics import evaluate_rows, sanity_metrics  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from common import bleu, read_jsonl, rouge_l, short_hash  # noqa: E402

CACHE = ROOT / "modeling" / "cache"


def _key(r):
    return short_hash(r["original"] + "␞" + r["simplification"], 16)


class Scorer:
    """Batch scorer with an on-disk cache. score(rows) -> list of raw scores in [~0, 1]."""

    def __init__(self, name: str, args):
        self.name, self.args = name, args
        self.cache_path = CACHE / f"{name}{'_' + Path(args.bertscore_model).name if name == 'bertscore' else ''}.jsonl"
        self.cache = {r["k"]: r["s"] for r in read_jsonl(self.cache_path)}
        self._model = None

    def _compute(self, rows):
        o = [r["original"] for r in rows]
        s = [r["simplification"] for r in rows]
        if self.name == "rougeL":
            return [rouge_l(a, b) for a, b in zip(o, s)]
        if self.name == "bleu":
            return [bleu(a, b) / 100 for a, b in zip(o, s)]
        if self.name == "labse":
            from sentence_transformers import SentenceTransformer
            self._model = self._model or SentenceTransformer("sentence-transformers/LaBSE")
            ea = self._model.encode(o, normalize_embeddings=True, batch_size=32)
            eb = self._model.encode(s, normalize_embeddings=True, batch_size=32)
            return [float((x * y).sum()) for x, y in zip(ea, eb)]
        if self.name == "bertscore":
            from bert_score import score
            _, _, f1 = score(s, o, model_type=self.args.bertscore_model, batch_size=16, verbose=False)
            return f1.tolist()
        raise ValueError(self.name)

    def score(self, rows):
        todo = [r for r in rows if _key(r) not in self.cache]
        uniq = list({_key(r): r for r in todo}.values())
        if uniq:
            vals = self._compute(uniq)
            CACHE.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "a", encoding="utf-8") as f:
                for r, v in zip(uniq, vals):
                    self.cache[_key(r)] = float(v)
                    f.write(json.dumps({"k": _key(r), "s": float(v)}) + "\n")
        return [self.cache[_key(r)] for r in rows]


def naive(x: float) -> float:
    return 1.0 + 9.0 * min(1.0, max(0.0, x))


def fit_line(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx if vx else 0.0
    return my - b * mx, b


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrics", nargs="+", default=["rougeL", "bleu"], choices=["rougeL", "bleu", "labse", "bertscore"])
    ap.add_argument("--splits", nargs="+", default=None, help="split dirs (default: all in data/splits)")
    ap.add_argument("--test-langs", nargs="+", default=None)
    ap.add_argument("--bertscore-model", default="xlm-roberta-large")
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args(argv)
    split_dirs = [Path(p) for s in (args.splits or [str(ROOT / "data" / "splits" / "*")]) for p in glob.glob(s)]
    split_dirs = sorted(d for d in split_dirs if d.is_dir() and (d / "test.jsonl").exists())
    if not split_dirs:
        sys.exit("no split dirs found — run src/split.py first")
    runs = Path(args.runs_dir) if args.runs_dir else None

    for metric in args.metrics:
        sc = Scorer(metric, args)
        for d in split_dirs:
            train, test = load_split(d, "train"), load_split(d, "test", args.test_langs)
            raw_train, raw_test = sc.score(train), sc.score(test)
            a, b = fit_line(raw_train, [r["label"] for r in train])
            holds = {n: read_jsonl(p) for n, p in holdout_files(d).items()}
            if args.test_langs:
                holds = {n: [r for r in rows if r["lang"] in args.test_langs] for n, rows in holds.items()}
            raw_holds = {n: sc.score(rows) for n, rows in holds.items() if rows}
            split_name = d.name + (f"__test-{'+'.join(args.test_langs)}" if args.test_langs else "")
            for system, f in ((metric, naive), (f"{metric}-cal", lambda x: a + b * x)):
                out = run_dir(system, split_name, runs)
                preds = [f(x) for x in raw_test]
                write_preds(out / "preds_test.jsonl", test, preds)
                m = {"test": evaluate_rows([dict(r, pred=min(10, max(1, p))) for r, p in zip(test, preds)])}
                for n, xs in raw_holds.items():
                    hp = [f(x) for x in xs]
                    write_preds(out / f"preds_{n}.jsonl", holds[n], hp)
                    m[n] = sanity_metrics([min(10, max(1, p)) for p in hp], n.split("_")[1])
                write_json(out / "metrics.json", m)
                write_json(out / "config.json", {"system": system, "metric": metric, "split": d.name,
                                                 "calibration": {"a": a, "b": b} if system.endswith("-cal") else "naive [0,1]->[1,10]"})
            print(f"{metric:10s} {d.name:22s} pearson={m['test']['overall']['pearson']:.3f}")


if __name__ == "__main__":
    main()
