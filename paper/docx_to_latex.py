"""Turn an edited copy of the IEEE Word paper into an Overleaf (IEEEtran, XeLaTeX) project.

    python paper/docx_to_latex.py paper/edited/LMP_paper_IEEE_edited.docx
        -> paper/out/overleaf_final/ (main.tex, latexmkrc, fonts/) and paper/out/LMP_paper_final_overleaf.zip

Use this when the wording was revised by hand in Word: the text comes from the .docx, not from content.py. It relies
on the layout that build_paper.py writes (and that survives editing in Word): centred small-caps "I.  Title" section
headings, italic "A.  Title" subsections, "TABLE N.  caption" lines followed by a table, "List Bullet" paragraphs,
E5 case paragraphs ("rti-s11_2 (HI, perturbed). ...") and "[n] ..." references after the "References" heading.
Tables are typeset with the same rules as build_latex.py.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_latex import FONT_NAME, FONT_SOURCES, LATEXMKRC, PREAMBLE, esc, latex_table  # noqa: E402

H1 = re.compile(r"^([IVXLC]+)\.\s+(.+)$")
H2 = re.compile(r"^([A-Z])\.\s+(.+)$")
CAPTION = re.compile(r"^TABLE\s+[IVXLC]+\.\s+(.+)$")
CASE = re.compile(r"^((?:rti|cpa)-s[\w]+ \((?:EN|HI), \w+\)\.)\s*(.*)$", re.S)
REF = re.compile(r"^\[(\d+)\]\s*(.+)$", re.S)


def _run0(p):
    return p.runs[0] if p.runs else None


def blocks(path: Path) -> list[tuple[str, object]]:
    """The document as (kind, value) blocks in reading order."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    d = docx.Document(str(path))
    out: list[tuple[str, object]] = []
    in_refs = False
    for el in d.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "tbl":
            t = Table(el, d)
            out.append(("table", [[c.text.strip() for c in row.cells] for row in t.rows]))
            continue
        if tag != "p":
            continue
        p = Paragraph(el, d)
        text = p.text.strip()
        if not text:
            continue
        r = _run0(p)
        size = r.font.size.pt if r is not None and r.font.size else None
        small_caps = bool(r is not None and r.font.small_caps)
        italic = bool(r is not None and r.italic)
        if in_refs:
            m = REF.match(text)
            out.append(("ref", m.group(2) if m else text))
        elif small_caps and text == "References":
            in_refs = True
        elif size == 24 and not any(k == "title" for k, _ in out):
            out.append(("title", text))
        elif text.startswith(("Abstract—", "Abstract -", "Abstract—")):
            out.append(("abstract", re.sub(r"^Abstract\s*[—-]\s*", "", text)))
        elif text.startswith(("Keywords—", "Index Terms—")):
            out.append(("keywords", re.sub(r"^(Keywords|Index Terms)\s*—\s*", "", text)))
        elif small_caps and CAPTION.match(text):
            out.append(("caption", CAPTION.match(text).group(1)))
        elif small_caps and H1.match(text):
            out.append(("h1", H1.match(text).group(2)))
        elif italic and H2.match(text) and len(text) < 120 and not any(k == "abstract" for k, _ in out[-1:]):
            out.append(("h2", H2.match(text).group(2)))
        elif p.style.name.startswith("List Bullet"):
            out.append(("bullet", text))
        elif size == 8 and CASE.match(text):
            m = CASE.match(text)
            out.append(("case", (m.group(1), m.group(2))))
        elif not any(k == "abstract" for k, _ in out):
            out.append(("front", (text, size, italic)))     # authors, roll numbers, affiliation, course line
        else:
            out.append(("p", text))
    return out


