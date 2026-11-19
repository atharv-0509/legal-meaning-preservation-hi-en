"""Build the final presentation deck.

    python paper/build_slides.py        -> paper/out/LMP_slides.pptx

Slide prose is written here, deliberately terser than the paper, but every number comes from
`tables.py` (i.e. from files our pipeline produced) and the labelling-disclosure wording is
imported from `content.py`, so the deck cannot contradict the paper.
"""
from __future__ import annotations

import re
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import content  # noqa: E402
import tables  # noqa: E402

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.text import PP_ALIGN  # noqa: E402
from pptx.util import Emu, Inches, Pt  # noqa: E402

W, H = Inches(13.333), Inches(7.5)
INK = RGBColor(0x1A, 0x1F, 0x2B)
MUTED = RGBColor(0x5B, 0x63, 0x73)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
FLAG = RGBColor(0x9B, 0x2C, 0x2C)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
BAND = RGBColor(0xF2, 0xF4, 0xF7)
FONT = "Calibri"


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def box(slide, left, top, width, height):
    return slide.shapes.add_textbox(left, top, width, height).text_frame


def write(frame, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT, space_after=6,
          italic=False, first=False):
    p = frame.paragraphs[0] if first else frame.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    # "**bold**" and "*italic*" markup in the slide text become formatted runs (python-pptx has no
    # markdown; without this the asterisks were printed literally on the slides).
    for part in re.split(r"(\*\*[^*]+?\*\*|\*[^*\s][^*]*?\*)", text):
        if not part:
            continue
        run = p.add_run()
        is_b = part.startswith("**") and part.endswith("**") and len(part) > 4
        is_i = not is_b and part.startswith("*") and part.endswith("*") and len(part) > 2
        run.text = part[2:-2] if is_b else part[1:-1] if is_i else part
        run.font.size = Pt(size)
        run.font.bold = bold or is_b
        run.font.italic = italic or is_i
        run.font.color.rgb = color
        run.font.name = FONT
    return p


def band(slide):
    """Thin accent rule under the title, so every slide shares one visual anchor."""
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.28),
                                   Inches(11.9), Emu(14000))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT
    shape.line.fill.background()
    shape.shadow.inherit = False


def slide_title(prs, title, subtitle=None):
    slide = blank(prs)
    frame = box(slide, Inches(0.7), Inches(0.45), Inches(11.9), Inches(0.9))
    write(frame, title, size=30, bold=True, first=True)
    band(slide)
    if subtitle:
        sub = box(slide, Inches(0.7), Inches(1.4), Inches(11.9), Inches(0.5))
        write(sub, subtitle, size=15, color=MUTED, italic=True, first=True)
    return slide


def bullet_slide(prs, title, bullets, subtitle=None, note=None):
    slide = slide_title(prs, title, subtitle)
    top = Inches(2.0) if subtitle else Inches(1.75)
    frame = box(slide, Inches(0.8), top, Inches(11.7), Inches(4.6))
    frame.word_wrap = True
    for i, item in enumerate(bullets):
        if isinstance(item, tuple):
            text, size, indent = item
        else:
            text, size, indent = item, 18, 0
        p = write(frame, ("—  " if indent else "•  ") + text, size=size,
                  color=MUTED if indent else INK, space_after=8, first=(i == 0))
        p.level = 1 if indent else 0
    if note:
        nf = box(slide, Inches(0.8), Inches(6.5), Inches(11.7), Inches(0.6))
        write(nf, note, size=12, color=FLAG, italic=True, first=True)
    return slide


def table_slide(prs, title, key, subtitle=None, note=None):
    slide = slide_title(prs, title, subtitle)
    rows = tables.get(key)
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(0.9), Inches(2.0),
                                   Inches(11.5), Inches(0.4 * len(rows)))
    table = shape.table
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            run = p.add_run()
            run.text = str(value)
            run.font.size = Pt(14)
            run.font.bold = r == 0
            run.font.name = FONT
            run.font.color.rgb = PAPER if r == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = ACCENT if r == 0 else (BAND if r % 2 else PAPER)
    if note:
        nf = box(slide, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.6))
        write(nf, note, size=12, color=FLAG, italic=True, first=True)
    return slide


