# Presentation guide (PID-08, 20 Nov 2026)

Slides: `paper/out/LMP_slides.pptx` (PDF copy `paper/out/LMP_slides.pdf`, 23 slides). Paper: `paper/out/LMP_paper_IEEE.docx`.

## Before the talk (10 minutes)

1. `git pull` in the project folder, then activate the environment (`.venv\Scripts\activate`).
2. Check the two models are present: `modeling\checkpoints\muril\demo_model` and
   `modeling\checkpoints\errcls\errcls_muril-base-cased-aug` (each has `config.json` and `model.safetensors`, ~900 MB).
3. Start the app and leave it running (loading the two models can take a minute on a laptop):
   `python modeling\app.py --model-dir modeling\checkpoints\muril\demo_model --errcls-dir modeling\checkpoints\errcls\errcls_muril-base-cased-aug`
4. Open http://127.0.0.1:7860 and score one example once, so the first live click is fast.
5. Fallback if the laptop fails: slide 17 shows a real output of the app.

## Demo script (about 3 minutes)

Pick the examples from the dropdown ("Try an example from the held-out test set"), then press **Score**. Outputs below
were produced with these exact models on 20 Nov 2026; the reference label is the mean of the two LLM annotators.

| Step | Example | Model | Reference | Error type shown | What to say |
|---|---|---|---|---|---|
| 1 | cpa-s10_1 · English · standard simplification | 10.0 Preserved | 10.0 | none | A faithful plain-language rewrite keeps the law. |
| 2 | cpa-s10_1 · English · one injected legal error | 2.0 Partially | 2.5 | negation (97%) | "shall … establish" became "will not set up": one word reverses the provision. |
| 3 | cpa-s10_1 · English · explained to a 12-year-old | 6.3 Partially | 6.0 | exception dropped (79%) | Aggressive simplification loses conditions. |
| 4 | cpa-s12 · English · one injected legal error | 5.0 Partially | 5.0 | scope (96%) | Scope narrowed: "any" became "certain". |
| 5 | cpa-s36_2 · English · one injected legal error | 4.9 Partially | 5.0 | number (92%) | A time limit changed (twenty-one → fourteen). |
| 6 | cpa-s33_1 · English · one injected legal error | **10.0** | 5.0 | modality (90%) | Honest failure: an obligation turned into a permission (must → may) still scores 10, though the classifier names it. This is the paper's main open problem. |

Optional live edit: load step 1, type "not" into the simplification, press Score again.
For provisions the model has never seen (better than the dropdown for showing it on new text), use the copy-paste
sheet `paper/DEMO_SAMPLES.md`: CPA 69(1), RTI 19(6) in Hindi and RTI 19(5), each with expected outputs.
Hindi works too (rti-s11_4 · Hindi), but the Hindi injected-error example also scores 10.0 against a reference of 5.0
(may → shall, flagged as modality 88%). Show it only as part of the honesty point.

## Numbers you may be asked for

- Data: 78 clauses (RTI 38, 35 with Hindi; CPA 40, English only) → 338 pairs, three variants each.
- Labels: two disclosed LLM annotators (Claude Opus 5.5), **not** humans; Krippendorff's α 0.610 (JUDGEBERT reported
  0.10). The 30-pair human validation sheet is prepared, not yet scored.
- Principal system (XLM-R, FrJUDGE pre-training + DA): Pearson 0.576 ± 0.102 over 5 seeds; from scratch 0.228 ± 0.288;
  best generic baseline (calibrated LaBSE) 0.101.
- MuRIL with the same recipe: 0.577 ± 0.068, better on Hindi (0.466) and RTI→CPA (0.251).
- Demo checkpoint: test Pearson 0.682 on one split (random_s42), not the headline number.
- Error-type classifier (MuRIL + augmentation): macro-F1 0.789 ± 0.101 vs rules 0.509.
- FrJUDGE reproduction: 0.707 ± 0.042 vs published 0.74.
- Hindi CPA: Bill text OCR'd (107/107 sections), not yet reviewed, not used in any result.

## Likely questions

- *Why LLM labels?* Deadline. Disclosed everywhere; the human sheet exists and is the first next step.
- *Is 0.682 the result?* No: the headline is 0.576 ± 0.102 (5 seeds). 0.682 is the single demo checkpoint.
- *Does it generalise?* Partly: across Acts it drops (CPA→RTI 0.388, RTI→CPA 0.119), and English↔Hindi zero-shot is near zero.
- *Why does an obligation ↔ permission flip score 10?* The score model under-penalises them (see the error analysis);
  the error classifier catches most of them (modality recall 0.83), so the app shows both outputs together.
