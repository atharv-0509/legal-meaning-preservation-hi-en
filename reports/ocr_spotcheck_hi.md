# Hindi OCR spot-check (to be done by a Hindi reader)

`reports/ocr_spotcheck_hi.csv` lists 8 of the 35 RTI clauses with Hindi text, drawn at random
(seed 2026) from `data/processed/clauses_final.jsonl`. For each row:

1. Open the official Hindi PDF from DoPT (`sources.json` → `rti.pdf_url.hi`) in a browser. The DoPT site
   blocks cloud machines, so this must be done from a computer in India.
2. Find the section and sub-section (the `approx_ocr_page` column is only a hint from text matching).
3. Compare the PDF text with `text_hi_ocr` word by word. Write `yes` if they match, otherwise `no` and the
   differences (wrong letters/matras, missing words, wrong numbers), and your name in `checked_by`.

Report the result in the paper's limitations section (§5 says no Hindi reader has checked the OCR yet).
An automated check by the cloud session was not possible: DoPT reset or timed out every connection,
both from the cloud machine and from Kaggle (19 Nov 2026).
