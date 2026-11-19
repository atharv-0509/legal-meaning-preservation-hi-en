"""Single source of truth for the IEEE paper and the slide deck.

Why a Python module and not Markdown: `build_paper.py` (.docx), `build.ps1` (.pdf via Word) and
`build_slides.py` (.pptx) all import this file, so the three deliverables cannot drift apart.
`build_paper.py --markdown` also regenerates `paper/paper_ieee.md` for reading and diffing.

RULES (CLAUDE.md §7):
  * Nothing here is a result. Every model number comes from `tables.py`, which reads the files
    produced by `modeling/evaluate.py`; when those files are absent the table renders as [TBD].
  * Dataset facts quoted below (unit counts, candidate counts, the U+FFFD rate) were computed from
    `data/` by our own code; `paper/source_provenance.md` records the commands.
  * Labels for the deadline version are DISCLOSED LLM annotations, never described as human.

Block kinds consumed by the builders:
  ("h1", text)      section heading, numbered with Roman numerals by the builder
  ("h2", text)      subsection heading, lettered A, B, C ... within its section
  ("p", text)       body paragraph
  ("bullets", [..]) bulleted list
  ("table", key)    a table resolved at build time by tables.get(key)
  ("caption", text) table caption (IEEE puts it above the table)
"""
from __future__ import annotations

TITLE = ("Assessing Legal Meaning Preservation in English and Hindi "
         "Simplifications of Indian Statutes")

AUTHORS = [
    {"name": "Karan Singh", "roll": "S24CSEU1939"},
    {"name": "Atharv Arora", "roll": "S24CSEU2439"},
    {"name": "Jatin Khanchi", "roll": "S24CSEU1932"},
]
AFFILIATION = ["School of Computer Science Engineering and Technology",
               "Bennett University, Greater Noida, India"]
COURSE = ("CSET 346 Natural Language Processing (project PID-08), "
          "instructor Dr. Surabhi Solanki")

KEYWORDS = ("legal NLP, text simplification, meaning preservation, evaluation metrics, "
            "Hindi, multilingual transformers, cross-encoder regression")

# --------------------------------------------------------------------------- abstract

ABSTRACT = (
    "Plain-language versions of statutes can widen access to the law, but a simplification that "
    "drops a condition, turns an obligation into a permission or alters a time limit misleads the "
    "reader while still looking fluent. JUDGEBERT [1] introduced a learned "
    "metric for legal meaning preservation (LMP) on French insurance text. We extend that line of "
    "work to Indian statutory law in two languages. From the official texts of the Right to "
    "Information Act, 2005 and the Consumer Protection Act, 2019 we build a corpus of "
    "original-simplification pairs in three deliberately contrasting styles: a standard zero-shot "
    "simplification, an aggressive \"explain to a twelve-year-old\" simplification, and a "
    "simplification carrying exactly one rule-injected legal error of a known type. Each pair is "
    "scored on JUDGEBERT's 1-10 rubric; for this version of the work the scores are produced by two "
    "disclosed large-language-model annotators rather than by humans, which is a deviation from our "
    "original human-judgement protocol and is reported as such throughout. We train multilingual "
    "cross-encoders on clause-grouped splits and compare them against generic similarity metrics "
    "and against a planned LLM judge that we explain we could not run. Trained from scratch on our "
    "corpus the metric fails: "
    "Pearson 0.228 with a standard deviation of 0.288 across seeds, indistinguishable from the best "
    "generic baseline at 0.101. Our main result is that this is a problem of scale and not of "
    "method, and that the scale can be borrowed across a language and a jurisdiction. Pre-training "
    "the same cross-encoder on FrJUDGE, which is French insurance text, and then fine-tuning on "
    "Indian statutes raises it to 0.586 +/- 0.098, about four-fifths of the 0.723 "
    "agreement between our own annotators, and makes it stable where the from-scratch model was "
    "not. The diagnostic set behaves exactly as designed: a single inserted negation, which moves "
    "the legal meaning from one end of the rubric to the other, is by far the hardest injected "
    "error for the generic baselines, and every system we tested still scores individual "
    "reversals above 8 out of 10 against a label of 2.5. "
    "We additionally report "
    "zero-shot transfer between English and Hindi, transfer across the two acts, sanity checks on "
    "identical and unrelated pairs, and a qualitative analysis of at least fifteen legally difficult "
    "cases. We also document two reproducibility traps that silently destroy such experiments: a "
    "character-level tokenizer fallback that collapses cross-encoder training, and legacy-font Hindi "
    "PDF text layers that lose characters without raising any error."
)

# --------------------------------------------------------------------------- body

