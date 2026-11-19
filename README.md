# Legal Meaning Preservation for English and Hindi Indian legal text

CSET 346 NLP course project (Bennett University, PID-08). We extend **JUDGEBERT** (Beauchemin et al., EMNLP 2025)
from French insurance text to **English and Hindi Indian central acts**. Given an original legal provision and a
simplified version of it, the model predicts a **Legal Meaning Preservation (LMP) score from 1 to 10**,
and a decision: Preserved, Partially Preserved or Not Preserved.

What this project adds to the paper:

**Status (19 Nov 2026):** 338 pairs from the RTI Act (English + Hindi) and the Consumer Protection Act
(English), labelled by **two disclosed LLM annotators** (both Claude Opus 5.5; one also wrote the
simplifications) — not by humans, so the brief's human-judgement requirement is not met. A 30-pair human
validation set is in `data/annotation/human/`. Start with [HANDOVER.md](HANDOVER.md) and the
[dataset card](DATASET_CARD.md); the paper and slides are in `paper/out/`.

| JUDGEBERT (FrJUDGE) | This project |
|---|---|
| French, one domain (insurance) | RTI EN+HI (35 bilingual clauses); CPA EN only because its Hindi source is unavailable |
| 297 pairs, one simplification style | 338 pairs: `normal`, `aggressive` and `perturbed` (one injected legal error) variants |
| α = 0.10 (five law students) | α = 0.610 between two LLM annotators (not human); 30-pair human validation set |
| pair-level splits (a test original can reappear as a DA pair in training) | clause-grouped splits, enforced by `check_disjoint` |
| 0.97 Pearson includes trivial DA test pairs | headline metrics on disclosed LLM-labelled test pairs; sanity checks reported separately on disjoint holdouts |
| no out-of-domain test | E2 EN vs HI + zero-shot on bilingual RTI clauses, E3 cross-act (RTI↔CPA), FrJUDGE→ours transfer |

## Layout

```
sources.json               the two acts, their India Code pages and PDF paths
data/raw/README.md         which PDFs to download by hand (India Code blocks scripted downloads)
guidelines/                annotation guidelines (rubric, Indian-law conventions, change log)
src/                       dataset pipeline (standard library + openpyxl + numpy)
modeling/                  cross-encoder training, baselines, LLM judge, evaluation, error analysis
tests/                     unit + end-to-end tests on synthetic fixtures
```

## Dataset pipeline

```bash
pip install -r requirements.txt          # poppler-utils for pdftotext; tesseract-ocr only for the OCR route
```

| # | Command | Output |
|---|---|---|
| 0 | Download the 4 PDFs into `data/raw/` (see `data/raw/README.md`) | |
| 1 | `python src/extract.py` (Hindi scans: `--act rti --lang hi --backend ocr`) | `data/interim/<act>_<lang>_units.jsonl` |
| 2 | `python src/select_clauses.py --per-act 30` | `clauses.jsonl`, `clauses_review.csv` |
| 2b | Review the CSV (`keep=0` for bad rows), then `python src/select_clauses.py --finalize --per-act 30` | `clauses_final.jsonl` |
| 3 | `LLM_API_KEY=… python src/simplify.py --model <exact id>` (`--dry-run`, `--limit 10` first) | `simplifications.jsonl` |
| 4 | `python src/perturb.py` | `perturbations.jsonl` |
| 5 | `python src/sanity.py` | DA pairs + holdouts |
| 6 | `python src/build_pairs.py --annotators A B C --per-pair 3 --pilot 20` | `pairs.jsonl` + blinded workbooks |
| 7 | `python src/agreement.py --pilot`, then after the main round `python src/agreement.py` | labels + `reports/agreement*.md` |
| 8 | `python src/split.py --seeds 42 43 44 45 46` | `data/splits/` |

## Modelling

See [`modeling/README.md`](modeling/README.md). In short:

```bash
pip install -r modeling/requirements.txt
bash modeling/run_experiments.sh xlm-roberta-base
```

## Tests

```bash
python tests/test_units.py && python tests/test_pipeline.py && python tests/test_modeling.py
```

The tests use synthetic sentences (`tests/fixtures.py`) that imitate the format of Indian acts. They are test
fixtures only and never enter `data/`.

## Reference

Beauchemin, Albert-Rochette, Khoury & Déziel. *JUDGEBERT: Assessing Legal Meaning Preservation Between Sentences.*
EMNLP 2025. https://aclanthology.org/2025.emnlp-main.5.pdf · https://github.com/GRAAL-Research/JUDGEBERT
