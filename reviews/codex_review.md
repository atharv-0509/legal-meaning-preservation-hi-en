# CODEX: hostile project review

Reviewed 19 November 2026, branch `handover`, tracked revision `9db79ae61ecb09d7e53080a418e15ddca0184607`. Review only; no source, dataset, predictions or deliverables changed.

## Verdict and grading against the brief

**Estimated grade: 50/100, with roughly a 10-point uncertainty because no official marking weights were supplied.** A strict examiner could fail the submission on the mandatory human-judgement requirement alone. This project measures agreement with two instances of its own simplifier's model family, not agreement with human legal judgement. Its central language comparison is not the RTI-only controlled experiment the paper describes; its cross-act training includes target-act text; and its most prominent error examples silently come from different experimental conditions than the aggregate they supposedly illustrate. The arithmetic in the stored model metrics is not the main problem. The problem is that the submission repeatedly attaches stronger interpretations to those numbers than the implementation supports. Disclosure of limitations does not repair contradictory claims elsewhere.

These are **reviewer-assigned weights**, not the instructor's rubric. Requirements are from `CLAUDE.md:74` onward.

| Requirement | Status | Estimated credit | Examiner's reason |
|---|---|---:|---|
| Extend beyond French to English + an Indian language/domain | Met in scope | 8/10 | EN and HI exist, but Hindi is one act and the controlled-comparison claim is false. |
| At least 300 pairs with human 1–10 judgements | **Missed** | **0/20** | 338 pairs, zero completed human judgements in the reviewed release. A 30-pair pilot would still not meet 300. |
| At least two generic similarity baselines | Met | 7/8 | LaBSE and BERTScore plus lexical baselines ran; the claimed FrJUDGE baseline validation is not evidenced in the supplied reproduction report. |
| JUDGEBERT-inspired regression model | Met as implementation | 7/8 | Cross-encoder/MSE training exists; the operational checkpoint is absent. |
| At least one generalisation experiment | Partly met | 3/10 | Experiments ran, but E2 changes act/content as well as language; E3 exposes training to target-act text. |
| Identical/unrelated sanity checks | Partly met | 3/5 | Both run overall; Hindi has three identical and **zero unrelated** holdouts. Failure is a result, not a reason to deny all credit. |
| At least 15 qualitative error cases | Partly met | 5/7 | 18 cases, but prediction provenance is hidden and mismatched to the diagnostic aggregate. |
| Pearson/RMSE plus supporting metrics | Met computationally | 6/7 | Recomputed metrics match; interpretation of uncertainty and “ceiling” does not. |
| Separate language/domain reporting | Partly met | 2/5 | Raw reports contain breakdowns, but the paper's language rows are confounded and its main table lacks a clear in-domain act breakdown. |
| Per-pair score and Preserved/Partially/Not output | Partly met | 2/5 | Mapping/code exists; the supplied project cannot score a new pair with the reported model without retraining or retrieving a checkpoint. |
| GitHub code + IEEE Word/PDF + slides | Partly met as submission | 7/15 | Files exist; slides contain false completed-work claims and placeholders, and PDF tables are badly squeezed. |
| **Total** | | **50/100** | Human annotation is the largest missing deliverable, not a cosmetic caveat. |

## Findings

### 1. [BLOCKER] The required human-labelled dataset does not exist

**Location:** `CLAUDE.md:78`; `paper/out/paper_ieee.md:104`; `paper/out/paper_ieee.md:112`; `HANDOVER.md`, section 4 item 1.

**Problem and consequence:** All 338 reference labels are means of LLM scores. The paper explicitly says the human pilot has not been scored. This cannot establish the assignment's target, agreement with human legal judgement. Calling a 30-pair human check the solution also understates the requirement: it validates a sample, not 300 human-judged pairs.

**Concrete fix:** Obtain human judgements for at least 300 pairs under documented instructions and report them separately from the LLM scores. If that cannot happen, ask the instructor for an explicit scope exception and title/frame the submission as a weak-supervision pilot. Do not claim full completion after only a 30-item pilot.

### 2. [MAJOR] Systematic annotator disagreement is averaged away, not resolved

**Location:** `paper/out/paper_ieee.md:106`; `paper/out/paper_ieee.md:108`; `reports/adjudicate.csv:2`; `data/processed/labeled_pairs.jsonl:123`.

