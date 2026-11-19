"""Step 3 without an API key: an LLM agent writes the simplifications, recorded with full provenance.

    python src/agent_simplify.py export                 # -> data/processed/simplify_tasks.jsonl
    python src/agent_simplify.py import answers.jsonl --model "claude-opus-5-5 (Claude Code agent)"

`export` lists every (clause, language, variant) with the exact prompt id and text from simplify.py.
The agent answers each task by following that prompt, one output per task, in a JSONL file of
{"sim_id": ..., "simplification": ...}. `import` validates the answers and appends rows to
simplifications.jsonl in the same schema simplify.py writes, so perturb.py and later steps work
unchanged. temperature/top_p/max_tokens are null because no sampling API was used; the paper states
that the simplifications were written by the named model acting as an agent (CLAUDE.md §7: provenance).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_jsonl, data_paths, read_jsonl, write_jsonl  # noqa: E402
from select_clauses import load_final_clauses  # noqa: E402
from simplify import PROMPTS, VARIANTS, clean_output, sim_id  # noqa: E402


def tasks(paths) -> list[dict]:
    out = []
    for c in load_final_clauses(paths):
        for lang in ("en", "hi"):
            text = c.get(f"text_{lang}")
            if not text:
                continue
            for variant in VARIANTS:
                pid, tmpl = PROMPTS[(lang, variant)]
                out.append({"sim_id": sim_id(c["clause_id"], lang, variant), "clause_id": c["clause_id"],
                            "act_id": c["act_id"], "lang": lang, "variant": variant, "prompt_id": pid,
                            "prompt": tmpl.format(text=text), "original": text})
    return out


def do_import(paths, answers_path: Path, model: str) -> dict:
    by_id = {t["sim_id"]: t for t in tasks(paths)}
    out_path = paths.processed / "simplifications.jsonl"
    done = {r["sim_id"] for r in read_jsonl(out_path)} if out_path.exists() else set()
    stats = {"imported": 0, "skipped_done": 0, "unknown": 0, "empty": 0}
    for a in read_jsonl(answers_path):
        t = by_id.get(a.get("sim_id"))
        if t is None:
            stats["unknown"] += 1
            continue
        if t["sim_id"] in done:
            stats["skipped_done"] += 1
            continue
        simp = clean_output(a.get("simplification", ""))
        if not simp:
            stats["empty"] += 1
            continue
        append_jsonl(out_path, {
            "sim_id": t["sim_id"], "clause_id": t["clause_id"], "act_id": t["act_id"], "lang": t["lang"],
            "variant": t["variant"], "original": t["original"], "simplification": simp,
            "raw_output": a.get("simplification", ""), "model": model, "served_model": model,
            "prompt_id": t["prompt_id"], "temperature": None, "top_p": None, "max_tokens": None, "seed": None,
            "finish_reason": "stop", "usage": None, "timestamp": datetime.now(timezone.utc).isoformat(),
            "generation": "agent",
        })
        done.add(t["sim_id"])
        stats["imported"] += 1
    stats["remaining"] = len(set(by_id) - done)
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export")
    imp = sub.add_parser("import")
    imp.add_argument("answers")
    imp.add_argument("--model", required=True)
    ap.add_argument("--data-dir", default=None)
    a = ap.parse_args(argv)
    paths = data_paths(a.data_dir)
    if a.cmd == "export":
        ts = tasks(paths)
        write_jsonl(paths.processed / "simplify_tasks.jsonl", ts)
        print(f"wrote {len(ts)} tasks -> {paths.processed / 'simplify_tasks.jsonl'}")
    else:
        print(do_import(paths, Path(a.answers), a.model))


if __name__ == "__main__":
    main()
