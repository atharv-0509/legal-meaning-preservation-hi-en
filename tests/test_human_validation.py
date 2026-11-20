"""Human validation report (src/human_validation.py) on the SYNTHETIC pipeline output: "pending" with empty
workbooks, "scored" with filled ones, and the files the paper and slides read.

    python tests/test_human_validation.py     (or: pytest tests/)
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "src"), str(HERE)]

import human_validation  # noqa: E402


def test_human_validation_pending_and_scored():
    from common import data_paths
    from test_pipeline import run_pipeline
    tmp = Path(tempfile.mkdtemp(prefix="lmp_human_test_"))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            run_pipeline(tmp)
        paths = data_paths(tmp / "data")
        out = {"--out": tmp / "hv.md", "--json": tmp / "hv.json", "--tables": tmp / "tables"}
        args = ["--data-dir", str(tmp / "data"), "--runs", str(tmp / "no_runs")] + \
               [x for k, v in out.items() for x in (k, str(v))]
        empty = tmp / "empty"
        empty.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            human_validation.main(args + ["--human-dir", str(empty)])
        assert json.loads((tmp / "hv.json").read_text())["status"] == "pending"
        assert not (tmp / "tables" / "human.tsv").exists()

        # the simulated, filled annotator workbooks stand in for human sheets
        human = tmp / "human"
        human.mkdir()
        for f in sorted((paths.data / "annotation").glob("*.xlsx"))[:3]:
            shutil.copy(f, human / f.name)
        with contextlib.redirect_stdout(io.StringIO()):
            human_validation.main(args + ["--human-dir", str(human)])
        res = json.loads((tmp / "hv.json").read_text())
        assert res["status"] == "scored" and res["n_pairs"] > 0 and len(res["annotators"]) == 3
        row = next(c for c in res["comparisons"] if c["name"] == "LLM label vs humans")
        assert -1 <= row["pearson"] <= 1 and row["mae"] >= 0
        assert "alpha_humans" in res
        tsv = (tmp / "tables" / "human.tsv").read_text(encoding="utf-8").splitlines()
        assert tsv[0].startswith("Comparison\tn\tPearson") and any(r.startswith("LLM label vs humans\t") for r in tsv)
        print("human validation OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_human_validation_pending_and_scored()
