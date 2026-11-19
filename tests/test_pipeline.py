"""End-to-end test of every pipeline step on SYNTHETIC units, a fake LLM server and simulated
annotators, in a temporary data directory (nothing is written to data/).

    python tests/test_pipeline.py
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "src"), str(HERE)]

import agreement  # noqa: E402
import build_pairs  # noqa: E402
import perturb  # noqa: E402
import sanity  # noqa: E402
import select_clauses  # noqa: E402
import simplify  # noqa: E402
import split  # noqa: E402
from common import data_paths, read_csv, read_jsonl, units_path, write_csv, write_jsonl  # noqa: E402
from fixtures import _Handler, make_units, start_fake_llm, write_sources  # noqa: E402
from rubric import BRACKETS, ERROR_COLS  # noqa: E402


def simulate_annotators(paths, folder: Path, seed: int = 0) -> None:
    """Fill workbooks like a (noisy) human would. Only the simulation peeks at pairs.jsonl."""
    from openpyxl import load_workbook
    pairs = {p["pair_uid"]: p for p in read_jsonl(paths.pairs)}
    for f in sorted(folder.glob("*.xlsx")):
        rng = random.Random(f"{seed}|{f.stem}")
        strict = rng.random() < 0.5                               # lenient vs strict annotator
        wb = load_workbook(f)
        ws = wb["Annotate"]
        header = [c.value for c in ws[1]]
        col = {h: i + 1 for i, h in enumerate(header)}
        for r in range(2, ws.max_row + 1):
            p = pairs[ws.cell(r, col["pair_uid"]).value]
            if p["variant"] == "normal":
                bracket, n_err = BRACKETS[0], rng.choice([0, 0, 1])
            elif p["variant"] == "aggressive":
                bracket, n_err = rng.choice(BRACKETS[:2]), rng.choice([1, 2, 3])
            else:
                bracket, n_err = BRACKETS[1], rng.choice([1, 2])
            n_err += int(strict)
            ws.cell(r, col["bracket"], bracket)
            ws.cell(r, col[rng.choice(ERROR_COLS)], n_err)
            ws.cell(r, col["simplicity"], "4 - easier")
            ws.cell(r, col["main_change"], "none" if n_err == 0 else rng.choice(["omission", "scope", "number/amount"]))
            ws.cell(r, col["comment"], "simulated")
        wb.save(f)


def test_pipeline():
    tmp = Path(tempfile.mkdtemp(prefix="lmp_test_"))
    try:
        run_pipeline(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_pipeline(tmp: Path):
    data = tmp / "data"
    src = tmp / "sources.json"
    write_sources(src, data)
    paths = data_paths(data)
    common_args = ["--data-dir", str(data)]

    # ---- step 1 (stand-in): synthetic units in the extract.py schema
    for act in ("rti", "cpa"):
        for lang, units in make_units(act).items():
            write_jsonl(units_path(paths, act, lang), units)

    # ---- step 2: select + review + finalize
    select_clauses.main(["--per-act", "10", "--sources", str(src), *common_args])
    clauses = read_jsonl(paths.clauses)
    assert len(clauses) == 26, len(clauses)                     # ceil(10 * 1.3) per act
    assert all(c["section"] not in {"1", "2"} for c in clauses), "boilerplate selected"
    per_sec = Counter((c["act_id"], c["section"]) for c in clauses)
    assert max(per_sec.values()) <= 3
    assert all(15 <= c["n_words_en"] <= 90 and c["reading_ease_en"] <= 50 for c in clauses)
    review = read_csv(paths.review_csv)
    review[0]["keep"] = "0"
    review[1]["text_hi"] = review[1]["text_hi"] + " "            # whitespace-only edit is not an edit
    review[2]["text_en"] = review[2]["text_en"].replace("shall", "shall", 1)
    write_csv(paths.review_csv, review, select_clauses.REVIEW_FIELDS)
    select_clauses.main(["--finalize", "--per-act", "10", "--sources", str(src), *common_args])
    final = read_jsonl(paths.clauses_final)
    assert len(final) == 20 and review[0]["clause_id"] not in {c["clause_id"] for c in final}

    # ---- step 3: simplify against a fake OpenAI-compatible server (and resume)
    srv, url = start_fake_llm()
    os.environ.update(LLM_BASE_URL=url, LLM_API_KEY="test-key")
    simplify.main(["--model", "fake-model-1", "--limit", "5", *common_args])
    assert _Handler.calls == 5 * 2 * 2
    simplify.main(["--model", "fake-model-1", *common_args])
    assert _Handler.calls == 20 * 2 * 2, _Handler.calls          # resumed, nothing generated twice
    simplify.main(["--model", "fake-model-1", *common_args])
    assert _Handler.calls == 80
    srv.shutdown()
    sims = read_jsonl(paths.simplifications)
    assert len(sims) == 80 and len({s["sim_id"] for s in sims}) == 80
    assert all(s["model"] == "fake-model-1" and s["prompt_id"] and s["timestamp"] for s in sims)
    assert not any(s["simplification"].startswith(("Simple:", "सरल:", "Explanation:")) for s in sims)

    # ---- step 4: perturbations (one per normal simplification, balanced types)
    perturb.main(common_args)
    pert = read_jsonl(paths.perturbations)
    assert len(pert) >= 35, len(pert)
    for p in pert:
        assert p["error_type"] in perturb.ERROR_TYPES and p["simplification"] != p["original"]
        base = next(s for s in sims if s["sim_id"] == p["base_sim_id"])
        assert p["simplification"] != base["simplification"]
    counts = Counter(p["error_type"] for p in pert)
    assert len(counts) >= 4 and max(counts.values()) - min(counts.values()) <= 6, counts

    # ---- step 5: DA + holdouts
    sanity.main(["--holdout-n", "8", "--sources", str(src), *common_args])
    aug = read_jsonl(paths.augment)
    ident = [a for a in aug if a["variant"] == "da_identical"]
    unrel = [a for a in aug if a["variant"] == "da_unrelated"]
    assert len(ident) == 40 and len(unrel) >= 20, (len(ident), len(unrel))
    assert all(a["label"] == 1.0 for a in unrel) and all(a["label"] == 10.0 for a in ident)
    hold = read_jsonl(paths.holdout_identical) + read_jsonl(paths.holdout_unrelated)
    final_texts = {c[f"text_{l}"] for c in final for l in ("en", "hi")}
    assert hold and not ({h["original"] for h in hold} & final_texts)
    da_partners = {a["simplification"] for a in unrel}
    assert not ({h["original"] for h in hold} | {h["simplification"] for h in hold}) & da_partners

    # ---- step 6: pairs + blinded workbooks
    build_pairs.main(["--annotators", "A", "B", "C", "--per-pair", "2", "--pilot", "6", *common_args])
    pairs = read_jsonl(paths.pairs)
    assert len(pairs) == 80 + len(pert)
    from openpyxl import load_workbook
    secret = {p["variant"] for p in pairs} | {p["error_type"] for p in pairs if p["error_type"]} | {"fake-model-1"}
    for f in list(paths.annotation.glob("*.xlsx")) + list(paths.pilot.glob("*.xlsx")):
        wb = load_workbook(f)
        ws = wb["Annotate"]
        header = [c.value for c in ws[1]]
        assert "variant" not in header and "error_type" not in header and "pair_id" not in header
        cells = {str(c.value) for row in ws.iter_rows() for c in row if c.value is not None}
        assert not (cells & secret), f"{f.name} leaks {cells & secret}"
        uids = [ws.cell(r, header.index("pair_uid") + 1).value for r in range(2, ws.max_row + 1)]
        clause_of = {p["pair_uid"]: p["clause_id"] for p in pairs}
        adjacent = sum(clause_of[a] == clause_of[b] for a, b in zip(uids, uids[1:]))
        assert adjacent <= 2, f"{f.name}: {adjacent} adjacent same-clause rows"
    assign = read_jsonl(paths.assignment)
    per = Counter(a["pair_uid"] for a in assign if a["round"] == "main")
    assert set(per.values()) == {2} and len(per) == len(pairs)
    assert Counter(a["annotator"] for a in assign if a["round"] == "pilot") == {"A": 6, "B": 6, "C": 6}
    try:
        build_pairs.main(["--annotators", "A", "B", "C", *common_args])
        raise AssertionError("workbooks overwritten without --force")
    except SystemExit:
        pass

    # ---- step 7: simulated annotation, pilot + main agreement
    simulate_annotators(paths, paths.pilot, seed=1)
    agreement.main(["--pilot", *common_args])
    assert (paths.reports / "agreement_pilot.md").exists() and not paths.labeled.exists()
    simulate_annotators(paths, paths.annotation, seed=2)
    agreement.main(common_args)
    labeled = read_jsonl(paths.labeled)
    assert len(labeled) == len(pairs)
    assert all(1 <= r["label"] <= 10 and r["n_annotators"] == 2 for r in labeled)
    by_var = defaultdict(list)
    for r in labeled:
        by_var[r["variant"]].append(r["label"])
    assert min(by_var["normal"]) > max(by_var["perturbed"]) - 3   # simulation sanity
    report = (paths.reports / "agreement.md").read_text(encoding="utf-8")
    assert "Krippendorff" in report and "Inter-annotator agreement" in report
    anns = read_jsonl(paths.annotations)
    assert all(a["lmp"] == max(1, {"Accurate (7-10)": 10, "Imprecise (2-6)": 6, "Off-track (1)": 1}[a["bracket"]]
                                - sum(a[c] for c in ERROR_COLS)) for a in anns)

    # ---- step 8: splits
    split.main(["--seeds", "42", "43", *common_args])
    for name in ("random_s42", "random_s43", "ood_rti_to_cpa", "ood_cpa_to_rti"):
        d = paths.splits / name
        parts = {n: read_jsonl(d / f"{n}.jsonl") for n in ("train", "dev", "test", "train_da", "dev_da")}
        split.check_disjoint(parts, hold)
        assert all(r["variant"] in ("normal", "aggressive", "perturbed") for r in parts["test"])
        assert len(parts["train_da"]) > len(parts["train"])
        cl = {n: {r["clause_id"] for r in parts[n]} for n in ("train", "dev", "test")}
        for r in parts["train"] + parts["test"]:                  # both languages of a clause together
            assert r["clause_id"] in cl["train"] | cl["test"]
        if name.startswith("ood"):
            a, b = name[4:].split("_to_")
            assert {r["act_id"] for r in parts["train"]} == {a} and {r["act_id"] for r in parts["test"]} == {b}
    s42 = read_jsonl(paths.splits / "random_s42" / "test.jsonl")
    s43 = read_jsonl(paths.splits / "random_s43" / "test.jsonl")
    assert {r["clause_id"] for r in s42} != {r["clause_id"] for r in s43}
    # check_disjoint must catch a leak
    leaky = {"train": parts["train"], "test": parts["test"] + parts["train"][:1]}
    try:
        split.check_disjoint(leaky)
        raise AssertionError("check_disjoint missed a leak")
    except AssertionError as e:
        assert "leak" in str(e)
    print("pipeline OK:", {"clauses": len(final), "pairs": len(pairs), "perturbed": dict(counts),
                           "DA": len(aug), "holdout": len(hold)})


if __name__ == "__main__":
    test_pipeline()
    print("1/1 passed")
