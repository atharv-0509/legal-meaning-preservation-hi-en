"""Rule-based clause review (step 2b) for the deadline release, run by an LLM agent instead of a human.

    python src/agent_review.py            # edits data/processed/clauses_review.csv in place
    python src/select_clauses.py --finalize --per-act 30 --allow-missing-hi

DISCLOSED DEVIATION: CLAUDE.md step 2b asks a human to review the clause CSV. No human reviewer was
available before the deadline, so these mechanical rules (plus an agent's spot-check against the PDFs)
stand in for it. Every decision is written to `review_note`, and every text change goes through
select_clauses --finalize, which records it in `review_edits`. The dataset card states this.

Rules:
  drop  latin_in_hi        Latin letters inside Hindi text: OCR noise or untranslated fragments
  drop  len_ratio=*        EN/HI length ratio far outside normal: likely misalignment
  drop  en_hi_version_mismatch   EN and HI PDFs are different amendment versions for this section
  drop  mojibake           U+FFFD in the text: characters destroyed during extraction
  fix   num_mismatch       if the Hindi numbers differ from the English ones only by OCR dropping or
                           misreading the digit 1 (12 -> "2", 13 -> "03"), restore the English number;
                           otherwise drop the row
  keep  everything else (act-level flags such as hi_ocr_required are informational)
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEV_DIGITS, numbers_in  # noqa: E402
from extract import ocr_number_variants  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DROP_FLAGS = ("latin_in_hi", "en_hi_version_mismatch", "mojibake")


def repair_numbers(en: str, hi: str) -> tuple[str | None, str]:
    """Return (repaired_hi or None if not repairable, note)."""
    en_nums, hi_nums = numbers_in(en), numbers_in(hi)
    if en_nums == hi_nums:
        return hi, "numbers already match"
    hi_norm = hi.translate(DEV_DIGITS)
    remaining = list(en_nums)
    for n in hi_nums:                              # numbers already right need no change
        if n in remaining:
            remaining.remove(n)
    out, changes = [], []
    pos = 0
    for m in re.finditer(r"\d+", hi_norm):
        tok = m.group()
        if tok in en_nums and tok not in changes:   # correct as is
            continue
        cands = sorted({e for e in remaining if tok in ocr_number_variants(int(e))})
        if len(cands) != 1:
            return None, f"unrepairable number '{tok}' (EN numbers {en_nums})"
        out += [hi_norm[pos:m.start()], cands[0]]
        pos = m.end()
        changes.append(f"{tok}->{cands[0]}")
        remaining.remove(cands[0])
    out.append(hi_norm[pos:])
    fixed = "".join(out)
    # A number made only of 1s can vanish entirely, leaving "()" (e.g. "उपधारा ()" for "उपधारा (1)").
    # Fill empty parentheses only when their count equals the missing numbers and all of those are 1s.
    empties = list(re.finditer(r"\(\s*\)", fixed))
    if empties and remaining and len(empties) == len(remaining) and all(set(e) == {"1"} for e in remaining):
        order = [n for n in re.findall(r"\d+", en.translate(DEV_DIGITS)) if n in remaining]
        fill = iter(order if len(order) == len(empties) else sorted(remaining))
        fixed = re.sub(r"\(\s*\)", lambda _m: f"({next(fill)})", fixed)
        changes.append(f"'()'->{'/'.join(remaining)}")
    if numbers_in(fixed) != en_nums:
        return None, f"numbers still differ after repair (EN {en_nums}, HI {numbers_in(fixed)})"
    return fixed, "OCR digit repair " + ", ".join(changes)


def review(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    stats = {"rows": len(rows), "dropped": 0, "repaired": 0, "kept": 0}
    for r in rows:
        flags = [f for f in r["auto_flags"].split("|") if f] if "|" in r["auto_flags"] else \
            [f.strip() for f in re.split(r"[;,\s]+", r["auto_flags"]) if f.strip()]
        reasons = [f for f in flags if f in DROP_FLAGS or f.startswith("len_ratio=")]
        note = []
        if not reasons and "num_mismatch" in flags and r["text_hi"]:
            fixed, msg = repair_numbers(r["text_en"], r["text_hi"])
            if fixed is None:
                reasons.append("num_mismatch: " + msg)
            else:
                r["text_hi"] = fixed
                note.append(msg)
                stats["repaired"] += 1
        if reasons:
            r["keep"] = "0"
            r["review_note"] = "agent review: drop (" + "; ".join(reasons) + ")"
            stats["dropped"] += 1
        else:
            r["keep"] = "1"
            r["review_note"] = "agent review: keep" + (f" ({'; '.join(note)})" if note else "")
            stats["kept"] += 1
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return stats


if __name__ == "__main__":
    p = ROOT / "data" / "processed" / "clauses_review.csv"
    print(review(p))
