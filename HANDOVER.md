# Handover — Legal Meaning Preservation (EN/HI), 19 Nov 2026

Branch **`handover`** contains everything: code, data, labels, splits, model predictions, results, paper and
slides. It merges `agent/real-extraction` (data + modelling), `agent/paper-slides` (paper + slides) and `main`.
Open a pull request `handover → main` and merge it to continue from `main`.

Read `CLAUDE.md` first (project spec, rules, §1 status). The full day-long coordination log between the
agents is in `docs/agents/agent-chat-history.md`.

## 1. What is done

| Item | Where | Result |
|---|---|---|
| Source texts | `data/raw/` (PDFs **not** in git; URLs in `sources.json` → `pdf_url`) | RTI EN+HI (DoPT), CPA EN (Gazette). **CPA HI missing** (India Code was down) |
| Hindi OCR | `data/ocr_cache/`, `src/extract.py` | Tesseract 5.4 + tessdata_best `hin`; OCR-dropped digit "1" repaired (`repair_ocr_numbering`) |
| Clauses | `data/processed/clauses_final.jsonl` | 78 clauses (RTI 38, 35 with HI; CPA 40). Review by rules + agent (`src/agent_review.py`), **not human** |
| Simplifications | `data/processed/simplifications.jsonl` | 226, written by an LLM agent (model in every row; `src/agent_simplify.py`) |
| Pairs | `data/processed/pairs.jsonl` | **338** (normal / aggressive / perturbed with 112 injected legal errors) |
| Labels | `data/annotation/*.xlsx`, `data/processed/labeled_pairs.jsonl` | Two **disclosed LLM annotators** (Claude Opus 5.5 ×2). α = 0.610; ceiling 0.723 (`reports/agreement.md`) |
| Splits | `data/splits/` | random_s42/43/44 (clause-grouped) + ood_rti_to_cpa / ood_cpa_to_rti + holdouts |
| Experiments | `modeling/runs/`, `reports/tables/*.tsv`, `reports/results.md` | see §2 |
| FrJUDGE check | `reports/frjudge_repro.md` (+ `.log`) | 0.707 ± 0.042 vs paper 0.74 → training code validated |
| Paper + slides | `paper/out/LMP_paper_IEEE.{docx,pdf}`, `paper/out/LMP_slides.pptx` | 11-page IEEE paper, 16 slides, authors filled in |
| Tests | `tests/` | 46 passing (`python -m pytest -q`) |

## 2. Headline results (Pearson on annotated test pairs, mean ± std over 3 seeds)

| System | E1 overall | EN | HI | CPA→RTI | RTI→CPA |
|---|---|---|---|---|---|
| **XLM-R pre-trained on FrJUDGE → ours** | **0.586 ± 0.098** | 0.675 | 0.308 | 0.384 | 0.319 |
| XLM-R from scratch + DA | 0.228 ± 0.288 | 0.297 | 0.010 | 0.144 | 0.040 |
| LaBSE (best generic baseline) | 0.101 | | | | |
| LLM-annotator ceiling | 0.723 | | | | |

Zero-shot EN↔HI transfer stays weak (≈ 0.07). Training settings that work: lr 2e-5, batch 8, 30 epochs,
**no early stopping**, keep best dev checkpoint (early stopping on the ~35-pair dev set collapsed every run).

## 3. How to run things

```powershell
python -m venv .venv; .venv\Scripts\pip install -r requirements.txt -r modeling\requirements.txt
.venv\Scripts\python -m pytest -q
# full results pipeline (labels → splits → Kaggle GPU → tables → paper):
.venv\Scripts\python run_all.py prepare          # agreement + splits
.venv\Scripts\python run_all.py push             # Kaggle kernels (needs KAGGLE_API_TOKEN or a KGAT_ KAGGLE_KEY)
.venv\Scripts\python run_all.py collect          # waits, downloads, unpacks into modeling/runs
.venv\Scripts\python run_all.py report           # reports/tables/*.tsv + rebuilds paper/out (needs MS Word for the PDF)
.venv\Scripts\python run_all.py push --only lmp-transfer   # just the FrJUDGE-transfer kernel
powershell -File paper\build.ps1                 # paper + slides only
```
- Kaggle account `atharvarora05`; kernels `lmp-experiments` (v3 = final no-transfer runs), `lmp-transfer`
  (final transfer runs), `lmp-frjudge-reproduction`. Max 2 concurrent GPU sessions per account; running
  kernels show logs only on the web page; cancel via kaggle.com → kernel → versions → … → Cancel.
- Hindi OCR needs Tesseract + tessdata_best `hin.traineddata` (pass `--tessdata-dir`). Only needed if you
  re-extract; the OCR text is cached in `data/ocr_cache/`.
- To download PDFs again: use `sources.json` → `pdf_url` (India Code handle pages are in `url`).

## 4. What is left (priority order)

1. **Human validation (most important for the grade).** The brief requires human LMP judgements. Have
   2–3 team members score the 30-pair workbook in `data/annotation/pilot/` (rubric:
   `guidelines/annotation_guidelines.md`), then report LLM-vs-human correlation in the paper. Ideally
   score more pairs and re-label.
2. **Merge `handover` into `main`** on GitHub.
3. **Hindi CPA PDF** from India Code when it is reachable → `data/raw/cpa_hi.pdf`, re-run extract → select
   → simplify (CPA HI) → annotate → `run_all.py all`. Makes E2 cover both acts.
4. **Demo**: `modeling/predict.py --demo` needs a saved checkpoint. Re-run the transfer model with
   `--save-model` (Kaggle output or Colab) and load it.
5. Improve zero-shot EN↔HI transfer (e.g. MuRIL/IndicBERT with FrJUDGE pre-training, more seeds).
6. Slides: check timing/visuals for the presentation; paper: final read-through.

## 5. Honesty notes that must stay in the paper
Labels are LLM-produced (not human); LLM-2 also wrote the simplifications (not blind in practice);
clause review was by an agent; CPA is English-only; training hyper-parameters differ from JUDGEBERT and why;
no LLM-judge baseline (would be circular with LLM labels).
