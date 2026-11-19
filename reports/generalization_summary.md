# Generalisation follow-up: MuRIL and five seeds (19 Nov 2026, evening)

Kaggle kernels `lmp-muril-frj` and `lmp-xlmr-5seeds` (commit aca72cb): each backbone first trained on FrJUDGE
(one pre-training run per kernel), then fine-tuned on our clause-grouped splits over seeds 42-46, with the deadline
training settings (lr 2e-5, batch 8, 30 epochs, keep best dev). Labels are the disclosed LLM-annotator labels.
All numbers: test Pearson, mean ± std over seeds, from `reports/generalization_followup.json`
(regenerate with `python modeling/evaluate.py --out reports/generalization_followup.md`). New runs carry the
`-5s` tag; the deadline runs (3 seeds) are unchanged and still what the paper reports.

| System (FrJUDGE → ours, with DA) | E1 all | E1 EN | E1 HI | E2 matched RTI: EN | E2: HI | E3 CPA→RTI | E3 RTI→CPA |
|---|---|---|---|---|---|---|---|
| XLM-R, deadline run (3 seeds, paper) | 0.576 ± 0.102 | 0.675 | 0.308 | 0.165 | −0.041 | 0.388 ± 0.021 | 0.119 ± 0.051 |
| XLM-R, new pre-training (5 seeds) | 0.486 ± 0.112 | 0.565 | 0.290 | 0.155 | 0.066 | 0.339 ± 0.046 | 0.147 ± 0.040 |
| **MuRIL (5 seeds)** | **0.577 ± 0.068** | 0.629 | **0.466** | **0.269** | **0.182** | **0.394 ± 0.054** | **0.251 ± 0.186** |

Zero-shot language transfer (E2, train one language, test the other) stays near zero for every system
(XLM-R 5s: EN→HI 0.115, HI→EN 0.136; MuRIL: 0.086, 0.104).

## Findings

1. **MuRIL generalises best.** Same overall level as the paper's XLM-R model (0.577 vs 0.576) with lower
   variance, and better on every generalisation measure: Hindi in E1 (0.466 vs 0.308), both languages on matched
   bilingual RTI provisions (0.269 / 0.182 vs 0.165 / −0.041), and RTI→CPA (0.251 vs 0.119, but ± 0.186).
2. **The FrJUDGE pre-training is unstable, and the transfer inherits it.** The same XLM-R pre-training (seed 42)
   reached FrJUDGE test Pearson 0.873 in the deadline kernel but 0.691 in this one (GPU non-determinism); downstream
   E1 fell from 0.576 to 0.486. Without DA the effect is drastic: 0.586 ± 0.098 (deadline, 3 seeds) vs
   0.166 ± 0.214 (new, 5 seeds). The paper's no-DA headline therefore depends on one pre-training run; the DA
   variants are the robust ones. MuRIL's pre-training reached 0.839.
3. **Zero-shot cross-lingual transfer is still absent**, for both backbones.

Per-seed E1 (DA): XLM-R new 0.304 / 0.542 / 0.450 / 0.580 / 0.553; MuRIL 0.578 / 0.646 / 0.492 / 0.530 / 0.642.

Recommendation: report MuRIL + FrJUDGE + DA as the system that generalises best, state the pre-training
instability as a limitation, and prefer DA variants. A MuRIL demo checkpoint is built by kernel `lmp-muril-demo`.
