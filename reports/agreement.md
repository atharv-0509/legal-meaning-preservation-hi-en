# Annotation agreement

Workbooks: llm_claude_opus55_a.xlsx, llm_claude_opus55_b.xlsx

- Complete ratings: 676; incomplete rows: 0
- Pairs with >= 2 ratings: 338 / 338
- **Krippendorff's alpha (interval, LMP 1-10): 0.610** (JUDGEBERT/FrJUDGE reported 0.10)
- Krippendorff's alpha (nominal, bracket): 0.503
- **Human ceiling** (mean leave-one-out Pearson): 0.723

## Annotators

| annotator | n | mean LMP | std | LOO Pearson | % Accurate | % Off-track |
|---|---|---|---|---|---|---|
| llm_claude_opus55_a | 338 | 8.12 | 2.21 | 0.723 | 70% | 0% |
| llm_claude_opus55_b | 338 | 6.93 | 2.99 | 0.723 | 54% | 6% |

Large differences in mean LMP indicate lenient vs. strict annotators (as in FrJUDGE).

## Pairwise Pearson

| pair | r | n |
|---|---|---|
| llm_claude_opus55_a-llm_claude_opus55_b | 0.723 | 338 |

## Mean LMP by language and variant (from pairs.jsonl)

| lang | variant | n pairs | mean | std |
|---|---|---|---|---|
| en | aggressive | 78 | 7.60 | 1.51 |
| en | normal | 78 | 9.96 | 0.17 |
| en | perturbed | 77 | 5.03 | 1.82 |
| en | perturbed:exception_drop | 14 | 6.50 | 1.95 |
| en | perturbed:modality | 14 | 5.61 | 1.61 |
| en | perturbed:negation | 20 | 3.20 | 1.05 |
| en | perturbed:number | 11 | 5.00 | 0.00 |
| en | perturbed:scope | 18 | 5.50 | 1.42 |
| hi | aggressive | 35 | 7.57 | 1.47 |
| hi | normal | 35 | 9.94 | 0.16 |
| hi | perturbed | 35 | 4.94 | 1.56 |
| hi | perturbed:exception_drop | 6 | 5.08 | 0.93 |
| hi | perturbed:modality | 12 | 5.96 | 1.78 |
| hi | perturbed:negation | 6 | 2.75 | 0.25 |
| hi | perturbed:number | 5 | 4.90 | 0.20 |
| hi | perturbed:scope | 6 | 5.00 | 0.00 |

## Adjudication

68 pairs with score range >= 4 or Accurate-vs-Off-track disagreement -> reports/adjudicate.csv
