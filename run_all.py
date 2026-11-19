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
    # review fixes (19 Nov): E2 on RTI-bilingual splits and E3 without target-act DA partners, for the
    # transfer model and the from-scratch baseline, plus one saved checkpoint for the demo
    "lmp-e23-fixed": "xlm-roberta-base=frj-e23;xlm-roberta-base=e23;xlm-roberta-base=frj-demo",
    # generalisation follow-up (19 Nov, evening): MuRIL with the same FrJUDGE pre-training, and XLM-R transfer
    # over five seeds; tagged run names so the deadline results are not overwritten
    "lmp-muril-frj": "google/muril-base-cased=frj-e1;google/muril-base-cased=frj-e23",
    "lmp-xlmr-5seeds": "xlm-roberta-base=frj-e1;xlm-roberta-base=frj-e23",
    # legal-error type classifier (brief: optional error type + P/R/F1): XLM-R from scratch, XLM-R from the
    # FrJUDGE-trained encoder, MuRIL; two saved checkpoints for the demo app
    "lmp-errcls": ("xlm-roberta-base=errcls;xlm-roberta-base=frj-errcls;google/muril-base-cased=errcls;"
                   "xlm-roberta-base=errcls-demo;xlm-roberta-base=frj-errcls-demo"),
}
KERNEL_SETS = {                   # extra placeholder values per kernel (see lmp_experiments.py)
    "lmp-muril-frj": {"__SEEDS__": "42 43 44 45 46", "__TAG__": "-5s"},
    "lmp-xlmr-5seeds": {"__SEEDS__": "42 43 44 45 46", "__TAG__": "-5s"},
    "lmp-errcls": {"__SEEDS__": "42 43 44 45 46"},
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


def source_commit() -> str:
    """The commit the kernel clones: the current checkout's HEAD, which must be clean and on GitHub,
    so a run always uses the code you are looking at (not whatever main happens to contain)."""
    if run("git", "status", "--porcelain", "--untracked-files=no", capture=True).stdout.strip():
        sys.exit("commit your changes first: the kernel clones the code from GitHub at HEAD")
    sha = run("git", "rev-parse", "HEAD", capture=True).stdout.strip()
    remote = run("git", "branch", "-r", "--contains", sha, capture=True).stdout.strip()
    if not remote:
        sys.exit(f"HEAD {sha[:7]} is not on GitHub yet: git push first")
    return sha


ONLY: list[str] = []              # --only <slug> restricts push/collect to some kernels
FAILURES: list[str] = []          # problems found by collect()


def push():
    b64 = ROOT / "modeling" / "kaggle" / "_splits.b64"
    b64.write_text(run(PY, "modeling/kaggle/pack_splits.py", capture=True).stdout, encoding="utf-8")
    sha = source_commit()
    print(f"kernel code: commit {sha[:7]}; splits bundle {b64.stat().st_size // 1024} KB")
    for slug, todo in KERNELS.items():
        if ONLY and slug not in ONLY:
            continue
        for attempt in range(48):                     # wait up to ~4 h for a free GPU session
            out = run(PY, "modeling/kaggle/kaggle_client.py", "push", "--user", KAGGLE_USER, "--slug", slug,
                      "--script", "modeling/kaggle/lmp_experiments.py", "--set", f"__COMMIT__={sha}",
                      "--set", f"__TODO__={todo}", "--set", f"__EXTRA__={TRAIN_FLAGS}", "--set-file", f"__SPLITS_B64__={b64}",
                      *[a for k, v in KERNEL_SETS.get(slug, {}).items() for a in ("--set", f"{k}={v}")],
                      capture=True, check=False)
            text = (out.stdout or "") + (out.stderr or "")
            print(text)
            if "session count" in text:
                print(f"{time.strftime('%H:%M')} no free Kaggle GPU session; retrying in 5 min", flush=True)
                time.sleep(300)
                continue
            if out.returncode != 0 or '"hasError": true' in text or "HTTP " in text:
                sys.exit(f"push of {slug} failed (see the message above)")
            break


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
    unknown: dict[str, int] = {}
    deadline = time.time() + max_hours * 3600
    while pending and time.time() < deadline:
        for slug in sorted(pending):
            st = status(slug)
            unknown[slug] = unknown.get(slug, 0) + 1 if st == "unknown" else 0
            if unknown[slug] >= 3:
                FAILURES.append(f"{slug}: kernel not found on Kaggle (was the push successful?)")
                pending.discard(slug)
                continue
            print(f"{time.strftime('%H:%M')} {slug}: {st}", flush=True)
            if st in ("complete", "error", "cancelAcknowledged"):
                log = LOGS / f"{slug}.log"
                run(PY, "modeling/kaggle/kaggle_client.py", "log", "--user", KAGGLE_USER, "--slug", slug,
                    "--out", log)
                text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
                failed = [l for l in text.splitlines() if l.startswith("FAILED:")]
                if st != "complete" or failed or "RUNS_TGZ_B64_BEGIN" not in text:
                    FAILURES.append(f"{slug}: status {st}, {len(failed)} failed jobs" +
                                    "".join("\n    " + l for l in failed[:10]))
                if "RUNS_TGZ_B64_BEGIN" in text:
                    run(PY, "modeling/kaggle/kaggle_client.py", "unpack", "--log", log, "--dest", "modeling")
                pending.discard(slug)
        if pending:
            time.sleep(poll_min * 60)
    if pending:
        FAILURES.append("still running: " + ", ".join(sorted(pending)))
    if FAILURES:
        sys.exit("collect finished with problems (results may be incomplete):\n  " + "\n  ".join(FAILURES))


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
            if run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", paper, check=False).returncode:
                sys.exit("paper build failed (tables are written; see the output above)")
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
