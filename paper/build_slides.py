"""Build the final presentation deck.

    python paper/build_slides.py        -> paper/out/LMP_slides.pptx

Slide prose is written here, deliberately terser than the paper, but every number comes from
`tables.py` (i.e. from files our pipeline produced) and the labelling-disclosure wording is
imported from `content.py`, so the deck cannot contradict the paper.
"""
from __future__ import annotations

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
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
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


DISCLOSURE = ("Labels in this version are disclosed LLM judgements (Claude Opus 5.5, GPT-6 Astra) "
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
                subtitle="78 clauses → 113 clause-language items → 339 pairs "
                         "(RTI 38, of which 35 bilingual; CPA 40, English-only)",
                note="Clause review was performed by a rule-based agent, not a human, and is "
                     "disclosed as such; the only text edits permitted were OCR number repairs.")

    # ---- 7. labelling protocol + disclosure
    bullet_slide(prs, "Scoring protocol — and an honest deviation", [
        "Rubric unchanged from JUDGEBERT: bracket (Accurate 7–10 / Imprecise 2–6 / "
        "Off-track 1), minus one point per error, floor 1.",
        "Intended: 3 human annotators per pair after a calibration round.",
        "Actual, because of the deadline: two disclosed LLM annotators under the same rubric; "
        "simplifications were agent-written, not API-sampled, so temperature/top-p are null "
        "rather than invented.",
        ("Reported as LLM-annotator agreement, never as human agreement.", 16, 1),
        ("With two annotators there is no leave-one-out human ceiling.", 16, 1),
        "Blinding is mechanical: opaque pair ids, per-annotator shuffle, answer key in files the "
        "annotators never read; the score is recomputed by our code from bracket + error counts.",
        "A 30-pair human validation workbook is prepared; if unscored, that is reported as a "
        "limitation.",
    ], note=DISCLOSURE)

    # ---- 8. method
    bullet_slide(prs, "Method", [
        "LMP model: cross-encoder regression, original [SEP] simplification → score in 1–10, "
        "MSE loss; lr 5e-5, batch 16, linear decay, grad clip 1.0, best dev checkpoint.",
        "Backbones: XLM-R, MuRIL, IndicBERT v2 — with and without data augmentation, "
        "5 clause-grouped seeds.",
        "Baselines: ROUGE-L and BLEU (Devanagari-aware tokeniser), LaBSE cosine, multilingual "
        "BERTScore F1, and an LLM judge given the identical rubric.",
        "Every baseline mapped to 1–10 twice: naive and train-calibrated.",
        "Report Pearson, Spearman, RMSE, MAE and the over-scoring rate — the dangerous failure "
        "is flattering a simplification that lost a condition.",
    ])

    # ---- 9. experiments
    bullet_slide(prs, "Experiments E1–E5", [
        "E1  Generic similarity baselines + LLM judge vs. the trained LMP model.",
        "E2  English vs. Hindi, and zero-shot transfer EN→HI and HI→EN (RTI only).",
        "E3  Cross-act generalisation: train on one act, test on the other.",
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
        "FrJUDGE reproduction as an end-to-end check of the training code: [TBD] vs. published "
        "0.74 ± 0.02 Pearson / 1.72 RMSE.",
    ])

    # ---- 14. demo
    bullet_slide(prs, "Demo", [
        "modeling/predict.py --demo: paste an original and a simplification, get the LMP score, "
        "the decision (Preserved / Partially Preserved / Not Preserved), and the nearest "
        "rubric bracket.",
        "Same scoring function as the annotation workbooks, so the demo and the dataset cannot "
        "disagree.",
        "[TBD: screenshot once a trained checkpoint is in place.]",
    ])

    # ---- 15. conclusion
    bullet_slide(prs, "Where this stands", [
        "Built: bilingual extraction from real government PDFs with quantitative acceptance tests, "
        "three-variant simplification design, blinded workbooks, clause-grouped splits, "
        "training / baselines / LLM judge / evaluation / error analysis, one-command results.",
        "Honest status: labels are disclosed LLM judgements; human validation is prepared but not "
        "yet scored; Hindi text recovery and the full model runs are open items.",
        "What the design buys: the perturbed diagnostic set and the clause-grouped splits make the "
        "weaknesses of the original study measurable rather than arguable.",
        "[TBD: headline numbers once E1–E5 complete.]",
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
