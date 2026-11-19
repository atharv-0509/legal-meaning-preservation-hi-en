"""Modelling code on the synthetic pipeline output: baselines, LLM judge (fake server),
evaluate, error analysis, and — if torch + transformers are installed — train.py with a tiny
randomly initialised BERT built offline (checks the training loop, not model quality).

    python tests/test_modeling.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "modeling"), str(HERE)]

import baselines  # noqa: E402
import error_analysis  # noqa: E402
import evaluate  # noqa: E402
import llm_judge  # noqa: E402
import metrics  # noqa: E402
from common import data_paths, read_jsonl  # noqa: E402
from fixtures import start_fake_llm  # noqa: E402
from test_pipeline import run_pipeline  # noqa: E402


def test_metrics():
    m = metrics.regression_metrics([1, 5, 9, 10], [1.5, 5, 8, 10])
    assert abs(m["rmse"] - (1.25 / 4) ** 0.5) < 1e-9 and m["mae"] == 0.375 and m["over_rate"] == 0.25
    assert m["decision_acc"] == 1.0 and m["decision_macro_f1"] == 1.0
    assert metrics.sanity_metrics([10, 9.95, 8], "identical")["pass_rate"] == 2 / 3
    assert metrics.macro_f1(["Preserved", "Not Preserved"], ["Preserved", "Preserved"]) == (2 / 3 + 0) / 2
    assert llm_judge.parse_judgement('x {"bracket": "Imprecise (2-6)", "omissions": 2}')["score"] == 4
    assert llm_judge.parse_judgement("no json") is None


def make_tiny_model(path: Path, texts: list[str]):
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizer
    sys.path.insert(0, str(ROOT / "src"))
    from common import tokenize
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + sorted({t for x in texts for t in tokenize(x)})
    path.mkdir(parents=True, exist_ok=True)
    (path / "vocab.txt").write_text("\n".join(vocab), encoding="utf-8")
    tok = BertTokenizer(str(path / "vocab.txt"), do_lower_case=True, tokenize_chinese_chars=False, strip_accents=False)
    cfg = BertConfig(vocab_size=len(vocab), hidden_size=32, num_hidden_layers=1, num_attention_heads=2,
                     intermediate_size=64, max_position_embeddings=512, num_labels=1)
    BertForSequenceClassification(cfg).save_pretrained(path)
    tok.save_pretrained(path)


def test_modeling():
    tmp = Path(tempfile.mkdtemp(prefix="lmp_model_test_"))
    try:
        run_pipeline(tmp)
        paths = data_paths(tmp / "data")
        runs, reports = tmp / "runs", tmp / "reports_out"
        splits = [str(paths.splits / "*")]

        baselines.main(["--metrics", "rougeL", "bleu", "--splits", *splits, "--runs-dir", str(runs)])
        for sysname in ("rougeL", "rougeL-cal", "bleu", "bleu-cal"):
            assert (runs / sysname / "random_s42" / "preds_test.jsonl").exists()
            assert (runs / sysname / "random_s42" / "preds_holdout_identical.jsonl").exists()
        ident = read_jsonl(runs / "rougeL" / "random_s42" / "preds_holdout_identical.jsonl")
        assert all(r["pred"] == 10.0 for r in ident)               # ROUGE-L of identical text = 1 -> 10

        srv, url = start_fake_llm()
        os.environ.update(LLM_BASE_URL=url, LLM_API_KEY="test")
        cache = ROOT / "modeling" / "cache" / "llm_judge_fake-judge.jsonl"
        cache.unlink(missing_ok=True)
        try:
            llm_judge.main(["--model", "fake-judge", "--splits", *splits, "--runs-dir", str(runs)])
            n_cached = len(read_jsonl(cache))
            llm_judge.main(["--model", "fake-judge", "--splits", *splits, "--runs-dir", str(runs)])
            assert len(read_jsonl(cache)) == n_cached              # resumed from cache
        finally:
            cache.unlink(missing_ok=True)
            srv.shutdown()
        jp = read_jsonl(runs / "llm-judge_fake-judge" / "random_s42" / "preds_test.jsonl")
        assert jp and all(1 <= r["pred"] <= 10 and r.get("explanation") for r in jp)

        trained = False
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import train
            texts = [r[k] for f in paths.splits.rglob("*.jsonl") for r in read_jsonl(f) for k in ("original", "simplification")]
            make_tiny_model(tmp / "tiny", texts)
            train.main(["--split-dir", str(paths.splits / "random_s42"), "--model", str(tmp / "tiny"), "--da",
                        "--epochs", "3", "--patience", "2", "--run-name", "tiny-da", "--runs-dir", str(runs),
                        "--save-model", str(tmp / "tiny_trained")])
            train.main(["--split-dir", str(paths.splits / "random_s42"), "--model", str(tmp / "tiny"),
                        "--train-langs", "en", "--test-langs", "hi", "--epochs", "2", "--run-name", "tiny",
                        "--runs-dir", str(runs)])
            assert (runs / "tiny-da" / "random_s42" / "preds_holdout_unrelated.jsonl").exists()
            assert (runs / "tiny" / "random_s42__train-en_test-hi" / "preds_test.jsonl").exists()
            hi = read_jsonl(runs / "tiny" / "random_s42__train-en_test-hi" / "preds_test.jsonl")
            assert {r["lang"] for r in hi} == {"hi"}
            import predict
            res = predict.LMPScorer(str(tmp / "tiny_trained")).score(["a b"], ["a"])
            assert 1 <= res[0]["lmp_score"] <= 10 and res[0]["decision"]
            trained = True
        except ImportError:
            print("torch/transformers not installed: skipped train.py check")

        evaluate.main(["--runs-dir", str(runs), "--labeled", str(paths.labeled), "--out", str(reports / "results.md")])
        res = (reports / "results.md").read_text(encoding="utf-8")
        assert "E1" in res and "E3" in res and "Inter-annotator agreement" in res and "sanity" in res
        if trained:
            assert "E2" in res
        error_analysis.main(["--system", "rougeL-cal", "--runs-dir", str(runs), "--labeled", str(paths.labeled),
                             "--out-dir", str(reports), "--n", "15"])
        ea = (reports / "error_analysis_rougeL-cal.md").read_text(encoding="utf-8")
        assert ea.count("## Case") >= 15 and "injected" in ea and "[TBD" in ea
        print("modeling OK (train.py checked)" if trained else "modeling OK (train.py skipped)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_metrics()
    test_modeling()
    print("2/2 passed")
