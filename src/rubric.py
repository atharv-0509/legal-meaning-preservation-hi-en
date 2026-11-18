"""The LMP rubric, in one place. build_pairs.py (workbook formulas), agreement.py (score
recomputation) and modeling/llm_judge.py all import from here, so they cannot drift apart.
Any change here must also go in the change log of guidelines/annotation_guidelines.md.

JUDGEBERT rubric (reused unchanged):
  1. pick a bracket: Accurate 7-10, Imprecise 2-6, Off-track 1
  2. subtract 1 per error from the bracket maximum, never below 1
  3. error types: omission, hallucination, consistency issue, confusion
"""
from __future__ import annotations

BRACKETS = ["Accurate (7-10)", "Imprecise (2-6)", "Off-track (1)"]
BRACKET_MAX = {"Accurate (7-10)": 10, "Imprecise (2-6)": 6, "Off-track (1)": 1}
ERROR_COLS = ["omissions", "hallucinations", "inconsistencies", "confusions"]
SCORE_MIN, SCORE_MAX = 1, 10
SIMPLICITY = ["1 - harder than original", "2 - as hard", "3 - a bit easier", "4 - easier", "5 - much easier"]

# What changed most, legally (for E5). Annotators pick one.
MAIN_CHANGES = [
    "none", "omission", "hallucination", "contradiction", "obligation/permission", "negation",
    "condition", "exception", "scope", "date/time limit", "number/amount", "entity/actor",
    "terminology", "other",
]

DECISIONS = [(7.0, "Preserved"), (2.0, "Partially Preserved"), (float("-inf"), "Not Preserved")]


def normalise_bracket(value) -> str | None:
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v:
        return None
    if v.startswith("acc"):
        return BRACKETS[0]
    if v.startswith("imp"):
        return BRACKETS[1]
    if v.startswith("off"):
        return BRACKETS[2]
    return None


def lmp_score(bracket: str | None, errors: dict) -> int | None:
    """Score from a bracket and error counts: bracket max minus total errors, floored at 1."""
    b = normalise_bracket(bracket)
    if b is None:
        return None
    total = sum(int(errors.get(c) or 0) for c in ERROR_COLS)
    return max(SCORE_MIN, BRACKET_MAX[b] - total)


def decision(score: float) -> str:
    """Map a (continuous) LMP score to the brief's three decisions using the paper's brackets:
    >= 7 Preserved, >= 2 Partially Preserved, otherwise Not Preserved."""
    for threshold, name in DECISIONS:
        if score >= threshold:
            return name
    return DECISIONS[-1][1]
