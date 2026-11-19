# Legal-error type classification

Task: predict the legal error in a simplification — none, modality (shall↔may), negation, number, exception_drop or scope. Gold labels are **objective**: "none" for the standard simplifications and the rule-injected error type for perturbed pairs (`src/perturb.py`), not LLM-annotator judgements. Aggressive pairs have no known type and are excluded. "none" means *no injected error*, not *no error*.

Clause-grouped random splits: random_s42 (n=64), random_s43 (n=68), random_s44 (n=66), random_s45 (n=66), random_s46 (n=65); pooled test gold distribution {'none': 165, 'negation': 42, 'scope': 33, 'modality': 44, 'number': 22, 'exception_drop': 23}. Mean ± std over splits.

| System | splits | Macro-F1 | Accuracy | EN macro-F1 | HI macro-F1 |
|---|---|---|---|---|---|
| rules | 5 | 0.509 ± 0.074 | 0.552 ± 0.074 | 0.495 ± 0.091 | 0.507 ± 0.165 |
| errcls-muril-base-cased | 5 | 0.362 ± 0.174 | 0.327 ± 0.115 | 0.366 ± 0.174 | 0.289 ± 0.189 |
| errcls-xlm-roberta-base-frjudge | 5 | 0.277 ± 0.059 | 0.298 ± 0.070 | 0.276 ± 0.065 | 0.245 ± 0.064 |
| errcls-xlm-roberta-base | 5 | 0.270 ± 0.082 | 0.318 ± 0.052 | 0.269 ± 0.099 | 0.186 ± 0.076 |
| majority (none) | 5 | 0.111 ± 0.001 | 0.502 ± 0.003 | 0.111 ± 0.001 | 0.124 ± 0.012 |

## Per-class F1

| Class | rules | errcls-muril-base-cased | errcls-xlm-roberta-base-frjudge | errcls-xlm-roberta-base | majority (none) |
|---|---|---|---|---|---|
| none | 0.605 ± 0.082 | 0.170 ± 0.190 | 0.355 ± 0.105 | 0.375 ± 0.075 | 0.668 ± 0.003 |
| modality | 0.447 ± 0.181 | 0.248 ± 0.089 | 0.181 ± 0.070 | 0.224 ± 0.079 | 0.000 ± 0.000 |
| negation | 0.629 ± 0.071 | 0.643 ± 0.235 | 0.386 ± 0.115 | 0.415 ± 0.258 | 0.000 ± 0.000 |
| number | 0.577 ± 0.194 | 0.567 ± 0.465 | 0.284 ± 0.125 | 0.356 ± 0.280 | 0.000 ± 0.000 |
| exception_drop | 0.332 ± 0.116 | 0.073 ± 0.163 | 0.270 ± 0.283 | 0.094 ± 0.158 | 0.000 ± 0.000 |
| scope | 0.463 ± 0.162 | 0.473 ± 0.325 | 0.185 ± 0.151 | 0.155 ± 0.146 | 0.000 ± 0.000 |

## errcls-muril-base-cased: precision / recall per class (mean over splits)

| Class | Precision | Recall |
|---|---|---|
| none | 0.531 ± 0.384 | 0.121 ± 0.153 |
| modality | 0.175 ± 0.053 | 0.553 ± 0.346 |
| negation | 0.642 ± 0.275 | 0.686 ± 0.261 |
| number | 0.583 ± 0.471 | 0.553 ± 0.463 |
| exception_drop | 0.050 ± 0.112 | 0.133 ± 0.298 |
| scope | 0.452 ± 0.371 | 0.592 ± 0.287 |

Pooled confusion matrix for errcls-muril-base-cased (rows = gold, columns = predicted):

| gold \ pred | none | modality | negation | number | exception_drop | scope |
|---|---|---|---|---|---|---|
| none | 20 | 83 | 11 | 4 | 16 | 31 |
| modality | 2 | 24 | 0 | 2 | 5 | 11 |
| negation | 1 | 6 | 30 | 0 | 4 | 1 |
| number | 3 | 4 | 1 | 12 | 2 | 0 |
| exception_drop | 5 | 11 | 3 | 0 | 2 | 2 |
| scope | 3 | 6 | 3 | 0 | 1 | 20 |

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

- The trained cross-encoder classifiers do **not** beat the rule baseline. With about 130 training pairs per split spread over six classes (15-20 per error type), the models do not learn the types reliably; class-weighted training also pushes them away from "none", so accuracy falls below the majority baseline.
- MuRIL is the best trained classifier and matches the rules on negation, number and scope, but fails on exception_drop and on "none".
- The rule baseline has an unfair advantage: its cues mirror the rules that injected the errors (`src/perturb.py`), so it is an upper-bound-style reference for these error types, not evidence that rules would find natural errors in real simplifications.
- Consequence for the system: the demo app and `predict.py` report the rule-based error type and explanation; the trained classifier is optional (`--errcls-dir`) and not recommended at this data size.
- What would help: more perturbed pairs per type (the perturbation step can generate them cheaply), a two-stage model (error vs none, then type), or training on rule features plus the encoder.
