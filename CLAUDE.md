# CLAUDE.md — Legal Meaning Preservation (English & Hindi)

College NLP course project: **CSET 346 Natural Language Processing, Bennett University, project PID-08**,
instructor **Dr. Surabhi Solanki**. We extend **JUDGEBERT** (EMNLP 2025) from French insurance text to
**English + Hindi Indian legal text**. The goal is a model that reads an original legal sentence and its
simplified version and predicts a **Legal Meaning Preservation (LMP) score, 1–10**, that agrees with human
legal judgement.

Team: [names / roll numbers]. The project should also work as a resume piece and, ideally, a paper.

---

## 1. Current status (update this section as work moves)

As of 18 Nov 2026:
- [x] Project chosen (PID-08) and Milestone 1 presented on 14 Oct 2026 (10-slide deck: problem, related work, gaps, feasibility, objectives, method, techniques, experiments + timeline).
- [x] Dataset pipeline (`legal-lmp-dataset/`) written and tested end to end on **synthetic** text (`tests/`).
  - 18 Nov 2026: the earlier code was not available in the cloud workspace, so the pipeline was rebuilt from this spec. The parser is unit-tested on synthetic page text (`tests/fixtures.py`), and the pdftotext route was checked once on Chromium-rendered EN/HI PDFs of those pages (clean units, Hindi "करे गा ।" repaired). The OCR route is untested (no tesseract in that environment), and nothing has been run on the real India Code PDFs yet. Step 2b now ends with `select_clauses.py --finalize`. The rubric lives in `src/rubric.py`. Identical provisions are deduplicated at selection and excluded from the holdouts.
- [x] (3 of 4; CPA HI missing) Download the 4 source PDFs into `data/raw/` (see §5). India Code blocks scripted downloads, so a person must download them in a browser.
- [x] Run `extract.py` on the real acts and tune the parser to their formatting.
- [x] (agent-written, disclosed) Choose the LLM used for simplifications and record its exact name.
- [ ] Pilot annotation round (20 shared pairs) → update guidelines → main round.
- [x] Training / evaluation code written (`modeling/`, see §8). Checked only on synthetic data with a tiny offline model; next check: reproduce FrJUDGE (`modeling/prepare_frjudge.py`).
- [x] FrJUDGE reproduction (week 1 check of `train.py`): released-code setting 0.707 ± 0.042 / RMSE 1.79 over 10 seeds on Kaggle (paper 0.74 / 1.72); see `reports/frjudge_repro.md`.
  - 19 Nov 2026, after the tokenizer fix, CPU, camembertv2-base, no DA, seed 42, patience 5 (best epoch 11): test Pearson 0.617, Spearman 0.551, RMSE 1.979, MAE 1.645 (paper: 0.74 ± 0.02 / 1.72 over 10 seeds). One seed only.
  - A 100-epoch keep-best run (released-code setting) reached dev MSE 1.72 at epoch 21 vs 2.24 with patience 5; it was stopped at epoch 47 with no test score. Next: all 10 seeds with `--patience 0` (Colab or Kaggle; `modeling/kaggle/`).
  - (resolved 19 Nov) Logs of running kernels are visible on the kernel's web page, not via the API. `lmp-frjudge-smoke` ran the pre-fix commit and was cancelled; `lmp-frjudge-reproduction` (commit f356b1c) produced the numbers above. The API has no cancel: use kaggle.com → kernel → versions → … → Cancel.
- [x] IEEE paper and final slides (`paper/out/`, built by `paper/build.ps1` from `paper/content.py` + `reports/tables/*.tsv`). [x] Demo checkpoint (`kaggle_client.py fetch ... --prefix demo_model/` → `modeling/checkpoints/demo_model`).
  - 19 Nov 2026 (evening): Codex hostile review fixed (`reviews/codex_review.md`): clean E2/E3 rerun, declared principal system, variant-lookup diagnostic, honest wording; paper/slides rewritten to the new numbers.
  - 18 Nov 2026: `paper/paper_draft.md` drafted (structure, dataset/method text from the design; every result is [TBD]; references to verify). Demo: `modeling/predict.py --demo` (Gradio).
  - `train.py` was checked with real PyTorch on a tiny offline BERT (dev MSE falls 39 → 6.5 in 40 epochs). Hugging Face was blocked in that cloud environment, so no pretrained backbone and no FrJUDGE run yet: do both on Colab first.