**Problem and consequence:** The “blinding is real and mechanical” paragraph says the answer key is in files the annotators never read, while the next paragraph admits annotator A generated the material. Two Claude instances are not independent evidence of legal validity. Recomputed mean scores are **8.115 for A versus 6.935 for B**. All **68 adjudication rows have blank decision fields**. For `rti-s11_2|hi|aggressive`, A gives 9 and B gives 4; the reported 6.5 is a numerical compromise between incompatible scoring conventions, not an adjudicated legal judgement.

**Concrete fix:** Remove the blanket blinding assertion, specify each annotator's actual access, and have an independent human resolve the largest disagreements. At minimum evaluate existing held-out predictions against A and B separately and by language/variant. That sensitivity analysis does **not** require retraining; retraining on each rater would be a separate, stronger experiment.

### 3. [MAJOR] E2 is not RTI-only and does not isolate language

**Location:** `modeling/make_tables.py:109`; `modeling/train.py:110`; `modeling/kaggle/lmp_experiments.py:73`; `paper/out/paper_ieee.md:67`; `paper/out/paper_ieee.md:138`; `paper/out/paper_ieee.md:210`; Table IV.

**Problem and consequence:** E2 filters by language, not by act or matched bilingual clause. Each random test split includes **36 CPA English pairs**, alongside 33 RTI English pairs and respectively 27/33/30 Hindi pairs for seeds 42/43/44. English training also includes CPA. Thus EN→HI combines a language shift with a content/domain-mixture shift, and HI→EN tests on an act absent from Hindi training. “Nothing but the language differs” and “confined to the Right to Information Act” are false descriptions of the executed experiment.

**Concrete fix:** Restrict E2 train/dev/test to the 35 bilingual RTI clause IDs, retaining clause-disjoint partitions and matched evaluation provisions. Regenerate the language rows and zero-shot runs. Until then relabel current results as mixed-act language-subset experiments and delete the controlled-language claim from paper/slides.

### 4. [MAJOR] E3 trains on text from the supposedly unseen act

**Location:** `src/sanity.py:27`; `src/sanity.py:80`; `src/sanity.py:92`; `src/split.py:89`; `data/splits/ood_cpa_to_rti/train_da.jsonl`; `data/splits/ood_rti_to_cpa/train_da.jsonl`; Table V.

**Problem and consequence:** Unrelated DA partners are sampled from a pool containing both acts before OOD splitting. The source act is recorded only for the original, not enforced for its partner. In the committed training files, **11 CPA→RTI training DA pairs use RTI English partner text** (seven distinct target provisions), and **30 RTI→CPA training DA pairs use CPA partner text** (22 distinct provisions). Examples include RTI `s8_2` and CPA `s5`. The model has therefore seen target-domain text with training labels before the claimed new-domain test. This is target-domain exposure, **not** evidence that the exact selected test originals leaked; those are different allegations.

**Concrete fix:** Build DA after the OOD split with both sides restricted to the training act; do the same for development data. Retain partner IDs through materialisation and assert both origins. Rerun E3 or explicitly call the current setting target-domain-exposed/transductive, not a clean unseen-act experiment.

### 5. [MAJOR] The paper's “most damning” examples silently use OOD seed 42, not the headline experiment

**Location:** `paper/e5.py:36`; `paper/e5.py:53`; `paper/e5.py:61`; `paper/out/paper_ieee.md:202`; Table VIII rows 2 and 4; slide 19.

**Problem and consequence:** `_predictions()` sorts every test prediction file, then keeps the first value for each pair/system. Alphabetical order puts OOD runs before random runs. **All 18 selected transfer predictions come from OOD seed 42.** The quoted 9.0 and 8.3 are from `ood_rti_to_cpa_s42`; on `random_s42`, that same `-frjudge-da` system predicts **3.211 and 2.006** for those two pairs. There is a second mismatch: Table VII's **1.878** negation MAE is from **transfer without local DA**, while Table VIII displays **transfer with DA**. The juxtaposition is not a within-model, within-protocol aggregate-versus-worst-case comparison.

**Concrete fix:** Select an explicit system, experiment family and seed (or a declared out-of-fold aggregation), carry that provenance into every case, and reject ambiguous lookups. Either report these as OOD failure cases or rebuild them from the experiment whose MAE is cited. Correct the abstract's and slides' inference, not just the table caption.

