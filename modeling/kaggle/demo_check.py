"""Kaggle check of the demo checkpoint: load `demo_model/` from the output of kernel lmp-e23-fixed
(mounted with --kernel-source atharvarora05/lmp-e23-fixed) through modeling/predict.py, score the test
pairs of random_s42 and compare with the Pearson that run recorded (0.479). A match shows the saved
checkpoint and the demo code path work; the score is the demo model's, not a new result.

    python modeling/kaggle/kaggle_client.py push --user atharvarora05 --slug lmp-demo-check \
        --title "LMP demo check" --script modeling/kaggle/demo_check.py --cpu \
        --kernel-source atharvarora05/lmp-e23-fixed --set __COMMIT__=$(git rev-parse HEAD)
"""
import glob
import json
import os
import subprocess
import sys

REPO = "https://github.com/atharv-0509/legal-meaning-preservation-hi-en"
COMMIT = "__COMMIT__"
R = "/kaggle/working/lmp"
subprocess.run(f"git clone -q {REPO} {R} && cd {R} && git checkout -q {COMMIT} && git log --oneline -1",
               shell=True, check=True)
hits = glob.glob("/kaggle/input/**/demo_model/model.safetensors", recursive=True)
print("checkpoint:", hits)
if not hits:
    sys.exit("demo_model not found under /kaggle/input")
model_dir = os.path.dirname(hits[0])
sys.path[:0] = [f"{R}/modeling", f"{R}/src"]
from predict import LMPScorer          # noqa: E402
from common import pearson            # noqa: E402

rows = [json.loads(l) for l in open(f"{R}/data/splits/random_s42/test.jsonl", encoding="utf-8")]
scorer = LMPScorer(model_dir)
out = scorer.score([r["original"] for r in rows], [r["simplification"] for r in rows])
p = pearson([r["label"] for r in rows], [o["lmp_score"] for o in out])
rec = json.load(open(f"{R}/modeling/runs/xlm-roberta-base-frjudge-demo/random_s42/metrics.json"))
print(f"DEMO_CHECK n={len(rows)} pearson_predict={p:.3f} pearson_recorded={rec['test']['overall']['pearson']:.3f}")
for r, o in list(zip(rows, out))[:5]:
    print(json.dumps({"pair_id": r["pair_id"], "label": r["label"], **o}, ensure_ascii=False))
dec = {}
for o in out:
    dec[o["decision"]] = dec.get(o["decision"], 0) + 1
print("DECISIONS", dec)
