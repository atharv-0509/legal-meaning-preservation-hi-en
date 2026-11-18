#!/usr/bin/env bash
# All experiments E1-E5 in one go (Colab T4: roughly a few hours for one backbone; run sections
# separately if the session times out). Run from the repo root after src/split.py.
#   bash modeling/run_experiments.sh xlm-roberta-base
set -euo pipefail
MODEL=${1:-xlm-roberta-base}            # also: google/muril-base-cased, ai4bharat/IndicBERTv2-MLM-only
NAME=$(basename "$MODEL")
SEEDS="42 43 44 45 46"
FP16=$(python -c "import torch; print('--fp16' if torch.cuda.is_available() else '')")

# E1 + E4: random clause-grouped splits, with and without DA
for s in $SEEDS; do
  python modeling/train.py --split-dir data/splits/random_s$s --model "$MODEL" --seed $s $FP16
  python modeling/train.py --split-dir data/splits/random_s$s --model "$MODEL" --seed $s --da $FP16
done

# E2: language transfer (zero-shot), DA on
for s in $SEEDS; do
  python modeling/train.py --split-dir data/splits/random_s$s --model "$MODEL" --seed $s --da \
      --train-langs en --test-langs hi $FP16
  python modeling/train.py --split-dir data/splits/random_s$s --model "$MODEL" --seed $s --da \
      --train-langs hi --test-langs en $FP16
done

# E3: out-of-domain (train on one act, test on the other), DA on, 5 model seeds
for split in ood_rti_to_cpa ood_cpa_to_rti; do
  for s in $SEEDS; do
    python modeling/train.py --split-dir data/splits/$split --model "$MODEL" --seed $s --da $FP16
  done
done

# Baselines (E1). LaBSE / BERTScore need: pip install -r modeling/requirements.txt
python modeling/baselines.py --metrics rougeL bleu labse bertscore
# LLM judge (needs LLM_API_KEY / LLM_BASE_URL):
#   python modeling/llm_judge.py --model <exact-model-id>

python modeling/evaluate.py
python modeling/error_analysis.py --system "${NAME}-da" --n 20       # E5
