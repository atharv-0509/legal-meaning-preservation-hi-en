"""Build the IEEE-format paper from `paper/content.py`.

    python paper/build_paper.py                  -> paper/out/LMP_paper_IEEE.docx
    python paper/build_paper.py --markdown       -> also paper/out/paper_ieee.md (reading copy)

The PDF is produced from the .docx by `paper/build.ps1`, so the two deliverables are the same
document rather than two independent renderings.

Layout follows the IEEE conference template: US Letter, 0.75in top / 1.0in bottom / 0.625in side
margins, a single-column title block, then a two-column body of 3.5in columns with a 0.25in
gutter, Times New Roman 10pt, centred small-caps section headings numbered with Roman numerals,
italic lettered subsection headings, 9pt abstract, 8pt tables and references.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import content  # noqa: E402
import e5  # noqa: E402
import tables  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.section import WD_SECTION  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Inches, Pt  # noqa: E402

FONT = "Times New Roman"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# --------------------------------------------------------------------------- docx plumbing
def set_columns(section, count: int, space_in: float = 0.25) -> None:
    """python-docx exposes no column API, so write w:cols on the section properties directly."""
    cols = section._sectPr.xpath("./w:cols")[0]
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), str(int(space_in * 1440)))
    cols.set(qn("w:equalWidth"), "1")


def page_setup(section) -> None:
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(0.625)
    section.right_margin = Inches(0.625)


def para(doc, text="", size=10, bold=False, italic=False, align=None, space_after=0,
         space_before=0, indent=0.0, small_caps=False, keep_with_next=False):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_after = Pt(space_after)
    fmt.space_before = Pt(space_before)
    fmt.line_spacing = 1.0
    if indent:
        fmt.first_line_indent = Inches(indent)
    if align is not None:
        p.alignment = align
    if keep_with_next:
        fmt.keep_with_next = True
    if text:
        run = p.add_run(text)
        run.font.name = FONT
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic
        run.font.small_caps = small_caps
        # East-Asian font name, or Word substitutes a different face for some glyphs.
        run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return p


FIXED_WIDTH_TABLES = {"human"}      # long first-column labels: autofit would push them past the column edge


def add_table(doc, rows: list[list[str]], size=8, fixed: bool = False) -> None:
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    ncols = len(rows[0])
    if ncols >= 7 or fixed:
        # Many-column tables overflow a narrow IEEE column under autofit (LibreOffice ignores the column
        # edge), so fix the widths to the column.
        sec = doc.sections[-1]
        width = (sec.page_width - sec.left_margin - sec.right_margin - Inches(0.25)) / 2
        # Each column first gets room for its longest unbreakable word (so "0.552" never splits), then the
        # rest is shared in proportion to how much longer its cells are (so labels get the slack).
        char, pad = Inches(0.055), Inches(0.16)
        words = [[w for row in rows[1:] for w in str(row[c]).split()] or [""] for c in range(ncols)]
        head = [max(map(len, str(rows[0][c]).replace("+", "+ ").split()), default=0) for c in range(ncols)]
        need = [pad + char * max(min(max(map(len, ws)), 10), min(h, 6)) for ws, h in zip(words, head)]
        want = [pad + char * min(max(len(str(row[c])) for row in rows[1:]), 24) for c in range(ncols)]
        slack = max(width - sum(need), 0)
        extra = [w - n for w, n in zip(want, need)]
        widths = [int(n + (slack * e / sum(extra) if sum(extra) else slack / ncols)) for n, e in zip(need, extra)]
        if sum(widths) > width:                              # too many columns even at minimum: scale down
            widths = [int(w * width / sum(widths)) for w in widths]
        table.autofit = False
        for r in range(len(rows)):
            for c in range(ncols):
                table.cell(r, c).width = widths[c]
        # LibreOffice lays tables out from w:tblGrid and w:tblW, not the per-cell widths.
        for col, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(int(w / 635)))
        tblPr = table._tbl.tblPr
        for tag, attrs in (("w:tblW", {"w:w": str(int(sum(widths) / 635)), "w:type": "dxa"}),
                           ("w:tblLayout", {"w:type": "fixed"})):
            el = tblPr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                tblPr.append(el)
            for k, v in attrs.items():
                el.set(qn(k), v)
        size = min(size, 7)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(value))
            run.font.name = FONT
            run.font.size = Pt(size)
            run.bold = r == 0
    # A borderless left/right edge reads better in a narrow IEEE column than a full grid box.
    para(doc, "", size=4)


def _clip(text: str, limit: int = 180) -> str:
    """Statutory text is long; quote enough to see the change without flooding the column."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def e5_rows() -> list[list[str]]:
    """The E5 case table: one row per case, built from `e5.cases()`.

    Predicted columns appear only for systems that actually produced test predictions, so the
    table grows a column when a run lands rather than needing an edit here.
    """
    systems = e5.shown_systems()
    header = ["Provision", "Variant", "Change", "Label", "Annot."]
    header += [_short_system(s) for s in systems]
    cases = e5.cases()
    if not cases:
        return [header, ["[TBD]"] * len(header)]
    rows = [header]
    short = {"perturbed": "pert.", "aggressive": "aggr.", "normal": "norm."}
    for case in cases:
        # Ten columns do not fit an IEEE column: language joins the provision, variants are abbreviated
        # (pert./aggr./norm., explained in the caption) and change names may wrap at "_" and "/".
        change = (case["error_type"] or case["main_change"] or "").replace("_", " ").replace("/", "/ ")
        row = [f"{case['clause']} {case['lang']}", short.get(case["variant"], case["variant"]),
               change, case["label"], str(case["annotator_score"])]
        row += [f"{case['preds'][s]:.1f}" if s in case["preds"] else "--" for s in systems]
        rows.append(row)
    return rows


