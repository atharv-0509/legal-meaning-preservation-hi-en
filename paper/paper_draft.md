# Assessing Legal Meaning Preservation in English and Hindi Simplifications of Indian Statutes

*Draft for the IEEE-format paper (convert to the IEEE Word template for submission). Every number marked
[TBD] must come from our data or runs; nothing here is a result yet. Check every reference against
the original publication before submission.*

Authors: [names, roll numbers], Bennett University. Course: CSET 346 Natural Language Processing (PID-08),
instructor Dr. Surabhi Solanki.

---

## Abstract

Plain-language versions of statutes can make the law accessible, but a simplification that drops a
condition, turns an obligation into a permission or changes a time limit misleads the reader. JUDGEBERT
(Beauchemin et al., 2025) introduced a learned metric for *legal meaning preservation* (LMP) on French
insurance text. We extend this line of work to Indian law in two languages. We build a dataset of
[TBD: n] English and Hindi original–simplification pairs from the official parallel texts of the Right to
Information Act, 2005 and the Consumer Protection Act, 2019, with simplifications of three kinds
(standard LLM simplification, aggressive "explain to a 12-year-old" simplification, and simplifications
with one injected legal error), each scored by [TBD: k] annotators on JUDGEBERT's 1–10 rubric after a
calibration round. We train multilingual cross-encoders on clause-grouped splits and compare them with
generic similarity metrics and an LLM judge given the human rubric. [TBD: one-sentence headline result,
e.g. Pearson of the best model vs. best baseline and vs. the human ceiling.] We further report zero-shot
transfer between English and Hindi, transfer across the two acts, sanity checks on identical and unrelated
pairs, and a qualitative analysis of [TBD: ≥15] legally difficult cases.

## I. Introduction

- Motivation: access to justice in India; statutes are long, drafted in complex English, with official Hindi
  translations that are equally hard to read. LLMs can simplify, but errors with legal consequences
  (modality, exceptions, conditions, numbers, scope) are hard to detect automatically.
- Generic similarity metrics reward lexical or semantic overlap and do not track legal consequences:
  JUDGEBERT reports BERTScore at Pearson 0.46 and SBERT at 0.13 with human LMP judgements on FrJUDGE, against
  0.74 for the learned metric.
- Gaps we address (each maps to a contribution):
  1. JUDGEBERT covers French and one domain → we cover English and Hindi, two legal domains, with
     official parallel texts so that the language comparison is controlled.
  2. FrJUDGE contains one simplification style → we add aggressive simplifications and controlled,
     rule-injected legal errors (a labelled diagnostic set).
  3. Krippendorff's α on FrJUDGE LMP was 0.10 → we run a pilot calibration round and report α and a
     leave-one-out human ceiling.
  4. FrJUDGE splits are pair-level, and the 0.97 Pearson of JUDGEBERT-DA is measured on a test set
     that contains trivial identical/unrelated pairs → our splits are clause-grouped and headline numbers
     use human-annotated pairs only, with sanity checks reported separately on disjoint holdouts.
  5. No out-of-domain test → we train on one act and test on the other.
- Contributions: (i) the dataset and annotation protocol; (ii) a JUDGEBERT-style multilingual LMP model;
  (iii) a comparison with generic metrics and an LLM judge; (iv) cross-lingual, cross-domain and sanity
  experiments; (v) error analysis. Code: [TBD: GitHub URL].

## II. Related work

- **Simplification evaluation.** Meaning preservation is usually measured with BLEU/SARI-style overlap,
  BERTScore (Zhang et al., 2020), sentence-embedding similarity, QuestEval (Scialom et al., 2021), LENS
  (Maddela et al., 2023) or MeaningBERT (Beauchemin et al., 2023). BLESS (Kew et al., 2023) benchmarks
  LLM simplification with zero-shot prompts; we reuse its prompt.
- **Legal meaning preservation.** JUDGEBERT (Beauchemin et al., 2025): FrJUDGE (297 pairs, 5 law-student
  annotators, mean label), rubric with three brackets and four error types, CamemBERT-v2 cross-encoder,
  data augmentation with identical (10) and unrelated (0) pairs.
- **Indian legal NLP.** Legal language models and benchmarks for Indian law (e.g. InLegalBERT, Paul et al.,
  2023; IL-TUR, Joshi et al., 2024) focus on judgments and classification tasks rather than simplification
  quality.
