"""Kaggle GPU script: run experiments E1-E4 on OUR dataset and print a results bundle to the log.

Pushed as a Kaggle "script" kernel (GPU T4, internet on) with modeling/kaggle/kaggle_client.py:

    python modeling/kaggle/pack_splits.py > /tmp/splits.b64          # data/splits -> base64 tar.gz
    python modeling/kaggle/kaggle_client.py push --user <u> --slug lmp-experiments-xlmr \
        --script modeling/kaggle/lmp_experiments.py --set <COMMIT placeholder>=<sha on GitHub> \
        --set __MODEL__=xlm-roberta-base --set __PLAN__=full --set-file <SPLITS placeholder>=/tmp/splits.b64

Why the splits are embedded: the training code is on GitHub, but the generated dataset is git-ignored
(CLAUDE.md §7), so the kernel receives `data/splits/` inside the script itself. Labels in those splits are
the disclosed LLM-annotator labels (see DATASET_CARD.md).

Plans (seeds 42-44 for the deadline; the paper reports mean ± std over these):
  full   E1 random splits with and without DA; E2 EN->HI and HI->EN zero-shot (DA); E3 rti->cpa and
         cpa->rti (DA); then baselines (ROUGE-L, BLEU, LaBSE, BERTScore) on every split
  e1     E1 only (for a second backbone)
  smoke  one 2-epoch run (pipeline check)
"""
import base64
import io
import json
import os
import subprocess
import tarfile
import time

REPO = "https://github.com/atharv-0509/legal-meaning-preservation-hi-en"
COMMIT = "__COMMIT__"
# "backbone=plan" items separated by ";" run one after another in this single GPU session
# (Kaggle allows only 2 concurrent GPU sessions per account).
TODO = "__TODO__"
# extra train.py flags for every run (e.g. "--lr 2e-5 --batch-size 8 --patience 10"); see the paper for why
EXTRA = "__EXTRA__" if "__EXTRA__" != "__" + "EXTRA__" else ""
SPLITS_B64 = "__SPLITS_B64__"
W = "/kaggle/working"
R = f"{W}/lmp"
RUNS = f"{W}/runs"
# seeds and a run-name tag can be set per kernel (run_all.KERNEL_SETS); defaults keep the deadline runs
SEEDS = [int(x) for x in "__SEEDS__".split()] if "__SEEDS__" != "__" + "SEEDS__" else [42, 43, 44]
TAG = "__TAG__" if "__TAG__" != "__" + "TAG__" else ""   # e.g. "-5s": new runs sit beside the old ones


def sh(cmd, check=True):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True, check=check, executable="/bin/bash")


t0 = time.time()
sh(f"git clone -q {REPO} {R} && cd {R} && git checkout -q {COMMIT} && git log --oneline -1")
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(SPLITS_B64)), mode="r:gz") as tar:
    safe = [m for m in tar.getmembers() if m.isfile() and not m.name.startswith(("/", "..")) and ".." not in m.name]
    tar.extractall(R, members=safe)
print("splits:", sorted(os.listdir(f"{R}/data/splits")), flush=True)
sh("pip install -q bert-score sentence-transformers 2>&1 | tail -2", check=False)
sh("nvidia-smi --query-gpu=name,memory.total --format=csv && python -c \"import torch, transformers; "
   "print(torch.__version__, transformers.__version__, torch.cuda.is_available())\"")

S = f"{R}/data/splits"
FRJ = f"{W}/frjudge-pretrained"          # FrJUDGE-pretrained checkpoint (plans prefixed "frj-")
JUDGEBERT_COMMIT = "e096cdf"             # pinned upstream FrJUDGE data revision
DEMO = f"{W}/demo_model"                 # checkpoint saved by the "demo" plan (downloadable kernel output)
jobs = []
plans = [item.split("=", 1) for item in TODO.split(";") if item.strip()]
# plan names:  e1    E1 on random_s*, with and without DA
#              e23   E2 on bilingual_s* (RTI clauses present in both languages: all / EN->HI / HI->EN) and
#                    E3 on ood_* (DA partners restricted to the training act)
#              full  e1 + e23 (+ baselines)
#              demo  one no-DA run on random_s42 that saves its best checkpoint to /kaggle/working/demo_model
#              smoke 2-epoch pipeline check
#              frj-<plan>  the same, starting from the backbone first trained on FrJUDGE
for model, plan in plans:
    name = model.split("/")[-1]
    if plan.startswith("frj"):
        model, name, plan = FRJ, f"{name}-frjudge", (plan.split("-", 1)[1] if "-" in plan else "full")
    name += TAG
    if plan == "smoke":
        jobs.append((model, f"{S}/random_s42", name, "--epochs 2", 42))
        continue
    if plan == "demo":
        jobs.append((model, f"{S}/random_s42", f"{name}-demo", f"--save-model {DEMO}", 42))
        continue
    if plan in ("e1", "full"):
        for s in SEEDS:
            jobs.append((model, f"{S}/random_s{s}", name, "", s))
            jobs.append((model, f"{S}/random_s{s}", f"{name}-da", "--da", s))
    if plan in ("e23", "full"):
        for s in SEEDS:
            jobs.append((model, f"{S}/bilingual_s{s}", f"{name}-da", "--da", s))
            jobs.append((model, f"{S}/bilingual_s{s}", f"{name}-da", "--da --train-langs en --test-langs hi", s))
            jobs.append((model, f"{S}/bilingual_s{s}", f"{name}-da", "--da --train-langs hi --test-langs en", s))
        for ood in sorted(d for d in os.listdir(S) if d.startswith("ood_")):
            for s in SEEDS:
                jobs.append((model, f"{S}/{ood}", f"{name}-da", "--da", s))
    if plan not in ("e1", "e23", "full"):
        raise SystemExit(f"unknown plan {plan!r}")

