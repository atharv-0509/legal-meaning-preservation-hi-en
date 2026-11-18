# CLAUDE.md — Legal Meaning Preservation (English & Hindi)

College NLP course project: **CSET 346 Natural Language Processing, Bennett University, project PID-08**,
instructor **Dr. Surabhi Solanki**. We extend **JUDGEBERT** (EMNLP 2025) from French insurance text to
**English + Hindi Indian legal text**. The goal is a model that reads an original legal sentence and its
simplified version and predicts a **Legal Meaning Preservation (LMP) score, 1–10**, that agrees with human
legal judgement.

Team: [names / roll numbers]. The project should also work as a resume piece and, ideally, a paper.

---

## 1. Current status (update this section as work moves)

As of 14 Oct 2026:
- [x] Project chosen (PID-08) and Milestone 1 presented on 14 Oct 2026 (10-slide deck: problem, related work, gaps, feasibility, objectives, method, techniques, experiments + timeline).
- [x] Dataset pipeline (`legal-lmp-dataset/`) written and tested end to end on **synthetic** text (`tests/`). Also checked on generated English and Hindi PDFs, including the OCR route.
- [ ] Download the 4 source PDFs into `data/raw/` (see §5). India Code blocks scripted downloads, so a person must download them in a browser.
- [ ] Run `extract.py` on the real acts and tune the parser to their formatting.
- [ ] Choose the LLM used for simplifications and record its exact name.
- [ ] Pilot annotation round (20 shared pairs) → update guidelines → main round.
- [ ] Training / evaluation code (not started; see §8).
- [ ] IEEE paper, final slides, demo.

When you (Claude) finish a step, tick it here and add one line saying what changed.

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
  - Blinded Excel workbook per annotator, items in a shuffled order, identified only by an opaque `pair_uid`.
  - Scores use the same rubric as the paper and are computed in the sheet.
  - 20-pair shared pilot round first (scores discarded).
  - 3 annotators per pair preferred (`--per-pair 2` if time is short).
- **Labels**: mean LMP across annotators, as in FrJUDGE. Also kept: `label_std`, raw `scores`, majority `main_change`.
- **Unrelated-pair label = 1** (the floor of our 1–10 scale). The paper used 0; `--unrelated-label 0` reproduces it.
- **Splits are clause-grouped**: a clause's English and Hindi pairs, all variants and its DA pairs stay in one split. `split.py` asserts this.
- **Test sets contain human-annotated pairs only.** Sanity checks run on separate holdout sets built from provisions never used elsewhere.
- **Splits**: random 60/10/30 by clause over 5 seeds (42–46), plus OOD `rti→cpa` and `cpa→rti`.

---

## 5. Repository: `legal-lmp-dataset/`

```
sources.json                 acts, domains, PDF paths
requirements.txt
data/raw/README.md           which PDFs to download, exact names
guidelines/annotation_guidelines.md   rubric, error types, conventions, change log
src/common.py                JSONL I/O, normalisation, Devanagari-aware tokeniser, ROUGE/BLEU, is_unrelated
src/extract.py               PDF -> sub-section units (pdftotext or Tesseract OCR)
src/select_clauses.py        EN-HI alignment, filters, weighted sampling, review CSV with auto_flags
src/simplify.py              LLM simplifications (OpenAI-compatible API), resumable
src/perturb.py               rule-based legal-error injection, EN + HI
src/sanity.py                identical/unrelated DA pairs + holdout sets
src/build_pairs.py           pairs.jsonl + blinded per-annotator .xlsx (+ pilot)
src/agreement.py             read workbooks, Krippendorff α, human ceiling, aggregate labels, adjudication list
src/split.py                 clause-grouped random + OOD splits
tests/test_units.py          parser, Hindi handling, perturbation rules (synthetic strings)
tests/test_pipeline.py       every step end to end: synthetic units, fake LLM, simulated annotators
```

### Pipeline

| # | Command | Output |
|---|---|---|
| 0 | Download `rti_en.pdf`, `rti_hi.pdf`, `cpa_en.pdf`, `cpa_hi.pdf` into `data/raw/` (by hand, from the India Code pages above; use the act's official PDF and its Hindi version) | |
| 1 | `python src/extract.py [--act rti --lang hi --backend ocr]` | `data/interim/<act>_<lang>_units.jsonl` |
| 2 | `python src/select_clauses.py --per-act 30` | `data/processed/clauses.jsonl`, `clauses_review.csv` |
| 2b | Humans review `clauses_review.csv` and set `keep=0` on misaligned, garbled or fragmentary rows | |
| 3 | `LLM_API_KEY=… [LLM_BASE_URL=…] python src/simplify.py --model <name>` (trial first: `--limit 10`; preview: `--dry-run`) | `simplifications.jsonl` |
| 4 | `python src/perturb.py` | `perturbations.jsonl` |
| 5 | `python src/sanity.py [--unrelated-label 1]` | `augment_pairs.jsonl`, `holdout_identical.jsonl`, `holdout_unrelated.jsonl` |
| 6 | `python src/build_pairs.py --annotators A B C [--per-pair 3] --pilot 20` | `pairs.jsonl`, `annotation/<name>.xlsx`, `annotation/pilot/` |
| 7 | `python src/agreement.py [--pilot]` | `labeled_pairs.jsonl`, `annotations.jsonl`, `reports/agreement*.md`, `reports/adjudicate*.csv` |
| 8 | `python src/split.py --seeds 42 43 44 45 46` | `data/splits/random_s<seed>/`, `ood_<A>_to_<B>/`, holdout copies |

Run the tests after any change: `python tests/test_units.py && python tests/test_pipeline.py`.

### Data schemas

- **Units**: `act_id, lang, section, subsection, key ("s7_1"), heading, text, n_words, n_sents`. EN and HI rows of the same provision share `key`.
- **`clauses.jsonl`**: `clause_id ("rti-s7_1"), act_id, domain, section, subsection, key, heading_en/hi, text_en/hi, n_words_en/hi, reading_ease_en, markers_en/hi, source`.
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
- `agreement.py` **recomputes** the score from the bracket and error counts, so the spreadsheet program used doesn't matter. Keep `ERROR_COLS` and `BRACKET_MAX` in sync if the rubric changes.

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

---

## 7. Rules for working in this repo

- **Never invent legal text, labels, statistics or results.** Synthetic sentences exist only as test fixtures in `tests/` and must never enter `data/`. If a number is not computed from our data or taken from the paper, write `[TBD]`.
- **Never let annotators see `pairs.jsonl`**, variant names or error types. Workbooks stay blinded.
- **Keep splits clause-grouped.** Any new split code must call `check_disjoint`, and DA pairs must follow their clause.
- **Headline correlations come from human-annotated test pairs only**; sanity checks are reported separately.
- **Record provenance**: which PDF version (date or amendment), which LLM (exact model string), and the prompt id for every simplification. `simplify.py` already writes model, prompt id, temperature, top_p and a timestamp.
- **Any rubric or guideline change** goes in the change log of `annotation_guidelines.md`, with the date and reason.
- Source PDFs, `.env` and API keys stay out of git (`.gitignore`).
- Python 3.10+, standard library + `requirements.txt`. Prefer small scripts with argparse and JSONL in and out, matching the existing style.
- After code changes, run both test files before saying something works.

---

## 8. Modelling plan (next phase; not built yet)

Put this in a separate `modeling/` folder that reads `data/splits/`.

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
