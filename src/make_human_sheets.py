"""Blinded human-validation workbooks: the 30 shared pilot pairs, one shuffled copy per person.

    python src/make_human_sheets.py --annotators "Karan Singh" "Atharv Arora" "Jatin Khanchi"
    # after scoring, put the filled files back in data/annotation/human/ and run:
    python src/human_validation.py

The pairs are the same 30 as data/annotation/pilot/ (a stratified sample of the 338 pairs, which both
LLM annotators also scored), so human scores can be compared with the LLM labels pair by pair.
Each sheet uses build_pairs.write_workbook: opaque ids, shuffled order, no variant or error type.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pairs import spread_shuffle, write_workbook  # noqa: E402
from common import data_paths, read_jsonl  # noqa: E402


def pilot_uids(pilot_dir: Path) -> list[str]:
    from openpyxl import load_workbook
    src = sorted(pilot_dir.glob("*.xlsx"))
    if not src:
        sys.exit(f"no pilot workbook in {pilot_dir}: run build_pairs.py --pilot 30 first")
    ws = load_workbook(src[0], read_only=True)["Annotate"]
    rows = list(ws.iter_rows(values_only=True))
    col = [str(h).strip() if h else "" for h in rows[0]].index("pair_uid")
    return [r[col] for r in rows[1:] if r[col]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annotators", nargs="+", required=True)
    ap.add_argument("--data-dir", default=None)
    a = ap.parse_args(argv)
    paths = data_paths(a.data_dir)
    uids = set(pilot_uids(paths.pilot))
    pairs = [p for p in read_jsonl(paths.processed / "pairs.jsonl") if p["pair_uid"] in uids]
    out_dir = paths.data / "annotation" / "human"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in a.annotators:
        items = spread_shuffle(pairs, random.Random(f"human|{name}"))
        path = out_dir / (name.lower().replace(" ", "_") + ".xlsx")
        write_workbook(path, name, items, "human_validation")
        print(f"{name}: {len(items)} items -> {path}")


if __name__ == "__main__":
    main()
