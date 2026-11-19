"""Legal-error type classification: rule baseline on SYNTHETIC strings, and the trained classifier +
evaluation end to end on the synthetic pipeline output with a tiny offline BERT (skipped without torch).

    python tests/test_error_classifier.py     (or: pytest tests/)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "modeling"), str(HERE)]

from legal_cues import ERROR_CLASSES, rule_error_type  # noqa: E402

ORIG_EN = "The officer shall decide the request within 30 days, unless the information is exempt."


def test_rules_english():
    assert rule_error_type(ORIG_EN, "The officer will decide the request within 30 days, unless the information "
                                    "is exempt.")[0] == "none"
    assert rule_error_type(ORIG_EN, "The officer will not decide the request within 30 days, unless the "
                                    "information is exempt.")[0] == "negation"
    assert rule_error_type(ORIG_EN, "The officer will decide the request within 60 days, unless the information "
                                    "is exempt.")[0] == "number"
    assert rule_error_type(ORIG_EN, "The officer may decide the request within 30 days, unless the information "
                                    "is exempt.")[0] == "modality"
    assert rule_error_type(ORIG_EN, "The officer will decide the request within 30 days.")[0] == "exception_drop"
    assert rule_error_type("Every citizen shall have the right to information.",
                           "Some citizens will have the right to information.")[0] == "scope"
    t, why = rule_error_type(ORIG_EN, "The officer will not decide the request within 30 days, unless exempt.")
    assert t == "negation" and "reverse" in why


def test_rules_hindi():
    orig = "अधिकारी तीस दिन के भीतर सूचना देगा।"
    assert rule_error_type(orig, "अधिकारी तीस दिन के भीतर सूचना नहीं देगा।")[0] == "negation"
    assert rule_error_type("प्रत्येक नागरिक को सूचना का अधिकार होगा।", "कुछ नागरिक को सूचना का अधिकार होगा।")[0] == "scope"
    assert rule_error_type("अधिकारी 30 दिन के भीतर सूचना देगा।", "अधिकारी 60 दिन के भीतर सूचना देगा।")[0] == "number"


def test_classifier_end_to_end():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        print("torch/transformers not installed: skipped classifier training check")
        return
    import error_classifier
    import error_eval
    from common import data_paths, read_jsonl
    from test_modeling import make_tiny_model
    from test_pipeline import run_pipeline
    tmp = Path(tempfile.mkdtemp(prefix="lmp_errcls_test_"))
    try:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            run_pipeline(tmp)
        paths = data_paths(tmp / "data")
        texts = [r[k] for f in paths.splits.rglob("*.jsonl") for r in read_jsonl(f) for k in ("original", "simplification")]
        make_tiny_model(tmp / "tiny", texts)
        runs = tmp / "runs_err"
        for seed in (42, 43):
            error_classifier.main(["--split-dir", str(paths.splits / f"random_s{seed}"), "--model", str(tmp / "tiny"),
                                   "--epochs", "2", "--seed", str(seed), "--runs-dir", str(runs),
                                   "--da", "--clip-min", "0"])          # unknown regression flags are tolerated
        preds = read_jsonl(runs / "errcls-tiny" / "random_s42" / "errcls_preds_test.jsonl")
        assert preds and all(p["pred"] in ERROR_CLASSES and p["gold"] in ERROR_CLASSES for p in preds)
        assert all(p["variant"] in ("normal", "perturbed") for p in preds)
        assert abs(sum(preds[0]["probs"].values()) - 1) < 1e-3
        m = json.loads((runs / "errcls-tiny" / "random_s42" / "errcls_metrics.json").read_text())
        assert 0 <= m["test"]["macro_f1"] <= 1 and "confusion" in m["test"]
        out = tmp / "report.md"
        error_eval.main(["--splits", str(paths.splits), "--runs-err", str(runs), "--out", str(out),
                         "--tables", str(tmp / "tables")])
        text = out.read_text(encoding="utf-8")
        assert "errcls-tiny" in text and "rules" in text and "majority (none)" in text
        assert (tmp / "tables" / "errcls.tsv").exists()
        print("error classifier OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_rules_english()
    test_rules_hindi()
    test_classifier_end_to_end()
    print("3/3 passed")
