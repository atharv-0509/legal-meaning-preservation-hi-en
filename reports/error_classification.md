# Legal-error type classification

Task: predict the legal error in a simplification — none, modality (shall↔may), negation, number, exception_drop or scope. Gold labels are **objective**: "none" for the standard simplifications and the rule-injected error type for perturbed pairs (`src/perturb.py`), not LLM-annotator judgements. Aggressive pairs have no known type and are excluded. "none" means *no injected error*, not *no error*.

Clause-grouped random splits: random_s42 (n=64), random_s43 (n=68), random_s44 (n=66), random_s45 (n=66), random_s46 (n=65); pooled test gold distribution {'none': 165, 'negation': 42, 'scope': 33, 'modality': 44, 'number': 22, 'exception_drop': 23}. Mean ± std over splits.

| System | splits | Macro-F1 | Accuracy | EN macro-F1 | HI macro-F1 |
|---|---|---|---|---|---|
| errcls-muril-base-cased-aug | 5 | 0.789 ± 0.101 | 0.754 ± 0.182 | 0.814 ± 0.135 | 0.715 ± 0.137 |
| errcls-xlm-roberta-base-augcue | 5 | 0.586 ± 0.042 | 0.591 ± 0.086 | 0.575 ± 0.036 | 0.562 ± 0.057 |
| errcls-xlm-roberta-base-aug | 5 | 0.581 ± 0.288 | 0.695 ± 0.177 | 0.589 ± 0.287 | 0.500 ± 0.302 |
| errcls-muril-base-cased-augcue | 5 | 0.573 ± 0.072 | 0.598 ± 0.126 | 0.566 ± 0.102 | 0.527 ± 0.096 |
| rules | 5 | 0.509 ± 0.074 | 0.552 ± 0.074 | 0.495 ± 0.091 | 0.507 ± 0.165 |
| errcls-muril-base-cased | 5 | 0.362 ± 0.174 | 0.327 ± 0.115 | 0.366 ± 0.174 | 0.289 ± 0.189 |
| errcls-xlm-roberta-base-frjudge | 5 | 0.277 ± 0.059 | 0.298 ± 0.070 | 0.276 ± 0.065 | 0.245 ± 0.064 |
| errcls-xlm-roberta-base | 5 | 0.270 ± 0.082 | 0.318 ± 0.052 | 0.269 ± 0.099 | 0.186 ± 0.076 |
| majority (none) | 5 | 0.111 ± 0.001 | 0.502 ± 0.003 | 0.111 ± 0.001 | 0.124 ± 0.012 |

## Per-class F1

| Class | errcls-muril-base-cased-aug | errcls-xlm-roberta-base-augcue | errcls-xlm-roberta-base-aug | errcls-muril-base-cased-augcue | rules | errcls-muril-base-cased | errcls-xlm-roberta-base-frjudge | errcls-xlm-roberta-base | majority (none) |
|---|---|---|---|---|---|---|---|---|---|
| none | 0.679 ± 0.352 | 0.623 ± 0.094 | 0.747 ± 0.140 | 0.634 ± 0.139 | 0.605 ± 0.082 | 0.170 ± 0.190 | 0.355 ± 0.105 | 0.375 ± 0.075 | 0.668 ± 0.003 |
| modality | 0.659 ± 0.219 | 0.430 ± 0.146 | 0.549 ± 0.383 | 0.469 ± 0.248 | 0.447 ± 0.181 | 0.248 ± 0.089 | 0.181 ± 0.070 | 0.224 ± 0.079 | 0.000 ± 0.000 |
| negation | 0.849 ± 0.096 | 0.632 ± 0.222 | 0.644 ± 0.380 | 0.744 ± 0.163 | 0.629 ± 0.071 | 0.643 ± 0.235 | 0.386 ± 0.115 | 0.415 ± 0.258 | 0.000 ± 0.000 |
| number | 0.967 ± 0.075 | 0.784 ± 0.153 | 0.693 ± 0.413 | 0.727 ± 0.300 | 0.577 ± 0.194 | 0.567 ± 0.465 | 0.284 ± 0.125 | 0.356 ± 0.280 | 0.000 ± 0.000 |
| exception_drop | 0.787 ± 0.162 | 0.354 ± 0.122 | 0.304 ± 0.188 | 0.380 ± 0.172 | 0.332 ± 0.116 | 0.073 ± 0.163 | 0.270 ± 0.283 | 0.094 ± 0.158 | 0.000 ± 0.000 |
| scope | 0.790 ± 0.180 | 0.691 ± 0.211 | 0.552 ± 0.373 | 0.486 ± 0.110 | 0.463 ± 0.162 | 0.473 ± 0.325 | 0.185 ± 0.151 | 0.155 ± 0.146 | 0.000 ± 0.000 |

