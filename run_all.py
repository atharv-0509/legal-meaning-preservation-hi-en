"""Push-button results: from filled annotation workbooks to every table and figure in the paper.

    python run_all.py prepare            # agreement -> labels -> clause-grouped splits (seeds 42-44)
    python run_all.py push               # launch the Kaggle GPU kernels (E1-E4 + baselines)
    python run_all.py collect            # wait for the kernels, download logs, unpack runs
    python run_all.py report             # evaluate -> reports/results.md(.json) + error analysis
    python run_all.py all                # everything in order

Kaggle needs KAGGLE_API_TOKEN (or a "KGAT_" KAGGLE_KEY) in the environment; on Windows the user
environment is read too. Kaggle account and backbones are set below. Re-running a stage is safe.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
KAGGLE_USER = "atharvarora05"
SEEDS = ["42", "43", "44"]
KERNELS = {                       # slug -> "backbone=plan;..." run in ONE GPU session (Kaggle allows 2 at once)
    "lmp-experiments": "xlm-roberta-base=full;google/muril-base-cased=e1",
    # XLM-R first trained on FrJUDGE (same task, French), then fine-tuned on ours: E1-E3
    "lmp-transfer": "xlm-roberta-base=frj",
}
LOGS = ROOT / "modeling" / "kaggle_logs"
# Early stopping on our ~35-pair dev set fires on noise: XLM-R stopped after a few epochs at the
# label mean (Pearson ~0) with patience 5 (v1) and patience 10 (v2). The FrJUDGE reproduction showed
# the released-code setting (no early stopping, keep the best dev checkpoint) is the stable one.
TRAIN_FLAGS = "--lr 2e-5 --batch-size 8 --patience 0 --epochs 30"


def run(*cmd, check=True, capture=False):
    print("$", " ".join(map(str, cmd)), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=ROOT, check=check, text=True,
                          capture_output=capture, encoding="utf-8", errors="replace")


def prepare():
    run(PY, "src/agreement.py")
    run(PY, "src/split.py", "--seeds", *SEEDS)


def github_main_sha() -> str:
    out = run("git", "ls-remote", "origin", "refs/heads/main", capture=True).stdout.split()
    if not out:
        sys.exit("cannot read origin/main from GitHub")
    return out[0]


ONLY: list[str] = []          # --only <slug> restricts push/collect to some kernels


def push():
    b64 = ROOT / "modeling" / "kaggle" / "_splits.b64"
    b64.write_text(run(PY, "modeling/kaggle/pack_splits.py", capture=True).stdout, encoding="utf-8")
    sha = github_main_sha()
    print(f"kernel code: GitHub main {sha[:7]}; splits bundle {b64.stat().st_size // 1024} KB")
    for slug, todo in KERNELS.items():
        if ONLY and slug not in ONLY:
            continue
        for attempt in range(48):                     # wait up to ~4 h for a free GPU session
            out = run(PY, "modeling/kaggle/kaggle_client.py", "push", "--user", KAGGLE_USER, "--slug", slug,
                      "--script", "modeling/kaggle/lmp_experiments.py", "--set", f"__COMMIT__={sha}",
                      "--set", f"__TODO__={todo}", "--set", f"__EXTRA__={TRAIN_FLAGS}", "--set-file", f"__SPLITS_B64__={b64}",
                      capture=True, check=False).stdout
            print(out)
            if "session count" not in out:
                break
            print(f"{time.strftime('%H:%M')} no free Kaggle GPU session; retrying in 5 min", flush=True)
            time.sleep(300)


def status(slug: str) -> str:
    out = run(PY, "modeling/kaggle/kaggle_client.py", "status", "--user", KAGGLE_USER, "--slug", slug,
              capture=True, check=False).stdout
    try:
        return json.loads(out).get("status", "unknown")
    except json.JSONDecodeError:
        return "unknown"


def collect(poll_min: float = 5.0, max_hours: float = 8.0):
    LOGS.mkdir(parents=True, exist_ok=True)
    pending = set(ONLY or KERNELS)
    deadline = time.time() + max_hours * 3600
    while pending and time.time() < deadline:
        for slug in sorted(pending):
            st = status(slug)
            print(f"{time.strftime('%H:%M')} {slug}: {st}", flush=True)
            if st in ("complete", "error", "cancelAcknowledged"):
                log = LOGS / f"{slug}.log"
                run(PY, "modeling/kaggle/kaggle_client.py", "log", "--user", KAGGLE_USER, "--slug", slug,
                    "--out", log)
                run(PY, "modeling/kaggle/kaggle_client.py", "unpack", "--log", log, "--dest", "modeling",
                    check=False)
                pending.discard(slug)
        if pending:
            time.sleep(poll_min * 60)
    if pending:
        print("still running:", ", ".join(sorted(pending)))


def report():
    run(PY, "modeling/evaluate.py")
    best = None
    res = json.loads((ROOT / "reports" / "results.json").read_text(encoding="utf-8"))
    for system, d in res.get("families", {}).get("random", {}).items():
        ps = [t["overall"]["pearson"] for t in d.get("test", []) if t.get("overall", {}).get("pearson") is not None]
        if ps and (best is None or sum(ps) / len(ps) > best[1]):
            best = (system, sum(ps) / len(ps))
    if best:
        run(PY, "modeling/error_analysis.py", "--system", best[0], "--n", "20", check=False)
        ea = sorted((ROOT / "reports").glob(f"error_analysis_{best[0]}*.md"))
        if ea:                            # stable name for the paper's @@INCLUDE
            (ROOT / "reports" / "error_analysis.md").write_text(ea[0].read_text(encoding="utf-8"), encoding="utf-8")
    run(PY, "modeling/make_tables.py")                 # reports/tables/*.tsv read by the paper and slides
    # paper + slides: in this repo since the handover merge (older layout: a sibling ../lmp-paper worktree)
    for paper in (ROOT / "paper" / "build.ps1", ROOT.parent / "lmp-paper" / "paper" / "build.ps1"):
        if paper.exists():
            run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", paper, check=False)
            break
    else:
        print("paper/build.ps1 not found: tables are written, paper/slides not rebuilt")
    print("reports/ ready" + (f"; best system {best[0]} (Pearson {best[1]:.3f})" if best else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["prepare", "push", "collect", "report", "all"])
    ap.add_argument("--only", nargs="*", default=[], help="kernel slugs for push/collect (default: all)")
    a = ap.parse_args(argv)
    ONLY.extend(a.only)
    stages = ["prepare", "push", "collect", "report"] if a.stage == "all" else [a.stage]
    for s in stages:
        print(f"\n=== {s} ===", flush=True)
        globals()[s]()


if __name__ == "__main__":
    main()
