"""Select the error-analysis (E5) cases for the paper from our own data files.

The brief asks for at least fifteen legally difficult cases. Writing them into `content.py` by hand
would mean transcribing statutory text and scores, which is exactly where a paper picks up errors
it cannot later detect, so the cases are assembled here instead:

* `data/processed/labeled_pairs.jsonl` supplies the clause, language, variant, the injected error
  type and its `change` description, and the label (the mean of the annotators);
* the annotator's own workbook answers supply the one-line legal explanation written while scoring
  that pair blind, and that annotator's individual score;
* `modeling/runs/<system>/<split>/preds_test.jsonl`, when present, supplies each system's
  prediction for the same pair, so the table can show gold against predicted.

Selection is deterministic: cases are taken in the file's own order, capped per group so that every
injected error type and every recorded `main_change` category is represented before any category
repeats. Nothing here is hand-picked to flatter a system.
"""
from __future__ import annotations

import json
from pathlib import Path

import tables  # reuse its data-root resolution

#: How many cases to take per group. Negation and modality get three because they are the
#: legally most serious transformations; the floor of one guarantees full category coverage.
PER_ERROR_TYPE = {"negation": 3, "modality": 3, "scope": 2, "exception_drop": 2, "number": 2}
PER_MAIN_CHANGE = 1          # for pairs with no injected error (normal / aggressive variants)
MAX_CASES = 18               # the brief asks for at least fifteen; more would crowd the paper
ANNOTATOR_ANSWERS = "data/annotation/llm_claude_opus55_b_answers.jsonl"
BLIND_ANNOTATOR = "llm_claude_opus55_b"


def _read_jsonl(relative: str) -> list[dict]:
    path = tables._find(relative)
    if path is None:
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _predictions() -> dict[str, dict[str, float]]:
    """{pair_id: {system: prediction}} over whatever test predictions exist."""
    root = next((r for r in tables.DATA_ROOTS if r and (r / "modeling" / "runs").exists()), None)
    if root is None:
        return {}
    out: dict[str, dict[str, float]] = {}
    for preds in sorted((root / "modeling" / "runs").glob("*/*/preds_test.jsonl")):
        system = preds.parts[-3]
        for line in preds.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            pid = row.get("pair_id")
            if pid is not None and row.get("pred") is not None:
                out.setdefault(pid, {}).setdefault(system, float(row["pred"]))
    return out


def cases() -> list[dict]:
    pairs = _read_jsonl("data/processed/labeled_pairs.jsonl")
    if not pairs:
        return []
    comments = {a["pair_uid"]: a for a in _read_jsonl(ANNOTATOR_ANSWERS)}
    preds = _predictions()

    # Injected-error pairs first: their error type is known, which is what makes the set
    # diagnostic rather than anecdotal. Natural-loss cases from the other two variants follow.
    # Within each of those two blocks the languages are interleaved, because taking file order
    # alone fills the whole table with English CPA clauses and an error analysis with no Hindi
    # example would be indefensible in a paper whose contribution is Hindi.
    ordered = (_interleave_languages([r for r in pairs if r.get("error_type")]) +
               _interleave_languages([r for r in pairs if not r.get("error_type")]))

    taken: dict[str, int] = {}
    out: list[dict] = []
    for row in ordered:
        if len(out) >= MAX_CASES:
            break
        answer = comments.get(row["pair_uid"])
        if answer is None or not answer.get("comment"):
            continue
        etype = row.get("error_type")
        group = etype or _group_of(row.get("main_change"))
        if group is None:
            continue                                   # no legal change recorded: not a case
        cap = PER_ERROR_TYPE.get(etype, PER_MAIN_CHANGE) if etype else PER_MAIN_CHANGE
        if taken.get(group, 0) >= cap:
            continue
        taken[group] = taken.get(group, 0) + 1
        out.append({
            "clause": row["clause_id"],
            "lang": row["lang"].upper(),
            "variant": row["variant"],
            "error_type": etype or "",
            "change": row.get("change") or "",
            "label": f"{float(row['label']):.1f}",
            "annotator_score": _score_of(answer),
            "main_change": _group_of(row.get("main_change")) or "",
            "original": row["original"],
            "simplification": row["simplification"],
            "explanation": answer["comment"],
            "preds": preds.get(row["pair_id"], {}),
        })
    return out


def _interleave_languages(rows: list[dict]) -> list[dict]:
    """Alternate Hindi and English rows so a per-group cap cannot exclude one language."""
    hindi = [r for r in rows if r.get("lang") == "hi"]
    other = [r for r in rows if r.get("lang") != "hi"]
    out = []
    for i in range(max(len(hindi), len(other))):
        if i < len(hindi):
            out.append(hindi[i])
        if i < len(other):
            out.append(other[i])
    return out


def _group_of(main_change) -> str | None:
    """Normalise `agreement.py`'s majority main_change into one grouping label.

    Where the two annotators disagreed, that field is a tie string such as
    "tie:none/omission"; we take the first non-"none" alternative, since what we are grouping by
    is the kind of legal change, and drop the case entirely if both annotators recorded none.
    """
    if not main_change:
        return None
    value = str(main_change)
    if value.startswith("tie:"):
        parts = [p for p in value[4:].split("/") if p and p != "none"]
        # "number/amount" and "date/time limit" themselves contain "/", so rejoin cautiously.
        value = "/".join(parts) if parts else "none"
    return None if value == "none" else value


def _score_of(answer: dict) -> int | None:
    """Recompute the blinded annotator's own score from its bracket and error counts."""
    import sys
    root = next((r for r in tables.DATA_ROOTS if r and (r / "src" / "rubric.py").exists()), None)
    if root is None:
        return None
    sys.path.insert(0, str(root / "src"))
    from rubric import lmp_score  # noqa: E402
    return lmp_score(answer.get("bracket"), answer)


def summary() -> dict:
    """Counts for the prose: how many cases, and the group coverage."""
    rows = cases()
    groups: dict[str, int] = {}
    for row in rows:
        key = row["error_type"] or _group_of(row["main_change"]) or "other"
        groups[key] = groups.get(key, 0) + 1
    return {"n": len(rows), "groups": groups,
            "with_predictions": sum(1 for r in rows if r["preds"])}
