# Handover — Legal Meaning Preservation (EN/HI), 19 Nov 2026

Branch **`handover`** contains everything: code, data, labels, splits, model predictions, results, paper and
slides. It merges `agent/real-extraction` (data + modelling), `agent/paper-slides` (paper + slides) and `main`.
Open a pull request `handover → main` and merge it to continue from `main`.

Read `CLAUDE.md` first (project spec, rules, §1 status). The full day-long coordination log between the
agents is in `docs/agents/agent-chat-history.md`.

## 0. Set up on your own laptop (Windows, ~10 minutes)

1. **Get the code** (Python 3.10+ and Git required):
   ```powershell
   git clone -b handover https://github.com/atharv-0509/legal-meaning-preservation-hi-en
   cd legal-meaning-preservation-hi-en
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt -r modeling\requirements.txt -r paper\requirements-paper.txt
   .venv\Scripts\python -m pytest -q          # expect: 46 passed
   ```
   After the PR is merged you can clone `main` instead of `-b handover`.
2. **Start Claude (Claude Code) in that folder** and paste the prompt from
   `docs/agents/START_HERE_FOR_CLAUDE.md`. It tells Claude to read this file, `CLAUDE.md` and the agent log,
   summarise the state, and wait for your instructions.
3. **Only if you need them:**
   - *Kaggle GPU runs* (`run_all.py push`): create a token at kaggle.com → Settings → API → "Create New
     Token" and set it once, without echoing it:
     `$t = Read-Host "Kaggle token" -AsSecureString; [Environment]::SetEnvironmentVariable("KAGGLE_API_TOKEN", [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($t)), "User")`
     then open a new terminal. Never commit or paste the token into files or chats.
   - *Paper PDF*: `paper\build.ps1` exports the PDF through Microsoft Word; without Word you still get the
     `.docx` and `.pptx`.
   - *Re-extracting PDFs / Hindi OCR*: download the PDFs from `sources.json` → `pdf_url` into `data\raw\`
     (names `rti_en.pdf`, `rti_hi.pdf`, `cpa_en.pdf`); install Tesseract 5 and put `hin.traineddata` +
     `eng.traineddata` from github.com/tesseract-ocr/tessdata_best in a folder passed as `--tessdata-dir`.
     Not needed otherwise: the extracted and OCR text is already in `data\`.

## 1. What is done

| Item | Where | Result |
|---|---|---|
| Source texts | `data/raw/` (PDFs **not** in git; URLs in `sources.json` → `pdf_url`) | RTI EN+HI (DoPT), CPA EN (Gazette). **CPA HI missing** (India Code was down) |
| Hindi OCR | `data/ocr_cache/`, `src/extract.py` | Tesseract 5.4 + tessdata_best `hin`; OCR-dropped digit "1" repaired (`repair_ocr_numbering`) |
| Clauses | `data/processed/clauses_final.jsonl` | 78 clauses (RTI 38, 35 with HI; CPA 40). Review by rules + agent (`src/agent_review.py`), **not human** |
| Simplifications | `data/processed/simplifications.jsonl` | 226, written by an LLM agent (model in every row; `src/agent_simplify.py`) |
| Pairs | `data/processed/pairs.jsonl` | **338** (normal / aggressive / perturbed with 112 injected legal errors) |
| Labels | `data/annotation/*.xlsx`, `data/processed/labeled_pairs.jsonl` | Two **disclosed LLM annotators** (Claude Opus 5.5 ×2). α = 0.610; inter-LLM Pearson 0.723, not a ceiling (`reports/agreement.md`) |
| Splits | `data/splits/` | random_s42/43/44 (clause-grouped), bilingual_s42/43/44 (35 RTI clauses, E2), ood_rti_to_cpa / ood_cpa_to_rti (DA from training act only) + holdouts |
| Experiments | `modeling/runs/`, `reports/tables/*.tsv`, `reports/results.md` | see §2 |
| FrJUDGE check | `reports/frjudge_repro.md` (+ `.log`) | 0.707 ± 0.042 vs paper 0.74 → training code validated |
| Paper + slides | `paper/out/LMP_paper_IEEE.{docx,pdf}`, `paper/out/LMP_slides.pptx` | 12-page IEEE paper, 21 slides, authors filled in, no `[TBD]` left; rebuilt on Windows with Word |
| Tests | `tests/` | 47 passing (`python -m pytest -q`) |

## 2. Headline results (Pearson on annotated test pairs, mean ± std over 3 seeds)

| System | E1 overall | E2 EN (matched RTI) | E2 HI (matched RTI) | E3 CPA→RTI | E3 RTI→CPA |
|---|---|---|---|---|---|
| **XLM-R pre-trained on FrJUDGE → ours (DA)** | **0.576 ± 0.102** (no DA: **0.586 ± 0.098**) | 0.165 ± 0.063 | −0.041 ± 0.144 | 0.388 ± 0.021 | 0.119 ± 0.051 |
| XLM-R from scratch + DA | 0.228 ± 0.288 | −0.059 | −0.058 | 0.186 | 0.056 |
| LaBSE, calibrated (best generic baseline) | 0.101 | | | | |
| Variant-mean lookup (uses answer key; diagnostic) | 0.831 | | | | |

E2/E3 are from the corrected `lmp-e23-fixed` kernel (collected 19 Nov, 14:12 UTC): E2 trains and tests on the
35 RTI clauses present in both languages; E3 takes DA partners only from the training act. They replace the
earlier E2 (0.675 EN / 0.308 HI), which was the E1 runs split by language and is confounded by act (EN pools
CPA, where the model scores 0.669, vs RTI 0.485), and the earlier E3 (0.384 / 0.319), whose DA partners came
from the target act. **The transfer gain is real overall and on CPA, but is not shown for Hindi on matched
provisions.** The corrected E2/E3 runs start from a fresh FrJUDGE pre-training (test Pearson 0.849, `modeling/runs_frj/.../frjudge_s42_e23fixed`); the E1 transfer runs and the paper's 0.873 use the earlier one (`frjudge_s42`). E5 now uses in-domain (E1) predictions: the transferred model averages 4.0 on low-label
negation reversals in domain (7.6 from scratch) but still gives single reversals 10.0, and 7.3 across acts.
Zero-shot EN↔HI transfer stays at zero (0.035 / 0.131). Within-variant Pearson of the principal system: aggressive 0.487, perturbed 0.584. Demo checkpoint: `python modeling/kaggle/kaggle_client.py fetch --user atharvarora05 --slug lmp-e23-fixed --prefix demo_model/` → `modeling/checkpoints/demo_model` (git-ignored, ~1.1 GB). Training settings that work: lr 2e-5, batch 8, 30 epochs,
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
2. ~~Merge `handover` into `main`~~ — done 19 Nov (fast-forward); clone `main` from now on.
3. **Hindi CPA PDF** (retried 19 Nov: not obtainable from the cloud machine; see `sources.json` → `cpa.hi_source_attempts`). Fastest route: open WIPO Lex 23153 in a browser and download the Hindi PDF (a consolidation up to Act 33 of 2021: drop sections that differ from the 2019 English Gazette), or India Code → `data/raw/cpa_hi.pdf`, re-run extract → select
   → simplify (CPA HI) → annotate → `run_all.py all`. Makes E2 cover both acts.
4. **Demo** — recommended checkpoint (19 Nov evening): **MuRIL + FrJUDGE + DA**, kernel `lmp-muril-demo`, test Pearson
   0.682 on `random_s42` (vs 0.479 for the XLM-R one below). Fetch:
   `python modeling/kaggle/kaggle_client.py fetch --user atharvarora05 --slug lmp-muril-demo --prefix demo_model/ --dest modeling/checkpoints/muril`
   then `python modeling/app.py --model-dir modeling/checkpoints/muril/demo_model` (or download `demo_model/` from that
   kernel's Output tab into `modeling/checkpoints/muril/demo_model`). The app reads the backbone from config.json and
   shows the matching description and test Pearson.
   Older XLM-R checkpoint: in the output of Kaggle kernel `lmp-e23-fixed` (`demo_model/`: XLM-R pre-trained on
   FrJUDGE, fine-tuned on `random_s42`, no DA; ~1.1 GB, not in git). Fetch it (Kaggle token needed, see §0):
   `python modeling/kaggle/kaggle_client.py fetch --user atharvarora05 --slug lmp-e23-fixed --prefix demo_model/`
   → `modeling/checkpoints/demo_model`, or download `demo_model/` from that kernel's Output tab in a browser.
   Run: `python modeling/app.py --model-dir modeling/checkpoints/demo_model` (needs `pip install gradio`; `--share`
   for a public link). The app (`modeling/app.py`, 19 Nov) has held-out test examples with reference labels, a
   colour-coded score, a rule-based legal cue check (negation, shall/may, exceptions, numbers; labelled as
   heuristic, not the model), input validation, and an optional "Generate simplification" button when
   `LLM_API_KEY` + `LLM_MODEL` are set. `predict.py --demo` launches the same app.
   **Verified 19 Nov** by Kaggle kernel `lmp-demo-check` (`modeling/kaggle/demo_check.py`): loaded through
   `predict.py` it reproduces the run's test Pearson exactly (0.479 on the 96 `random_s42` test pairs).
4b. **Legal-error type (brief's optional output)** — `reports/error_classification.md`: rule baseline macro-F1
   0.509 ± 0.074 vs trained classifiers (MuRIL 0.362 ± 0.174, XLM-R 0.270, XLM-R+FrJUDGE 0.277; majority 0.111)
   over 5 clause-grouped seeds; targets are objective (injected error types). The app and `predict.py` use the
   rules (type + explanation); the trained classifier is optional (`--errcls-dir`) and not recommended at this data size.
   Generalisation follow-up (MuRIL, 5 seeds): `reports/generalization_summary.md`.
5. Improve zero-shot EN↔HI transfer (e.g. MuRIL/IndicBERT with FrJUDGE pre-training, more seeds).
6. Slides: check timing/visuals for the presentation; paper: final read-through.
7. **Verify a Hindi reader on the OCR'd clauses** (ready: `reports/ocr_spotcheck_hi.md` + `.csv`, 8 sampled clauses; DoPT blocks cloud machines, so do it from India). The corpus rests on OCR that no Hindi reader has
   checked; §5 of the paper says so, but a sample review would either remove that caveat or find a
   real problem. It is the cheapest remaining risk to retire.

## 5. Honesty notes that must stay in the paper
Labels are LLM-produced (not human); LLM-2 also wrote the simplifications (not blind in practice);
clause review was by an agent; CPA is English-only; training hyper-parameters differ from JUDGEBERT and why;
no LLM-judge baseline (would be circular with LLM labels).
