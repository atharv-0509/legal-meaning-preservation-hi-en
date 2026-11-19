# FrJUDGE reproduction (implementation check)

Our `modeling/train.py` on the released FrJUDGE splits, Kaggle T4, commit `f356b1c` (tokenizer fix). Source: `reports/frjudge_repro.log` (verbatim kernel log lines; run still in progress). JUDGEBERT reports Pearson 0.74 ± 0.02, RMSE 1.72 (no DA, 10 seeds).

| Configuration | seeds | Pearson | Spearman | RMSE | MAE |
|---|---|---|---|---|---|
| CamemBERT-v2, no DA, patience 5 (paper text) | 10 | 0.606 ± 0.284 | 0.555 ± 0.260 | 1.906 ± 0.269 | 1.548 ± 0.237 |
| CamemBERT-v2, no DA, 100 epochs keep-best (released code) | 10 | 0.707 ± 0.042 | 0.654 ± 0.045 | 1.788 ± 0.115 | 1.415 ± 0.115 |
| CamemBERT-v2, DA, 100 epochs keep-best (human test pairs; partial) | 2 | 0.869 ± 0.023 | 0.853 ± 0.018 | 1.276 ± 0.128 | 0.906 ± 0.129 |

Note: in the patience-5 setting seed 42 stopped at epoch 5 and collapsed (Pearson −0.196); the other nine seeds average 0.695. The released-code setting (no early stopping) is stable.
