import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modeling"))
import make_tables


def _t(p, extra=None):
    t = {"overall": {"pearson": p, "spearman": p, "rmse": 1.5, "mae": 1.2, "over_rate": 0.4},
         "by_lang": {"en": {"pearson": p, "rmse": 1.4, "over_rate": 0.3}, "hi": {"pearson": p - 0.1, "rmse": 1.7, "over_rate": 0.5}},
         "by_error_type": {"modality": {"n": 5, "mae": 2.0}, "negation": {"n": 4, "mae": 1.0}}}
    return t


def test_tables_from_synthetic_results(tmp_path, monkeypatch):
    (tmp_path / "reports").mkdir()
    fams = {
        "random": {"xlm-roberta-base-da": {"test": [_t(0.7), _t(0.6)], "holdout_identical": [{"pass_rate": 1.0}],
                                           "holdout_unrelated": [{"pass_rate": 0.9}]},
                   "labse-cal": {"test": [_t(0.3), _t(0.35)]}},
        "random__train-en_test-hi": {"xlm-roberta-base-da": {"test": [_t(0.5)]}},
        "ood_rti_to_cpa": {"xlm-roberta-base-da": {"test": [_t(0.4)]}},
    }
    (tmp_path / "reports" / "results.json").write_text(json.dumps({"human_ceiling": None, "families": fams}))
    monkeypatch.setattr(make_tables, "ROOT", tmp_path)
    monkeypatch.setattr(make_tables, "OUT", tmp_path / "reports" / "tables")
    make_tables.main()
    read = lambda n: list(csv.reader((tmp_path / "reports" / "tables" / f"{n}.tsv").open(encoding="utf-8"), delimiter="\t"))
    e1 = read("e1")
    assert e1[0] == ["System", "Pearson", "Spearman", "RMSE", "MAE", "Over-score %"]
    assert e1[1][0] == "xlm-roberta-base-da" and e1[1][1].startswith("0.650")
    assert any("zero-shot" in r[0] for r in read("e2"))
    assert read("e3")[1][0] == "RTI → CPA"
    assert read("e4")[1][1:] == ["100.0", "90.0"]
    diag = read("diag")
    assert diag[1][0] == "modality" and "labse-cal" in diag[1][3]