- **Multilingual encoders for Indian languages.** XLM-R (Conneau et al., 2020), MuRIL (Khanuja et al.,
  2021), IndicBERT v2 (Doddapaneni et al., 2023), LaBSE (Feng et al., 2022).

## III. Dataset

### A. Sources

Two central acts with official English and Hindi texts from India Code: the Right to Information Act, 2005
(public information) and the Consumer Protection Act, 2019 (consumer law). Versions: [TBD: "as on" dates
from sources.json]. Because the Hindi text is the official translation, every selected provision exists in
both languages.

### B. Extraction and clause selection

PDFs are converted to sub-section units with `pdftotext` (OCR with Tesseract for Hindi where the text layer
is broken; [TBD: which files needed OCR]). English and Hindi units are aligned by section/sub-section
number. A clause is eligible if it has 1–5 sentences, 15–90 English words and Flesch reading ease ≤ 50, is
not boilerplate (short title, definitions, rule-making powers, repeal, savings…), and has no identical
duplicate elsewhere in the acts. At most three clauses are taken per section. Sampling is weighted toward
clauses with exceptions, overrides, conditions and time limits. We oversample by 1.3, review every
clause by hand (misaligned, garbled or fragmentary rows are dropped, [TBD: number dropped]) and keep
[TBD: 30] per act.

### C. Simplifications

For each clause and language:
- **normal**: zero-shot BLESS prompt (Hindi translation for Hindi), [TBD: exact model id], temperature 1.0,
  top-p 0.9 (as in JUDGEBERT), output cap 200 (EN) / 500 (HI) tokens ([TBD: number truncated]).
- **aggressive**: "Explain the following legal text to a 12-year-old in at most 2 sentences."
- **perturbed**: a normal simplification with exactly one rule-based legal error, balanced over five
  types: modality (shall/must ↔ may), negation, number, exception/proviso/override deletion, and scope
  (all/every/any → some/certain; Hindi equivalents). Hindi verb rules operate on clause-final verb groups
  (e.g. करेगा → कर सकेगा; करना होगा → करने की छूट है). [TBD: count per type.]

Table I: [TBD] dataset statistics by act × language × variant (pairs, mean words, mean label ± std).

### D. Annotation

- Annotators: [TBD: k, background]. Each pair is scored by [TBD: 3] annotators in a blinded workbook (opaque
  ids, per-annotator shuffled order, items from the same clause kept apart; annotators are never told the
  variant or error type).
- Rubric (JUDGEBERT, unchanged): bracket Accurate (7–10), Imprecise (2–6) or Off-track (1); minus one point
  per error (omission, hallucination, inconsistency, confusion), floor 1. We add Indian-law conventions
  (shall/may, provisos, overrides, time limits, actors) in the guidelines, a 1–5 simplicity rating and the
  single most important legal change.
- Calibration: a shared 20-pair pilot, discussion of disagreements, guideline revision ([TBD: changes, from
  the guideline change log]); pilot scores discarded.
- Label: mean LMP across annotators (as FrJUDGE). Agreement: Krippendorff's α (interval) [TBD] vs. 0.10 on
  FrJUDGE; nominal α on brackets [TBD]; human ceiling (mean leave-one-out Pearson of each annotator against
  the mean of the others) [TBD].

### E. Augmentation, sanity holdouts and splits

- DA (as JUDGEBERT): for each clause and language, an identical pair (label 10) and an unrelated pair
  (label 1, the floor of our scale; JUDGEBERT used 0) whose partner is a provision with ROUGE-1/2/L < 0.25 and
  BLEU < 25, computed with a Devanagari-aware tokeniser (the common `rouge_score` package drops non-ASCII
  text, making every Hindi pair look unrelated).
- Sanity holdouts: [TBD: n] identical and [TBD: n] unrelated pairs built only from provisions that are not
  selected, not in a section with a selected clause and not used as DA partners.
- Splits: 60/10/30 by clause, stratified by act, 5 seeds (42–46); a clause's English and Hindi pairs, all
  variants and its DA pairs share a split, enforced by an automatic disjointness check (clause- and text-level).
  Out-of-domain splits: train/dev on one act, test on the other. Test sets contain human-annotated pairs only.

## IV. Methods

- **LMP model.** Cross-encoder regression: `[CLS] original [SEP] simplification [SEP]` → linear head → score;
  MSE loss; AdamW, lr 5e-5, batch 16, linear decay without warm-up, up to 100 epochs, early stopping with
  patience 5 on human dev MSE; predictions clipped to [1, 10]. Backbones: [TBD: confirmed ids, e.g.
  xlm-roberta-base, google/muril-base-cased, ai4bharat/IndicBERTv2-MLM-only]. Trained with and without DA.