### 6. [MAJOR] The 0.723 inter-rater correlation is not an upper bound on prediction of the mean

**Location:** `paper/content.py:292`; `paper/content.py:521`; `paper/out/paper_ieee.md:222`; slides 8 and 17.

**Problem and consequence:** The target is `(A+B)/2`, but the proposed ceiling is `corr(A,B)`. Those are different quantities. On the actual data, `corr(A, mean)` is **0.904** and `corr(B, mean)` is **0.949**, both already above the alleged 0.723 upper bound. The repeated “four-fifths of the ceiling” framing has no justified performance interpretation. Shared model family and generator overlap make its use as an independent reliability bound even less defensible.

**Concrete fix:** Rename it **inter-LLM Pearson agreement**, remove “upper bound” and percentages-of-ceiling claims, and show rater-to-consensus comparisons only with their self-inclusion caveat. Do not replace it with another purported human ceiling without independent human data and a stated reliability model.

### 7. [MAJOR] Transfer helps in these runs; the asserted causal explanation is not established

**Location:** `paper/out/paper_ieee.md:14`; `paper/out/paper_ieee.md:206`; `paper/out/paper_ieee.md:220`; `paper/out/paper_ieee.md:224`; Conclusion; `modeling/runs_frj/xlm-roberta-base-frjudge-pretrain/frjudge_s42/config.json:1`.

**Problem and consequence:** “The limitation is scale”, “entirely sufficient”, and a language/jurisdiction-independent rubric are causal/general claims from three splits and one shared French pretraining checkpoint. Local fine-tuning settings do match: lr 2e-5, batch 8, 30 epochs, patience 0, annotated dev, max length 512. But transfer adds 30 epochs of French supervised DA training, a learned head, and different data/label distributions. The paper even uses successful FrJUDGE training with a comparable number of pairs as proof of a numerical sample-size limitation. These observations do not isolate scale from task initialization, optimization or data construction. The three random runs vary both partition and model seed, and have overlapping test clauses; they are not three independent datasets. A roughly 1.4-SE argument is not a proper paired baseline comparison or proof of equivalence.

**Concrete fix:** State the observed transfer improvement without the causal conclusion. Name the single shared pretraining seed, distinguish initialization variance from split variance, and report paired clause-level uncertainty. Add learning-curve/compute-matched and independent-pretraining-seed controls only if claiming the mechanism. No Indian train/test overlap was found by the existing disjointness checks; the released French split's own leakage assumptions were not independently re-audited here.

### 8. [MAJOR] The test set chooses the featured systems

**Location:** `modeling/make_tables.py:96`; `modeling/make_tables.py:105`; `modeling/make_tables.py:107`; `modeling/make_tables.py:127`; `run_all.py:110`.

**Problem and consequence:** Systems are sorted by **test Pearson**. The winner supplies the diagnostic model; the best DA model supplies E2/E3; the runbook selects error analysis by the same test results. This is test-informed reporting/model selection, despite prose suggesting selection was confined to development data. E3 also silently falls back to the first available system if the selected model is missing, without putting that system in the table.

**Concrete fix:** Predeclare the principal system or choose it using development results, report all planned comparisons, and name the exact system in every table. Fail rather than substituting an unnamed model. If keeping this exploratory selection, label it explicitly and reserve fresh data for confirmation.

### 9. [MAJOR] Corpus construction can explain high correlation without legal understanding

**Location:** `data/processed/labeled_pairs.jsonl:1`; `reports/agreement.md`; `paper/out/paper_ieee.md:216`.

**Problem and consequence:** Mean labels by variant are **9.956 normal, 7.593 aggressive, 5.004 perturbed**. I fitted a diagnostic lookup using **training labels only**, predicting each test item by its variant's training mean. It obtains Pearson **0.810 / 0.902 / 0.780** and RMSE **1.392 / 1.244 / 1.519** on seeds 42/43/44, exceeding the reported learned model without reading any text. Variant is answer-key information, so this is **not a fair deployable baseline**; it is evidence that the benchmark strongly encodes its construction recipe. The current result does not distinguish recognizing writing style/error templates from assessing legal consequences.

**Concrete fix:** Report within-variant performance prominently, add paired normal-versus-perturbed sensitivity tests and a natural-error-only evaluation, and include this construction-only diagnostic clearly labelled as privileged information. Stop treating overall Pearson alone as evidence of a jurisdiction-independent legal metric.