if any(p.startswith("frj") for _, p in plans):
    base = next(m for m, p in plans if p.startswith("frj"))
    sh(f"git clone -q https://github.com/GRAAL-Research/JUDGEBERT {W}/JUDGEBERT && "
       f"cd {W}/JUDGEBERT && git checkout -q {JUDGEBERT_COMMIT} && git log --oneline -1")
    sh(f"cd {R} && python modeling/prepare_frjudge.py --repo {W}/JUDGEBERT --out {R}/data/splits_frjudge/frjudge")
    sh(f"set -o pipefail; cd {R} && python modeling/train.py --split-dir {R}/data/splits_frjudge/frjudge --model {base} "
       f"--run-name {base.split('/')[-1]}-frjudge-pretrain --seed 42 --fp16 {EXTRA} --da --dev-set da --clip-min 0 "
       f"--runs-dir {W}/runs_frj --save-model {FRJ} 2>&1 | grep -E 'TEST|Error|Traceback'")   # failure stops the kernel
    print(f"FrJUDGE pretraining done: {(time.time() - t0) / 60:.1f} min", flush=True)

# Kaggle gives two T4s: run two jobs at a time, one per GPU (train.py itself uses a single device).
import queue
import threading

FAILED: list = []
q = queue.Queue()
for i, job in enumerate(jobs, 1):
    q.put((i, job))


def worker(gpu: int):
    while True:
        try:
            i, (model, split, run, flags, seed) = q.get_nowait()
        except queue.Empty:
            return
        r = sh(f"set -o pipefail; cd {R} && CUDA_VISIBLE_DEVICES={gpu} python modeling/train.py --split-dir {split} --model {model} "
           f"--run-name {run} --seed {seed} --fp16 {EXTRA} {flags} --runs-dir {RUNS} 2>&1 | "
           f"grep -E 'TEST|early stop|Error|Traceback' | sed 's/^/[gpu{gpu} job{i}] /'", check=False)
        if r.returncode != 0:
            FAILED.append(f"job{i} {run} {os.path.basename(split)} {flags} seed {seed}")
        print(f"[{i}/{len(jobs)}] gpu{gpu} {run} {os.path.basename(split)} {flags} seed {seed}: "
              f"elapsed {(time.time() - t0) / 60:.1f} min", flush=True)


threads = [threading.Thread(target=worker, args=(g,)) for g in (0, 1)]
for t in threads:
    t.start()
for t in threads:
    t.join()

if any(p == "full" for _, p in plans):
    splits = " ".join(f"{S}/{d}" for d in sorted(os.listdir(S)) if d.startswith(("random_", "ood_")))
    sh(f"cd {R} && python modeling/baselines.py --metrics rougeL bleu labse bertscore --splits {splits} "
       f"--runs-dir {RUNS} 2>&1 | grep -v -i warn | tail -15", check=False)

# preds + metrics + config of every run (incl. holdout preds for E4), gzipped + base64 into the log
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for root, _, files in list(os.walk(RUNS)) + list(os.walk(f"{W}/runs_frj")):
        for f in files:
            if f.endswith((".json", ".jsonl")):
                tar.add(os.path.join(root, f), arcname=os.path.relpath(os.path.join(root, f), W))
b64 = base64.b64encode(buf.getvalue()).decode()
print(f"===== FAILED_JOBS {len(FAILED)} =====")
for f in FAILED:
    print("FAILED:", f)
print(f"===== RUNS_TGZ_B64_BEGIN {len(b64)} =====")
for i in range(0, len(b64), 10000):
    print(b64[i:i + 10000])
print("===== RUNS_TGZ_B64_END =====")
print(f"total {(time.time() - t0) / 60:.1f} min")
