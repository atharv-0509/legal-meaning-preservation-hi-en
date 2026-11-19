"""Step 2: align EN/HI units, filter, sample clauses; step 2b: finalize after human review.

    python src/select_clauses.py --per-act 30            # -> clauses.jsonl + clauses_review.csv
    # humans edit clauses_review.csv (keep=0 for misaligned / garbled / fragmentary rows;
    # small OCR typo fixes in text_en / text_hi are allowed and recorded)
    python src/select_clauses.py --finalize --per-act 30 # -> clauses_final.jsonl

Selection (CLAUDE.md §4): 1-5 sentences, 15-90 English words, Flesch reading ease <= 50, no
boilerplate sections, <= 3 clauses per section, weighted toward exceptions, overrides,
conditions and time limits; oversample x1.3 so the review drop still leaves --per-act clauses.
"""
from __future__ import annotations

import argparse
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (count_sentences, count_words, data_paths, devanagari_ratio, find_markers,  # noqa: E402
                    load_sources, numbers_in, one_line, read_csv, read_jsonl, split_sentences, units_path,
                    write_csv, write_jsonl)

BOILERPLATE_EN = re.compile(
    r"short title|definitions?|interpretation|power(?:s)? (?:of .{0,40})?to make (?:rules|regulations)|"
    r"rule-making|regulations? making|repeal|savings?\b|removal of difficult|power to remove difficult|"
    r"laying of rules|commencement|extent|amendment of", re.I)
BOILERPLATE_HI = re.compile(r"संक्षिप्त नाम|परिभाषाएं|परिभाषाएँ|परिभाषा|नियम बनाने|विनियम बनाने|निरसन|व्यावृत्ति|"
                            r"कठिनाइयों को दूर|प्रारंभ|विस्तार")

WEIGHTS = {"exception": 1.0, "override": 0.75, "condition": 0.5, "time_limit": 0.75}
REVIEW_FIELDS = ["keep", "clause_id", "act_id", "section", "subsection", "heading_en", "text_en", "text_hi",
                 "n_words_en", "n_words_hi", "n_sents_en", "reading_ease_en", "markers_en", "markers_hi",
                 "auto_flags", "review_note"]


