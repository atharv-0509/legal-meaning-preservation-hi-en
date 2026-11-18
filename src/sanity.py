"""Step 5: data-augmentation (DA) pairs and sanity-check holdout sets.

    python src/sanity.py [--unrelated-label 1] [--holdout-n 50]

DA (as in JUDGEBERT): for every selected clause and language,
  identical  original vs. itself, label 10
  unrelated  original vs. a provision that shares almost no words with it
             (ROUGE-1/2/L < 0.25 and BLEU < 25, our Devanagari-aware tokeniser), label 1
             (the floor of our 1-10 scale; the paper used 0 -> `--unrelated-label 0`).

Holdouts (E4) are built from provisions that are used NOWHERE else: not selected, not in a section
that has a selected clause, and not used as a DA partner. The unselected provisions are split into
two disjoint pools by section, one feeding DA partners and one feeding holdouts.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_paths, is_unrelated, load_sources, one_line, read_jsonl, short_hash, units_path, write_jsonl  # noqa: E402
from select_clauses import load_final_clauses  # noqa: E402


def load_pool(paths, sources, lang, min_words, max_words) -> list[dict]:
    pool = []
    for act in sources:
        for u in read_jsonl(units_path(paths, act["act_id"], lang)):
            if min_words <= u["n_words"] <= max_words:
                pool.append(u)
    return pool


def find_partner(text: str, pool: list[dict], rng: random.Random, used: set, tries: int = 200) -> dict | None:
    idx = list(range(len(pool)))
    rng.shuffle(idx)
    for i in idx[:tries]:
        u = pool[i]
        uid = (u["act_id"], u["key"], u["lang"])
        if uid in used:
            continue
        if is_unrelated(text, u["text"]) and is_unrelated(u["text"], text):
            return u
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--identical-label", type=float, default=10.0)
    ap.add_argument("--unrelated-label", type=float, default=1.0)
    ap.add_argument("--holdout-n", type=int, default=50, help="holdout pairs per language and type")
    ap.add_argument("--min-words", type=int, default=10)
    ap.add_argument("--max-words", type=int, default=120)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--sources", default=None)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    sources = load_sources(args.sources)
    rng = random.Random(args.seed)
    clauses = load_final_clauses(paths)
    selected_sections = {(c["act_id"], c["section"]) for c in clauses}

    augment, hold_id, hold_un = [], [], []
    for lang in ("en", "hi"):
        # exclude selected sections, and any provision whose text equals a selected clause's text
        # (acts repeat standard wording, e.g. identical provisos in different sections)
        selected_texts = {one_line(c[f"text_{lang}"]) for c in clauses}
        pool = [u for u in load_pool(paths, sources, lang, args.min_words, args.max_words)
                if (u["act_id"], u["section"]) not in selected_sections and one_line(u["text"]) not in selected_texts]
        seen_texts, dedup = set(), []
        for u in pool:                                   # one provision per distinct text
            if one_line(u["text"]) not in seen_texts:
                seen_texts.add(one_line(u["text"]))
                dedup.append(u)
        pool = dedup
        # split unselected provisions into DA-partner / holdout pools by section (stable hash)
        da_pool = [u for u in pool if int(short_hash(f"{u['act_id']}|{u['section']}|{args.seed}"), 16) % 2 == 0]
        ho_pool = [u for u in pool if int(short_hash(f"{u['act_id']}|{u['section']}|{args.seed}"), 16) % 2 == 1]
        print(f"[{lang}] unselected provisions: {len(pool)} (DA partners {len(da_pool)}, holdout {len(ho_pool)})")

        n_fail = 0
        for c in clauses:
            orig = c[f"text_{lang}"]
            if not orig:
                continue
            base = {"clause_id": c["clause_id"], "act_id": c["act_id"], "lang": lang, "original": orig}
            augment.append(dict(base, pair_id=f"{c['clause_id']}|{lang}|da_identical", variant="da_identical",
                                simplification=orig, label=args.identical_label))
            partner = find_partner(orig, da_pool, rng, used=set())
            if partner is None:
                n_fail += 1
                continue
            augment.append(dict(base, pair_id=f"{c['clause_id']}|{lang}|da_unrelated", variant="da_unrelated",
                                simplification=partner["text"], label=args.unrelated_label,
                                partner=f"{partner['act_id']}-{partner['key']}"))
        if n_fail:
            print(f"  WARNING: no unrelated partner found for {n_fail} clauses ({lang})")

        # holdouts: originals and partners both from the holdout pool, each provision used once
        rng.shuffle(ho_pool)
        used: set = set()
        originals = ho_pool[: args.holdout_n]
        for u in originals:
            used.add((u["act_id"], u["key"], u["lang"]))
        for u in originals:
            cid = f"holdout-{u['act_id']}-{u['key']}"
            hold_id.append({"pair_id": f"{cid}|{lang}|identical", "clause_id": cid, "act_id": u["act_id"],
                            "lang": lang, "variant": "identical", "original": u["text"],
                            "simplification": u["text"], "label": args.identical_label})
        rest = [u for u in ho_pool if (u["act_id"], u["key"], u["lang"]) not in used]
        for u in originals:
            p = find_partner(u["text"], rest, rng, used)
            if p is None:
                continue
            used.add((p["act_id"], p["key"], p["lang"]))
            cid = f"holdout-{u['act_id']}-{u['key']}"
            hold_un.append({"pair_id": f"{cid}|{lang}|unrelated", "clause_id": cid, "act_id": u["act_id"],
                            "lang": lang, "variant": "unrelated", "original": u["text"],
                            "simplification": p["text"], "label": args.unrelated_label,
                            "partner": f"{p['act_id']}-{p['key']}"})
        if len(originals) < args.holdout_n:
            print(f"  WARNING: only {len(originals)} holdout provisions available for {lang}")

    write_jsonl(paths.augment, augment)
    write_jsonl(paths.holdout_identical, hold_id)
    write_jsonl(paths.holdout_unrelated, hold_un)
    print(f"wrote {paths.augment} ({len(augment)}), {paths.holdout_identical} ({len(hold_id)}), "
          f"{paths.holdout_unrelated} ({len(hold_un)})")


if __name__ == "__main__":
    main()