## errcls-muril-base-cased-aug: precision / recall per class (mean over splits)

| Class | Precision | Recall |
|---|---|---|
| none | 0.829 ± 0.199 | 0.636 ± 0.359 |
| modality | 0.606 ± 0.278 | 0.829 ± 0.096 |
| negation | 0.810 ± 0.146 | 0.908 ± 0.103 |
| number | 0.943 ± 0.128 | 1.000 ± 0.000 |
| exception_drop | 0.877 ± 0.116 | 0.783 ± 0.274 |
| scope | 0.753 ± 0.228 | 0.846 ± 0.119 |

Pooled confusion matrix for errcls-muril-base-cased-aug (rows = gold, columns = predicted):

| gold \ pred | none | modality | negation | number | exception_drop | scope |
|---|---|---|---|---|---|---|
| none | 105 | 42 | 8 | 1 | 3 | 6 |
| modality | 5 | 37 | 0 | 1 | 0 | 1 |
| negation | 2 | 1 | 38 | 0 | 0 | 1 |
| number | 0 | 0 | 0 | 22 | 0 | 0 |
| exception_drop | 5 | 1 | 0 | 0 | 17 | 0 |
| scope | 1 | 2 | 1 | 0 | 0 | 29 |

## rules: precision / recall per class (mean over splits)

| Class | Precision | Recall |
|---|---|---|
| none | 0.799 ± 0.061 | 0.490 ± 0.089 |
| modality | 0.388 ± 0.168 | 0.550 ± 0.213 |
| negation | 0.470 ± 0.063 | 0.955 ± 0.062 |
| number | 1.000 ± 0.000 | 0.427 ± 0.198 |
| exception_drop | 0.433 ± 0.320 | 0.317 ± 0.124 |
| scope | 0.397 ± 0.156 | 0.581 ± 0.186 |

Pooled confusion matrix for rules (rows = gold, columns = predicted):

| gold \ pred | none | modality | negation | number | exception_drop | scope |
|---|---|---|---|---|---|---|
| none | 81 | 30 | 29 | 0 | 7 | 18 |
| modality | 8 | 24 | 2 | 0 | 4 | 6 |
| negation | 1 | 0 | 40 | 0 | 0 | 1 |
| number | 1 | 3 | 6 | 10 | 0 | 2 |
| exception_drop | 7 | 4 | 3 | 0 | 7 | 2 |
| scope | 3 | 3 | 6 | 0 | 1 | 20 |

## Findings (19 Nov 2026)

- Without augmentation the trained classifiers do **not** beat the rules (best MuRIL 0.362 vs 0.509): about 130 training pairs per split over six classes (15-20 per error type) are too few.
- **With augmentation they do.** `--augment 3 --augment-originals` adds, for the training clauses only, injected-error pairs built from the standard simplifications and from the original statute texts (~630 training pairs per split, every type >= 21). **MuRIL + augmentation reaches macro-F1 0.789 ± 0.101** and beats the rules on every class (negation 0.849, number 0.967, exception_drop 0.787, scope 0.790, modality 0.659). Per seed: 0.852 / 0.874 / 0.621 / 0.779 / 0.817; seed 44 over-flags standard simplifications. XLM-R + augmentation is unstable (one seed collapses to 0.112).
- Adding the rule cues to the input (`--cue-features`) does **not** help (MuRIL 0.573, XLM-R 0.586): the model leans on the cues and inherits their false alarms.
- Caveat: the augmentation uses the same rules that injected the test errors (`src/perturb.py`), as do the rule baseline's cues. These results show the model learns *these* error types; they say nothing about natural errors in real simplifications, which have no type labels here (aggressive pairs are excluded).
- Consequence: the demo app and `predict.py` show the rule-based type and explanation always, and the MuRIL + augmentation classifier when its checkpoint is passed with `--errcls-dir` (Kaggle kernel `lmp-errcls-demo`).
