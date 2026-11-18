"""Step 8: clause-grouped splits.

    python src/split.py --seeds 42 43 44 45 46

  data/splits/random_s<seed>/   60/10/30 by clause (stratified by act)
  data/splits/ood_rti_to_cpa/   train+dev on one act (90/10 by clause), test on the other
  data/splits/ood_cpa_to_rti/
  data/splits/holdout_identical.jsonl, holdout_unrelated.jsonl   (E4 sanity checks)

Each split dir: train.jsonl, dev.jsonl, test.jsonl (human-annotated pairs only), train_da.jsonl,
dev_da.jsonl (human pairs + the DA pairs of those same clauses), meta.json.
A clause's EN and HI pairs, all its variants and its DA pairs always share a split; check_disjoint()
asserts this and that no holdout text appears in any split.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_paths, one_line, read_jsonl, write_jsonl  # noqa: E402

FIELDS = ["pair_id", "clause_id", "act_id", "lang", "variant", "original", "simplification", "label"]
EXTRA = ["error_type", "label_std", "main_change", "n_annotators"]


def slim(r: dict) -> dict:
    out = {k: r.get(k) for k in FIELDS}
    out.update({k: r[k] for k in EXTRA if k in r})
    return out


def check_disjoint(split: dict[str, list[dict]], holdouts: list[dict] = ()) -> None:
    """Fail loudly if any clause or text leaks across splits."""
    names = [n for n in ("train", "dev", "test") if n in split]
    clause_sets = {n: {r["clause_id"] for r in split[n]} for n in names}
    for a in names:
        for b in names:
            if a < b:
                both = clause_sets[a] & clause_sets[b]
                assert not both, f"clause leak {a}/{b}: {sorted(both)[:5]}"
    for n in ("train_da", "dev_da"):
        if n in split:
            base = n.split("_")[0]
            stray = {r["clause_id"] for r in split[n]} - clause_sets[base]
            assert not stray, f"{n} has DA pairs of clauses outside {base}: {sorted(stray)[:5]}"
            assert all(not r["variant"].startswith("da_") or r["clause_id"] in clause_sets[base] for r in split[n])
    if "test" in split:
        assert all(not r["variant"].startswith("da_") for r in split["test"]), "DA pairs in test"
        test_texts = {one_line(r["original"]) for r in split["test"]}
        for n in ("train", "dev", "train_da", "dev_da"):
            if n in split:
                leak = test_texts & {one_line(r["original"]) for r in split[n]} \
                    | (test_texts & {one_line(r["simplification"]) for r in split[n]})
                assert not leak, f"test original appears in {n}: {list(leak)[:1]}"
    if holdouts:
        h = {one_line(r["original"]) for r in holdouts} | {one_line(r["simplification"]) for r in holdouts}
        for n, rows in split.items():
            used = {one_line(r["original"]) for r in rows} | {one_line(r["simplification"]) for r in rows}
            assert not (h & used), f"holdout text appears in {n}"


def grouped_split(clauses_by_act: dict[str, list[str]], ratios, rng: random.Random) -> dict[str, set]:
    out = {"train": set(), "dev": set(), "test": set()}
    for act, cids in sorted(clauses_by_act.items()):
        cids = sorted(cids)
        rng.shuffle(cids)
        n = len(cids)
        n_tr = round(ratios[0] * n)
        n_dev = round(ratios[1] * n)
        out["train"] |= set(cids[:n_tr])
        out["dev"] |= set(cids[n_tr:n_tr + n_dev])
        out["test"] |= set(cids[n_tr + n_dev:])
    return out


def materialise(assign: dict[str, set], human: list[dict], da: list[dict]) -> dict[str, list[dict]]:
    split = {}
    for name in ("train", "dev", "test"):
        split[name] = [slim(r) for r in human if r["clause_id"] in assign[name]]
    for name in ("train", "dev"):
        split[f"{name}_da"] = split[name] + [slim(r) for r in da if r["clause_id"] in assign[name]]
    return split


def write_split(out_dir: Path, split: dict[str, list[dict]], meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in split.items():
        write_jsonl(out_dir / f"{name}.jsonl", sorted(rows, key=lambda r: r["pair_id"]))
    meta = dict(meta, counts={n: len(r) for n, r in split.items()},
                clauses={n: len({r["clause_id"] for r in split[n]}) for n in ("train", "dev", "test")},
                by_lang={n: dict(Counter(r["lang"] for r in split[n])) for n in ("train", "dev", "test")})
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    ap.add_argument("--ratios", nargs=3, type=float, default=[0.6, 0.1, 0.3])
    ap.add_argument("--ood-dev", type=float, default=0.1, help="dev share of the training act in OOD splits")
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    human = read_jsonl(paths.labeled)
    if not human:
        sys.exit("no labeled_pairs.jsonl — run agreement.py first")
    da = read_jsonl(paths.augment)
    hold_id, hold_un = read_jsonl(paths.holdout_identical), read_jsonl(paths.holdout_unrelated)
    holdouts = hold_id + hold_un

    by_act = defaultdict(set)
    for r in human:
        by_act[r["act_id"]].add(r["clause_id"])
    print(f"{len(human)} labelled pairs, {sum(map(len, by_act.values()))} clauses, acts {sorted(by_act)}; "
          f"{len(da)} DA pairs; holdouts {len(hold_id)} identical / {len(hold_un)} unrelated")

    for seed in args.seeds:
        assign = grouped_split(by_act, args.ratios, random.Random(seed))
        split = materialise(assign, human, da)
        check_disjoint(split, holdouts)
        write_split(paths.splits / f"random_s{seed}", split, {"type": "random", "seed": seed, "ratios": args.ratios})
        print(f"random_s{seed}: " + ", ".join(f"{n}={len(v)}" for n, v in split.items()))

    acts = sorted(by_act)
    for a in acts:
        for b in acts:
            if a == b:
                continue
            rng = random.Random(42)
            src = sorted(by_act[a])
            rng.shuffle(src)
            n_dev = max(1, round(args.ood_dev * len(src)))
            assign = {"train": set(src[n_dev:]), "dev": set(src[:n_dev]), "test": set(by_act[b])}
            split = materialise(assign, human, da)
            check_disjoint(split, holdouts)
            write_split(paths.splits / f"ood_{a}_to_{b}", split, {"type": "ood", "train_act": a, "test_act": b})
            print(f"ood_{a}_to_{b}: " + ", ".join(f"{n}={len(v)}" for n, v in split.items()))

    write_jsonl(paths.splits / "holdout_identical.jsonl", [slim(r) for r in hold_id])
    write_jsonl(paths.splits / "holdout_unrelated.jsonl", [slim(r) for r in hold_un])
    print(f"holdouts copied to {paths.splits}/")


if __name__ == "__main__":
    main()