def build(src: Path, out_dir: Path) -> list[str]:
    bl = blocks(src)
    title = next(v for k, v in bl if k == "title")
    front = [v for k, v in bl if k == "front"]
    names = front[0][0] if front else ""
    rolls = front[1][0] if len(front) > 1 and re.search(r"\d", front[1][0]) else ""
    rest = front[2:] if rolls else front[1:]
    aff = [t for t, size, it in rest if size != 9]
    course = next((t for t, size, it in rest if size == 9), "")
    L = [PREAMBLE, rf"\title{{{esc(title)}}}"]
    author = esc(names) + (r"\\ " + esc(rolls) if rolls else "")
    affil = r"\\ ".join(esc(a) for a in aff) + (r"\\ \textit{" + esc(course) + "}" if course else "")
    L.append(rf"\author{{\IEEEauthorblockN{{{author}}}\IEEEauthorblockA{{{affil}}}}}")
    L.append(r"\maketitle")
    caption, n_table, refs, i = None, 0, [], 0
    warnings = []
    while i < len(bl):
        kind, v = bl[i]
        if kind == "abstract":
            L += [r"\begin{abstract}", esc(v), r"\end{abstract}"]
        elif kind == "keywords":
            L += [r"\begin{IEEEkeywords}", esc(v), r"\end{IEEEkeywords}", ""]
        elif kind == "h1":
            L += [rf"\section{{{esc(v)}}}", ""]
        elif kind == "h2":
            L += [rf"\subsection{{{esc(v)}}}", ""]
        elif kind == "p":
            L += [esc(v), ""]
        elif kind == "bullet":
            items = []
            while i < len(bl) and bl[i][0] == "bullet":
                items.append(bl[i][1])
                i += 1
            L += [r"\begin{itemize}"] + [rf"\item {esc(t)}" for t in items] + [r"\end{itemize}", ""]
            continue
        elif kind == "caption":
            caption = v
        elif kind == "table":
            n_table += 1
            if caption is None:
                warnings.append(f"table {n_table} has no 'TABLE N.' caption line before it")
            L.append(latex_table(v, caption or "", f"tab:{n_table}"))
            caption = None
        elif kind == "case":
            L.append(r"{\footnotesize")
            while i < len(bl) and bl[i][0] == "case":
                head, body = bl[i][1]
                L += [rf"\noindent\textbf{{{esc(head)}}} {esc(body)}", ""]
                i += 1
            L.append("}")
            continue
        elif kind == "ref":
            refs.append(v)
        i += 1
    if refs:
        L += [r"\begin{thebibliography}{99}"] + [rf"\bibitem{{ref{n}}} {esc(t)}" for n, t in enumerate(refs, 1)]
        L += [r"\end{thebibliography}", ""]
    L += [r"\end{document}", ""]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "main.tex").write_text("\n".join(L), encoding="utf-8")
    (out_dir / "latexmkrc").write_text(LATEXMKRC, encoding="utf-8")
    fonts = out_dir / "fonts"
    fonts.mkdir(exist_ok=True)
    font = next((p for p in FONT_SOURCES if p.exists()), None)
    if font is None:
        sys.exit(f"{FONT_NAME} not found (install fonts-noto-core, or put it in paper/fonts/)")
    (fonts / FONT_NAME).write_bytes(font.read_bytes())
    (fonts / "README.txt").write_text("Noto Serif Devanagari, SIL Open Font License 1.1: https://openfontlicense.org\n",
                                      encoding="utf-8")
    counts = {k: sum(1 for kk, _ in bl if kk == k) for k in ("h1", "h2", "p", "bullet", "table", "case", "ref")}
    print("read:", ", ".join(f"{v} {k}" for k, v in counts.items()))
    return warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docx")
    ap.add_argument("--out-dir", default=str(HERE / "out" / "overleaf_final"))
    ap.add_argument("--zip", default=str(HERE / "out" / "LMP_paper_final_overleaf.zip"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    for w in build(Path(args.docx), out):
        print("WARNING:", w)
    with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file() and f.suffix not in (".pdf", ".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".xdv"):
                z.write(f, f.relative_to(out).as_posix())
    print(f"wrote {out / 'main.tex'} and {args.zip}")


if __name__ == "__main__":
    main()
