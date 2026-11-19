"""Kaggle GPU script: reproduce JUDGEBERT on the released FrJUDGE splits with our training code.

Pushed as a Kaggle "script" kernel (GPU T4, internet on) by modeling/kaggle/push_kernel.py. It clones this
repository at a pinned commit and the JUDGEBERT repository, converts the FrJUDGE splits, trains every
configuration below, scores our baselines, and prints a compact results bundle to the log (Kaggle output
files may not be downloadable from the machine that pushed the kernel).

Configurations (paper: no-DA Pearson 0.74 ± 0.02 / RMSE 1.72; DA 0.97 / 1.01 on the DA test set):
  cam-p5       camembertv2-base, no DA, patience 5 (paper text)
  cam-p0       camembertv2-base, no DA, 100 epochs, best dev loss (released code)
  cam-da-p0    camembertv2-base, DA, DA dev set, 100 epochs (released code); also scores test_da
  cam-da-p5    camembertv2-base, DA, DA dev set, patience 5; also scores test_da
  xlmr-p5      xlm-roberta-base, no DA, patience 5 (does a multilingual encoder match CamemBERT?)
"""
import base64
import io
import json
import os
import subprocess
import sys
import tarfile
import time

REPO = "https://github.com/atharv-0509/legal-meaning-preservation-hi-en"
COMMIT = os.environ.get("LMP_COMMIT", "__COMMIT__")
CONFIGS = os.environ.get("LMP_CONFIGS", "__CONFIGS__")
W = "/kaggle/working"
R = f"{W}/lmp"
RUNS = f"{W}/runs"


def sh(cmd, check=True):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True, check=check)


t0 = time.time()
sh(f"git clone -q {REPO} {R} && cd {R} && git checkout -q {COMMIT} && git log --oneline -1")
sh(f"git clone -q --depth 1 https://github.com/GRAAL-Research/JUDGEBERT {W}/JUDGEBERT && "
   f"cd {W}/JUDGEBERT && git log --oneline -1")
sh("pip install -q bert-score sentence-transformers 2>&1 | tail -2", check=False)
sh(f"cd {R} && python modeling/prepare_frjudge.py --repo {W}/JUDGEBERT --out {R}/data/splits_frjudge/frjudge")
sh("nvidia-smi --query-gpu=name,memory.total --format=csv && python -c \"import torch, transformers; "
   "print(torch.__version__, transformers.__version__, torch.cuda.is_available())\"")

SPLIT = f"{R}/data/splits_frjudge/frjudge"
CAM, XLMR = "almanach/camembertv2-base", "xlm-roberta-base"
ALL = {
    "cam-p5": (CAM, "--patience 5", range(42, 52)),
    "cam-p0": (CAM, "--patience 0", range(42, 52)),
    "cam-da-p0": (CAM, "--da --dev-set da --patience 0 --extra-test test_da", range(42, 52)),
    "cam-da-p5": (CAM, "--da --dev-set da --patience 5 --extra-test test_da", range(42, 52)),
    "xlmr-p5": (XLMR, "--patience 5", range(42, 47)),
    "smoke": (CAM, "--patience 5 --epochs 2", [42]),          # pipeline check only
}
wanted = [c for c in CONFIGS.split(",") if c in ALL] if CONFIGS not in ("all", "__CONFIGS__") \
    else [c for c in ALL if c != "smoke"]
for name in wanted:
    model, flags, seeds = ALL[name]
    for s in seeds:
        r = sh(f"cd {R} && python modeling/train.py --split-dir {SPLIT} --model {model} --run-name frjudge-{name} "
               f"--clip-min 0 --seed {s} --fp16 {flags} --runs-dir {RUNS} 2>&1 | grep -E 'TEST|early stop|Error|Traceback'",
               check=False)
        print(f"[{name} seed {s}] elapsed {(time.time() - t0) / 60:.1f} min", flush=True)

if CONFIGS in ("all", "__CONFIGS__") or "baselines" in CONFIGS:
    sh(f"cd {R} && python modeling/baselines.py --metrics rougeL bleu labse bertscore --splits {SPLIT} "
       f"--runs-dir {RUNS} 2>&1 | grep -v -i warn | tail -12", check=False)
sh(f"cd {R} && python modeling/evaluate.py --runs-dir {RUNS} --labeled /nonexistent --out {W}/results.md "
   f"--unrelated-max 1.0 > /dev/null", check=False)

# ---- compact summary: per system, mean ± std over seeds of test (and test_da) metrics
summary = {}
for system in sorted(os.listdir(RUNS)):
    for split in sorted(os.listdir(f"{RUNS}/{system}")):
        p = f"{RUNS}/{system}/{split}/metrics.json"
        if os.path.exists(p):
            m = json.load(open(p))
            cfg = f"{RUNS}/{system}/{split}/config.json"
            best = json.load(open(cfg)).get("best_epoch") if os.path.exists(cfg) else None
            summary.setdefault(system, []).append({
                "split": split, "best_epoch": best,
                **{f"test_{k}": m["test"]["overall"].get(k) for k in ("pearson", "spearman", "rmse", "mae", "over_rate")},
                **({f"test_da_{k}": m["test_da"]["overall"].get(k) for k in ("pearson", "rmse")} if "test_da" in m else {}),
                **{f"{h}_pass": m[h]["pass_rate"] for h in ("holdout_identical", "holdout_unrelated") if h in m},
                **{f"{h}_mean": m[h]["mean_pred"] for h in ("holdout_identical", "holdout_unrelated") if h in m},
            })
json.dump(summary, open(f"{W}/summary.json", "w"), indent=1)
print("\n===== RESULTS.MD =====")
print(open(f"{W}/results.md").read() if os.path.exists(f"{W}/results.md") else "(no results.md)")
print("===== SUMMARY_JSON_BEGIN =====")
print(json.dumps(summary))
print("===== SUMMARY_JSON_END =====")

# preds_test + metrics + config of every run, gzipped and base64-encoded (holdout preds left out for size)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for root, _, files in os.walk(RUNS):
        for f in files:
            if f in ("metrics.json", "config.json", "preds_test.jsonl", "preds_test_da.jsonl"):
                tar.add(os.path.join(root, f), arcname=os.path.relpath(os.path.join(root, f), W))
b64 = base64.b64encode(buf.getvalue()).decode()
print(f"===== RUNS_TGZ_B64_BEGIN {len(b64)} =====")
for i in range(0, len(b64), 10000):
    print(b64[i:i + 10000])
print("===== RUNS_TGZ_B64_END =====")
print(f"total {(time.time() - t0) / 60:.1f} min")
