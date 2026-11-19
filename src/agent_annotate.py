"""Let an LLM annotator fill ITS OWN blinded workbook, without ever touching the answer key.

    python src/agent_annotate.py export data/annotation/llm_claude_opus55_b.xlsx   # -> <name>_items.jsonl
    python src/agent_annotate.py import data/annotation/llm_claude_opus55_b.xlsx answers.jsonl

`export` reads only the given workbook (opaque pair_uid, original, simplification, in the workbook's
own shuffled order) and writes them to `data/annotation/<name>_items.jsonl`. It never opens
pairs.jsonl, perturbations.jsonl or another annotator's workbook, so the annotator stays blind to
the variant and the injected error type.

The annotator answers each item under guidelines/annotation_guidelines.md with
{"pair_uid", "bracket", "omissions", "hallucinations", "inconsistencies", "confusions",
 "simplicity", "main_change", "comment"}; `import` validates the values against src/rubric.py and
writes them into the workbook's input columns. agreement.py then recomputes the LMP score from the
bracket and error counts exactly as for human annotators.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric import BRACKETS, ERROR_COLS, MAIN_CHANGES, SIMPLICITY  # noqa: E402


def _header(ws) -> dict[str, int]:
    return {str(c.value).strip(): c.column for c in ws[1] if c.value}


def export(xlsx: Path) -> Path:
    from openpyxl import load_workbook
    ws = load_workbook(xlsx, read_only=True)["Annotate"]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h).strip() if h else "" for h in rows[0]]
    out = xlsx.with_name(xlsx.stem + "_items.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for vals in rows[1:]:
            r = dict(zip(head, vals))
            if r.get("pair_uid"):
                f.write(json.dumps({"item": r.get("item"), "pair_uid": r["pair_uid"], "original": r["original"],
                                    "simplification": r["simplification"]}, ensure_ascii=False) + "\n")
    return out


def _valid(a: dict) -> list[str]:
    errs = []
    if a.get("bracket") not in BRACKETS:
        errs.append(f"bracket {a.get('bracket')!r}")
    for c in ERROR_COLS:
        v = a.get(c, 0)
        if not isinstance(v, int) or not 0 <= v <= 9:
            errs.append(f"{c}={v!r}")
    if a.get("simplicity") is not None and a["simplicity"] not in SIMPLICITY:
        errs.append(f"simplicity {a.get('simplicity')!r}")
    if a.get("main_change") is not None and a["main_change"] not in MAIN_CHANGES:
        errs.append(f"main_change {a.get('main_change')!r}")
    return errs


def do_import(xlsx: Path, answers: Path) -> dict:
    from openpyxl import load_workbook
    wb = load_workbook(xlsx)
    ws = wb["Annotate"]
    col = _header(ws)
    row_of = {ws.cell(row=r, column=col["pair_uid"]).value: r for r in range(2, ws.max_row + 1)}
    stats = {"written": 0, "unknown": 0, "invalid": 0}
    problems = []
    for line in answers.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        r = row_of.get(a.get("pair_uid"))
        if r is None:
            stats["unknown"] += 1
            continue
        bad = _valid(a)
        if bad:
            stats["invalid"] += 1
            problems.append(f"{a['pair_uid']}: {', '.join(bad)}")
            continue
        ws.cell(row=r, column=col["bracket"], value=a["bracket"])
        for c in ERROR_COLS:
            ws.cell(row=r, column=col[c], value=int(a.get(c, 0)))
        if a.get("simplicity"):
            ws.cell(row=r, column=col["simplicity"], value=a["simplicity"])
        if a.get("main_change"):
            ws.cell(row=r, column=col["main_change"], value=a["main_change"])
        if a.get("comment"):
            ws.cell(row=r, column=col["comment"], value=a["comment"])
        stats["written"] += 1
    wb.save(xlsx)
    filled = sum(1 for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=col["bracket"]).value)
    stats["filled_total"], stats["items"] = filled, ws.max_row - 1
    if problems:
        print("invalid rows (fix and re-import):\n  " + "\n  ".join(problems[:20]))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("workbook")
    i = sub.add_parser("import")
    i.add_argument("workbook")
    i.add_argument("answers")
    a = ap.parse_args(argv)
    if a.cmd == "export":
        print(f"wrote {export(Path(a.workbook))}")
    else:
        print(do_import(Path(a.workbook), Path(a.answers)))


if __name__ == "__main__":
    main()
