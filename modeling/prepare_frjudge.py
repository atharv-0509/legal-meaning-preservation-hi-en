"""Convert the released FrJUDGE splits into our split format, to check train.py against the paper
(JUDGEBERT no-DA Pearson 0.74 ± 0.02, RMSE 1.72; with DA 0.97 / 1.01 on the DA test set).

    git clone https://github.com/GRAAL-Research/JUDGEBERT /tmp/JUDGEBERT
    python modeling/prepare_frjudge.py --repo /tmp/JUDGEBERT        # -> data/splits_frjudge/frjudge/
    python modeling/train.py --split-dir data/splits_frjudge/frjudge --model almanach/camembertv2-base \
        --run-name frjudge-camembertv2 --clip-min 0 --patience 0 --seed 42          # no DA
    python modeling/train.py --split-dir data/splits_frjudge/frjudge --model almanach/camembertv2-base \
        --run-name frjudge-camembertv2-da --da --dev-set da --clip-min 0 --patience 0 --seed 42 \
        --extra-test test_da

FrJUDGE data is CC-BY-NC-SA 4.0; it is written under data/ (git-ignored) and must not be redistributed
with our dataset. Their DA test set is written as test_da.jsonl (the 0.97 number is on that set).
Kept outside data/splits/ so our own evaluate.py runs do not mix it with Indian-law results.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import read_jsonl, write_jsonl  # noqa: E402

FILES = {"train": "train_FrJUDGE", "dev": "dev_FrJUDGE", "test": "test_FrJUDGE",
         "train_da": "train_FrJUDGE_with_data_augmentation", "dev_da": "dev_FrJUDGE_with_data_augmentation",
         "test_da": "test_FrJUDGE_with_data_augmentation",
         "holdout_identical": "holdout_identical_FrJUDGE", "holdout_unrelated": "holdout_unrelated_FrJUDGE"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="path to a clone of GRAAL-Research/JUDGEBERT")
    ap.add_argument("--out", default=str(ROOT / "data" / "splits_frjudge" / "frjudge"))
    args = ap.parse_args(argv)
    src = Path(args.repo) / "datastore" / "training"
    out = Path(args.out)
    for ours, theirs in FILES.items():
        rows = read_jsonl(src / f"{theirs}.jsonl")
        if not rows:
            sys.exit(f"missing {src / theirs}.jsonl")
        conv = []
        for i, r in enumerate(rows):
            same = r["original"] == r["simplification"]
            variant = "human" if ours in ("train", "dev", "test") else ("da_identical" if same else "da_unrelated"
                                                                       if r["label"] == 0 else "human")
            conv.append({"pair_id": f"frjudge-{ours}-{i}", "clause_id": f"frjudge-{ours}-{i}", "act_id": "insurance",
                         "lang": "fr", "variant": variant, "original": r["original"],
                         "simplification": r["simplification"], "label": float(r["label"])})
        write_jsonl(out / f"{ours}.jsonl", conv)
        print(f"{ours}: {len(conv)}")
    print(f"wrote {out}. Note: FrJUDGE splits are pair-level; the paper's 10 runs vary only the model seed.")


if __name__ == "__main__":
    main()