### 10. [MAJOR] Clean Unicode and a rule-based review do not validate the Hindi or guarantee a single error

**Location:** `src/agent_review.py:33`; `src/agent_review.py:80`; `src/agent_review.py:95`; `paper/out/paper_ieee.md:83`; `data/processed/labeled_pairs.jsonl:154`; `data/processed/labeled_pairs.jsonl:155`; `data/processed/labeled_pairs.jsonl:200`.

**Problem and consequence:** The review accepts everything outside a short flag list; it has no semantic alignment or legal-word correctness test. `rti-s16_1` still contains the extraction residue `.'ऐसी`. More importantly, the normal `rti-s12_6` narrows `विधान-मंडल` to `विधानसभा`, which the blinded annotator flags; its perturbed copy keeps that difference **and** removes a negation. A single injected edit is not a guarantee of exactly one total legal error relative to the statute. Zero U+FFFD/misplaced matras cannot certify legal vocabulary, and no Hindi human verification is recorded.

**Concrete fix:** Have a Hindi reader verify the 35 kept provisions against the PDFs and their EN counterparts, recording page references and decisions. Preserve before/after provenance for corrections. Describe perturbations as one additional rule edit to a potentially imperfect base, or first verify the base and annotate the total error inventory. Do not silently repair statutory text during this review.

### 11. [MAJOR] E4 provides no Hindi unrelated-pair evidence

**Location:** `data/splits/holdout_identical.jsonl:1`; `data/splits/holdout_unrelated.jsonl:1`; `modeling/make_tables.py:133`; Table VI.

**Problem and consequence:** The actual holdouts are **50 EN + 3 HI identical pairs and 17 EN + 0 HI unrelated pairs**. The 94.1% unrelated pass rate is therefore English-only. Repeating the same 17 pairs across seeds does not create new evidence or support a bilingual sanity claim. The tables hide these denominators and pool languages.

**Concrete fix:** Print counts and language-specific pass rates, mark Hindi unrelated as **not evaluated**, and create a separate reviewed Hindi holdout before claiming bilingual sanity coverage. Show per-seed rates as well as mean/SD so the identical-pair collapse is visible.

### 12. [MAJOR] Several paper statements contradict the artifacts or claim validation that was not recorded

**Location:** `paper/out/paper_ieee.md:85`; `paper/out/paper_ieee.md:100`; `paper/out/paper_ieee.md:110`; `paper/out/paper_ieee.md:124`; `paper/out/paper_ieee.md:212`; Section VII final paragraph; `src/agent_simplify.py:63`.

**Problem and consequence:** Specific corrections are required, not another general disclaimer:

- Section III-D says **339** pairs; the data/Table II contain **338** because one perturbation is absent.
- Section III-F says labels have “nothing at 6 or 7”. The final means contain **15 labels of 6 and 7 labels of 7**. This was apparently copied from one annotator's distribution. Even for an individual annotator, those values are not mathematically impossible under the rubric.
- Section III-E asserts token caps and that every generation terminated normally. The executed agent importer records **`max_tokens=None`** and unconditionally writes **`finish_reason='stop'`**. That field is not observed termination telemetry and cannot prove a cap was enforced or never reached.
- Section IV-A says the candidate backbones are each trained with/without DA, including IndicBERT v2. The stored runs contain XLM-R and MuRIL, not IndicBERT v2.
- Section V says the same code reproduces BERTScore's published FrJUDGE behaviour. `reports/frjudge_repro.md` documents cross-encoder runs, and the supplied reproduction log has no corresponding BERTScore result. A script capable of running it is not evidence it ran successfully.
- Section VII says FrJUDGE “is used only for this check”, contradicted by the central transfer experiment.

**Concrete fix:** Correct these statements in `paper/content.py`, derive counts/distributions from artifacts, describe agent-import status honestly, and either attach the claimed BERTScore validation output/config or remove the claim. Explicitly label naive versus calibrated LaBSE in the prose: 5.896/3.022 and Table VII's 4.629/2.254 are different mappings, not interchangeable numbers. The main E1–E4 table values and the FrJUDGE report's listed cross-encoder numbers otherwise agree at their reported precision.

### 13. [MAJOR] “Run the handover” actually executes whatever remote main happens to contain

