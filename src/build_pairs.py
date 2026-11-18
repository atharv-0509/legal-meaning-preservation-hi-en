"""Step 6: pairs.jsonl (the answer key) + one blinded Excel workbook per annotator (+ pilot).

    python src/build_pairs.py --annotators A B C [--per-pair 3] [--pilot 20]

pairs.jsonl holds variant, error type and model; annotators NEVER see it. Workbooks show only an
opaque pair_uid, the original and the simplification, in a different shuffled order per annotator,
with items from the same clause kept apart. Pilot: --pilot N pairs, stratified by language and
variant, shared by every annotator (data/annotation/pilot/). Pilot scores are discarded; the pilot
pairs are annotated again in the main round after the guidelines are updated.
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_paths, read_jsonl, short_hash, write_jsonl  # noqa: E402
from rubric import BRACKETS, ERROR_COLS, MAIN_CHANGES, SIMPLICITY  # noqa: E402
from select_clauses import load_final_clauses  # noqa: E402

COLUMNS = ["item", "pair_uid", "original", "simplification", "simplicity", "bracket", *ERROR_COLS,
           "main_change", "lmp_score", "check", "comment", "minutes"]
INPUT_COLS = {"simplicity", "bracket", *ERROR_COLS, "main_change", "comment", "minutes"}
WIDTHS = {"item": 6, "pair_uid": 13, "original": 60, "simplification": 60, "simplicity": 14, "bracket": 16,
          "omissions": 10, "hallucinations": 12, "inconsistencies": 13, "confusions": 10, "main_change": 18,
          "lmp_score": 10, "check": 26, "comment": 40, "minutes": 9}

INSTRUCTIONS = [
    "Legal Meaning Preservation (LMP) annotation",
    "",
    "Read guidelines/annotation_guidelines.md before you start. Score each row on the 'Annotate' sheet.",
    "Fill only the yellow columns. Do not edit pair_uid, original or simplification. Do not reorder rows.",
    "",
    "For each row:",
    "1. simplicity: is the simplification easier to read than the original? (1-5)",
    "2. bracket: does the simplification keep the LEGAL meaning (rights, duties, conditions, exceptions, limits)?",
    "     Accurate (7-10): the legal meaning is kept; at most small slips.",
    "     Imprecise (2-6): the legal meaning is partly kept, partly lost or distorted.",
    "     Off-track (1): the simplification misrepresents the law or is about something else.",
    "3. Count errors (0-9 each). Every error costs 1 point from the bracket maximum (10, 6 or 1); the score never goes below 1.",
    "     omissions: an essential legal element of the original is missing (condition, exception, time limit, actor...).",
    "     hallucinations: the simplification adds a legal element that is not in the original.",
    "     inconsistencies: terms are used inconsistently or a legal term is replaced by a non-equivalent word.",
    "     confusions: the simplification states something different from / contrary to the original "
    "(e.g. 'may' for 'shall', wrong number, wrong actor, negation).",
    "4. main_change: the single most important legal change (or 'none').",
    "5. lmp_score and check are computed for you. Resolve any message in 'check' other than OK.",
    "6. comment: a short reason, especially for scores below 7. minutes: optional, time spent on the row.",
    "",
    "Judge only legal meaning: ignore style and fluency unless they change the meaning.",
    "Score each row on its own. Similar-looking rows are not necessarily the same.",
]


def pair_uid(pair_id: str) -> str:
    return short_hash("lmp-v1|" + pair_id, 10)


def collect_pairs(paths) -> list[dict]:
    clauses = {c["clause_id"]: c for c in load_final_clauses(paths)}
    rows = read_jsonl(paths.simplifications) + read_jsonl(paths.perturbations)
    pairs, seen = [], set()
    n_trunc = 0
    for r in rows:
        c = clauses.get(r["clause_id"])
        if c is None:
            continue                                   # clause dropped at review
        if not (r.get("simplification") or "").strip():
            continue
        pid = f"{r['clause_id']}|{r['lang']}|{r['variant']}"
        if pid in seen:
            continue
        seen.add(pid)
        n_trunc += r.get("finish_reason") == "length"
        pairs.append({
            "pair_id": pid, "pair_uid": pair_uid(pid), "clause_id": r["clause_id"], "act_id": c["act_id"],
            "domain": c["domain"], "lang": r["lang"], "variant": r["variant"],
            "original": c[f"text_{r['lang']}"], "simplification": r["simplification"],
            "error_type": r.get("error_type"), "change": r.get("change"), "model": r.get("model"),
            "prompt_id": r.get("prompt_id"), "base_sim_id": r.get("base_sim_id"),
        })
    if n_trunc:
        print(f"WARNING: {n_trunc} pairs come from truncated LLM outputs (finish_reason=length).")
    uids = Counter(p["pair_uid"] for p in pairs)
    assert max(uids.values(), default=1) == 1, "pair_uid collision"
    return sorted(pairs, key=lambda p: p["pair_id"])


def assign(pairs: list[dict], annotators: list[str], per_pair: int, rng: random.Random) -> dict[str, list[dict]]:
    """Each pair goes to `per_pair` annotators; loads are balanced. A clause's pairs are spread so
    no annotator is guaranteed to see every variant of the same clause when per_pair < n."""
    per_pair = min(per_pair, len(annotators))
    load = Counter({a: 0 for a in annotators})
    out = defaultdict(list)
    order = pairs[:]
    rng.shuffle(order)
    for p in order:
        chosen = sorted(annotators, key=lambda a: (load[a], rng.random()))[:per_pair]
        for a in chosen:
            out[a].append(p)
            load[a] += 1
    return out


def spread_shuffle(items: list[dict], rng: random.Random, key="clause_id") -> list[dict]:
    """Shuffle, then swap to avoid two rows of the same clause next to each other (best effort)."""
    items = items[:]
    rng.shuffle(items)
    for _ in range(3):
        for i in range(1, len(items)):
            if items[i][key] == items[i - 1][key]:
                for j in range(len(items)):
                    ok_j = all(items[k][key] != items[i][key] for k in (j - 1, j + 1) if 0 <= k < len(items) and k != i)
                    ok_i = all(items[k][key] != items[j][key] for k in (i - 1, i + 1) if 0 <= k < len(items) and k != j)
                    if j != i and items[j][key] != items[i][key] and ok_j and ok_i:
                        items[i], items[j] = items[j], items[i]
                        break
    return items


def pilot_sample(pairs: list[dict], n: int, rng: random.Random) -> list[dict]:
    strata = defaultdict(list)
    for p in pairs:
        strata[(p["lang"], p["variant"])].append(p)
    for v in strata.values():
        rng.shuffle(v)
    out, keys = [], sorted(strata)
    while len(out) < n and any(strata.values()):
        for k in keys:
            if strata[k] and len(out) < n:
                out.append(strata[k].pop())
    return out


def write_workbook(path: Path, annotator: str, items: list[dict], round_name: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ins = wb.active
    ins.title = "Instructions"
    for i, line in enumerate(INSTRUCTIONS, 1):
        ins.cell(row=i, column=1, value=line).alignment = Alignment(wrap_text=True, vertical="top")
    ins["A1"].font = Font(bold=True, size=14)
    ins.column_dimensions["A"].width = 130

    ws = wb.create_sheet("Annotate")
    col = {name: i + 1 for i, name in enumerate(COLUMNS)}
    L = {name: get_column_letter(i) for name, i in col.items()}
    yellow = PatternFill("solid", fgColor="FFF2CC")
    grey = PatternFill("solid", fgColor="EDEDED")
    for name, c in col.items():
        cell = ws.cell(row=1, column=c, value=name)
        cell.font = Font(bold=True)
        cell.fill = yellow if name in INPUT_COLS else grey
        ws.column_dimensions[L[name]].width = WIDTHS[name]
    n = len(items)
    for r, p in enumerate(items, 2):
        ws.cell(row=r, column=col["item"], value=r - 1)
        ws.cell(row=r, column=col["pair_uid"], value=p["pair_uid"])
        ws.cell(row=r, column=col["original"], value=p["original"])
        ws.cell(row=r, column=col["simplification"], value=p["simplification"])
        b, e0, e1 = f"{L['bracket']}{r}", f"{L[ERROR_COLS[0]]}{r}", f"{L[ERROR_COLS[-1]]}{r}"
        ws.cell(row=r, column=col["lmp_score"],
                value=f'=IF({b}="","",MAX(1,IF(LEFT({b},3)="Acc",10,IF(LEFT({b},3)="Imp",6,1))-SUM({e0}:{e1})))')
        ws.cell(row=r, column=col["check"], value=(
            f'=IF({b}="","TODO",IF(AND(LEFT({b},3)="Imp",SUM({e0}:{e1})=0),"Imprecise needs >=1 error",'
            f'IF(AND(LEFT({b},3)="Acc",SUM({e0}:{e1})>3),"Score < 7: really Accurate?",'
            f'IF(AND(LEFT({b},3)="Off",SUM({e0}:{e1})>0),"Off-track: errors ignored","OK"))))'))
        for name in COLUMNS:
            c = ws.cell(row=r, column=col[name])
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if name in INPUT_COLS:
                c.fill = yellow
        ws.row_dimensions[r].height = 110
    last = n + 1
    if n:
        dv_b = DataValidation(type="list", formula1='"' + ",".join(BRACKETS) + '"', allow_blank=True)
        dv_b.add(f"{L['bracket']}2:{L['bracket']}{last}")
        dv_s = DataValidation(type="list", formula1='"' + ",".join(SIMPLICITY) + '"', allow_blank=True)
        dv_s.add(f"{L['simplicity']}2:{L['simplicity']}{last}")
        dv_m = DataValidation(type="list", formula1='"' + ",".join(MAIN_CHANGES) + '"', allow_blank=True)
        dv_m.add(f"{L['main_change']}2:{L['main_change']}{last}")
        dv_e = DataValidation(type="whole", operator="between", formula1="0", formula2="9", allow_blank=True)
        dv_e.add(f"{L[ERROR_COLS[0]]}2:{L[ERROR_COLS[-1]]}{last}")
        for dv in (dv_b, dv_s, dv_m, dv_e):
            ws.add_data_validation(dv)
    ws.freeze_panes = "C2"

    meta = wb.create_sheet("meta")
    for i, (k, v) in enumerate([("annotator", annotator), ("round", round_name), ("n_items", n),
                                ("created", date.today().isoformat()), ("rubric", "JUDGEBERT v1")], 1):
        meta.cell(row=i, column=1, value=k)
        meta.cell(row=i, column=2, value=v)
    meta.sheet_state = "hidden"
    wb.active = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annotators", nargs="+", required=True, help="names used as workbook file names")
    ap.add_argument("--per-pair", type=int, default=3)
    ap.add_argument("--pilot", type=int, default=20, help="shared pilot pairs (0 = no pilot)")
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="overwrite existing workbooks")
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    rng = random.Random(args.seed)

    pairs = collect_pairs(paths)
    if not pairs:
        sys.exit("no pairs — run simplify.py and perturb.py first")
    write_jsonl(paths.pairs, pairs)
    by = Counter((p["lang"], p["variant"]) for p in pairs)
    print(f"wrote {paths.pairs}: {len(pairs)} pairs {dict(sorted(by.items()))}")

    existing = [paths.annotation / f"{a}.xlsx" for a in args.annotators if (paths.annotation / f"{a}.xlsx").exists()]
    if existing and not args.force:
        sys.exit(f"workbooks already exist ({existing[0]}); pass --force to overwrite (annotations would be lost)")

    assignment = assign(pairs, args.annotators, args.per_pair, rng)
    rows = []
    for a in args.annotators:
        items = spread_shuffle(assignment[a], random.Random(f"{args.seed}|{a}"))
        write_workbook(paths.annotation / f"{a}.xlsx", a, items, "main")
        rows += [{"pair_uid": p["pair_uid"], "annotator": a, "round": "main"} for p in items]
        print(f"  {a}: {len(items)} items -> {paths.annotation / (a + '.xlsx')}")
    if args.pilot:
        pilot = pilot_sample(pairs, args.pilot, rng)
        for a in args.annotators:
            items = spread_shuffle(pilot, random.Random(f"pilot|{args.seed}|{a}"))
            write_workbook(paths.pilot / f"{a}.xlsx", a, items, "pilot")
            rows += [{"pair_uid": p["pair_uid"], "annotator": a, "round": "pilot"} for p in items]
        print(f"  pilot: {len(pilot)} shared items -> {paths.pilot}/")
    write_jsonl(paths.assignment, rows)
    per = Counter(r["pair_uid"] for r in rows if r["round"] == "main")
    print(f"each pair has {min(per.values())}-{max(per.values())} annotators. "
          "Send ONLY the .xlsx files to annotators (never pairs.jsonl).")


if __name__ == "__main__":
    main()
