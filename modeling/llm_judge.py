"""LLM-as-judge baseline: the LLM gets the SAME rubric as the human annotators and returns a
bracket + error counts; the score is computed with rubric.lmp_score, exactly like a human's.

    LLM_API_KEY=... [LLM_BASE_URL=...] python modeling/llm_judge.py --model <exact-model-id> \
        --splits data/splits/random_s* data/splits/ood_*

Each unique pair is judged once (cache: modeling/cache/llm_judge_<model>.jsonl, resumable), then
predictions are written for every split, like the other baselines. Temperature 0.
Use a different model from the one that wrote the simplifications if you can (self-preference bias),
and report the exact model id.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmp_data import ROOT, holdout_files, load_split, run_dir, write_json, write_preds  # noqa: E402
from metrics import evaluate_rows, sanity_metrics  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from common import append_jsonl, read_jsonl, short_hash  # noqa: E402
from rubric import BRACKETS, ERROR_COLS, MAIN_CHANGES, lmp_score, normalise_bracket  # noqa: E402
from simplify import LLMClient  # noqa: E402

PROMPT_ID = "judge_rubric_v1"
PROMPT = """You are an expert in Indian law. You assess whether a simplified version of a legal provision \
preserves its LEGAL meaning: who must or may do what, under which conditions, with which exceptions, \
time limits, amounts and scope. Ignore style and fluency unless they change the legal meaning. \
The texts may be in English or Hindi; compare the simplification with the original in the same language.

Procedure:
1. Choose a bracket:
   - "Accurate (7-10)": the legal meaning is kept; a reader relying on the simplification would not be misled.
   - "Imprecise (2-6)": the legal meaning is partly kept; something legally relevant is lost, added or distorted.
   - "Off-track (1)": the simplification misrepresents the law (e.g. reverses a duty or prohibition) or is about something else.
2. Count each distinct error (0-9 per type):
   - omissions: an essential legal element of the original is missing (condition, exception/proviso, time limit, actor, amount).
   - hallucinations: a legal element is added that is not in the original.
   - inconsistencies: a legal term is replaced by a non-equivalent word, or terms are used inconsistently.
   - confusions: the simplification states something different from or contrary to the original \
(shall/may swapped, negation added or removed, wrong number, wrong actor, all->some).
   Omitting genuinely unimportant drafting detail is not an error.
3. main_change: the single most important legal change, one of: {changes}.

Original:
{original}

Simplification:
{simplification}

Answer with JSON only, no other text:
{{"bracket": "...", "omissions": 0, "hallucinations": 0, "inconsistencies": 0, "confusions": 0, \
"main_change": "...", "explanation": "one short sentence"}}"""


def parse_judgement(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    bracket = normalise_bracket(d.get("bracket"))
    if bracket is None:
        return None
    errors = {}
    for c in ERROR_COLS:
        try:
            errors[c] = max(0, min(9, int(d.get(c) or 0)))
        except (TypeError, ValueError):
            errors[c] = 0
    return {"bracket": bracket, **errors, "score": lmp_score(bracket, errors),
            "main_change": d.get("main_change"), "explanation": d.get("explanation")}


def _key(r):
    return short_hash(r["original"] + "␞" + r["simplification"], 16)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--splits", nargs="+", default=None)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=None, help="judge at most N new pairs (trial run)")
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args(argv)
    split_dirs = [Path(p) for s in (args.splits or [str(ROOT / "data" / "splits" / "*")]) for p in glob.glob(s)]
    split_dirs = sorted(d for d in split_dirs if d.is_dir() and (d / "test.jsonl").exists())
    if not split_dirs:
        sys.exit("no split dirs found")

    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    client = LLMClient(base, os.environ.get("LLM_API_KEY", ""), args.model)
    cache_path = ROOT / "modeling" / "cache" / f"llm_judge_{re.sub(r'[^A-Za-z0-9._-]', '_', args.model)}.jsonl"
    cache = {r["k"]: r for r in read_jsonl(cache_path) if r.get("score") is not None}

    def all_rows(d):
        rows = load_split(d, "test")
        for p in holdout_files(d).values():
            rows += read_jsonl(p)
        return rows

    todo = {_key(r): r for d in split_dirs for r in all_rows(d) if _key(r) not in cache}
    todo = list(todo.values())[: args.limit]
    print(f"{len(cache)} cached judgements, {len(todo)} to request")
    for i, r in enumerate(todo, 1):
        prompt = PROMPT.format(changes=", ".join(MAIN_CHANGES), original=r["original"], simplification=r["simplification"])
        j = None
        for _attempt in range(3):
            out = client.chat(prompt, temperature=0.0, top_p=1.0, max_tokens=args.max_tokens)
            j = parse_judgement(out["text"])
            if j:
                break
        row = {"k": _key(r), "pair_id": r.get("pair_id"), "model": args.model, "prompt_id": PROMPT_ID,
               **(j or {"score": None, "raw": out["text"][:500]})}
        append_jsonl(cache_path, row)
        if j:
            cache[row["k"]] = row
        print(f"[{i}/{len(todo)}] {r.get('pair_id')}: {row.get('bracket')} -> {row.get('score')}")
        if args.sleep:
            time.sleep(args.sleep)

    system = f"llm-judge_{re.sub(r'[^A-Za-z0-9._-]', '_', args.model)}"
    runs = Path(args.runs_dir) if args.runs_dir else None
    for d in split_dirs:
        test = [r for r in load_split(d, "test") if _key(r) in cache]
        out = run_dir(system, d.name, runs)
        preds = [cache[_key(r)]["score"] for r in test]
        rows = [dict(r, main_change_pred=cache[_key(r)].get("main_change"), explanation=cache[_key(r)].get("explanation"))
                for r in test]
        write_preds(out / "preds_test.jsonl", rows, preds)
        m = {"test": evaluate_rows([dict(r, pred=p) for r, p in zip(test, preds)]),
             "missing": len(load_split(d, "test")) - len(test)}
        for n, p in holdout_files(d).items():
            hrows = [r for r in read_jsonl(p) if _key(r) in cache]
            hp = [cache[_key(r)]["score"] for r in hrows]
            write_preds(out / f"preds_{n}.jsonl", hrows, hp)
            m[n] = sanity_metrics(hp, n.split("_")[1])
        write_json(out / "metrics.json", m)
        write_json(out / "config.json", {"system": system, "model": args.model, "prompt_id": PROMPT_ID,
                                         "temperature": 0.0, "brackets": BRACKETS})
        print(f"{system} {d.name}: pearson={m['test']['overall'].get('pearson', float('nan')):.3f} (missing {m['missing']})")


if __name__ == "__main__":
    main()
