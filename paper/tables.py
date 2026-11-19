"""Resolve the paper's tables from files produced by our own code.

Contract with the results pipeline (P1). Every results table is read from

    reports/tables/<key>.tsv

a tab-separated file whose first row is the header. If the file is absent, the table renders with
its expected header and a single `[TBD]` row, so the paper always builds and never shows a number
that no file backs. `missing()` lists what is still unresolved, and the builders print it.

Keys and the headers the pipeline should emit:

    e1    System | Pearson | Spearman | RMSE | MAE | Over-score %
    e2    Setting | Pearson | RMSE | Over-score %          (per-language rows + EN->HI, HI->EN)
    e3    Split | Pearson | RMSE | MAE                     (rti->cpa, cpa->rti)
    e4    System | Identical >= 9.9 % | Unrelated <= 1.1 %
    diag  Injected error type | n | MAE LMP model | MAE best baseline | MAE LLM judge
    dataset  Act | Lang | Clauses | Pairs | Mean words | Mean label

`dataset.tsv` must be written by the data track, NOT read here from `pairs.jsonl`: this builder is
run by the agent that also serves as a blinded annotator, so it must never touch the pair-level
answer key. Aggregates in a TSV are safe; opening `pairs.jsonl` here would not be.

The `sources` table is dataset provenance, not a result: it is built from `sources.json` and, when
the extraction outputs are reachable, the real unit counts in `data/interim/`.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

#: Where to look for `data/` and `reports/`. A git worktree does not carry the git-ignored `data/`
#: directory, so fall back to the sibling main checkout, and let the environment override both.
DATA_ROOTS = [
    Path(os.environ["LMP_DATA_ROOT"]) if os.environ.get("LMP_DATA_ROOT") else None,
    REPO,
    REPO.parent / "legal-meaning-preservation-hi-en",
]

EXPECTED_HEADERS = {
    "e1": ["System", "Pearson", "Spearman", "RMSE", "MAE", "Over-score %"],
    "e2": ["System", "Setting", "Pearson", "RMSE", "Over-score %"],
    "e3": ["System", "Split", "Pearson", "RMSE", "MAE"],
    "e4": ["System", "Identical >= 9.9 %", "Unrelated <= 1.1 %"],
    "diag": ["Injected error type", "n per test split", "MAE LMP model", "MAE baseline"],
    "dataset": ["Act", "Lang", "Clauses", "Pairs", "Mean words", "Mean label"],
    "variant": ["Variant", "n per test split", "Mean label", "MAE", "Mean signed error", "Within-variant Pearson"],
}

_missing: list[str] = []


def _find(relative: str) -> Path | None:
    for root in DATA_ROOTS:
        if root and (root / relative).exists():
            return root / relative
    return None


def _read_tsv(key: str) -> list[list[str]] | None:
    path = _find(f"reports/tables/{key}.tsv")
    if path is None:
        return None
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = [row for row in csv.reader(fh, delimiter="\t") if any(cell.strip() for cell in row)]
    # A header with no body rows means the pipeline wrote the file but produced no results for it
    # (this happened to e2.tsv). Rendering that as an empty table would look like a measured
    # result of nothing, so treat it as missing and let the caller show [TBD] instead.
    if len(rows) < 2:
        return None
    return rows


def _tbd(key: str) -> list[list[str]]:
    header = EXPECTED_HEADERS[key]
    _missing.append(f"reports/tables/{key}.tsv")
    return [header, ["[TBD]"] + ["[TBD]"] * (len(header) - 1)]


def _count_units(act: str, lang: str) -> tuple[str, str]:
    """(sections, units) from the real extraction output, or ('[TBD]', '[TBD]')."""
    path = _find(f"data/interim/{act}_{lang}_units.jsonl")
    if path is None:
        return "[TBD]", "[TBD]"
    units = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return str(len({u["section"] for u in units})), str(len(units))


def _sources_table() -> list[list[str]]:
    """Provenance of the four source documents. Editions come from `sources.json`."""
    path = _find("sources.json")
    notes = {}
    if path is not None:
        for act in json.loads(path.read_text(encoding="utf-8"))["acts"]:
            notes[act["act_id"]] = act.get("version_note", "")
    else:
        _missing.append("sources.json")

    rows = [["Document", "Edition", "Sections", "Units"]]
    labels = {
        ("rti", "en"): ("RTI Act 2005, English (DoPT)", "As on 18 Nov 2025; includes the 2023 amendment"),
        ("rti", "hi"): ("RTI Act 2005, Hindi (DoPT)", "Carries the 2019 amendments; sec. 8(1) is the "
                                                      "older wording; text layer unusable, read by "
                                                      "OCR (Tesseract 5.4, tessdata_best hin)"),
        ("cpa", "en"): ("Consumer Protection Act 2019, English (Gazette)", "Act 35 of 2019, 9 Aug 2019; "
                                                                          "original enactment"),
    }
    for (act, lang), (label, edition) in labels.items():
        sections, units = _count_units(act, lang)
        rows.append([label, edition, sections, units])
    rows.append(["Consumer Protection Act 2019, Hindi", "Not obtainable; India Code unreachable", "--", "--"])
    if notes:
        pass  # version notes are quoted in the prose; the table keeps the short form
    return rows


def get(key: str) -> list[list[str]]:
    """Header row followed by body rows, always non-empty."""
    if key == "sources":
        return _sources_table()
    return _read_tsv(key) or _tbd(key)


def missing() -> list[str]:
    """Files the build wanted and did not find, in encounter order, de-duplicated."""
    seen, out = set(), []
    for item in _missing:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
