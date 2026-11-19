import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modeling"))
import make_tables as mt


def _t(p):
    return {"overall": {"pearson": p, "spearman": p, "rmse": 1.5, "mae": 1.2, "over_rate": 0.4},
            "by_lang": {"en": {"pearson": p, "rmse": 1.4, "over_rate": 0.3},
                        "hi": {"pearson": p - 0.1, "rmse": 1.7, "over_rate": 0.5}},
            "by_error_type": {"modality": {"n": 5, "mae": 2.0}, "negation": {"n": 4, "mae": 1.0}}}


def _jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _setup(tmp_path, monkeypatch, fams):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "results.json").write_text(json.dumps({"families": fams}))
    for s in (42, 43, 44):                      # synthetic splits for the variant-lookup diagnostic
        rows = [{"variant": v, "label": l} for v, l in (("normal", 10), ("aggressive", 7), ("perturbed", 4))] * 3
        _jsonl(tmp_path / "data" / "splits" / f"random_s{s}" / "train.jsonl", rows)
        _jsonl(tmp_path / "data" / "splits" / f"random_s{s}" / "test.jsonl", rows)
        _jsonl(tmp_path / "modeling" / "runs" / mt.PRINCIPAL / f"random_s{s}" / "preds_test.jsonl",
               [dict(r, pred=r["label"] - 0.5) for r in rows])
        _jsonl(tmp_path / "modeling" / "runs" / mt.PRINCIPAL / f"random_s{s}" / "preds_holdout_identical.jsonl",
               [{"lang": "en", "pred": 9.95}, {"lang": "hi", "pred": 8.0}])
    _jsonl(tmp_path / "data" / "splits" / "holdout_identical.jsonl", [{"lang": "en"}, {"lang": "hi"}])
    _jsonl(tmp_path / "data" / "splits" / "holdout_unrelated.jsonl", [{"lang": "en"}])
    for k, v in {"ROOT": tmp_path, "OUT": tmp_path / "reports" / "tables", "RUNS": tmp_path / "modeling" / "runs",
                 "SPLITS": tmp_path / "data" / "splits"}.items():
        monkeypatch.setattr(mt, k, v)


def _fams():
    sysd = lambda p: {mt.PRINCIPAL: {"test": [_t(p), _t(p - 0.1)]}, mt.SCRATCH: {"test": [_t(0.2), _t(0.3)]}}
    fams = {"random": dict(sysd(0.6), **{mt.BASELINE: {"test": [_t(0.1), _t(0.12)]}}),
            "bilingual": sysd(0.5), "bilingual__train-en_test-hi": sysd(0.1), "bilingual__train-hi_test-en": sysd(0.1),
            "ood_cpa_to_rti": sysd(0.4), "ood_rti_to_cpa": sysd(0.3)}
    return fams


def _read(tmp_path, key):
    return list(csv.reader((tmp_path / "reports" / "tables" / f"{key}.tsv").open(encoding="utf-8"), delimiter="\t"))


def test_tables_use_declared_systems_and_report_counts(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, _fams())
    mt.main()
    e1 = _read(tmp_path, "e1")
    assert e1[1][0] == mt.name(mt.PRINCIPAL)                     # declared order, not sorted by score
    assert e1[-1][0].startswith("Variant-mean lookup")            # privileged diagnostic is labelled
    e2 = _read(tmp_path, "e2")
    assert any("zero-shot" in r[1] for r in e2) and {r[0] for r in e2[1:]} == {mt.name(mt.PRINCIPAL), mt.name(mt.SCRATCH)}
    assert {r[1] for r in _read(tmp_path, "e3")[1:]} == {"CPA → RTI", "RTI → CPA"}
    e4 = _read(tmp_path, "e4")
    assert "HI (n=0)" in e4[0][4]                                 # Hindi unrelated holdouts: none
    principal = next(r for r in e4 if r[0] == mt.name(mt.PRINCIPAL))
    assert principal[1].startswith("100.0") and principal[2].startswith("0.0") and principal[4] == "not evaluated"
    assert [r[0] for r in _read(tmp_path, "variant")[1:]] == ["normal", "aggressive", "perturbed"]


def test_missing_declared_run_is_an_error(tmp_path, monkeypatch):
    fams = _fams()
    del fams["ood_rti_to_cpa"][mt.SCRATCH]
    _setup(tmp_path, monkeypatch, fams)
    with pytest.raises(SystemExit, match="missing results"):
        mt.main()