- 19 Nov 2026: Windows Python 3.12.6 environment installed; full pytest baseline passes (33 passed, 0 failed, 0 skipped). Reset the fake-server request counter between tests; setup commands are in `modeling/README.md`.
- 19 Nov 2026: DoPT RTI EN/HI and Gazette CPA EN extracted; 78 provisional review rows generated; 38 tests pass. Hindi OCR and amendment review remain blocked; CPA HI missing. See `paper/source_provenance.md`; no human review or finalization claimed.
- 19 Nov 2026 (later, deadline run; branch `agent/real-extraction`):
  - PDFs: 3 of 4 in `data/raw/` (India Code was down; official DoPT/Gazette copies; `sources.json` has `pdf_url`). **`cpa_hi.pdf` still missing** → CPA is EN-only, E2 uses RTI.
  - Hindi RTI re-extracted with Tesseract 5.4 + tessdata_best `hin` (devanagari 0.993, bad-matra 0, no U+FFFD); `extract.repair_ocr_numbering` restores OCR-dropped "1" in section/sub-section numbers.
  - Clause review done by rules + agent spot-check (`src/agent_review.py`, **disclosed, not human**): 78 final clauses (RTI 38, 35 with HI; CPA 40).
  - Simplifications written by an LLM agent (`src/agent_simplify.py`, model recorded per row); perturb/sanity/build_pairs → **338 pairs**.
  - Labels: two **disclosed LLM annotators** (Claude Opus 5.5 ×2; annotator A also wrote the simplifications, so not blind in practice). α(interval) 0.610; inter-LLM Pearson 0.723 (not a ceiling). The 30-pair human validation workbook (`data/annotation/pilot/`) is **not yet scored**.
  - Results (`reports/tables/*.tsv`, kernels `lmp-experiments` v3, `lmp-transfer`, `lmp-e23-fixed`; runbook `run_all.py`): principal system XLM-R FrJUDGE→ours+DA **0.576 ± 0.102** (EN 0.675, HI 0.308); from-scratch XLM-R+DA 0.228 ± 0.288; calibrated LaBSE 0.101; variant-mean lookup (answer key, diagnostic) 0.831. E2 (35 bilingual RTI clauses) inconclusive (≈0); E3 CPA→RTI 0.388, RTI→CPA 0.119 (DA from training act only). Training: lr 2e-5, batch 8, 30 epochs, no early stopping.
  - FrJUDGE reproduction (`reports/frjudge_repro.md`): released-code setting 0.707 ± 0.042 vs paper 0.74.
  - Open: score the human validation pilot; get the Hindi CPA PDF; push branches to GitHub; demo needs a saved checkpoint.