def _short_system(name: str) -> str:
    """Column headings have to fit a 3.5in column, so shorten the long checkpoint names."""
    return (name.replace("xlm-roberta-base", "XLM-R")
                .replace("muril-base-cased", "MuRIL")
                .replace("-frjudge", "+fr").replace("-da", "+DA")
                .replace("labse", "LaBSE").replace("bertscore", "BERTSc"))


def add_bullets(doc, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Inches(0.2)
        run = p.add_run(item)
        run.font.name = FONT
        run.font.size = Pt(10)


# --------------------------------------------------------------------------- build
def build(out_path: Path) -> list[str]:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(0)

    title_section = doc.sections[0]
    page_setup(title_section)
    set_columns(title_section, 1)

    # ---- single-column title block
    para(doc, content.TITLE, size=24, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    names = ", ".join(a["name"] for a in content.AUTHORS)
    rolls = ", ".join(a["roll"] for a in content.AUTHORS)
    para(doc, names, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    para(doc, rolls, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)
    for line in content.AFFILIATION:
        para(doc, line, size=10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, content.COURSE, size=9, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    # ---- two-column body
    body = doc.add_section(WD_SECTION.CONTINUOUS)
    page_setup(body)
    set_columns(body, 2)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.0
    head = p.add_run("Abstract—")
    head.bold, head.italic = True, True
    head.font.name, head.font.size = FONT, Pt(9)
    rest = p.add_run(content.ABSTRACT)
    rest.bold = True
    rest.font.name, rest.font.size = FONT, Pt(9)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(10)
    head = p.add_run("Keywords—")
    head.bold, head.italic = True, True
    head.font.name, head.font.size = FONT, Pt(9)
    rest = p.add_run(content.KEYWORDS)
    rest.bold = True
    rest.font.name, rest.font.size = FONT, Pt(9)

    section_no, sub_no, table_no = 0, 0, 0
    for kind, value in content.BODY:
        if kind == "h1":
            section_no += 1
            sub_no = 0
            label = f"{ROMAN[section_no - 1]}.  {value}"
            para(doc, label, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10,
                 space_after=3, small_caps=True, keep_with_next=True)
        elif kind == "h2":
            label = f"{LETTERS[sub_no]}.  {value}"
            sub_no += 1
            para(doc, label, size=10, italic=True, space_before=6, space_after=2,
                 keep_with_next=True)
        elif kind == "p":
            para(doc, value, size=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=0.2, space_after=3)
        elif kind == "bullets":
            add_bullets(doc, value)
            para(doc, "", size=4)
        elif kind == "caption":
            table_no += 1
            cap = para(doc, "", align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6, space_after=2,
                       keep_with_next=True)
            run = cap.add_run(f"TABLE {ROMAN[table_no - 1]}.")
            run.font.name, run.font.size, run.font.small_caps = FONT, Pt(8), True
            run = cap.add_run(f"  {value}")
            run.font.name, run.font.size = FONT, Pt(8)
        elif kind == "table":
            add_table(doc, tables.get(value), fixed=value in FIXED_WIDTH_TABLES)
        elif kind == "cases":
            add_table(doc, e5_rows())
            for case in e5.cases():
                para(doc, f"{case['clause']} ({case['lang']}, {case['variant']}). "
                          f"Original: “{_clip(case['original'])}”  Simplification: "
                          f"“{_clip(case['simplification'])}”  {case['explanation']}",
                     size=8, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=3)
        else:
            raise ValueError(f"unknown block kind {kind!r}")

    para(doc, "References", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10,
         space_after=3, small_caps=True)
    unverified = 0
    for i, ref in enumerate(content.REFERENCES, 1):
        text = f"[{i}] {ref['text']}"
        if ref.get("status") != "verified":
            unverified += 1
            text += "  [UNVERIFIED]"
        para(doc, text, size=8, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)

    warnings = [f"{m} not found -> table rendered as [TBD]" for m in tables.missing()]
    if unverified:
        warnings.append(f"{unverified}/{len(content.REFERENCES)} references still marked UNVERIFIED")
    return warnings


def build_markdown(out_path: Path) -> None:
    """A reading/diffing copy of exactly the same content."""
    lines = [f"# {content.TITLE}", "",
             "*Generated from `paper/content.py` by `paper/build_paper.py`. Do not edit this file; "
             "edit `content.py`.*", "",
             ", ".join(a["name"] for a in content.AUTHORS) + " — " + ", ".join(
                 a["roll"] for a in content.AUTHORS), "",
             "  \n".join(content.AFFILIATION), "", f"*{content.COURSE}*", "",
             "## Abstract", "", content.ABSTRACT, "",
             f"**Keywords—** {content.KEYWORDS}", ""]
    section_no, sub_no, table_no = 0, 0, 0
    for kind, value in content.BODY:
        if kind == "h1":
            section_no += 1
            sub_no = 0
            lines += [f"## {ROMAN[section_no - 1]}. {value}", ""]
        elif kind == "h2":
            lines += [f"### {LETTERS[sub_no]}. {value}", ""]
            sub_no += 1
        elif kind == "p":
            lines += [value, ""]
        elif kind == "bullets":
            lines += [f"- {item}" for item in value] + [""]
        elif kind == "caption":
            table_no += 1
            lines += [f"**TABLE {ROMAN[table_no - 1]}. {value}**", ""]
        elif kind in ("table", "cases"):
            rows = e5_rows() if kind == "cases" else tables.get(value)
            lines += ["| " + " | ".join(rows[0]) + " |",
                      "|" + "---|" * len(rows[0])]
            lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows[1:]] + [""]
            if kind == "cases":
                for case in e5.cases():
                    lines += [f"- **{case['clause']} ({case['lang']}, {case['variant']})** "
                              f"Original: “{_clip(case['original'])}” "
                              f"Simplification: “{_clip(case['simplification'])}” "
                              f"{case['explanation']}"]
                lines += [""]
    lines += ["## References", ""]
    for i, ref in enumerate(content.REFERENCES, 1):
        mark = "" if ref.get("status") == "verified" else "  **[UNVERIFIED]**"
        lines.append(f"{i}. {ref['text']}{mark}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "out" / "LMP_paper_IEEE.docx"))
    ap.add_argument("--markdown", action="store_true", help="also write the Markdown reading copy")
    args = ap.parse_args(argv)

    out = Path(args.out)
    warnings = build(out)
    print(f"wrote {out}")
    if args.markdown:
        md = out.parent / "paper_ieee.md"
        build_markdown(md)
        print(f"wrote {md}")
    for w in warnings:
        print(f"  NOTE: {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