# --------------------------------------------------------------------------- readability
def count_syllables(word: str) -> int:
    """Heuristic English syllable counter (no cmudict / network needed)."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(groups))


def reading_ease(text: str) -> float:
    """Flesch reading ease: 206.835 - 1.015 (words/sentences) - 84.6 (syllables/words)."""
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    if not words:
        return 0.0
    n_sents = max(1, len(split_sentences(text)))
    syll = sum(count_syllables(w) for w in words)
    return round(206.835 - 1.015 * (len(words) / n_sents) - 84.6 * (syll / len(words)), 1)


# --------------------------------------------------------------------------- flags / weights
def auto_flags(en: str, hi: str, en_words: int, hi_words: int) -> list[str]:
    flags = []
    if not hi:
        return ["no_hi"]
    if re.search(r"[A-Za-z]{2,}", hi):
        flags.append("latin_in_hi")
    if numbers_in(en) != numbers_in(hi):
        flags.append("num_mismatch")
    ratio = hi_words / max(1, en_words)
    if not 0.7 <= ratio <= 2.2:
        flags.append(f"len_ratio={ratio:.2f}")
    if devanagari_ratio(hi) < 0.8:
        flags.append("low_devanagari")
    from extract import bad_matra_ratio  # local import keeps module import light
    if bad_matra_ratio(hi) > 0.03:
        flags.append("bad_matra")
    if re.search(r"[:;,]\s*$|\b(?:and|or)\s*$", en.strip()):
        flags.append("ends_mid_list")
    return flags


def clause_weight(markers: list[str]) -> float:
    return 1.0 + sum(WEIGHTS.get(m, 0.0) for m in markers)


def is_boilerplate(heading_en: str, heading_hi: str, section: str) -> bool:
    return bool(BOILERPLATE_EN.search(heading_en or "")) or bool(BOILERPLATE_HI.search(heading_hi or "")) \
        or section in {"1"}


# --------------------------------------------------------------------------- candidates
def candidates_for_act(act: dict, paths, args) -> tuple[list[dict], dict]:
    en = {u["key"]: u for u in read_jsonl(units_path(paths, act["act_id"], "en"))}
    hi = {u["key"]: u for u in read_jsonl(units_path(paths, act["act_id"], "hi"))}
    stats = {"en_units": len(en), "hi_units": len(hi), "aligned": 0, "boilerplate": 0,
             "length": 0, "sentences": 0, "readability": 0, "duplicate": 0, "candidates": 0}
    seen_texts: set = set()
    if not en:
        print(f"[{act['act_id']}] no English units — run extract.py first")
        return [], stats
    missing_hi = sorted(set(en) - set(hi))
    if missing_hi:
        print(f"[{act['act_id']}] {len(missing_hi)} EN units without HI match, e.g. {missing_hi[:8]}")
    out = []
    for key, ue in en.items():
        uh = hi.get(key)
        if uh is None and not args.allow_missing_hi:
            continue
        stats["aligned"] += 1
        if is_boilerplate(ue["heading"], uh["heading"] if uh else "", ue["section"]):
            stats["boilerplate"] += 1
            continue
        n_words = count_words(ue["text"])
        if not args.min_words <= n_words <= args.max_words:
            stats["length"] += 1
            continue
        n_sents = count_sentences(ue["text"])
        if not 1 <= n_sents <= args.max_sents:
            stats["sentences"] += 1
            continue
        fre = reading_ease(ue["text"])
        if fre > args.max_reading_ease:
            stats["readability"] += 1
            continue
        text_hi = uh["text"] if uh else ""
        # identical wording in two provisions would let one clause leak across splits
        if one_line(ue["text"]).lower() in seen_texts or (text_hi and one_line(text_hi) in seen_texts):
            stats["duplicate"] += 1
            continue
        seen_texts.update({one_line(ue["text"]).lower(), one_line(text_hi)} - {""})
        m_en, m_hi = find_markers(ue["text"], "en"), find_markers(text_hi, "hi") if text_hi else []
        n_words_hi = count_words(text_hi)
        out.append({
            "clause_id": f"{act['act_id']}-{key}", "act_id": act["act_id"], "domain": act["domain"],
            "section": ue["section"], "subsection": ue["subsection"], "key": key,
            "heading_en": ue["heading"], "heading_hi": uh["heading"] if uh else "",
            "text_en": ue["text"], "text_hi": text_hi, "n_words_en": n_words, "n_words_hi": n_words_hi,
            "n_sents_en": n_sents, "reading_ease_en": fre, "markers_en": m_en, "markers_hi": m_hi,
            "weight": clause_weight(m_en), "auto_flags": auto_flags(ue["text"], text_hi, n_words, n_words_hi)
            + act.get("review_flags", []) + act.get("section_review_flags", {}).get(ue["section"], []),
            "source": {"en": act["pdf"]["en"], "hi": act["pdf"]["hi"], "url": act.get("url"),
                       "version_note": act.get("version_note")},
        })
    stats["candidates"] = len(out)
    return out, stats


def weighted_sample(cands: list[dict], k: int, max_per_section: int, rng: random.Random) -> list[dict]:
    """Efraimidis-Spirakis weighted sampling without replacement, with a per-section cap.
    Each chosen clause records its `sample_rank` (0 = drawn first)."""
    keyed = sorted(cands, key=lambda c: rng.random() ** (1.0 / c["weight"]), reverse=True)
    chosen, per_sec = [], {}
    for c in keyed:
        if len(chosen) >= k:
            break
        if per_sec.get(c["section"], 0) >= max_per_section:
            continue
        per_sec[c["section"]] = per_sec.get(c["section"], 0) + 1
        chosen.append(dict(c, sample_rank=len(chosen)))
    return chosen


def select(args) -> None:
    paths = data_paths(args.data_dir)
    rng = random.Random(args.seed)
    all_chosen = []
    for act in load_sources(args.sources):
        cands, stats = candidates_for_act(act, paths, args)
        target = math.ceil(args.per_act * args.oversample)
        chosen = weighted_sample(cands, target, args.max_per_section, rng)
        print(f"[{act['act_id']}] {stats} -> selected {len(chosen)} (target {target})")
        if len(chosen) < target:
            print(f"  WARNING: only {len(chosen)} clauses pass the filters for {act['act_id']}.")
        all_chosen.extend(chosen)
    write_jsonl(paths.clauses, all_chosen)
    review = [dict(c, keep=1, review_note="") for c in all_chosen]
    write_csv(paths.review_csv, review, REVIEW_FIELDS)
    n_flag = sum(bool(c["auto_flags"]) for c in all_chosen)
    print(f"wrote {paths.clauses} ({len(all_chosen)} clauses) and {paths.review_csv}")
    print(f"{n_flag} rows have auto_flags. Review the CSV: set keep=0 on misaligned, garbled or fragmentary rows,"
          " then run with --finalize.")


def finalize(args) -> None:
    """Apply the human review: keep=1 rows only, reviewer text edits recorded, trim to --per-act."""
    paths = data_paths(args.data_dir)
    clauses = {c["clause_id"]: c for c in read_jsonl(paths.clauses)}
    if not clauses:
        sys.exit("no clauses.jsonl — run select_clauses.py first")
    if not paths.review_csv.exists():
        sys.exit(f"{paths.review_csv} not found")
    final, dropped, edited = [], 0, 0
    for row in read_csv(paths.review_csv):
        c = clauses.get(row["clause_id"])
        if c is None:
            print(f"  unknown clause_id in review CSV: {row['clause_id']}")
            continue
        if str(row.get("keep", "1")).strip() not in {"1", "1.0", "y", "yes", "true"}:
            dropped += 1
            continue
        c = dict(c, review_note=row.get("review_note", ""))
        for lang in ("en", "hi"):
            new = (row.get(f"text_{lang}") or "").strip()
            if new and new != c[f"text_{lang}"]:
                c.setdefault("review_edits", {})[lang] = {"before": c[f"text_{lang}"]}
                c[f"text_{lang}"] = new
                c[f"n_words_{lang}"] = count_words(new)
                edited += 1
        final.append(c)
    out = []
    for act in load_sources(args.sources):
        rows = sorted([c for c in final if c["act_id"] == act["act_id"]], key=lambda c: c["sample_rank"])
        if len(rows) < args.per_act:
            print(f"  WARNING: {act['act_id']} has {len(rows)} kept clauses (< {args.per_act}).")
        out.extend(rows[:args.per_act])
    write_jsonl(paths.clauses_final, out)
    print(f"review: dropped {dropped}, text edits {edited}. wrote {paths.clauses_final} ({len(out)} clauses)")


def load_final_clauses(paths) -> list[dict]:
    rows = read_jsonl(paths.clauses_final)
    if not rows:
        sys.exit(f"{paths.clauses_final} missing — run `python src/select_clauses.py --finalize` after review.")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-act", type=int, default=30)
    ap.add_argument("--oversample", type=float, default=1.3)
    ap.add_argument("--max-per-section", type=int, default=3)
    ap.add_argument("--min-words", type=int, default=15)
    ap.add_argument("--max-words", type=int, default=90)
    ap.add_argument("--max-sents", type=int, default=5)
    ap.add_argument("--max-reading-ease", type=float, default=50.0)
    ap.add_argument("--allow-missing-hi", action="store_true", help="keep EN units with no HI match (not for E2)")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--finalize", action="store_true", help="apply clauses_review.csv -> clauses_final.jsonl")
    ap.add_argument("--sources", default=None)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    finalize(args) if args.finalize else select(args)


if __name__ == "__main__":
    main()
