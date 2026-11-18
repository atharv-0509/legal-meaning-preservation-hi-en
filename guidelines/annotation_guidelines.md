# Annotation guidelines: Legal Meaning Preservation (LMP)

Version 1.0 (pre-pilot). The rubric is the JUDGEBERT rubric (Beauchemin et al., EMNLP 2025), reused
unchanged. These guidelines add conventions for Indian legal text in English and Hindi. Update the
**change log** at the bottom whenever anything here changes.

## 1. Your task

Each row of the `Annotate` sheet shows an **original** sentence block from an Indian central act and
a **simplification** of it. Decide how well the simplification keeps the **legal meaning** of the
original: who must or may do what, under which conditions, with which exceptions, time limits,
amounts and scope.

You do **not** judge style, grammar or fluency, except when they change the legal meaning.

You will not be told how a simplification was produced. Some are good, some are poor, and some
contain a deliberate error. Score every row on its own, even when two rows look alike.

## 2. Procedure for each row

1. Read the original carefully, then the simplification.
2. **simplicity** (1–5): is the simplification easier to read than the original?
   1 = harder, 2 = as hard, 3 = a bit easier, 4 = easier, 5 = much easier.
3. **bracket**: choose one.
   | Bracket | Meaning | Max score |
   |---|---|---|
   | Accurate (7–10) | The legal meaning is kept. A reader who relies on the simplification would not be misled about their rights or duties. | 10 |
   | Imprecise (2–6) | The legal meaning is partly kept: something legally relevant is lost, added or distorted, but the provision is still recognisable. | 6 |
   | Off-track (1) | The simplification misrepresents the law (e.g. reverses a duty or a prohibition) or is about something else. | 1 |
4. **Count errors** (0–9 in each column). Each error subtracts 1 point from the bracket maximum; the
   score never goes below 1. The sheet computes `lmp_score`.
5. **main_change**: the single most important legal change (or `none`).
6. **comment**: one short sentence explaining the score. Required when the score is below 7.
7. Resolve any message in the `check` column other than `OK`.

## 3. Error types

Count **each distinct** problem once, in the column that fits it best.

| Column | Count when… | Examples |
|---|---|---|
| omissions | An essential legal element of the original is missing. | A condition ("if the request is made in writing"), an exception or proviso, a time limit, the actor, an amount, a cross-reference that limits scope. |
| hallucinations | The simplification adds a legal element that is not in the original. | A new right, duty, deadline, penalty or condition. |
| inconsistencies | A legal term is replaced by a non-equivalent word, or terms are used inconsistently. | "complainant" → "customer"; "public authority" → "government office"; one actor called by two names. |
| confusions | The simplification states something different from, or contrary to, the original. | shall ↔ may; must ↔ need not; adding or removing "not"; wrong number or date; wrong actor; "all" → "some". |

Omitting genuinely unimportant information (drafting redundancy, "for the purposes of this Act") is
**not** an error; that is what simplification is for.

## 4. Conventions for Indian legal text

- **shall / करेगा / करना होगा** is an obligation. **may / कर सकेगा / कर सकता है** is a permission
  (discretion). Swapping them is a *confusion* and usually means *Imprecise* or *Off-track*.
- **shall not / नहीं करेगा / कोई … नहीं** is a prohibition. Turning a prohibition into a permission or a duty
  is *Off-track*.
- **Provisos** ("Provided that…", "परंतु…") and **Explanations** ("स्पष्टीकरण") are part of the provision.
  Dropping a proviso that limits a right or duty is an *omission*.
- **Override clauses** ("Notwithstanding anything…", "…के होते हुए भी") and **subject-to clauses**
  ("Subject to section 8…", "…के अधीन रहते हुए") change scope. Dropping one is an *omission*.
- **Time limits and amounts** ("within thirty days", "तीस दिन के भीतर", "ten thousand rupees") must be exact.
  A changed number is a *confusion*; a missing one is an *omission*.
- **Actors** (Public Information Officer, District Commission, Central Government…) must stay the
  same. "the officer" for "the Central Public Information Officer" is acceptable if unambiguous in context.
- **Cross-references** ("referred to in sub-section (1)") can be dropped if the simplification states the
  referenced content or the reference does not limit scope.
- **Hindi**: judge the Hindi simplification against the **Hindi original** only. Common administrative
  synonyms (सूचना/जानकारी, आवेदन/अर्जी) are fine; legal terms of art (लोक प्राधिकरण, परिवाद, शास्ति)
  should not be replaced by non-equivalent everyday words.
- A simplification that is **truncated** mid-sentence: count each lost legal element as an omission.

## 5. Calibration examples

These are fixed after the pilot round, using pilot items the group discussed. Until then:

| Situation | Typical bracket | Typical errors |
|---|---|---|
| Plain-language paraphrase, all conditions and limits kept | Accurate | 0 → 10 |
| Same, but one minor qualifier dropped | Accurate | 1 omission → 9 |
| Time limit dropped | Imprecise | 1 omission → 5 |
| "shall" became "may" | Imprecise or Off-track | 1 confusion → 5 (or 1) |
| Prohibition turned into permission | Off-track | → 1 |
| Exception dropped and one term changed | Imprecise | 1 omission + 1 inconsistency → 4 |

## 6. Practicalities

- Fill only the yellow columns. Do not reorder rows or edit `pair_uid`, `original` or `simplification`.
- Any spreadsheet program works (Excel, LibreOffice, Google Sheets → download as .xlsx). The score is
  recomputed from your bracket and error counts, so the `lmp_score` formula does not have to work.
- Work in sessions of at most an hour; note the minutes per row if you can.
- Do not discuss specific items with other annotators during the main round (the pilot discussion
  is the place for that).
- Return the file with the same name.

## 7. Process

1. **Pilot**: everyone scores the same 20 pairs (`annotation/pilot/<name>.xlsx`). We run
   `python src/agreement.py --pilot`, discuss the items in `reports/adjudicate_pilot.csv`, and update
   these guidelines (change log below). Pilot scores are discarded.
2. **Main round**: each pair is scored by 3 annotators (2 if time is short).
3. **Labels**: mean LMP across annotators (as in FrJUDGE). Pairs in `reports/adjudicate.csv`
   (score range ≥ 4) are discussed, but the mean is kept as the label; the discussion goes in the paper's
   error analysis.

## Change log

| Date | Version | Change | Reason |
|---|---|---|---|
| 2026-11-18 | 1.0 | Initial guidelines: JUDGEBERT rubric + Indian-law conventions. | Before pilot. |
