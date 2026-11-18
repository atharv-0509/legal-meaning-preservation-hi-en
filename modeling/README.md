# Modelling and experiments

Everything here reads `data/splits/` (from `src/split.py`) and writes predictions to
`modeling/runs/<system>/<split>/preds_*.jsonl`. `evaluate.py` recomputes every metric from those files,
so models, baselines and the LLM judge are evaluated identically.

| Script | Purpose |
|---|---|
| `train.py` | JUDGEBERT-style cross-encoder regression (`original [SEP] simplification` → score), MSE |
| `baselines.py` | ROUGE-L, BLEU (Devanagari-aware), LaBSE cosine, multilingual BERTScore; naive and train-calibrated mapping to 1–10 |
| `llm_judge.py` | LLM given the human rubric; returns bracket + error counts, scored with `src/rubric.py` |
| `evaluate.py` | Pearson, Spearman, RMSE, MAE, over-scoring %, decision macro-F1; by language / act / variant / error type; sanity checks; human ceiling → `reports/results.md` |
| `error_analysis.py` | ≥ 15 cases for E5 → `reports/error_analysis_<system>.md/.csv` (analysis column left for the team) |
| `predict.py` | score new pairs with a saved model; `--demo` launches a Gradio demo |
| `prepare_frjudge.py` | convert the released FrJUDGE splits so `train.py` can be checked against the paper |
| `run_experiments.sh` | E1–E5 for one backbone |

## Setup on Colab (T4)

`data/` is git-ignored, so copy the splits in yourself (e.g. zip `data/splits` and upload it, or mount Drive):

```bash
git clone <this repo> && cd legal-lmp-dataset
pip install -r requirements.txt -r modeling/requirements.txt
unzip /content/splits.zip -d data/          # -> data/splits/random_s42/...
python tests/test_modeling.py               # quick check: trains a tiny offline model
bash modeling/run_experiments.sh xlm-roberta-base
```

Confirm each backbone's exact Hugging Face id before the main runs (candidates: `xlm-roberta-base`,
`google/muril-base-cased`, `ai4bharat/IndicBERTv2-MLM-only`) and record it in the paper.

## Experiments

| ID | What | How |
|---|---|---|
| E1 | baselines vs. LMP model | `train.py` (± `--da`) on `random_s42..46`; `baselines.py`; `llm_judge.py` |
| E2 | English vs. Hindi; zero-shot transfer | per-language rows in `results.md`; `train.py --train-langs en --test-langs hi` and the reverse |
| E3 | new legal domain | `train.py --split-dir data/splits/ood_rti_to_cpa` (and `ood_cpa_to_rti`), 5 model seeds |
| E4 | sanity checks | holdout identical / unrelated pairs scored by every run (pass: ≥ 9.9 / ≤ 1.1) |
| E5 | qualitative errors | `error_analysis.py --system <best system>` |

## First check: reproduce FrJUDGE

Before the Indian-law runs, check the training code on the paper's data (Pearson 0.74 ± 0.02 / RMSE 1.72 without
DA). Commands are in the docstring of `prepare_frjudge.py`. Use `--patience 0` there: the released JUDGEBERT
script trains for 100 epochs and keeps the best dev-loss checkpoint (its early-stopping callback is commented out),
while the paper text says patience 5. Our default for the main runs is `--patience 5`.

## Choices to state in the paper

- Model selection on **human dev pairs** (`--dev-set human`), even when training with DA. `--dev-set da` mirrors the paper.
- Predictions clipped to [1, 10] (unrelated label = 1). For FrJUDGE use `--clip-min 0`.
- Decisions on continuous scores: ≥ 7 Preserved, ≥ 2 Partially Preserved, < 2 Not Preserved.
- Baselines are shown both naive (raw score in [0, 1] → [1, 10]) and calibrated (linear fit on the split's human
  training pairs). Pearson and Spearman are the same for both.
- Over-scoring rate = share of test pairs where prediction > human label (paper Table 6).
- The LLM judge should be a different model from the simplifier; record the exact model id.