- **Baselines.** ROUGE-L and BLEU (our tokeniser), LaBSE cosine, multilingual BERTScore F1
  ([TBD: model]); each mapped to 1–10 naively ([0,1] → [1,10]) and by a linear fit on the training pairs.
- **LLM judge.** [TBD: model id], temperature 0, given the annotators' rubric; it returns a bracket and error
  counts and is scored with the same formula as the humans.
- **Decisions.** ≥ 7 Preserved, ≥ 2 Partially Preserved, < 2 Not Preserved (the rubric brackets).
- **Check of our implementation.** On the released FrJUDGE splits our training code obtains
  [TBD] Pearson / [TBD] RMSE without DA (paper: 0.74 ± 0.02 / 1.72).

## V. Experiments and results

Metrics: Pearson, Spearman, RMSE, MAE (mean ± std over 5 seeds), over-scoring rate (share of pairs where the
prediction exceeds the human label), decision accuracy and macro-F1. All from human-annotated test pairs.

- **E1 Baselines vs. LMP model.** Table II [TBD from reports/results.md]. Compare with the human ceiling.
- **E2 English vs. Hindi.** Per-language results (Table III) and zero-shot EN→HI / HI→EN transfer
  (Table IV) [TBD].
- **E3 New legal domain.** RTI→CPA and CPA→RTI (Table V) [TBD].
- **E4 Sanity checks.** Share of identical holdout pairs scored ≥ 9.9 and unrelated pairs scored ≤ 1.1, for
  every system (Table VI) [TBD].
- **Diagnostic set.** Mean error of each system on perturbed pairs by injected error type (Table VII) [TBD]:
  does a metric notice shall→may?

## VI. Error analysis (E5)

[TBD: ≥ 15 cases from reports/error_analysis_<system>.md, grouped by error type (omission, hallucination,
contradiction, obligation/permission, condition, exception, scope, date/time, number, entity). For each:
original, simplification, gold vs. predicted score, and the team's legal explanation.]

## VII. Limitations and ethics

- Two acts and one Indian language; one LLM generated the simplifications ([TBD: model]).
- Annotators are [TBD: background], not practising lawyers; the label is a mean of possibly lenient and strict
  annotators.
- Perturbations are rule-based and may be easier to detect than natural errors; we report them separately.
- Statute texts are public government documents; FrJUDGE (CC-BY-NC-SA 4.0) is used only to check our code
  and is not redistributed. The model is an evaluation aid, not legal advice.

## VIII. Conclusion

[TBD after results.]

## References (verify each before submission)

1. O. Beauchemin, M. Albert-Rochette, R. Khoury, P.-L. Déziel, "JUDGEBERT: Assessing Legal Meaning Preservation
   Between Sentences," EMNLP 2025, pp. 92–118.
2. T. Kew et al., "BLESS: Benchmarking Large Language Models on Sentence Simplification," EMNLP 2023.
3. T. Zhang et al., "BERTScore: Evaluating Text Generation with BERT," ICLR 2020.
4. F. Feng et al., "Language-agnostic BERT Sentence Embedding," ACL 2022.
5. A. Conneau et al., "Unsupervised Cross-lingual Representation Learning at Scale," ACL 2020.
6. S. Khanuja et al., "MuRIL: Multilingual Representations for Indian Languages," arXiv:2103.10730, 2021.
7. S. Doddapaneni et al., "Towards Leaving No Indic Language Behind: Building Monolingual Corpora, Benchmark and
   Models for Indic Languages," ACL 2023.
8. K. Krippendorff, "Computing Krippendorff's Alpha-Reliability," 2011.
9. T. Scialom et al., "QuestEval: Summarization Asks for Fact-based Evaluation," EMNLP 2021.
10. M. Maddela et al., "LENS: A Learnable Evaluation Metric for Text Simplification," ACL 2023.
11. D. Beauchemin et al., "MeaningBERT: Assessing Meaning Preservation Between Sentences," Frontiers in AI, 2023.
12. S. Paul et al., "Pre-trained Language Models for the Legal Domain: A Case Study on Indian Law," ICAIL 2023.
13. A. Joshi et al., "IL-TUR: Benchmark for Indian Legal Text Understanding and Reasoning," ACL 2024.
