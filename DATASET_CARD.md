# Legal LMP dataset: provisional status

As of 19 November 2026, this is an extraction/review candidate set, not a completed labelled dataset.
Pair count, label distribution, annotator agreement and model results: **[TBD]**.

## Sources and coverage

Sources are official DoPT RTI English/Hindi PDFs and the original 2019 CPA English Gazette.
Exact URLs and version notes are in `sources.json`; extraction observations are in
`paper/source_provenance.md`. CPA Hindi is unavailable. RTI Hindi requires OCR, and the RTI
English/Hindi editions differ in section 8. Clause selection requires review before finalization.
E2 is intended to use RTI EN/HI only; CPA contributes English-only examples.

## Planned labels and disclosure

The deadline plan uses two LLM annotators (Claude Opus 5.5, GPT-6 Astra) following the human
rubric, with variant and error type hidden in separate shuffled workbooks. This deviates from
the brief's human-judgement requirement because of time constraints. No LLM annotations have
yet been completed; do not describe this plan as an executed experiment.

The planned label is the mean of the two LLM rubric scores. Report agreement explicitly as
**LLM-annotator agreement**, never human agreement or a human ceiling. Record actual model/runtime
identifiers when generation and annotation occur. A generator cannot be assumed blind in the
same context; any generator/annotator overlap and model-family bias must be disclosed.
Annotators must not inspect the pair answer key, perturbation records or each other's scores.
Do not evaluate a same-model LLM judge against its own labels.

A separate 30-pair human validation workbook is planned. Human validation scores and
LLM-versus-human correlation remain [TBD]; if no humans score it, report that limitation.

## Intended use and limitations

This is an exploratory course-project resource for evaluating legal simplification, not a
validated legal decision tool. LLM labels cannot substitute for evidence of agreement with
human legal judgement. Text corruption, edition differences, missing CPA Hindi and the small
sample limit any conclusions. Source licensing and redistribution terms remain [TBD].
Split all variants and languages by source clause and keep sanity pairs out of headline metrics.