- 19 Nov 2026 (14:30 UTC): collected Kaggle `lmp-e23-fixed` (corrected E2 on RTI-bilingual splits, E3 without target-act DA partners, demo checkpoint). **E2 matched RTI: EN 0.165, HI −0.041 (transfer model); E3 CPA→RTI 0.388, RTI→CPA 0.119.** The old 0.675/0.308 were E1 runs split by language, confounded by act. Paper, slides, HANDOVER rebuilt and corrected; E5 now uses in-domain predictions (transferred model: reversals mean 4.0 in domain, still up to 10.0; 7.3 across acts). Slides now render **bold**/*italic* markup. PDF exported with LibreOffice here; re-export with Word via `paper/build.ps1`.

- 19 Nov 2026 (evening): generalisation follow-up (`reports/generalization_summary.md`): **MuRIL + FrJUDGE + DA** 0.577 ± 0.068 over 5 seeds, best on Hindi (0.466), matched RTI (EN 0.269 / HI 0.182) and RTI→CPA (0.251); a fresh XLM-R FrJUDGE pre-training scored 0.691 (vs 0.873) and its transfer fell to 0.486 (DA) / 0.166 (no DA): the pre-training is unstable. MuRIL demo checkpoint (kernel `lmp-muril-demo`, test 0.682). Legal-error type classification (`reports/error_classification.md`): without augmentation trained classifiers lose to the rules (0.362 vs 0.509); with training-clause augmentation (`--augment 3 --augment-originals`) **MuRIL reaches macro-F1 0.789 ± 0.101**, best on every class; rule cues as input do not help. Demo classifier: kernel `lmp-errcls-demo`. Demo app `modeling/app.py`. Paper not yet updated with these (decision pending).

- 19 Nov 2026 (night): paper + slides updated with the MuRIL follow-up (Table IX) and error-type classification (Table X); wide paper tables now fit the IEEE column. **Hindi CPA**: the team supplied the Hindi text of the Consumer Protection *Bill*, 2019 (Bill No. 144, as introduced; not the enacted Act; provenance in `sources.json`). New backend `extract.py --backend ocr-bill` (Tesseract psm 3 + TSV, margin notes and line numbers removed, sections in sequence, logged द्व/द्ध conjunct repairs, `-l hin` only) gives 107/107 sections; 228 of 229 EN units have a HI key, median HI/EN length 0.96, no Latin junk. Still needed before use: EN-referenced number repair (~48 units lost a digit 1) and Hindi-reader review (e.g. s90(1)(a) HI lacks the negation of EN 'does not result'). **Not used in the corpus, splits or results yet.**

- 20 Nov 2026: final pre-presentation run. 53 tests pass; every table regenerates identically from the run files (`results.md` now also lists the follow-up runs). Demo app redesigned; MuRIL demo models re-fetched and verified (test Pearson 0.682 on random_s42). Demo slide shows a real app output (`paper/figures/demo_ui.png`); presenter checklist, demo script and Q&A in `paper/PRESENTATION_GUIDE.md`.

When you (Claude) finish a step, tick it here and add one line saying what changed.

19 Nov 2026 decision: the deadline version uses disclosed LLM annotations, not human labels
(see §4/§7). This does not meet the brief's human-judgement requirement; the 30-pair human
validation set is built but not yet scored.

---

## 2. The assignment brief (what the grader checks)

- Extend JUDGEBERT beyond French insurance: **English + one Indian language** (we chose Hindi), at least one legal domain.
- **≥ 300 original–simplified pairs** with **human LMP judgements on a 1–10 scale**, with the scoring procedure documented.
- Compare **≥ 2 generic semantic-similarity baselines** with a **JUDGEBERT-inspired transformer regression model**.
- At least **one generalisation experiment**: language, legal domain, context, or another legal transformation task.
- **Sanity checks**: identical pairs and clearly unrelated pairs.
- **≥ 15 qualitative error cases**: omission, hallucination, contradiction, obligation/permission, conditions, exceptions, scope, dates, numbers, entities.
- Metrics: **Pearson and RMSE**, plus MAE / Spearman (and F1 if we add a legal-error classifier). Report results separately by language and domain.
- Output per pair: LMP score 1–10, a decision (**Preserved / Partially Preserved / Not Preserved**), optionally an error type and a short explanation.
- Must be a clear **extension** of the paper, not just a reproduction.
- Deliverables: **source code on GitHub**, **research paper (IEEE style, Word + PDF)**, **presentation slides**.

Required experiments from the brief, and our names for them:

| ID | Experiment |
|---|---|
| E1 | Generic semantic-similarity baselines vs. JUDGEBERT-style LMP model |
| E2 | English vs. Hindi (plus zero-shot English → Hindi transfer) |
| E3 | Generalisation to a new legal domain: train on one act, test on the other |
| E4 | Identical / unrelated sanity checks |
| E5 | Qualitative error analysis, ≥ 15 legally difficult examples |

---

## 3. Reference paper: facts to rely on

Beauchemin, Albert-Rochette, Khoury & Déziel, "JUDGEBERT: Assessing Legal Meaning Preservation Between
Sentences", EMNLP 2025, pp. 92–118. https://aclanthology.org/2025.emnlp-main.5.pdf ·
Code and data: https://github.com/GRAAL-Research/JUDGEBERT (data CC-BY-NC-SA 4.0).

**Dataset (FrJUDGE):**
- 297 French sentence blocks from Quebec property-damage insurance forms.
- Simplified zero-shot by `gpt-4-turbo-2024-04-09` (temperature 1.0, top_p 0.9, max 100 new tokens), using the Kew et al. (2023) prompt translated into French.
- Selection: 1–5 sentences, no boilerplate, hard to read.
- Annotated by 5 law students. Final label = **mean** of the five LMP scores.

**Rubric** (we reuse it unchanged):
1. Pick a bracket: Accurate 7–10, Imprecise 2–6, Off-track 1.
2. Subtract 1 per error from the bracket maximum, never below 1.
3. Error types: **omission, hallucination, consistency issue, confusion**.

**Agreement:** Krippendorff's α on LMP was only **0.10**. Annotators split into a lenient group and a strict group.

**Model:**
- `almanach/camembertv2-base` with a regression head; the sentence pair is concatenated with [SEP].
- lr 5e-5, batch 16, up to 100 epochs, patience 5, linear decay.
- In the released `few_shot_training.py` the `EarlyStoppingCallback(patience=5)` is commented out: it trains 100 epochs and keeps the best dev-loss checkpoint (`load_best_model_at_end`). Pairs are tokenised as `tokenizer(original, simplification, truncation=True)`.
- Released split files are `{original, simplification, label}` JSONL (train 186 / dev 21 / test 90; with DA 560 / 63 / 268).
- 10 runs with seeds 42–51, 60/10/30 split.

**Data augmentation (DA):**
- 594 extra pairs: identical pairs labelled 10 and unrelated pairs labelled 0.
- Unrelated pairs come from Quebec legal texts with ROUGE-1/2/L < 0.25 and BLEU < 25.

**Results (Pearson / RMSE):**

| Setting | Metric | Pearson | RMSE |
|---|---|---|---|
| No DA | JUDGEBERT | 0.74 ± 0.02 | 1.72 |
| No DA | BERTScore | 0.46 | |
| No DA | LENS | 0.38 | |
| No DA | Coverage | 0.19 | |
| No DA | MeaningBERT | 0.17 | |
| No DA | SBERT | 0.13 | |
| No DA | SBERT-multi | 0.06 | |
| No DA | QuestEval | −0.05 | |
| With DA | JUDGEBERT-DA | 0.97 | 1.01 |

- With DA, JUDGEBERT-DA is the only metric that passes both sanity checks.
- BERTScore and MeaningBERT **over-score** humans on 82% of test pairs; JUDGEBERT on 0%.

**Weaknesses we exploit (our contribution):**
1. French only, one domain → English + Hindi, two domains.
2. Small dataset (297 pairs).
3. Weak agreement (α = 0.10) → pilot round, calibrated guidelines, report α and a human ceiling.
4. No out-of-domain test → E3.
5. The 0.97 is measured on a test set that includes trivial identical/unrelated pairs → we report human-annotated pairs only.
6. Their splits are pair-level, so a test original can appear in training as an identical DA pair → our splits are clause-grouped.

Their repo is useful as reference: `article_src/src/` (training, `dataset_tools.py`), `datastore/`
(FrJUDGE splits), `annotation_tool/` (Prodigy). Reproducing their FrJUDGE number is a good first check of
our training code.

---

## 4. Our design decisions (state these in the paper)

- **Sources**: two central acts with **official** English and Hindi texts, one per domain:
  - **Right to Information Act, 2005** (`rti`, public information) — https://www.indiacode.nic.in/handle/123456789/2065
  - **Consumer Protection Act, 2019** (`cpa`, consumer law) — https://www.indiacode.nic.in/handle/123456789/15256

  Because the Hindi is the official translation, every clause exists in both languages, which makes E2 fair. The two acts give E3. Sources are configured in `sources.json`.
- **Clause selection**:
  - 1–5 sentences, 15–90 English words, Flesch reading ease ≤ 50.
  - No boilerplate sections (short title, definitions, rule-making powers, repeal…).
  - ≤ 3 clauses per section.
  - Weighted toward clauses with exceptions, overrides, conditions and time limits.
  - Default 30 per act, oversampled ×1.3 to allow for the manual review drop.
- **Three simplification variants per clause and language**:
  - `normal`: the paper's zero-shot prompt, translated.
  - `aggressive`: "explain to a 12-year-old in ≤ 2 sentences"; tends to drop conditions, which gives the low scores FrJUDGE lacked.
  - `perturbed`: a `normal` output with ONE rule-based legal error (obligation↔permission, negation, number, exception drop, scope). Error types are balanced. Annotators score these **blind**; the known error type is a labelled diagnostic set for E5.
- **Scale**: ~60 clauses × 2 languages × 3 variants ≈ **360 pairs**.
- **Annotation**:
  - **19 Nov 2026 override for the deadline:** two disclosed LLM annotators, Claude Opus 5.5 and GPT-6 Astra, using separate blinded workbooks (`llm_claude_opus55`, `llm_gpt6_astra`). These are planned roles; record actual runtime provenance when executed. Generator overlap must be disclosed; a generator's existing context is not blind.
  - Blinded Excel workbook per annotator, items in a shuffled order, identified only by an opaque `pair_uid`.
  - Scores use the same rubric as the paper and are computed in the sheet.
  - A separate 30-pair human validation workbook is planned; absent human scores must be reported as missing.
  - Two LLM annotators per main pair; report their agreement as LLM-annotator agreement, not human agreement.
- **Labels**: mean LMP across the two LLM annotators. This deviates from the brief's human-judgement requirement because of time constraints. Also kept: `label_std`, raw `scores`, majority `main_change`.
- **Unrelated-pair label = 1** (the floor of our 1–10 scale). The paper used 0; `--unrelated-label 0` reproduces it.
- **Splits are clause-grouped**: a clause's English and Hindi pairs, all variants and its DA pairs stay in one split. `split.py` asserts this.
- **Test sets contain main annotated pairs only** (disclosed LLM labels for the deadline version). Sanity checks run on separate holdout sets built from provisions never used elsewhere.
- **Splits**: random 60/10/30 by clause over 5 seeds (42–46), plus OOD `rti→cpa` and `cpa→rti`.

---

## 5. Repository: `legal-lmp-dataset/`

```
sources.json                 acts, domains, PDF paths
requirements.txt
data/raw/README.md           which PDFs to download, exact names
guidelines/annotation_guidelines.md   rubric, error types, conventions, change log
src/common.py                JSONL I/O, normalisation, Devanagari-aware tokeniser, ROUGE/BLEU, is_unrelated, Pearson/Spearman
src/rubric.py                BRACKETS, BRACKET_MAX, ERROR_COLS, MAIN_CHANGES, lmp_score(), decision(): single source of truth
src/extract.py               PDF -> sub-section units (pdftotext or Tesseract OCR)
src/select_clauses.py        EN-HI alignment, filters, dedup, weighted sampling, review CSV with auto_flags; --finalize applies the review
src/simplify.py              LLM simplifications (OpenAI-compatible API), resumable
src/perturb.py               rule-based legal-error injection, EN + HI
src/sanity.py                identical/unrelated DA pairs + holdout sets
src/build_pairs.py           pairs.jsonl + blinded per-annotator .xlsx (+ pilot)
src/agreement.py             read workbooks, Krippendorff α, human ceiling, aggregate labels, adjudication list
src/split.py                 clause-grouped random + OOD splits
tests/test_units.py          parser, Hindi handling, perturbation rules (synthetic strings)
tests/test_pipeline.py       every step end to end: synthetic units, fake LLM, simulated annotators
tests/test_modeling.py       baselines, LLM judge (fake server), evaluate, error analysis, train.py on a tiny offline BERT
tests/fixtures.py            SYNTHETIC fixtures only (never copy into data/)
modeling/                    see §8
```

### Pipeline

| # | Command | Output |
|---|---|---|
| 0 | Download `rti_en.pdf`, `rti_hi.pdf`, `cpa_en.pdf`, `cpa_hi.pdf` into `data/raw/` (by hand, from the India Code pages above; use the act's official PDF and its Hindi version) | |
| 1 | `python src/extract.py [--act rti --lang hi --backend ocr]` | `data/interim/<act>_<lang>_units.jsonl` |
| 2 | `python src/select_clauses.py --per-act 30` | `data/processed/clauses.jsonl`, `clauses_review.csv` |
| 2b | Humans review `clauses_review.csv` and set `keep=0` on misaligned, garbled or fragmentary rows (small OCR fixes in `text_en`/`text_hi` are allowed and recorded in `review_edits`), then `python src/select_clauses.py --finalize --per-act 30` | `clauses_final.jsonl` (later steps read only this) |
| 3 | `LLM_API_KEY=… [LLM_BASE_URL=…] python src/simplify.py --model <name>` (trial first: `--limit 10`; preview: `--dry-run`) | `simplifications.jsonl` |
| 4 | `python src/perturb.py` | `perturbations.jsonl` |
| 5 | `python src/sanity.py [--unrelated-label 1]` | `augment_pairs.jsonl`, `holdout_identical.jsonl`, `holdout_unrelated.jsonl` |
| 6 | `python src/build_pairs.py --annotators A B C [--per-pair 3] --pilot 20` | `pairs.jsonl`, `annotation/<name>.xlsx`, `annotation/pilot/` |
| 7 | `python src/agreement.py [--pilot]` | `labeled_pairs.jsonl`, `annotations.jsonl`, `reports/agreement*.md`, `reports/adjudicate*.csv` |
| 8 | `python src/split.py --seeds 42 43 44 45 46` | `data/splits/random_s<seed>/`, `ood_<A>_to_<B>/`, holdout copies |

Run the tests after any change: `python tests/test_units.py && python tests/test_pipeline.py && python tests/test_modeling.py`.

### Data schemas

- **Units**: `act_id, lang, section, subsection, key ("s7_1"), heading, text, n_words, n_sents`. EN and HI rows of the same provision share `key`.
- **`clauses.jsonl`** / **`clauses_final.jsonl`**: `clause_id ("rti-s7_1"), act_id, domain, section, subsection, key, heading_en/hi, text_en/hi, n_words_en/hi, n_sents_en, reading_ease_en, markers_en/hi, weight, auto_flags, sample_rank, source` (+ `review_note`, `review_edits` after finalize).
- **`simplifications.jsonl`**: `sim_id, clause_id, act_id, lang, variant, original, simplification, raw_output, model, served_model, prompt_id, temperature, top_p, max_tokens, seed, finish_reason, usage, timestamp`.
- **`perturbations.jsonl`**: `sim_id, base_sim_id, clause_id, act_id, lang, variant="perturbed", original, simplification, error_type, change, span, model, prompt_id`.
- **`pairs.jsonl`** (the answer key; annotators never see it): `pair_id ("<clause_id>|<lang>|<variant>"), pair_uid (sha1, 10 hex), clause_id, act_id, domain, lang, variant, original, simplification, error_type, change, model, base_sim_id`.
- **`labeled_pairs.jsonl`**: the `pairs.jsonl` fields plus `label` (mean), `label_std, scores, n_annotators, main_change, simplicity, mean_<error>`.
- **Split files**: `pair_id, clause_id, act_id, lang, variant, original, simplification, label`.
  - `{train,dev,test}.jsonl` hold human pairs only.
  - `{train,dev}_da.jsonl` add the DA pairs of those clauses.

### Workbook

- **Sheets**: `Instructions` and `Annotate`.
- **Input columns** (yellow):
  - `simplicity`
  - `bracket`: "Accurate (7-10)", "Imprecise (2-6)" or "Off-track (1)"
  - `omissions`, `hallucinations`, `inconsistencies`, `confusions` (0–9)
  - `main_change`
  - `comment`, `minutes`
- **Computed columns**: `lmp_score` and `check`.
- A hidden `meta` sheet records annotator, round and creation date (nothing that reveals the variant).
- `agreement.py` **recomputes** the score from the bracket and error counts, so the spreadsheet program used doesn't matter. `ERROR_COLS` and `BRACKET_MAX` live only in `src/rubric.py`; if the rubric changes, also update the formula in `build_pairs.write_workbook` and the guidelines change log.

---

## 6. Gotchas we have already hit (do not re-learn these)

- **`rouge_score` drops all non-ASCII text**, so every Hindi pair would look "unrelated". Use `common.rouge_n / rouge_l / bleu / is_unrelated`, which tokenise Devanagari, including matras, correctly.
- **`textstat` needs NLTK's cmudict** (a network download). `select_clauses.reading_ease` is our own Flesch implementation. Keep it.
- **Hindi PDF text layers** are often scanned, use legacy fonts, or come out in visual glyph order. `extract.py` reports a "bad-matra" ratio and tells you to use `--backend ocr`.
  - OCR needs `tesseract-ocr`, `poppler-utils` and the **tessdata_best** `hin.traineddata`; the fast model misreads legal words.
  - OCR text **must** go through the human review in step 2b. Use the `auto_flags` column (Latin letters inside Hindi, numbers that differ between EN and HI).
- **Hindi spacing artefacts** such as "करे गा", spaces before matras, `|` for `।` and `--` for `—` are fixed by `extract.fix_hindi_spacing`. Zero-width joiners are stripped in `normalize_text`.
- **Sub-section parsing**: "(3)" after "sub-section", "उपधारा", "section" or "धारा" is a cross-reference, not a new sub-section; `split_subsections` handles this. Amendment markers like `1[...]` and `2***` and footnotes at the page bottom are stripped in `clean_pages`.
- **RTI was amended (2019, 2023).** If the English and Hindi PDFs are different versions, some sections (e.g. 8(1)(j), 13, 16) differ. Drop those clauses at review rather than "fixing" text.
- **Hindi verb perturbations**:
  - Shall→may maps करेगा → कर सकेगा, देगा → दे सकेगा and जाएगा → जा सकेगा.
  - Must→may maps करना होगा → करने की छूट है.
  - May→shall maps लगा सकता है → लगाएगा.
  - Rules only fire at clause ends, so they don't touch words like उपयोगी. Add a unit test for any new rule.
- **India Code blocks scripted fetches** (robots disallowed). Don't try to download from there in code; ask a human.
- On Windows, open CSVs written with `utf-8-sig`, or Excel garbles the Hindi.
- **Acts repeat wording** (standard provisos, "as may be prescribed" sections). Two provisions with identical text would leak across clause-grouped splits, so `select_clauses` drops duplicates and `sanity` excludes from the holdouts any provision whose text equals a selected clause. `check_disjoint` also checks at the text level.
- **Perturbation "as may be prescribed"**: `may` in this idiom is not a permission; modality and negation rules skip it (`EN_PERM_SKIP_*`).
- **Simplification length caps** differ from the paper (100 tokens): defaults are 200 (EN) / 500 (HI) because clauses go up to 90 words and Devanagari costs more tokens. Truncated outputs are reported (`finish_reason=length`). State this in the paper.
- **transformers 5.x loads `almanach/camembertv2-base` as a character-level tokenizer** (`AutoTokenizer` → byte-level `RobertaTokenizer` without merges). Pairs became ~650 single-character tokens, were cut at 256, and FrJUDGE training collapsed to predicting the label mean (train MSE ≈ label variance 5.3, test Pearson ≈ −0.25). `modeling/lmp_data.load_tokenizer` detects this and falls back to the checkpoint's `tokenizer.json`; always load tokenizers through it. Check any new backbone the same way.
- **Gradient clipping**: the HF `Trainer` used by JUDGEBERT clips to norm 1.0 by default; `train.py --max-grad-norm 1.0` (default) matches it.
- **Kaggle GPU runs**: `modeling/kaggle/kaggle_client.py` pushes a script kernel (T4, internet on) that clones this repo at a pinned commit; results come back through the kernel log (`log` then `unpack`). Kaggle derives the kernel slug from the title. Account: `atharvarora05`. The credential is held by the cloud environment's proxy, not in any file.
- **The `normal` prompt** (`bless_en_v1`) is the BLESS (Kew et al., 2023) simplification prompt as we recall it; diff it against the paper before the main run. A Hindi speaker must check `bless_hi_v1` and `kid12_hi_v1`.

---

## 7. Rules for working in this repo

- **Never invent legal text, labels, statistics or results.** Synthetic sentences exist only as test fixtures in `tests/` and must never enter `data/`. If a number is not computed from our data or taken from the paper, write `[TBD]`.
- **19 Nov 2026 annotation decision:** actual LLM rubric judgements are allowed only with explicit LLM provenance, never described as human scores. Annotators must not read `pairs.jsonl`, `perturbations.jsonl`, or each other's workbooks. Disclose generator/annotator overlap; omit a same-model LLM-judge comparison. All prose and reports must distinguish planned annotations from completed work and LLM agreement from human validation.
- **Never let annotators see `pairs.jsonl`**, variant names or error types. Workbooks stay blinded.
- **Keep splits clause-grouped.** Any new split code must call `check_disjoint`, and DA pairs must follow their clause.
- **Headline correlations identify their reference labels explicitly**: disclosed LLM-labelled test pairs for the deadline version; human validation separately if available. Sanity checks are reported separately and never mixed into headline test metrics.
- **Record provenance**: which PDF version (date or amendment), which LLM (exact model string), and the prompt id for every simplification. `simplify.py` already writes model, prompt id, temperature, top_p and a timestamp.
- **Any rubric or guideline change** goes in the change log of `annotation_guidelines.md`, with the date and reason.
- Source PDFs, `.env` and API keys stay out of git (`.gitignore`).
- Python 3.10+, standard library + `requirements.txt`. Prefer small scripts with argparse and JSONL in and out, matching the existing style.
- After code changes, run both test files before saying something works.

---

## 8. Modelling (code written; see `modeling/README.md`)

`modeling/` reads `data/splits/` and writes `modeling/runs/<system>/<split>/preds_*.jsonl`; `evaluate.py` recomputes all
metrics from those files into `reports/results.md`. Scripts: `train.py`, `baselines.py`, `llm_judge.py`, `evaluate.py`,
`error_analysis.py`, `predict.py` (+ Gradio `--demo`), `prepare_frjudge.py`, `run_experiments.sh`.
Implementation choices: model selection on the human dev set by default (`--dev-set da` mirrors the paper); fixed splits
(OOD, FrJUDGE) get an `_s<seed>` suffix per model seed so `evaluate.py` aggregates them; baselines reported naive and
train-calibrated.

**Main model:** a cross-encoder regression (JUDGEBERT setup).
- Input is `original [SEP] simplification`; output is a score 1–10. Regression head, MSE loss.
- Hyperparameters as in the paper (lr 5e-5, batch 16, early stopping, patience 5, linear decay).
- Run on 5 clause-grouped seeds, with and without DA.
- Candidate backbones (confirm the exact checkpoint names on Hugging Face before use):
  - MuRIL `google/muril-base-cased`
  - IndicBERT v2 `ai4bharat/IndicBERTv2-MLM-only`
  - XLM-R `xlm-roberta-base`
- Decision mapping for the brief: ≥ 7 Preserved, 2–6 Partially Preserved, 1 Not Preserved (the paper's brackets). Report the thresholds used on the continuous predictions.

**Baselines** (≥ 2 required):
- Multilingual BERTScore F1.
- LaBSE cosine similarity (`sentence-transformers/LaBSE`).
- An LLM-as-judge given the same rubric as the humans. This is the most interesting comparison.
- Optionally ROUGE/BLEU using our tokeniser.
- Normalise every baseline's output to the 1–10 range before computing RMSE.

**Reporting:**
- Pearson, Spearman, RMSE and MAE as mean ± std over seeds.
- The **over-scoring rate** (% of predictions above the human label), as in the paper's Table 6.
- Results split by language, act and variant.
- Correlation with humans compared against the **human ceiling** from `agreement.py`.
- Sanity checks: % of identical pairs scored ≥ 9.9 and % of unrelated pairs scored ≤ 1.1 (or our equivalent thresholds, stated).
- E2: train on EN and test on HI zero-shot, and the reverse.
- E3: the OOD splits.
- E5: at least 15 cases grouped by `error_type` and `main_change`.

Compute: base-size encoders on a few hundred pairs fit a free Colab T4.

---

## 9. Timeline (relative, from mid-October)

| Week | Work |
|---|---|
| 1 | Lock scope; reproduce JUDGEBERT on FrJUDGE |
| 2–3 | Collect clauses, generate simplifications, pilot annotation |
| 3–5 | Full annotation; baselines and LLM judge |
| 5–6 | Train models; run E1–E4 |
| 7–8 | Error analysis, IEEE paper, demo |

Adjust to the real submission date: [TBD].