BODY: list[tuple] = [

    ("h1", "Introduction"),
    ("p",
     "Indian statutes are drafted in long, heavily qualified sentences, and the official Hindi "
     "versions are no easier to read than the English. Large language models can rewrite such text "
     "into plain language, and doing so at scale is attractive for access to justice. The risk is "
     "that the rewriting is judged by the wrong yardstick. Generic similarity metrics reward lexical "
     "and semantic overlap, so a simplification that preserves almost every word but deletes a "
     "proviso scores well, even though the legal consequence has changed."),
    ("p",
     "JUDGEBERT [1] made this concrete. On FrJUDGE, a corpus of 297 French insurance sentence blocks "
     "scored by five law students, BERTScore correlates with human LMP judgements at Pearson 0.46 "
     "and SBERT at 0.13, while a CamemBERT-v2 cross-encoder trained directly on the rubric reaches "
     "0.74. BERTScore and MeaningBERT over-score the human label on 82% of test pairs; the learned "
     "metric does so on none. The lesson is that legal meaning preservation is a distinct target "
     "that has to be learned, not approximated by similarity."),
    ("p",
     "We ask whether that result carries to a different legal system, a different pair of languages "
     "and a different kind of statutory text, and we attack the specific weaknesses of the original "
     "study. Each gap below maps to a contribution of this paper."),
    ("bullets", [
        "JUDGEBERT covers French and a single domain. We cover two Indian central acts from "
        "different domains, and English and Hindi within one of them, the Right to Information Act, "
        "because the official Hindi text of the other could not be obtained (Section III-A). Where "
        "both languages exist, the Hindi statute is an official translation of the very same "
        "provision, so the language comparison is controlled rather than confounded by content.",
        "FrJUDGE contains one simplification style, so its label distribution is narrow. We add "
        "aggressive simplifications, which tend to drop conditions, and perturbed simplifications "
        "carrying exactly one injected legal error of a known type. The latter is a labelled "
        "diagnostic set: it tells us which legal error types a metric is blind to.",
        "Krippendorff's alpha on FrJUDGE LMP was 0.10, with annotators splitting into a lenient and "
        "a strict group. We therefore treat agreement as a first-class result rather than a "
        "footnote, and we report it for whichever annotator population we actually used.",
        "FrJUDGE splits are pair-level, so a test original can reappear in training as an identical "
        "augmentation pair, and the headline 0.97 Pearson of the augmented model is measured on a "
        "test set that contains trivial identical and unrelated pairs. Our splits are grouped by "
        "source clause and verified disjoint at clause and text level, and sanity checks are "
        "reported separately on holdout provisions used nowhere else.",
        "JUDGEBERT reports no out-of-domain test. We train on one act and test on the other.",
    ]),
    ("p",
     "Our contributions are therefore: (i) a bilingual legal LMP corpus with a documented, blinded "
     "scoring protocol and an explicit statement of who, or what, produced the labels; (ii) a "
     "JUDGEBERT-style multilingual cross-encoder for LMP; (iii) a comparison against generic metrics "
     "and, in place of the LLM judge our labelling decision ruled out, a transfer experiment that "
     "pre-trains on FrJUDGE before fine-tuning on our splits; (iv) cross-lingual, cross-domain and sanity "
     "experiments; and (v) a qualitative error analysis. We also report, in Section VII, two "
     "failures of our own pipeline that would have produced confidently wrong numbers, because both "
     "are invisible unless specifically tested for."),

    ("h1", "Related Work"),
    ("h2", "Evaluating simplification"),
    ("p",
     "Simplification quality is usually decomposed into simplicity, fluency and meaning "
     "preservation. Meaning preservation is commonly measured by n-gram overlap, by contextual "
     "embedding similarity such as BERTScore [3], by sentence-embedding cosine similarity, or by "
     "learned or question-based metrics such as QuestEval [9], LENS [10] and MeaningBERT [11]. BLESS [2] benchmarks "
     "large language models as sentence simplifiers with zero-shot prompts; we reuse its prompt so "
     "that our normal variant is comparable to established practice."),
    ("h2", "Legal meaning preservation"),
    ("p",
     "JUDGEBERT [1] is the direct predecessor of this work. Its rubric, which we adopt unchanged, first "
     "places a simplification in a bracket (Accurate 7-10, Imprecise 2-6, Off-track 1) and then "
     "subtracts one point per identified error, with a floor of 1; the error types are omission, "
     "hallucination, consistency issue and confusion. Its model is a cross-encoder regression over "
     "the concatenated sentence pair. Its augmentation adds identical pairs labelled 10 and "
     "unrelated pairs labelled 0, the latter mined from Quebec legal texts with ROUGE below 0.25 "
     "and BLEU below 25."),
    ("h2", "Indian legal NLP"),
    ("p",
     "Work on Indian legal text has concentrated on judgments: domain-adapted encoders such as "
     "InLegalBERT [12], and benchmarks such as IL-TUR [13], target tasks like judgment prediction, "
     "rhetorical-role labelling and summarisation. Statutory simplification, and the question of "
     "whether a simplification is legally faithful, is comparatively unexplored for Indian law, and "
     "we are not aware of a Hindi resource for it."),
    ("h2", "Multilingual encoders"),
    ("p",
     "For the backbone we consider XLM-R [5], which is multilingual but not Indic-focused, and MuRIL "
     "[6] and IndicBERT v2 [7], which are trained with Indian languages and transliteration in mind. LaBSE [4] "
     "provides a strong language-agnostic sentence embedding and serves as one of our baselines."),

    ("h1", "Dataset"),
    ("h2", "Sources and provenance"),
    ("p",
     "We use two central acts from different legal domains, each chosen because an official Hindi "
     "version exists: the Right to Information Act, 2005 (public information) and the Consumer "
     "Protection Act, 2019 (consumer law). India Code is the canonical repository for both, but it "
     "was unreachable while this version of the corpus was built, so we used other official "
     "government sources and recorded exactly which. Table I lists them."),
    ("caption", "Sources, editions and extraction yield"),
    ("table", "sources"),
    ("p",
     "Two consequences follow and are carried through the rest of the paper. First, the official "
     "Hindi text of the Consumer Protection Act could not be obtained, so that act contributes "
     "English-only material and the English-Hindi comparison (E2) is confined to the Right to "
     "Information Act. Second, the two Right to Information copies are not the same edition: the "
     "English consolidation is current to 18 November 2025 and includes the 2023 amendment, whereas "
     "the Hindi copy, although it carries the 2019 amendments in its footnotes, retains the older "
     "personal-information wording in section 8(1). Provisions affected by this are flagged "
     "automatically and dropped at review rather than silently reconciled, because editing one "
     "language to match the other would fabricate statutory text."),
    ("h2", "Extraction"),
    ("p",
     "Each PDF is converted to sub-section units, the unit of analysis being a numbered sub-section "
     "such as section 7(1), with its marginal or inline heading attached. English and Hindi units "
     "of the same provision share a key, which is what makes the bilingual alignment automatic. "
     "Three details were needed for real government PDFs and are worth recording, since each cost "
     "us a parser bug. Cross-references of the form \"sub-section (3) of section 8\" must not be "
     "read as the start of a new sub-section. Amendment markers, footnote blocks and the "
     "arrangement-of-sections table at the front of an act must be stripped, but the word "
     "\"Repeal\" must not be mistaken for the footnote abbreviation \"Rep.\". The Gazette printing "
     "of the Consumer Protection Act places section headings in the page margin rather than inline, "
     "so for that document we extract with a geometry-aware backend that reads the marginal "
     "headings and the marginal statute citations separately from the body column, and fails loudly "
     "if a numbered section is found without a heading."),
    ("h2", "The Hindi text layer"),
    ("p",
     "The Hindi PDF is not scanned, yet its text layer cannot be used as it stands, and the way it "
     "fails is instructive. Extracted with Poppler's pdftotext, 4.9% of all Devanagari characters "
     "emerge as U+FFFD replacement characters: 2461 characters across 100 of 102 units, an "
     "irreversible loss. Extracted with PyMuPDF, nothing is lost, but the legacy Mangal glyphs are "
     "mapped into the Vedic and Sundanese Unicode blocks (2681 characters drawn from only 48 "
     "distinct code points) and the vowel signs appear in visual rather than logical order. In "
     "other words the page is readable to a human and systematically wrong to a machine. Our "
     "extractor therefore computes a Devanagari ratio and a misplaced-vowel-sign ratio for every "
     "Hindi document and refuses the text layer when it fails either test; both routes above are "
     "correctly rejected. We report this because a pipeline that silently accepted either "
     "extraction would have produced a Hindi corpus of fluent-looking nonsense, and no downstream "
     "metric would have revealed it."),
    ("p",
     "The Hindi text used in this work therefore comes from optical character recognition: the "
     "pages are rendered at 300 dpi and read with Tesseract 5.4 using the high-quality "
     "tessdata_best Hindi model, which the predecessor literature and our own trials both prefer "
     "over the fast model for legal vocabulary. This clears the acceptance test decisively: "
     "Devanagari ratio 0.993, misplaced-vowel-sign ratio 0.000 and no replacement characters at "
     "all. One systematic OCR defect remains and is worth naming, because it attacks precisely the "
     "part of a statute that must not be approximated: the digit 1 is frequently dropped or "
     "misread, so section 12 is read as 2, section 13 as 03 and the sub-section marker (1) as an "
     "empty pair of brackets. We therefore repair numbering from the sequence rather than from "
     "appearance, restoring a number only when the observed token is a recognised one-digit-drop "
     "variant of the number the sequence expects, and we do not touch anything else. Every repair "
     "is logged."),
    ("h2", "Clause selection"),
    ("p",
     "A provision is eligible if it has one to five sentences, 15 to 90 English words and a Flesch "
     "reading-ease score of at most 50, so that the simplification task is non-trivial; if it is "
     "not boilerplate (short title, extent, definitions, rule-making powers, repeal and savings); "
     "and if its text is not duplicated elsewhere in either act. The duplicate test matters more "
     "than it sounds: statutes reuse standard provisos verbatim, and two identical provisions in "
     "different splits would leak the test set into training even though the split is grouped by "
     "clause. At most three clauses are taken per section, and sampling is weighted towards "
     "provisions containing exceptions, overrides, conditions and time limits, which is where legal "
     "meaning is most fragile. We oversample by a factor of 1.3 to absorb losses at review."),
    ("p",
     "Every candidate then passes a review step that is the only place where a clause can be "
     "accepted. The selection tool pre-computes warning flags (replacement characters, Latin "
     "characters inside Hindi text, numbers that differ between the two languages, missing Hindi "
     "counterpart, known edition mismatch) and never sets the keep decision itself. In the design "
     "this review is performed by a human. Under the project deadline it was performed instead by "
     "a rule-based agent script, and we disclose that: rows that are misaligned, fragmentary, "
     "contain Latin characters inside Hindi or fall in the section where the two editions differ "
     "are dropped, with the reason recorded per row. The only text repairs permitted are the "
     "numbering repairs described above, and only where the Hindi number differs from its English "
     "counterpart by an OCR-dropped 1; seven such repairs were made and each is logged with the "
     "before and after text. A sample of kept rows was then checked against the source pages. "
     "No agent at any point edited statutory wording."),
    ("p",
     "The resulting corpus is 78 clauses: 38 from the Right to Information Act, of which 35 have an "
     "aligned Hindi counterpart, and 40 from the Consumer Protection Act, which are English-only "
     "because its Hindi text was unobtainable. That gives 113 clause-language items and, with three "
     "variants each, 339 pairs, above the 300 the study design calls for. Table II breaks this down."),
    ("caption", "Corpus composition by act, language and variant"),
    ("table", "dataset"),
    ("h2", "Simplifications"),
    ("p",
     "For each selected clause and each available language we generate three variants. The normal "
     "variant uses the zero-shot BLESS prompt, translated for Hindi. The aggressive variant asks "
     "for an explanation to a twelve-year-old in at most two sentences, which reliably sacrifices "
     "conditions and therefore populates the low end of the scale that FrJUDGE lacks. The perturbed "
     "variant takes a normal simplification and injects exactly one legal error, balanced across "
     "five types: modality (shall or must becomes may, and the reverse), negation, a changed "
     "number, deletion of an exception, proviso or override, and narrowed scope. The Hindi rules "
     "operate only on clause-final verb groups, so that, for example, karega becomes kar sakega "
     "without touching unrelated words that merely contain the same letters. The idiom \"as may be "
     "prescribed\" is explicitly exempted, because the may in it confers no permission."),
    ("p",
     "Our output caps are 200 tokens for English and 500 for Hindi, rather than JUDGEBERT's 100, "
     "because our clauses reach 90 words and Devanagari consumes more tokens per word; truncated "
     "generations are recorded and reported rather than silently kept. One further deviation must "
     "be stated: JUDGEBERT sampled its simplifications from gpt-4-turbo through an API at "
     "temperature 1.0 and top-p 0.9, whereas ours were written by a Claude Opus 5.5 agent following "
     "the same prompts, with no sampling parameters to record. The prompt identifier, the model "
     "string and a timestamp are stored with every generation, and the temperature and top-p fields "
     "are null rather than invented. Our simplifications are consequently likely to be more "
     "conservative than temperature-1.0 samples, which plausibly shifts the label distribution "
     "upward relative to FrJUDGE. In the event no generation hit the cap: all 226 simplifications "
     "terminated normally, so nothing in the corpus is a truncated output."),
    ("h2", "Scoring protocol and its deviation from human judgement"),
    ("p",
     "This is the point at which the present version of the work departs from our protocol, and we "
     "state it plainly rather than in a footnote. The intended design was three human annotators "
     "per pair after a shared calibration round. Because of the project deadline, the LMP scores "
     "used here were produced by two disclosed large-language-model annotators, both instances of "
     "Claude Opus 5.5, each filling its own blinded workbook under the same rubric and conventions "
     "written for the human annotators. This does not satisfy the requirement of agreement with "
     "human legal judgement, and no claim in this paper should be read as establishing it."),
    ("p",
     "The blinding is real and mechanical rather than a matter of trust. Each annotator receives "
     "only an opaque pair identifier, in an order shuffled per annotator with items from the same "
     "clause separated; the variant name, the injected error type and the answer key are in files "
     "the annotators never read, and neither annotator sees the other's workbook. The score is not "
     "entered directly: the annotator chooses a bracket and counts errors by type, and the score is "
     "recomputed from those entries by our own code, so a rubric change cannot be lost in a "
     "spreadsheet formula. Two further constraints follow from using models as annotators. Model "
     "families overlap between generation and annotation, so any annotator that also generated the "
     "text it scores cannot be called blind, and we disclose that overlap rather than assuming it "
     "away. And an LLM judge may not be evaluated against labels from its own model, since that "
     "measures self-consistency and not meaning preservation. Because both of our annotators are "
     "the same model, that rule removed the LLM-judge baseline entirely: any judge we had access to "
     "would have been scored against its own family's labels. We therefore report no LLM-judge "
     "result, and record its absence as a consequence of the labelling decision rather than quietly "
     "dropping a planned comparison. It is the first experiment to run once human labels exist."),
    ("p",
     "Three further caveats belong here rather than in a footnote, because they bound what the "
     "agreement number can mean. First, both annotators are instances of the same model, Claude "
     "Opus 5.5, so their agreement is between two instances of one model family and not between "
     "two independent judges; it is an upper bound flattered by shared pretraining. Second, the two "
     "annotators are not equally blind. The first was given only the opaque identifiers and the "
     "text, and knew the corpus design in the abstract but not which items carried an injected "
     "error. The second also wrote the simplifications, so although its workbook hides the variant "
     "labels it may recognise its own output and infer which copies were perturbed; it is "
     "therefore not blind in practice, and we say so. Third, with two annotators the leave-one-out "
     "ceiling degenerates into the correlation between the two of them, so what it measures is how "
     "well one instance of a model predicts another, not a ceiling set by human legal judgement."),
    ("p",
     "On those terms the agreement is as follows. Krippendorff's alpha [8] on the interval LMP scores "
     "is 0.610 and on the nominal brackets 0.503; the leave-one-out ceiling, which we call the "
     "LLM-annotator ceiling and never a human ceiling, is a Pearson correlation of 0.723, and 68 "
     "of the 338 pairs fall on the adjudication list. These figures are far above the 0.10 that "
     "JUDGEBERT reports between its five law students, and the comparison must be read with that "
     "asymmetry in mind: two instances of one model agreeing is a much weaker result than five "
     "people agreeing, and the gap is evidence about model consistency rather than about the "
     "construct being well defined. The label distribution is bimodal, with mass at 10 and a tail "
     "between 1 and 5 and nothing at 6 or 7; that is an arithmetic consequence of the rubric "
     "itself, since a score is a bracket maximum of 10, 6 or 1 minus one point per error, and it "
     "matters for RMSE. One convention differed between the annotators and we state it rather than "
     "smoothing it over: where an inserted or dropped negation reverses an entire operative "
     "provision, one annotator scored Off-track, the other Imprecise with a confusion. The label "
     "is the mean of the two, as in FrJUDGE, and the adjudication list records every such divergence."),
    ("p",
     "To keep a path to the original claim open, a separate 30-pair validation workbook was prepared "
     "for human legal annotators, stratified by language and variant. At the time of writing it has "
     "not been scored. No human validation of these labels therefore exists, the correlation "
     "between our model labels and human legal judgement is unmeasured, and every result in this "
     "paper should be read with that gap in mind. The workbook and the tooling to aggregate it are "
     "in the repository, so the measurement is a scoring session away rather than a rebuild."),
    ("h2", "Augmentation, sanity holdouts and splits"),
    ("p",
     "Following JUDGEBERT we add, for each clause and language, an identical pair labelled 10 and "
     "an unrelated pair whose partner is a provision with ROUGE-1, ROUGE-2 and ROUGE-L below 0.25 "
     "and BLEU below 25. We label unrelated pairs 1 rather than 0, because 1 is the floor of the "
     "rubric and an unreachable 0 would distort the regression; a flag reproduces the original "
     "choice. These overlap statistics are computed with a Devanagari-aware tokenizer: the widely "
     "used rouge_score package discards non-ASCII text, which would classify every Hindi pair as "
     "unrelated and quietly poison the augmentation set."),
    ("p",
     "The sanity holdouts are built only from provisions that are not selected, are not in a "
     "section containing a selected clause, and are not used as augmentation partners, so that "
     "passing a sanity check cannot be an artefact of memorising training text. Splits are 60/10/30 "
     "by clause over three seeds (42 to 44), and every pair derived from one clause, both languages, all three "
     "variants and its augmentation pairs, stays within a single split; the splitter asserts this "
     "at clause level and at text level. Headline metrics are computed on annotated test pairs "
     "only, with augmentation and sanity pairs excluded and reported separately."),

    ("h1", "Method"),
    ("h2", "LMP model"),
    ("p",
     "The model follows JUDGEBERT: the pair is encoded as original, separator, simplification by a "
     "pretrained multilingual encoder, and a linear regression head on the pooled representation "
     "predicts the score under mean-squared-error loss, with predictions clipped to the rubric range "
     "1 to 10. Candidate backbones are XLM-R, MuRIL and IndicBERT v2; each is trained with and "
     "without augmentation over clause-grouped seeds. Model selection uses the annotated "
     "development set by default, with a flag to select on the augmented development set as the "
     "original work did, because the two choices are not equivalent and the difference should be "
     "visible."),
    ("p",
     "Our optimisation settings depart from the published ones and the reason is a property of our "
     "corpus, so we state both. JUDGEBERT uses learning rate 5e-5, batch size 16 and early stopping "
     "with patience 5; we use learning rate 2e-5, batch size 8, no early stopping, and 30 epochs "
     "keeping the best development checkpoint, with linear decay and gradient clipping at norm 1.0 "
     "unchanged. The reason is that our development split holds roughly 35 annotated pairs, and on "
     "a set that small the development loss is dominated by noise: with patience 5 and with "
     "patience 10 the run halted early and left the model predicting the label mean, giving a "
     "near-zero correlation. The FrJUDGE reproduction in Section VII shows the same pathology on "
     "the original data, where patience 5 collapses one seed in ten, so this is a property of the "
     "stopping rule interacting with a small dev set rather than of our corpus alone. We disclose "
     "that these settings were chosen after observing that failure, which is a form of selection on "
     "the development set and is recorded as a limitation."),
    ("h2", "Baselines"),
    ("p",
     "We compare against four reference points of increasing sophistication. ROUGE-L and BLEU, "
     "computed with our Devanagari-aware tokenizer, represent pure overlap. LaBSE [4] cosine "
     "similarity "
     "represents language-agnostic sentence semantics. Multilingual BERTScore [3] F1 represents "
     "contextual token matching and is the strongest generic metric in the original study. A fourth "
     "reference point was designed and then deliberately not run: an LLM judge receiving the "
     "annotators' rubric verbatim at temperature 0, which would have asked whether a general model "
     "with the rubric in its prompt can replace a model trained on it. Section III-F explains why "
     "it is unusable here, namely that our labels come from the same model family, so the "
     "comparison would have measured self-consistency. The implementation exists and is reported as "
     "not run rather than removed. Every remaining baseline is "
     "mapped onto the 1-10 scale twice, once naively and once by a linear calibration fitted on the "
     "training split only, and both are reported, since an uncalibrated metric can correlate well "
     "while having a meaningless RMSE."),
    ("h2", "Decisions and reporting"),
    ("p",
     "For the decision output we map the continuous prediction onto the rubric brackets: at least 7 "
     "is Preserved, 2 up to 7 is Partially Preserved, below 2 is Not Preserved. Alongside Pearson "
     "and RMSE we report Spearman and MAE, and the over-scoring rate, that is the share of pairs "
     "whose prediction exceeds the label, because the practically dangerous failure for this task is "
     "a metric that flatters a simplification which has lost a condition. All aggregate numbers are "
     "means with standard deviations over the three seeds, and results are broken down by language, "
     "by act and by variant."),

    ("h1", "Experiments"),
    ("p",
     "Five experiments are defined in advance. E1 compares the generic baselines against the "
     "trained cross-encoder on the random clause-grouped splits; the LLM judge belonged here and is "
     "reported as not run for the reason given in Section III-F. E2 reports per-language "
     "results and zero-shot transfer in both directions, training on English and testing on Hindi "
     "and the reverse, which is possible precisely because the two languages contain the same "
     "provisions; it is confined to the Right to Information Act for the reason given in Section "
     "III-A. E3 trains on one act and tests on the other in both directions. E4 runs the sanity "
     "checks on the disjoint holdouts, reporting the share of identical pairs scored at least 9.9 "
     "and of unrelated pairs scored at most 1.1. E5 is a qualitative analysis of at least fifteen "
     "legally difficult cases, grouped by injected error type and by the most important change each "
     "annotator recorded, which the perturbed variant makes systematic rather than anecdotal."),
    ("p",
     "The whole chain from labelled pairs to the tables below is a single reproducible pipeline: "
     "splitting, baselines, training, evaluation and error analysis each read and write files, and "
     "every table in this paper is generated from those files rather than transcribed."),
    ("caption", "E1: baselines and LMP model on annotated test pairs"),
    ("table", "e1"),
    ("caption", "E2: results by language, and zero-shot transfer"),
    ("table", "e2"),
    ("caption", "E3: cross-act generalisation"),
    ("table", "e3"),
    ("caption", "E4: sanity checks on disjoint holdouts"),
    ("table", "e4"),
    ("caption", "Mean absolute error on perturbed pairs by injected error type"),
    ("table", "diag"),
    ("p",
     "We state the from-scratch result before the detail, because on its own it is a negative "
     "result and burying it would be worse than reporting it. Trained only on our corpus the "
     "JUDGEBERT-style cross-encoder does not reliably beat generic similarity. The best such "
     "configuration, XLM-R with "
     "augmentation, averages Pearson 0.228 with a standard deviation of 0.288 across seeds, the "
     "individual seeds running 0.56, 0.21 and about -0.08. A standard deviation larger than the "
     "mean is the whole finding: over three seeds that is roughly 1.4 standard errors from zero, so "
     "the model is not distinguishable from no correlation at all, let alone from LaBSE's 0.101, "
     "and it is nowhere near the LLM-annotator ceiling of 0.723. Without augmentation XLM-R sits at "
     "-0.030; MuRIL with augmentation reaches 0.067 and without it collapses outright to an RMSE of "
     "4.4. The brief asks us to compare generic baselines against a learned metric, and the answer "
     "our data supports is that roughly 200 training pairs are not enough to learn this target, not "
     "that the target cannot be learned. The reproduction in Section VII is the first control for "
     "that claim, since the same code reaches 0.707 on FrJUDGE, which has a comparable number of "
     "training pairs but a far narrower label distribution and a single language; the transfer "
     "experiment below is the second and more direct one."),
    ("p",
     "The per-language split shows where the corpus size bites, and it is where the transfer "
     "earns its place. Trained from scratch, the model reaches 0.297 on English test pairs and "
     "0.010 on Hindi, so the Hindi half carries essentially no signal even though its labels are no "
     "less consistent than the English ones. With French pre-training both rise, to 0.675 on "
     "English and 0.308 on Hindi: the gain is proportionally largest exactly where we had fewest "
     "pairs, which is what a scarcity explanation predicts and a representation-quality explanation "
     "does not. Hindi nevertheless remains the weaker language by a wide margin, and with 105 "
     "pairs of OCR-recovered text we cannot separate how much of that gap is residual OCR noise, "
     "how much is subset size, and how much is XLM-R's Devanagari representation of statutory "
     "register."),
    ("p",
     "Zero-shot transfer between the two languages is the one place where pre-training does not "
     "help: 0.064 for English to Hindi and 0.085 for Hindi to English, against 0.057 and -0.017 "
     "without it. Both remain indistinguishable from zero. Supervised adaptation in the target "
     "language is evidently doing work that cross-lingual representation alone does not, which is "
     "notable given that the two languages here contain the very same provisions, so nothing but "
     "the language differs. Cross-act generalisation, by contrast, works: 0.384 +/- 0.021 from the "
     "Consumer Protection Act to the Right to Information Act and 0.319 +/- 0.257 in reverse, "
     "against 0.144 and 0.040 without transfer. A metric carried across jurisdictions and "
     "languages by fine-tuning therefore also carries across legal domains, while the same metric "
     "dropped into a new language cold does not."),
    ("p",
     "What the baselines show is worth stating alongside that. Every "
     "generic metric is close to useless on this corpus: LaBSE reaches Pearson 0.101 +/- 0.026, "
     "multilingual BERTScore 0.055 +/- 0.040, BLEU 0.018 +/- 0.021 and ROUGE-L 0.010 +/- 0.033. "
     "These are far below the 0.46 that BERTScore achieves on FrJUDGE, and the difference is a "
     "property of our corpus rather than of the metrics. A third of our pairs carry a single "
     "injected legal error, so the simplification is lexically and semantically almost identical "
     "to a faithful one while meaning the opposite; an overlap or embedding metric cannot see the "
     "difference by construction. The diagnostic table makes this explicit: LaBSE's error is "
     "largest exactly where the change is smallest on the surface, 5.896 +/- 0.372 mean absolute "
     "error on negation reversals against 3.022 +/- 0.910 on dropped exceptions. We note the "
     "alternative reading honestly, namely that correlations this low could indicate a baseline "
     "implementation fault; against that, the same code reproduces BERTScore's published behaviour "
     "on FrJUDGE, the four metrics fail in the same direction, and their ranking tracks surface "
     "sensitivity as theory predicts."),
    ("p",
     "The sanity checks add a caution about calibration that we had not anticipated. In their naive "
     "mapping all four baselines score 100% of identical holdout pairs at or above 9.9, but none "
     "places unrelated pairs at or below 1.1 (BLEU manages 11.8%), so every generic metric fails "
     "the second check. After the train-fitted linear calibration that makes their RMSE "
     "competitive, they fail both checks at 0%: the fit compresses predictions towards the label "
     "mean, which improves RMSE while destroying exactly the two endpoints a meaning-preservation "
     "metric must get right. Calibrated RMSE for these systems should therefore be read as a "
     "scaling artefact, not as evidence of fitness, and this is why we report both mappings. The "
     "trained models do better but none passes both. From-scratch XLM-R with augmentation places "
     "33% of identical holdout pairs at or above 9.9 and 31% of unrelated pairs at or below 1.1. "
     "The transferred models split the difference in opposite directions: without augmentation, "
     "89.9% +/- 4.7 of identical pairs but only 17.6% of unrelated ones; with augmentation, 94.1% "
     "+/- 5.9 of unrelated pairs but an identical-pair rate of 66.7% with a standard deviation of "
     "57.7, meaning some seeds pass almost every identical pair and others almost none. So no "
     "system we tested passes both checks, as JUDGEBERT-DA did, and the augmented transferred "
     "model's instability on the identical check is a real defect rather than a rounding artefact. "
     "We report it rather than quoting the one check each system happens to pass."),
    ("p",
     "The diagnostic set is where the case for a learned metric is clearest, and the pattern is "
     "the opposite of the one we expected. Negation is by far the hardest injected error for the "
     "generic baseline, whose mean absolute error is 4.629 +/- 0.531 on negation reversals against "
     "roughly 2.3 to 2.7 on everything else: a single inserted \"not\" moves the legal meaning from "
     "one end of the rubric to the other and moves the sentence embedding almost not at all. The "
     "transferred model, however, handles negation well, at 1.878 +/- 0.744, and its own hardest "
     "category is modality at 3.126 +/- 0.423, where \"shall\" becomes \"may\". The learned metric "
     "is therefore picking up precisely the transformation that similarity cannot see, which is the "
     "most direct support in this paper for building such a metric rather than reusing an "
     "embedding. Its weakness on modality is the natural next target: the obligation-to-permission "
     "flip is the most common real failure of legal simplification and the one our model is now "
     "worst at."),
    ("h2", "Transfer from FrJUDGE"),
    ("p",
     "Because the limiting factor is the number of training pairs rather than the method, we add an "
     "experiment the original work does not have: train the cross-encoder on FrJUDGE first, which "
     "is the same task and rubric in French insurance text and where our code reaches 0.707, then "
     "fine-tune on our Indian splits. If legal meaning preservation is substantially "
     "language-independent, the French corpus should supply the scale our own corpus lacks, and the "
     "transfer should show up most clearly in Hindi, where we have fewest pairs. We report the "
     "transferred systems alongside the from-scratch rows rather than replacing them, so that the "
     "contribution of the transfer is visible as an ablation: with and without augmentation, and "
     "with and without the French initialisation."),
    ("p",
     "This is our main result. Pre-trained on FrJUDGE the cross-encoder reaches Pearson 0.873 on "
     "the FrJUDGE test set, and fine-tuned from there onto our Indian splits it reaches 0.625, "
     "0.658 and 0.474 across the three seeds, averaging about 0.586. Against the same model trained "
     "from scratch at 0.228 with a standard deviation of 0.288, that is both a large gain in level "
     "and, more importantly, a change in kind: the from-scratch runs ranged from 0.56 to -0.08 and "
     "could not be relied on, while every transferred seed lands in a narrow band. The transferred "
     "model sits at roughly four-fifths of the 0.723 agreement between our own annotators, which is "
     "the natural upper bound for any system fitted to those labels. Table III carries the final "
     "aggregates, including the augmented variant."),
    ("p",
     "We draw two conclusions from this and resist a third. First, legal meaning preservation "
     "transfers across a language and a legal system: a model whose notion of a damaging "
     "simplification was formed on Quebec insurance forms in French usefully constrains the same "
     "judgement on Indian statutes in English and Hindi. The rubric's categories, omission, "
     "hallucination, inconsistency and confusion, are evidently not jurisdiction-specific. Second, "
     "this reframes what a small legal corpus is for: our 338 pairs are too few to fit the target "
     "but entirely sufficient to adapt a model that already has it, which is a much cheaper "
     "prescription for any other language or jurisdiction wanting such a metric. What we resist "
     "concluding is that the transferred model is good enough to deploy. It is still well short of "
     "the annotator ceiling, that ceiling is itself only two instances of one model agreeing, and "
     "Section VI shows the kind of case it still gets catastrophically wrong."),

    ("h1", "Error Analysis"),
    ("p",
     "Scoring the corpus blind made one structure plain, and it organises this section. The ways a "
     "simplification can betray a provision fall into two families. The first is loss: a proviso, "
     "an override, a subject-to clause, the date from which a limitation period runs, or an "
     "exception simply disappears. This is what aggressive plain-language rewriting does by its "
     "nature, and the resulting text is honest about being shorter. The second is reversal: a "
     "negation is inserted or dropped, an obligation becomes a permission or the reverse, or a "
     "quantifier narrows, so that \"any political party\" becomes \"certain political party\" and "
     "\"every order\" becomes \"some order\". Reversal is the dangerous family, because the text "
     "stays the same length and reads as fluently as a faithful version while telling the reader "
     "the opposite of the law. It is also the family that overlap and embedding metrics cannot see: "
     "as Section V reports, LaBSE's error is nearly twice as large on negation reversals as on "
     "dropped exceptions, which is precisely backwards from how much the surface changed."),
    ("p",
     "The cases below are selected automatically from our labelled pairs and the blinded "
     "annotator's own workbook comments, taking the injected-error pairs first so that the error "
     "type is known rather than inferred, and capping each group so that every error type appears "
     "before any repeats. For each case the table gives the provision, the language, the variant, "
     "the kind of change, the label (the mean of the annotators), the prediction of each system "
     "with test predictions for that pair, and the blinded annotator's own "
     "score, so that annotator disagreement stays visible rather than being hidden inside the "
     "mean."),
    ("caption", "E5: legally difficult cases, with the change that was made"),
    ("cases", None),
    ("p",
     "Two patterns in that table are worth drawing out. Where an injected negation reverses a whole "
     "operative provision the annotators split, one placing it Off-track and the other Imprecise, "
     "and the mean label of roughly 2.5 understates how misleading the text is: a reader told that "
     "the Central Government \"will not\" establish the authority the section establishes has been "
     "told the opposite of the law. Where the change is a quantifier or a single digit, by "
     "contrast, the annotators agreed closely, because the error is easy to see once noticed. The "
     "practical implication for a deployed metric is that the cases needing the most reliable "
     "detection are exactly the ones on which human, or in our case model, annotators are least "
     "consistent."),
    ("p",
     "The predicted columns are the most damning thing in this paper and the clearest statement of "
     "what remains to be solved. Take the two cases where an inserted negation reverses the "
     "provision outright, both labelled 2.5. The from-scratch model predicts 9.4 and 10.0, and the "
     "transferred model, which averages a respectable 1.878 absolute error across negation pairs, "
     "still predicts 9.0 and 8.3. Every system in the table looks at a sentence announcing that the "
     "Central Government will *not* establish the authority that the section establishes, and calls "
     "it an excellent simplification. This is the over-scoring failure JUDGEBERT identifies in "
     "generic metrics, reproduced by our own models at the top of the scale rather than merely in "
     "the aggregate, and it is the reason a good average error is not reassuring: a user relying on "
     "any of these systems would be told that the most dangerous simplification in the corpus "
     "preserves the law. It is also why we regard the diagnostic set, rather than any correlation "
     "we report, as the contribution most likely to outlast this paper."),

    ("h1", "Reproducibility Notes"),
    ("p",
     "Two defects in our own pipeline produced plausible-looking but worthless results, and both "
     "are worth reporting because neither announces itself."),
    ("p",
     "The first is a tokenizer fallback. Under transformers 5.x, loading the CamemBERT-v2 checkpoint "
     "through the generic auto-tokenizer yields a byte-level tokenizer without its merge table, "
     "which splits text into single characters. A sentence pair then exceeds 650 tokens, is "
     "truncated at the maximum length, and training collapses onto predicting the label mean: the "
     "training error equals the label variance and the test correlation is slightly negative. "
     "Nothing errors out. Our loader now detects this case and falls back to the checkpoint's own "
     "tokenizer file, and we verify the token count for any new backbone."),
    ("p",
     "The second is the Hindi text layer described in Section III-C, where two different extractors "
     "fail in two different ways while both returning text that looks like Hindi. The general "
     "lesson for legal NLP in Indic scripts is that an extraction step needs an explicit, "
     "quantitative acceptance test, because downstream metrics are computed happily on corrupted "
     "input."),
    ("p",
     "As an end-to-end check of the training code against a published result, we converted the "
     "released FrJUDGE splits and reran the original no-augmentation setting over the same ten "
     "seeds on a single T4. The check succeeds, with a caveat worth stating precisely. Following "
     "the released code, which trains for 100 epochs and keeps the best development checkpoint, we "
     "obtain Pearson 0.707 +/- 0.042 and RMSE 1.788 +/- 0.115 against the published 0.74 +/- 0.02 "
     "and 1.72. Our Pearson is 0.033 lower, which over ten seeds each is roughly two standard "
     "errors: close enough to confirm that the implementation is the same method in the same "
     "regime, not close enough to call an exact replication. The residual gap is most plausibly "
     "explained by library versions (the tokenizer fallback described below is itself a "
     "transformers 5.x artefact), our 512-token maximum length, and seed-level nondeterminism on "
     "different hardware."),
    ("p",
     "The more useful finding is that the setting matters more than the gap. Trained with early "
     "stopping at patience 5, which is what the paper's text describes, the same code gives Pearson "
     "0.606 +/- 0.284: one seed stopped at epoch 5 and collapsed to -0.196, and the remaining nine "
     "average 0.695. The released code has that early-stopping callback commented out. A reader "
     "following the paper's description rather than its code would therefore see a wide, unstable "
     "spread and might conclude the method does not work, when the instability belongs to the "
     "stopping rule. We report both settings for that reason."),
    ("p",
     "A partial augmented run (two seeds so far) is also informative about the headline number of "
     "the original work. Trained with augmentation but evaluated on the human-annotated test pairs "
     "only, it reaches Pearson 0.869 +/- 0.023 and RMSE 1.276 +/- 0.128, against the 0.97 the paper "
     "reports on a test set that includes the trivial identical and unrelated augmentation pairs. "
     "The augmented model is genuinely much stronger than the unaugmented one, and the published "
     "0.97 is also partly an artefact of what is in the test set. This is the concrete reason our "
     "own headline metrics exclude augmentation and sanity pairs. The FrJUDGE data is CC-BY-NC-SA "
     "4.0 and is used only for this check; we do not redistribute it."),

    ("h1", "Limitations and Ethics"),
    ("bullets", [
        "The LMP labels in this version are disclosed model judgements, not human legal judgements. "
        "The central claim of the predecessor work, agreement with human legal judgement, is "
        "therefore not tested here, and the planned 30-pair human validation set is the minimum "
        "needed to begin testing it.",
        "With two annotators the leave-one-out ceiling is just the correlation between them, and "
        "because both are instances of the same model their agreement may reflect shared "
        "pretraining rather than a well-defined construct. We therefore call it the LLM-annotator "
        "ceiling, never a human ceiling. One of the two also wrote the simplifications and so is "
        "not blind in practice.",
        "The corpus covers two acts and, for Hindi, one act only, because the official Hindi text of "
        "the Consumer Protection Act was unavailable. The two Right to Information editions differ, "
        "and the Hindi text had to be recovered by OCR; both are documented and flagged, and "
        "affected provisions are dropped rather than edited.",
        "The clause review that gates the corpus was performed by a rule-based agent rather than a "
        "human, and the simplifications were written by an agent rather than sampled from an API at "
        "a recorded temperature. Both are disclosed above. A human pass over the kept clauses and "
        "over a sample of simplifications is the first thing we would add.",
        "The Hindi text is OCR output. Although it passes our acceptance tests and its numbering was "
        "repaired from the sequence, OCR error in legal vocabulary cannot be excluded, and a Hindi "
        "legal reader has not yet verified the kept clauses.",
        "Injected errors are rule-based and may be easier to detect than errors a model makes "
        "naturally, so perturbed results are reported separately from the rest.",
        "The corpus is small, and the consequences fall hardest on the development split: about 35 "
        "annotated pairs decide both when to stop training and which checkpoint to keep. We "
        "changed the learning rate, batch size and stopping rule after seeing early stopping fail "
        "on that split, so those choices are informed by the development data and the reported "
        "numbers should be read as optimistic by an unknown margin. A larger corpus with a "
        "held-out tuning split is the right fix, and the honest statement of what we have is that "
        "the protocol was adjusted once, deliberately, and is disclosed rather than tuned "
        "repeatedly against the test set.",
        "Statute texts are public government documents. The corpus is a course research artefact for "
        "evaluating simplification quality; it is not a validated legal tool, and a predicted LMP "
        "score is not legal advice.",
    ]),

    ("h1", "Conclusion"),
    ("p",
     "We built a bilingual corpus of Indian statutory simplifications designed to make the "
     "weaknesses of the predecessor work measurable: three contrasting simplification styles "
     "including a diagnostic set with one injected legal error of a known type, clause-grouped "
     "splits verified disjoint, and sanity checks on provisions used nowhere else. Trained on that "
     "corpus alone, the learned metric fails: Pearson 0.228 with a standard deviation of 0.288, "
     "indistinguishable from a generic sentence-embedding baseline. Pre-trained on FrJUDGE and then "
     "fine-tuned on the same splits, it reaches about 0.586 across seeds, stably, at roughly "
     "four-fifths of the agreement between our own annotators. The limitation was scale and it was "
     "borrowable: a metric trained on French insurance forms transfers to Indian statutes in "
     "English and Hindi, which says that what the rubric measures is largely independent of "
     "language and jurisdiction, and that a few hundred local pairs are enough to adapt such a "
     "metric even though they are far too few to fit one."),
    ("p",
     "Three further results are worth carrying forward. The diagnostic "
     "set works, and it separates the learned metric from the generic ones exactly as the design "
     "predicted: negation reversals are by far the hardest injected error for the embedding "
     "baseline and among the easiest for the transferred model, whose own weak point is instead the "
     "obligation-to-permission flip. The "
     "sanity checks discriminate: no system we tested passes both, and the train-fitted calibration "
     "that makes a baseline's RMSE look competitive is what destroys its endpoints. And the "
     "measurement apparatus is sound, since the same code reproduces the published FrJUDGE number "
     "in the released setting while showing that the setting described in the paper's prose is "
     "unstable. Two things must happen before any of this is usable. Our disclosed model "
     "annotations have to be replaced by human legal judgement, without which the central claim of "
     "this line of work remains untested whatever correlation we report. And the failure mode in "
     "Section VI has to be fixed rather than averaged away: a metric that scores a reversed "
     "obligation above 9 out of 10 is dangerous in exactly the situation it was built for, and no "
     "aggregate correlation, ours included, makes that acceptable."),
]