**Location:** `run_all.py:48`; `run_all.py:61`; `modeling/kaggle/lmp_experiments.py:48`; `HANDOVER.md`, sections 0 and 3.

**Problem and consequence:** `push()` resolves `refs/heads/main`, not the checked-out handover commit. It combines local splits and a local kernel script with training code fetched from another revision. A fresh handover checkout therefore does not reproduce itself; a later main update can change its experiment without changing the user's checkout. The upstream FrJUDGE clone is also unpinned.

**Concrete fix:** Require an explicit, remotely available source commit, defaulting to the current clean checkout's commit, and pin the upstream dataset revision too. Record both hashes plus split hashes in each run. Do not silently fall back to main if the local commit is not pushed.

### 14. [MAJOR] Failed experiments and failed paper builds can be reported as completed

**Location:** `run_all.py:70`; `run_all.py:100`; `run_all.py:101`; `run_all.py:125`; `run_all.py:129`; `modeling/kaggle/lmp_experiments.py:85`; `modeling/kaggle/lmp_experiments.py:105`.

**Problem and consequence:** Kernel training is piped through grep/sed with `check=False`; a Python failure can still produce a successful-looking job completion message and a partial bundle. Collection treats error/cancelled states as collectible completion, ignores unpack failure and discards the pending item. Paper build failure is ignored before printing “reports/ ready”. Existing tracked run files can then supply stale results while the new run is incomplete. The test suite does not exercise these failure paths.

**Concrete fix:** Propagate subprocess failures, use pipefail or capture/filter logs after checking the training return code, validate the expected system/split/seed manifest, and refuse to publish mixed old/new results. A failed build must return failure. Add one mocked failure-path test for each stage rather than launching GPUs to test the runner.

### 15. [MAJOR] The delivered model cannot perform the advertised demo

**Location:** `modeling/kaggle/lmp_experiments.py:103`; `modeling/kaggle/lmp_experiments.py:121`; `modeling/predict.py:47`; `HANDOVER.md`, section 4 item 4; slide 15.

**Problem and consequence:** The local fine-tuning jobs do not save the selected model, and the return bundle includes only JSON/JSONL. No final checkpoint is supplied. `predict.py` requires `--model-dir`; the slide's `modeling/predict.py --demo` is incomplete. A future retraining plan is not an executable decision-output deliverable. The claim that the demo and annotations “cannot disagree” because they share a scoring function is also false: sharing decision thresholds does not make regression predictions equal rubric labels.

**Concrete fix:** Save and retrieve one explicitly selected final checkpoint and tokenizer, document its exact inference command and optional Gradio dependency, and test a real EN and HI prediction. Otherwise remove the demo claim and present only an offline prediction-file walkthrough, labelled as such.

### 16. [MINOR] Environment provenance is insufficient for a project whose key failure was version-specific

**Location:** `requirements.txt:2`; `modeling/requirements.txt:2`; `modeling/kaggle/lmp_experiments.py:53`; model `config.json` files.

**Problem and consequence:** Open-ended package lower bounds and unpinned model downloads do not reconstruct the environment that produced the reported numbers. Configs record hyperparameters and transient Kaggle model paths, but not a complete environment/model-revision manifest. This matters directly because tokenizer loading already changed behaviour between library versions.

**Concrete fix:** Keep the small requirements files, but add the resolved package versions, Python/CUDA versions, model revisions and artifact checksums for the reported run. Verify the documented minimum Python version separately; this audit executed Python 3.12, not a 3.10/3.11 environment. A second dependency-management framework is unnecessary.

### 17. [MAJOR] The final slide deck still claims experiments that never ran

**Location:** `paper/out/LMP_slides.pptx`, slides **7, 9, 10, 14, 15**; `paper/build_slides.py:205`; `paper/build_slides.py:235`; `paper/build_slides.py:270`.

**Problem and consequence:** Extracting the actual deck with python-pptx finds: slide 7 says **339** pairs above a **338** table; slide 9 says **five seeds**, includes **IndicBERT v2**, and lists an **LLM judge** as a baseline; slide 10 again includes the LLM judge in E1; slide 14 still has **`[TBD]`** for the FrJUDGE reproduction; slide 15 still has a **`[TBD: screenshot ...]`**. Slides 4/5/10/18 repeat the false controlled/RTI-only language claim. These are submission-visible contradictions, despite the coordination log claiming the deck was synchronized and placeholder-free.

