import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import agent_review


def test_repairs_dropped_leading_one_and_duplicates():
    en = "notwithstanding the Official Secrets Act, 1923 (19 of 1923), and any other law"
    hi = "शासकीय गुप्त बात अधिनियम, 923 (923 का 9) और"
    fixed, note = agent_review.repair_numbers(en, hi)
    assert fixed is not None and "1923 (1923 का 19)" in fixed, note


def test_fills_empty_parentheses_only_for_ones():
    fixed, _ = agent_review.repair_numbers("under sub-section (1) within 5 days", "उपधारा () के अधीन 5 दिन")
    assert fixed == "उपधारा (1) के अधीन 5 दिन"
    bad, note = agent_review.repair_numbers("under sub-section (2) within 5 days", "उपधारा () के अधीन 5 दिन")
    assert bad is None, note                    # a vanished 2 is not an OCR "1" error: drop instead


def test_ambiguous_numbers_are_not_guessed():
    assert agent_review.repair_numbers("within 30 days or 40 days", "30 दिन या 70 दिन")[0] is None