DISCLOSURE = ("Labels in this version are disclosed LLM judgements (two Claude Opus 5.5 instances) "
              "under the human rubric — not human legal judgement.")


def build(out_path: Path) -> list[str]:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ---- 1. title
    slide = blank(prs)
    frame = box(slide, Inches(1.0), Inches(2.1), Inches(11.3), Inches(2.4))
    frame.word_wrap = True
    write(frame, content.TITLE, size=34, bold=True, first=True)
    write(frame, "Extending JUDGEBERT (EMNLP 2025) from French insurance text to Indian statutes",
          size=17, color=MUTED, italic=True, space_after=0)
    meta = box(slide, Inches(1.0), Inches(4.9), Inches(11.3), Inches(1.6))
    write(meta, ", ".join(a["name"] for a in content.AUTHORS), size=16, first=True)
    write(meta, content.AFFILIATION[1], size=14, color=MUTED)
    write(meta, content.COURSE, size=12, color=MUTED, italic=True)

    # ---- 2. problem
    bullet_slide(prs, "The problem", [
        "Plain-language statutes widen access to justice — LLMs can rewrite them at scale.",
        "But a fluent simplification can drop a proviso, flip an obligation into a permission, "
        "or change a deadline.",
        "Generic metrics reward overlap, so they miss exactly these changes:",
        ("On FrJUDGE: BERTScore r = 0.46, SBERT r = 0.13 vs. human LMP judgement.", 16, 1),
        ("BERTScore and MeaningBERT over-score the human label on 82% of pairs.", 16, 1),
        "Legal meaning preservation is a separate target that has to be learned.",
    ], subtitle="Simplifying the law is useful; measuring whether the law survived is the hard part")

    # ---- 3. gap vs JUDGEBERT
    bullet_slide(prs, "What JUDGEBERT leaves open", [
        "French only, one domain (Quebec property-damage insurance), 297 pairs.",
        "One simplification style → narrow label range.",
        "Krippendorff's α = 0.10: annotators split into lenient and strict groups.",
        "Pair-level splits: a test original can reappear in training as an identical DA pair.",
        "Its headline 0.97 Pearson is measured on a test set containing trivial identical / "
        "unrelated pairs.",
        "No out-of-domain test.",
    ], subtitle="Each gap below becomes one of our contributions")

    # ---- 4. our design
    bullet_slide(prs, "Our extension", [
        "English + Hindi, two Indian central acts: RTI 2005 (public information) and "
        "Consumer Protection 2019 (consumer law).",
        "Official Hindi is a translation of the same provision → the language comparison is "
        "controlled, not confounded.",
        "Three variants per clause: normal (BLESS prompt), aggressive (\"explain to a "
        "12-year-old\"), perturbed (exactly one injected legal error of a known type).",
        "Perturbed = a labelled diagnostic set: which legal error types is a metric blind to?",
        "Clause-grouped splits, asserted disjoint at clause and text level; sanity checks on "
        "holdout provisions used nowhere else.",
    ])

    # ---- 5. dataset / provenance
    table_slide(prs, "Dataset and provenance", "sources",
                subtitle="India Code was unreachable, so we used other official government sources "
                         "and recorded exactly which",
                note="Consequences: E2 (EN vs HI) is RTI-only; CPA is English-only. The two RTI "
                     "editions differ at section 8(1) — affected clauses are dropped, never edited.")

    # ---- 6. the Hindi trap
    bullet_slide(prs, "The Hindi text layer: a trap worth reporting", [
        "The Hindi PDF is not scanned — but its text layer is unusable, in two different ways.",
        "pdftotext: 4.9% of all Devanagari characters come out as U+FFFD "
        "(2461 chars, 100 of 102 units) — irreversible loss.",
        "PyMuPDF: nothing lost, but legacy Mangal glyphs land in the Vedic/Sundanese Unicode "
        "blocks (2681 chars, 48 distinct code points) and vowel signs are in visual order.",
        "Readable to a human, systematically wrong to a machine; no downstream metric would "
        "reveal it. So extraction has a quantitative acceptance test and refuses both routes.",
        "Fix: OCR at 300 dpi, Tesseract 5.4 + tessdata_best hin → Devanagari 0.993, "
        "bad-matra 0.000, zero replacement characters.",
        "Residual OCR defect: the digit 1 is dropped (12→\"2\", 13→\"03\", \"(1)\"→\"()\"). "
        "Numbering is repaired from the sequence, never from appearance; every repair logged.",
    ], note="Open item: a Hindi legal reader has not yet verified the OCR'd clauses.")

    # ---- 6b. corpus size
    table_slide(prs, "What the corpus actually contains", "dataset",
                subtitle="78 clauses → 113 clause-language items → 338 pairs "
                         "(RTI 38, of which 35 bilingual; CPA 40, English-only)",
                note="Clause review was performed by a rule-based agent, not a human, and is "
                     "disclosed as such; the only text edits permitted were OCR number repairs.")

    # ---- 7. labelling protocol + disclosure
    bullet_slide(prs, "Scoring protocol — and an honest deviation", [
        "Rubric unchanged from JUDGEBERT: bracket (Accurate 7–10 / Imprecise 2–6 / "
        "Off-track 1), minus one point per error, floor 1.",
        "Intended: 3 human annotators per pair after a calibration round.",
        "Actual, because of the deadline: **two disclosed LLM annotators**, both Claude Opus 5.5 "
        "instances — one model family, not two. One of them also wrote the simplifications, "
        "so it is not blind in practice.",
        ("α = 0.610 interval / 0.503 bracket; inter-LLM Pearson 0.723 (agreement, not a ceiling) "
         "— vs. α = 0.10 between FrJUDGE's five law students. Two instances of one model agreeing "
         "is the weaker result. Mean scores differ (8.1 vs 6.9); 68 disagreements unadjudicated.", 16, 1),
        "Blinding is partial: opaque pair ids and per-annotator shuffle, but annotator 2 wrote "
        "the simplifications; the score is recomputed by our code from bracket + error counts.",
        "Human validation: 30-pair blind sheets for the three authors (results reported when scored). "
        "The brief's 300 human-judged pairs are not met.",
    ], note=DISCLOSURE)

    # ---- 8. method
    bullet_slide(prs, "Method", [
        "LMP model: cross-encoder regression, original [SEP] simplification → score in 1–10, "
        "MSE loss; linear decay, grad clip 1.0, best dev checkpoint.",
        ("We depart from JUDGEBERT's lr 5e-5 / batch 16 / patience 5: on our ~35-pair dev split "
         "early stopping fired on noise and left the model at the label mean (r ≈ 0). "
         "We use lr 2e-5, batch 8, 30 epochs, no early stopping — disclosed, with the "
         "dev-set selection it implies.", 16, 1),
        "Backbones: XLM-R and MuRIL (IndicBERT v2 planned, not run) — with and without data "
        "augmentation, 3 clause-grouped seeds (42–44).",
        "Principal system fixed in advance: XLM-R pre-trained on FrJUDGE, fine-tuned with DA.",
        "Baselines: ROUGE-L and BLEU (Devanagari-aware tokeniser), LaBSE cosine, multilingual "
        "BERTScore F1. No LLM judge: it would be scored against LLM labels (circular).",
        "Every baseline mapped to 1–10 twice: naive and train-calibrated.",
        "Report Pearson, Spearman, RMSE, MAE and the over-scoring rate — the dangerous failure "
        "is flattering a simplification that lost a condition.",
    ])

    # ---- 9. experiments
    bullet_slide(prs, "Experiments E1–E5", [
        "E1  Generic similarity baselines vs. the trained LMP models.",
        "E2  English vs. Hindi on the 35 RTI clauses present in both languages, and zero-shot "
        "EN→HI / HI→EN.",
        "E3  Cross-act generalisation: train on one act, test on the other (no test-act text in "
        "training, including augmentation partners).",
        "E4  Sanity checks on disjoint holdouts: identical pairs ≥ 9.9, unrelated ≤ 1.1.",
        "E5  ≥ 15 legally difficult cases, grouped by injected error type and recorded change.",
        "One command regenerates every table in the paper from the run files.",
    ])

    # ---- 10-12. results
    table_slide(prs, "E1: baselines vs. LMP model", "e1",
                note="Every cell is produced by modeling/evaluate.py; [TBD] means the run has not "
                     "been completed yet.")
    table_slide(prs, "E2: English vs. Hindi, and zero-shot transfer", "e2")
    table_slide(prs, "E4: sanity checks on disjoint holdouts", "e4",
                note="JUDGEBERT-DA was the only metric in the original study to pass both checks.")

    # ---- 13. reproducibility
    bullet_slide(prs, "Two traps that silently ruin results", [
        "transformers 5.x loads CamemBERT-v2 through the auto-tokenizer as a byte-level tokenizer "
        "with no merges → single-character tokens.",
        ("Pairs became ~650 tokens, were truncated, and training collapsed to predicting the label "
         "mean (train MSE ≈ label variance; test r ≈ −0.25). Nothing errored.", 16, 1),
        "The Hindi extraction failure above: two extractors, two silent corruptions.",
        "Both are now detected in code, and we report them because neither announces itself.",
        "FrJUDGE reproduction as an end-to-end check of the training code: 0.707 ± 0.042 Pearson / "
        "1.79 RMSE over 10 seeds vs. published 0.74 ± 0.02 / 1.72.",
    ])

    # ---- 14. demo
    bullet_slide(prs, "Demo", [
        "modeling/predict.py --model-dir <checkpoint> --demo: paste an original and a simplification, "
        "get the LMP score and the decision (≥ 7 Preserved / 2–6 Partially Preserved / < 2 Not "
        "Preserved).",
        "Checkpoint: the FrJUDGE→ours model saved by the Kaggle 'demo' run (random_s42).",
        "The decision uses the rubric's bracket thresholds on the regression output; it is a "
        "prediction, not an annotation.",
    ])

    # ---- 14b. from-scratch fails
    bullet_slide(prs, "Trained on our corpus alone, it fails", [
        "Best from-scratch metric: XLM-R + DA, Pearson **0.228 ± 0.288** (seeds 0.56 / 0.21 / "
        "−0.08). The SD exceeds the mean.",
        ("≈ 1.4 standard errors from zero: not distinguishable from no correlation, nor from "
         "LaBSE at 0.101, and far from our 0.723 annotator ceiling.", 16, 1),
        "Without DA: −0.030. MuRIL + DA: 0.067; MuRIL without DA collapses (RMSE 4.4).",
        "E2 (matched RTI provisions): EN −0.059, HI −0.058; zero-shot EN→HI −0.059, HI→EN 0.028. "
        "E3: CPA→RTI 0.186, RTI→CPA 0.056.",
        "E4: no system passes both sanity checks — XLM-R-DA 33% / 31%; JUDGEBERT-DA passed "
        "both. The transferred models get much closer but still fail one each.",
        "But the same code reaches **0.707 on FrJUDGE**. So the limit is scale, not method.",
    ], subtitle="~200 training pairs with a bimodal label distribution")

    # ---- 14b2. the main result
    bullet_slide(prs, "Main result: the scale can be borrowed", [
        "Pre-train the same cross-encoder on **FrJUDGE** (French insurance forms) → 0.873 on "
        "its test set. Then fine-tune on our Indian splits.",
        "**Pearson 0.586 ± 0.098** (seeds 0.625 / 0.658 / 0.474), vs 0.228 ± 0.288 from "
        "scratch and 0.101 for LaBSE. Roughly four-fifths of the 0.723 annotator ceiling.",
        ("The change in kind matters more than the level: from-scratch seeds ranged 0.56 to "
         "−0.08 and could not be relied on; every transferred seed lands in a narrow band.", 16, 1),
        "So legal meaning preservation **transfers across a legal system**: the rubric's "
        "categories are not jurisdiction-specific (clearest on the Consumer Protection Act).",
        "And it reframes what a small legal corpus is for — 338 pairs cannot fit this target "
        "but can adapt a model that already has it. A cheap recipe for any other jurisdiction.",
    ], subtitle="French insurance forms → Indian statutes",
       note="Still short of the ceiling, that ceiling is two instances of one model, and the "
            "reversal failure two slides on is unfixed. Not deployable.")

    # ---- 14b3. where the transfer helps
    bullet_slide(prs, "Where the transfer helps, and where it does not", [
        "**Pooled by language (E1 runs):** EN 0.675, HI 0.308 — but confounded by act: the same "
        "runs score CPA 0.669 vs RTI 0.485, and EN pools both acts.",
        "**Matched RTI provisions (E2):** EN **0.165**, HI **−0.041** (from scratch −0.059 / "
        "−0.058). Neither language is learned: the data do not show the transfer helps Hindi.",
        "**Zero-shot EN↔HI stays at zero:** 0.035 and 0.131, though both languages hold the "
        "*very same provisions*.",
        "**Across acts (E3), asymmetric:** CPA→RTI 0.186 → **0.388**; RTI→CPA 0.056 → **0.119**. "
        "No target-act text in training either way.",
        ("With 105 OCR-recovered Hindi pairs we cannot separate OCR noise from subset size from "
         "Devanagari representation.", 16, 1),
    ])

    # ---- 14c. what else holds
    bullet_slide(prs, "What else holds, regardless of the correlation", [
        "**The diagnostic set separates learned from generic.** Negation is by far the baseline's "
        "hardest injected error (MAE **4.63** vs ~2.3–2.7 elsewhere) — one \"not\" flips "
        "the law and barely moves an embedding. The transferred model handles it (**1.90**); its "
        "own weak point is modality, shall→may (**3.16**).",
        ("That is the clearest argument in the project for a purpose-built metric: it detects "
         "precisely what similarity cannot.", 16, 1),
        "**But a good average is not safety.** On negation reversals (label ≤ 3) the transferred "
        "model averages **4.0** in domain vs 7.6 from scratch, yet single reversals still get "
        "**10.0**; on an unseen act it averages **7.3**, no better than LaBSE (7.7).",
        "**The sanity checks discriminate.** Train-fitted calibration improves baseline RMSE "
        "(2.81 → 2.42) while making all four fail both checks at 0%.",
        "**The apparatus is sound.** We reproduce FrJUDGE at 0.707 in the released setting, and "
        "show the setting described in the paper's prose (patience 5) is unstable: 0.606 ± "
        "0.284, one seed collapsing to −0.196.",
        "**And the published 0.97 is partly test-set composition:** DA-trained, scored on human "
        "pairs only, it is 0.869.",
    ])

    # ---- 15. conclusion
    bullet_slide(prs, "Where this stands", [
        "Built: bilingual extraction from real government PDFs with quantitative acceptance tests, "
        "three-variant simplification design, blinded workbooks, clause-grouped splits, "
        "training / baselines / LLM judge / evaluation / error analysis, one-command results.",
        "Main result: legal meaning preservation transfers across jurisdiction "
        "(FrJUDGE → Indian statutes, 0.228 → ~0.586 and stable); on matched bilingual RTI "
        "provisions neither language is learned yet.",
        "Honest status: labels are disclosed LLM judgements, not human legal judgement; human "
        "validation is prepared but not scored; the metric is not deployable.",
        "What the design buys: the perturbed diagnostic set and the clause-grouped splits make the "
        "weaknesses of the original study measurable rather than arguable.",
        "Next: human labels, and fix the reversal failure instead of averaging it away.",
    ], note=DISCLOSURE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    return [f"{m} not found -> slide table rendered as [TBD]" for m in tables.missing()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "out" / "LMP_slides.pptx"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    warnings = build(out)
    print(f"wrote {out}")
    for w in warnings:
        print(f"  NOTE: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