**Concrete fix:** Correct the slide source, regenerate once, then extract and check **the built PPTX**, not just its source. Put the transfer setup before its result tables, identify the reference labels on result slides, and replace the unimplemented demo with an honest status slide or an actual working demo.

### 18. [MINOR] The document has IEEE-like columns, but its tables are not submission-ready

**Location:** `paper/out/LMP_paper_IEEE.pdf`, pages **5–6 and 8**; `paper/out/LMP_slides.pptx`, slides **11, 13, 19**.

**Problem and consequence:** Visual inspection shows Table III split across pages and Table VII split across columns without a repeated header. Table VIII squeezes ten columns into one text column: IDs, “EN”, “perturbed”, and even some numbers break over lines. The 11-page paper contains no explanatory figure and repeats the same causal/disclosure narrative at length. Slide 11 has a 14-system, six-column table using **14-point** text; slide 19 has roughly **1,230 characters**. This is difficult to read or defend live. No instructor page limit was provided, so I am **not** claiming eleven pages violates one.

**Concrete fix:** Use short model names and a two-column-spanning results/case table, repeat headers, remove the repeated “LLM judge not run” column, and move full cases/secondary baselines to an appendix. Replace a dense table slide with a small uncertainty plot and one original→changed-text example. Complete reference metadata rather than merely calling the list verified: for example [BLESS's official record](https://aclanthology.org/2023.emnlp-main.821/) supplies pages 13291–13309 and a DOI omitted from entry 2. I spot-checked BLESS and [JUDGEBERT](https://aclanthology.org/2025.emnlp-main.5/), not all thirteen references.

### 19. [MAJOR] Public-facing provenance still describes a different project, and generated reports call LLM labels human

**Location:** `README.md:10`; `DATASET_CARD.md:16`; `reports/results.md:3`; `reports/results.md:5`; `reports/agreement.md:9`; `CLAUDE.md`, sections 4 and 8.

**Problem and consequence:** README/dataset card still name **Claude + GPT-6 Astra**, say annotation is not completed, and leave planned counts. Generated results explicitly say **human-annotated test pairs** and **Human ceiling**, while the paper says the opposite. The living specification also retains five seeds/old hyperparameters in later sections. A reader should not have to reconstruct the final protocol from an agent chat log. Copying these reports into another document would actively misrepresent label provenance.

**Concrete fix:** Update the top-level README/card to the executed protocol and make the report generators use the actual annotation population. Separate historical/planned notes from final settings in the spec. Have one compact run manifest supply annotators, counts, seeds, model names and settings to both prose and slides.

## Data spot-check ledger

I compared the following **15 rows** in `pairs.jsonl` and `labeled_pairs.jsonl`, including both texts, injection descriptions and raw rater scores. References below are line numbers in `data/processed/labeled_pairs.jsonl`; the source pair IDs match. This is an adversarial targeted sample, **not** a random quality estimate or human legal adjudication. Scores are **A / B → mean**.

| Line / pair ID | Observation |
|---|---|
| 3 — `cpa-s10_1|en|perturbed` | `will`→`will not` reverses establishment. 4 / 1 → 2.5 exposes the bracket disagreement. |
| 46 — `cpa-s51_2|en|aggressive` | Saving clause disappears; “substantial question of law” becomes “important legal question”. Still 9 / 8 → 8.5. The reference target rewards a visibly weakened condition. |
| 48 — `cpa-s51_2|en|perturbed` | Leading saving clause removed as declared. 9 / 9 → 9: “injected error” does not imply the label calls it unsafe. |
| 123 — `rti-s11_2|hi|aggressive` | Ten-day period loses its receipt-of-notice start point and actors. 9 / 4 → 6.5; severe rater-policy disagreement. |
| 125 — `rti-s11_2|hi|perturbed` | `दस`→`पंद्रह` is present; both score 5. The original's cross-reference was agent-repaired from empty parentheses. |
| 129 — `rti-s11_3|hi|aggressive` | Drops the section 7 override, representation condition and request-receipt start date. 8 / 3 → 5.5. |
| 131 — `rti-s11_3|hi|perturbed` | `चालीस`→`तीस` is present; 5 / 5 → 5. |
| 137 — `rti-s11_4|hi|perturbed` | Entitlement to appeal becomes `अपील करेगा`; 5 / 5 → 5. Original section 19 reference was repaired from 9, so PDF verification matters. |
| 143 — `rti-s12_1|hi|perturbed` | `करेगा`→`कर सकेगा` changes the assigned-functions limb; establishment remains mandatory. 5 / 5 → 5. Do not describe this as reversing the entire provision. |
| 149 — `rti-s12_4|hi|perturbed` | Functions narrowed to `कुछ`, while the powers still say `सभी`; 5 / 5 → 5. The exact scope of the edit matters. |
| 154 — `rti-s12_6|hi|normal` | `विधान-मंडल`→`विधानसभा` is already flagged by B, but receives 10 / 9 → 9.5. The base is not error-free. |
| 169 — `rti-s14_1|hi|normal` | B flags `हटाया जाएगा`→`हटाया जा सकेगा`; 10 / 9 → 9.5. This needs independent review, not my replacement label. |
| 180 — `rti-s15_5|hi|aggressive` | Omits the Chief Commissioner and uses an open illustrative list. 9 / 4 → 6.5. |
| 182 — `rti-s15_5|hi|perturbed` | `होंगे`→`हो सकेंगे` changes the eminence requirement; knowledge/experience sentence remains. 5 / 5 → 5. |
| 200 — `rti-s16_1|hi|perturbed` | Age-65 proviso removed as declared; 5 / 5 → 5. Original still contains `.'ऐसी` extraction residue. |

Supplementary check: row **155**, the perturbed counterpart of row 154, preserves the legislature/assembly narrowing and adds negation removal. This directly falsifies interpreting “one injected error” as “one total error”. The first adjudication rows also show score gaps of six, not just the isolated negation convention described in the paper; none has a recorded resolution.

## Validation and limits of this review

- `python -m pytest -q`: **46 passed, 0 failed, 0 skipped**, 83.74 seconds. Also ran the documented venv explicitly: **46 passed**, 27.42 seconds. Passing synthetic tests does not validate statutory accuracy or the experiment descriptions.
- Recomputed Pearson/RMSE/MAE for **82 stored test-prediction files** against their per-run `metrics.json`: no discrepancies above `1e-8`.
- Ran existing `check_disjoint` on all **five** committed random/OOD split directories with the holdouts: all pass. This test does not check the OOD partner-act restriction identified in finding 4.
- Inspected the generated Markdown, table TSVs, reproduction report/log, relevant training/data/reporting paths, all 20 slides' text, and PDF page renders **1, 4, 5, 6, 7, 8 and 11**. The PDF has 11 pages; its abstract is no longer the main formatting issue.
- Assumed a course-project CLI run by one operator, not a production multi-user service. No GPU retraining, paid API calls, report regeneration, repository push, destructive command or project-code/data edit was performed.
- Did not independently repeat OCR, certify Hindi against every PDF page, audit all upstream French split contents, reproduce the pretrained baseline inference, render the slides in PowerPoint, or verify all thirteen references. Missing saved checkpoints prevent an actual reported-model inference test.
- Untracked human-annotation work appeared during the review (`data/annotation/human/`, `src/make_human_sheets.py`); it was not authored, changed or treated as completed annotation by this review. Findings refer to the tracked release and its current built deliverables.

## Top five fixes before submission

1. **Resolve the human-label requirement:** collect the required judgements or obtain an explicit instructor-approved scope reduction. A pilot does not meet the 300-pair condition.
2. **Repair the experimental claims:** RTI-matched E2; source-act-only DA for E3; explicit system/family/seed provenance for E5. Rerun affected experiments or relabel the existing results honestly.
3. **Correct the interpretation and visible contradictions:** remove the 0.723 ceiling/causal-scale claims; fix the 338/339 count, label histogram, fabricated termination inference, unrun-model claims, stale slide placeholders and “human” report headings.
4. **Validate the reference data:** independent Hindi/source-page review and adjudication of the 68 disagreements; report per-rater, within-variant and language-specific sanity results rather than hiding these weaknesses in a pooled correlation.
5. **Make the submission runnable and readable:** pin the actual code/data revision, fail on incomplete runs, retrieve one final checkpoint, and rebuild/proofread the Word/PDF/PPTX with readable tables and an executable inference command.