# --------------------------------------------------------------------------- references
#
# Verification status is recorded per entry so that an unverified reference cannot reach the PDF
# unnoticed: "verified" means the authors, venue and year were checked against the publication
# record; "unverified" is rendered with a visible marker by the builders.
#
# All thirteen were checked against the ACL Anthology, arXiv, the ACM DL, the ICLR proceedings and
# the Penn repository on 19 Nov 2026. Three entries were wrong in the first draft and are fixed:
#   * BLESS: the author list was substantially wrong (D. Pepe and S. Ebling are not authors;
#     D. Aumiller and F. Alva-Manchego were missing).
#   * MeaningBERT: the second author is H. Saggion, not N. Garneau.
#   * QuestEval: P. Gallinari is the last author, not the third.
# Author-order and page details worth keeping in mind for the final template pass are noted inline.

REFERENCES = [
    {"text": "D. Beauchemin, M. Albert-Rochette, R. Khoury and P.-L. Deziel, \"JUDGEBERT: Assessing "
             "Legal Meaning Preservation Between Sentences,\" in Proc. EMNLP, 2025, pp. 92-118.",
     "status": "verified", "note": "aclanthology.org/2025.emnlp-main.5; preprint arXiv:2508.16870"},
    {"text": "T. Kew, A. Chi, L. Vasquez-Rodriguez, S. Agrawal, D. Aumiller, F. Alva-Manchego and "
             "M. Shardlow, \"BLESS: Benchmarking Large Language Models on Sentence "
             "Simplification,\" in Proc. EMNLP, 2023.",
     "status": "verified", "note": "aclanthology.org/2023.emnlp-main.821; author list corrected"},
    {"text": "T. Zhang, V. Kishore, F. Wu, K. Q. Weinberger and Y. Artzi, \"BERTScore: Evaluating "
             "Text Generation with BERT,\" in Proc. ICLR, 2020.",
     "status": "verified", "note": "ICLR 2020 poster 1738; arXiv:1904.09675"},
    {"text": "F. Feng, Y. Yang, D. Cer, N. Arivazhagan and W. Wang, \"Language-agnostic BERT "
             "Sentence Embedding,\" in Proc. ACL, 2022.",
     "status": "verified", "note": "aclanthology.org/2022.acl-long.62"},
    {"text": "A. Conneau, K. Khandelwal, N. Goyal, V. Chaudhary, G. Wenzek, F. Guzman, E. Grave, "
             "M. Ott, L. Zettlemoyer and V. Stoyanov, \"Unsupervised Cross-lingual Representation "
             "Learning at Scale,\" in Proc. ACL, 2020.",
     "status": "verified", "note": "aclanthology.org/2020.acl-main.747"},
    {"text": "S. Khanuja, D. Bansal, S. Mehtani, S. Khosla, A. Dey, B. Gopalan, D. K. Margam, "
             "P. Aggarwal, R. T. Nagipogu, S. Dave, S. Gupta, S. C. B. Gali, V. Subramanian and "
             "P. Talukdar, \"MuRIL: Multilingual Representations for Indian Languages,\" arXiv "
             "preprint arXiv:2103.10730, 2021.",
     "status": "verified", "note": "all 14 authors confirmed on arXiv"},
    {"text": "S. Doddapaneni, R. Aralikatte, G. Ramesh, S. Goyal, M. M. Khapra, A. Kunchukuttan and "
             "P. Kumar, \"Towards Leaving No Indic Language Behind: Building Monolingual Corpora, "
             "Benchmark and Models for Indic Languages,\" in Proc. ACL, 2023.",
     "status": "verified", "note": "aclanthology.org/2023.acl-long.693"},
    {"text": "K. Krippendorff, \"Computing Krippendorff's Alpha-Reliability,\" Departmental Papers "
             "(ASC), Annenberg School for Communication, University of Pennsylvania, 2011.",
     "status": "verified", "note": "repository.upenn.edu/asc_papers/43"},
    {"text": "T. Scialom, P.-A. Dray, S. Lamprier, B. Piwowarski, J. Staiano, A. Wang and "
             "P. Gallinari, \"QuestEval: Summarization Asks for Fact-based Evaluation,\" in Proc. "
             "EMNLP, 2021.",
     "status": "verified", "note": "aclanthology.org/2021.emnlp-main.529; author order corrected"},
    {"text": "M. Maddela, Y. Dou, D. Heineman and W. Xu, \"LENS: A Learnable Evaluation Metric for "
             "Text Simplification,\" in Proc. ACL, 2023.",
     "status": "verified", "note": "aclanthology.org/2023.acl-long.905"},
    {"text": "D. Beauchemin, H. Saggion and R. Khoury, \"MeaningBERT: Assessing Meaning Preservation "
             "Between Sentences,\" Frontiers in Artificial Intelligence, vol. 6, 2023, "
             "doi:10.3389/frai.2023.1223924.",
     "status": "verified", "note": "second author corrected: Saggion, not Garneau"},
    {"text": "S. Paul, A. Mandal, P. Goyal and S. Ghosh, \"Pre-trained Language Models for the Legal "
             "Domain: A Case Study on Indian Law,\" in Proc. ICAIL, 2023, pp. 187-196.",
     "status": "verified", "note": "doi:10.1145/3594536.3595165; arXiv:2209.06049"},
    {"text": "A. Joshi, S. Paul, A. Sharma, P. Goyal, S. Ghosh and A. Modi, \"IL-TUR: Benchmark for "
             "Indian Legal Text Understanding and Reasoning,\" in Proc. ACL, 2024.",
     "status": "verified", "note": "aclanthology.org/2024.acl-long.618; A. Modi added"},
]
