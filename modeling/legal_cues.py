"""Rule-based legal cues for an original/simplification pair (English or Hindi).

Used by the demo app (cue table) and as the rule baseline of the legal-error classifier (`rule_error_type`).
These are surface heuristics: they see negation words, modal verbs, exception/override markers,
quantifiers and numbers, and they miss paraphrases. They are an explanation aid, not the LMP model.

Error types follow src/perturb.py: modality, negation, number, exception_drop, scope (+ "none").
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import devanagari_ratio, find_markers, numbers_in  # noqa: E402

ERROR_CLASSES = ["none", "modality", "negation", "number", "exception_drop", "scope"]

EXPLANATIONS = {
    "none": "No change of an obligation, negation, number, exception or scope was detected.",
    "modality": "The obligation/permission differs: e.g. 'shall' (a duty) became 'may' (a discretion), or the reverse.",
    "negation": "A negation was added or removed, which can reverse what the provision says.",
    "number": "A number differs (a time limit, amount or count may have changed).",
    "exception_drop": "An exception, proviso or override in the original is missing from the simplification.",
    "scope": "A quantifier differs ('all/every/any' vs 'some/certain'), so the provision's scope may have changed.",
}

CUES = [  # (marker category, label shown to the user)
    ("prohibition", "Prohibition (shall not / नहीं …)"),
    ("obligation", "Obligation (shall / must / करेगा)"),
    ("permission", "Permission (may / सकेगा)"),
    ("exception", "Exception / proviso"),
    ("override", "Override (notwithstanding / subject to)"),
    ("condition", "Condition (if / where / यदि)"),
    ("time_limit", "Time limit"),
]
NEG = {"en": re.compile(r"\b(not|no|never|cannot|can't|won't|neither|nor)\b", re.I),
       "hi": re.compile(r"(?<![ऀ-ॿ])(नहीं|न|मत)(?![ऀ-ॿ])")}
# English modality in plain-language simplifications: "will"/"has to" usually carry the obligation of "shall",
# and "may" inside drafting idioms ("as it may specify", "may be prescribed") is not a permission.
EN_OBLIG = re.compile(r"\b(shall|must|will|has to|have to|is required to|are required to|needs? to)\b(?!\s+not)", re.I)
EN_PERM = re.compile(r"\b(may|can|is allowed to|are allowed to|is entitled to|are entitled to)\b(?!\s+not)", re.I)
EN_PERM_IDIOM = re.compile(r"\b(as|which|that)\s+(\w+\s+){0,3}may\b|\bmay\s+be\s+(prescribed|specified|notified|"
                           r"determined|necessary|required)|\bcase\s+may\s+be\b", re.I)
SCOPE_WIDE = {"en": re.compile(r"\b(all|every|each|any|anyone|everyone|anybody|everybody|always|whole|entire|only)\b", re.I),
              "hi": re.compile(r"(?<![ऀ-ॿ])(सभी|सब|प्रत्येक|हर|किसी भी|कोई भी|सदैव|हमेशा|संपूर्ण|पूरी|केवल)(?![ऀ-ॿ])")}
SCOPE_NARROW = {"en": re.compile(r"\b(some|certain|particular|part of)\b", re.I),
                "hi": re.compile(r"(?<![ऀ-ॿ])(कुछ|विशेष|आंशिक|कभी-कभी)(?![ऀ-ॿ])")}


def lang_of(text: str) -> str:
    return "hi" if devanagari_ratio(text) > 0.3 else "en"


def en_modality(text: str) -> set[str]:
    out = set()
    if EN_OBLIG.search(text):
        out.add("obligation")
    if EN_PERM.search(EN_PERM_IDIOM.sub(" ", text)):
        out.add("permission")
    return out


def markers(text: str, lang: str) -> set[str]:
    m = set(find_markers(text, lang))
    if lang == "en":                           # replace the generic English modality markers
        m -= {"obligation", "permission"}
        m |= en_modality(text)
    return m


def compare(original: str, simplification: str) -> dict:
    """All cue differences between the two texts (inputs to the table and to rule_error_type)."""
    lo, ls = lang_of(original), lang_of(simplification)
    mo, ms = markers(original, lo), markers(simplification, ls)
    numo, nums = numbers_in(original), numbers_in(simplification)
    return {
        "lang": (lo, ls), "markers": (mo, ms),
        "neg": (len(NEG[lo].findall(original)), len(NEG[ls].findall(simplification))),
        "numbers": (numo, nums),
        "scope_wide": (len(SCOPE_WIDE[lo].findall(original)), len(SCOPE_WIDE[ls].findall(simplification))),
        "scope_narrow": (len(SCOPE_NARROW[lo].findall(original)), len(SCOPE_NARROW[ls].findall(simplification))),
    }


def rule_error_type(original: str, simplification: str) -> tuple[str, str]:
    """(error type, explanation) from simple rules, checked in a fixed priority order."""
    c = compare(original, simplification)
    (mo, ms), (no, ns) = c["markers"], c["neg"]
    numo, nums = c["numbers"]
    if no != ns:
        return "negation", EXPLANATIONS["negation"] + f" (negation words: original {no}, simplification {ns})"
    if set(numo) != set(nums) and set(nums) - set(numo):
        new = ", ".join(sorted(set(nums) - set(numo)))
        return "number", EXPLANATIONS["number"] + f" (new in simplification: {new})"
    if ("obligation" in mo) != ("obligation" in ms) or ("permission" in ms and "permission" not in mo):
        return "modality", EXPLANATIONS["modality"]
    if ({"exception", "override"} & mo) and not ({"exception", "override"} & ms):
        return "exception_drop", EXPLANATIONS["exception_drop"]
    (wo, ws), (nao, nas) = c["scope_wide"], c["scope_narrow"]
    if ws < wo or nas > nao:
        return "scope", EXPLANATIONS["scope"]
    return "none", EXPLANATIONS["none"]


def cue_rows(original: str, simplification: str) -> list[tuple[str, str, str, str]]:
    """Rows (cue, original, simplification, note) for the app's table; note is empty when consistent."""
    c = compare(original, simplification)
    (mo, ms), (no, ns) = c["markers"], c["neg"]
    rows = []
    if no != ns:
        rows.append(("Negation words", f"{no}", f"{ns}", "Negation count differs: meaning may be reversed"))
    for cat, label in CUES:
        a, b = cat in mo, cat in ms
        if a or b:
            note = ("Present in original, missing in simplification" if a and not b
                    else "Added in simplification" if b and not a else "")
            rows.append((label, "yes" if a else "—", "yes" if b else "—", note))
    numo, nums = c["numbers"]
    if numo or nums:
        lost, new = sorted(set(numo) - set(nums)), sorted(set(nums) - set(numo))
        note = "; ".join(x for x in (f"missing: {', '.join(lost)}" if lost else "",
                                     f"new: {', '.join(new)}" if new else "") if x)
        rows.append(("Numbers", ", ".join(numo) or "—", ", ".join(nums) or "—", note))
    return rows
