# Legal LMP dataset (English / Hindi Indian statutes) — dataset card

Release: 19 November 2026 (branch `handover`). Files: `data/processed/pairs.jsonl` (answer key),
`data/processed/labeled_pairs.jsonl` (labels), `data/annotation/` (workbooks), `data/splits/`.

## Contents
- **Sources:** RTI Act 2005 English and Hindi (DoPT, amended editions; section 8(1) wording differs
  between them) and the Consumer Protection Act 2019 English (Gazette of India, Act 35 of 2019). Exact
  URLs and version notes: `sources.json`; extraction notes: `paper/source_provenance.md`. **The CPA Hindi
  text was unavailable**, so CPA is English-only.
- **Hindi text** was recovered with Tesseract 5.4 OCR (tessdata_best `hin`); OCR-dropped digit "1" in
  section/sub-section numbers was repaired from the numbering sequence (`src/extract.py`). **No Hindi
  reader has verified the text against the PDFs.**
- **Clauses:** 78 (RTI 38, of which 35 bilingual; CPA 40), selected by `src/select_clauses.py` and
  reviewed by rules plus an automated agent spot-check (`src/agent_review.py`) — **not by a human**.
- **Simplifications:** 226 (`normal` BLESS prompt and `aggressive` "explain to a 12-year-old"), written by
  a Claude Opus 5.5 agent (`src/agent_simplify.py`; model recorded per row; no sampling API, so
  `max_tokens` is null and `finish_reason` is not an observation).
- **Perturbations:** 112 rule-based edits of normal simplifications (`src/perturb.py`: modality, negation,
  number, exception drop, scope). The base simplification is not verified error-free, so a perturbed pair
  carries one *additional* injected error, not necessarily exactly one error.
- **Pairs:** 338 (EN 233, HI 105; normal 113 / aggressive 113 / perturbed 112).

## Labels — disclosed LLM judgements, not human judgements
- Each pair was scored on JUDGEBERT's rubric by **two LLM annotators, both Claude Opus 5.5 instances**
  (`llm_claude_opus55_a`, `llm_claude_opus55_b`), each in its own shuffled workbook with opaque ids. The
  label is their mean. Annotator **A also wrote the simplifications**, so it is not blind in practice;
  B saw only the items and knew the corpus design.
- Agreement (`reports/agreement.md`): Krippendorff's α 0.610 (interval), 0.503 (brackets); Pearson
  between the two annotators 0.723 (**inter-LLM agreement — not a ceiling**; each annotator correlates
  0.904 / 0.949 with the mean label). Mean scores differ (A 8.115, B 6.935). 68 large disagreements are
  listed in `reports/adjudicate.csv` and **were not adjudicated**.
- Mean label by variant: normal 9.956, aggressive 7.593, perturbed 5.004 — the corpus strongly encodes its
  construction (a variant-mean lookup that uses the answer key already correlates highly with the labels).
- **This does not meet the brief's requirement of ≥ 300 pairs with human judgements.** A 30-pair blind
  human validation set (`data/annotation/human/`, one sheet per author) compares human scores with these
  labels via `src/human_validation.py`; results are reported only once scored.

## Splits
- `random_s42/43/44`: 60/10/30 by clause, all variants, both languages and DA pairs of a clause together.
- `bilingual_s42/43/44`: only the 35 RTI clauses present in both languages (E2; identical EN/HI clause sets).
- `ood_cpa_to_rti`, `ood_rti_to_cpa`: train on one act, test on the other; DA partners restricted to the
  training act (E3).
- Holdouts (E4): 50 EN + 3 HI identical pairs, 17 EN + 0 HI unrelated pairs.

## Intended use and limitations
An exploratory course-project resource for evaluating legal simplification, not a validated legal tool.
LLM labels cannot substitute for agreement with human legal judgement. Statute texts are public government
documents; FrJUDGE (CC-BY-NC-SA 4.0) is used for a reproduction check and as transfer pre-training data and
is not redistributed. Keep sanity pairs out of headline metrics and split by source clause.
