"""Turn the slide deck (paper/out/LMP_slides.pptx) into an Overleaf Beamer project.

    python paper/pptx_to_beamer.py [paper/out/LMP_slides.pptx]
        -> paper/out/overleaf_slides/ (main.tex, figures/) and paper/out/LMP_slides_overleaf.zip

Reads what build_slides.py lays out: a title slide, then per slide a title (30 pt), an optional italic subtitle,
bullets ("•  " / "—  " prefixes, **bold** and *italic* runs), at most one table, an optional picture and a red
italic note at the bottom. The deck has no Devanagari, so it compiles with pdfLaTeX (Overleaf's default).
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_latex import NUMERIC, esc  # noqa: E402

EMU_IN = 914400

PREAMBLE = r"""\documentclass[aspectratio=169,11pt]{beamer}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{tgheros}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,tabularx,array,adjustbox,graphicx}
\definecolor{ink}{HTML}{1A1F2B}
\definecolor{muted}{HTML}{5B6373}
\definecolor{accent}{HTML}{1F4E79}
\definecolor{flag}{HTML}{9B2C2C}
\definecolor{band}{HTML}{F2F4F7}
\setbeamertemplate{navigation symbols}{}
\setbeamercolor{normal text}{fg=ink}
\setbeamercolor{frametitle}{fg=ink}
\setbeamercolor{framesubtitle}{fg=muted}
\setbeamercolor{itemize item}{fg=accent}
\setbeamercolor{itemize subitem}{fg=muted}
\setbeamerfont{frametitle}{series=\bfseries,size=\Large}
\setbeamerfont{framesubtitle}{shape=\itshape,size=\small}
\setbeamertemplate{itemize item}{\small\raisebox{0.1ex}{$\bullet$}}
\setbeamertemplate{itemize subitem}{\small---}
\makeatletter
\setbeamertemplate{frametitle}{%
  \vspace*{0.6em}\usebeamerfont{frametitle}\usebeamercolor[fg]{frametitle}\insertframetitle\par
  \vspace*{0.25em}{\color{accent}\rule{\linewidth}{0.6pt}}\par
  \ifx\insertframesubtitle\@empty\else{\usebeamerfont{framesubtitle}\usebeamercolor[fg]{framesubtitle}\insertframesubtitle\par}\fi}
\makeatother
\setbeamertemplate{footline}{\hfill{\scriptsize\color{muted}\insertframenumber\,/\,\inserttotalframenumber}\hspace*{1.2em}\vspace*{0.8em}}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\newcommand{\slidenote}[1]{\vfill\parbox{0.9\textwidth}{\scriptsize\itshape\color{flag}#1}\par}
"""


def runs_tex(paragraph) -> str:
    """A paragraph's runs with bold/italic kept; the bullet prefix is dropped."""
    out = []
    for r in paragraph.runs:
        t = esc(r.text)
        if not t:
            continue
        if r.font.bold:
            t = r"\textbf{" + t + "}"
        if r.font.italic:
            t = r"\emph{" + t + "}"
        out.append(t)
    text = "".join(out)
    return re.sub(r"^(\\textbf\{|\\emph\{)?(•|—)\s+", r"\1", text)


def size_for(chars: int) -> str:
    return "\\footnotesize" if chars > 640 else "\\small" if chars > 430 else ""


def bullets_tex(frame) -> str:
    paras = [p for p in frame.paragraphs if p.text.strip()]
    chars = sum(len(p.text) for p in paras)
    size = size_for(chars)
    lines, level = [size, r"\begin{itemize}"], 0
    for p in paras:
        lv = 1 if (p.level or p.text.startswith("—")) else 0
        if lv > level:
            lines.append(r"\begin{itemize}" + (size or r"\normalsize"))   # Beamer would shrink sub-items
        elif lv < level:
            lines.append(r"\end{itemize}")
        level = lv
        lines.append(r"\item " + runs_tex(p))
    if level:
        lines.append(r"\end{itemize}")
    lines.append(r"\end{itemize}")
    return "\n".join(l for l in lines if l)


def cell(text: str) -> str:
    """Escaped cell text that may break after an arrow ("FrJUDGE→ours" is too wide for a narrow column)."""
    return esc(text).replace(r"\ensuremath{\rightarrow}", r"\ensuremath{\rightarrow}\allowbreak{}")


def table_tex(table, max_height: str) -> str:
    rows = [[c.text.strip() for c in r.cells] for r in table.rows]
    ncols = len(rows[0])
    numeric = [i > 0 and all(NUMERIC.match(r[i]) for r in rows[1:]) for i in range(ncols)]
    # Every column wraps (tabularx X); text columns get a larger share of the width, scaled by how much text
    # they hold, so long numeric headers cannot squeeze the label column. The shares must add up to ncols.
    avg = [sum(len(r[i]) for r in rows[1:]) / max(len(rows) - 1, 1) for i in range(ncols)]
    weight = [1.0 if numeric[i] else min(3.0, max(1.4, avg[i] / 10)) for i in range(ncols)]
    weight = [w * ncols / sum(weight) for w in weight]
    spec = "".join((r">{\centering\arraybackslash\hsize=%.3f\hsize}X" if numeric[i]
                    else r">{\raggedright\arraybackslash\hsize=%.3f\hsize}X") % weight[i] for i in range(ncols))
    size = "\\tiny" if len(rows) > 12 else "\\scriptsize" if len(rows) > 7 or ncols > 6 else "\\footnotesize"
    lines = [rf"\begin{{adjustbox}}{{max width=\textwidth, max totalheight={max_height}, center}}",
             r"\begin{minipage}{\textwidth}" + size,
             rf"\begin{{tabularx}}{{\textwidth}}{{{spec}}}", r"\toprule",
             " & ".join(r"\textbf{" + cell(c) + "}" for c in rows[0]) + r" \\", r"\midrule"]
    lines += [" & ".join(cell(c) for c in r) + r" \\" for r in rows[1:]]
    lines += [r"\bottomrule", r"\end{tabularx}", r"\end{minipage}", r"\end{adjustbox}"]
    return "\n".join(lines)


def build(src: Path, out_dir: Path) -> int:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(str(src))
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    slides = list(prs.slides)
    # ---- title slide
    first = [sh for sh in slides[0].shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    first.sort(key=lambda s: s.top)
    title = " ".join(p.text.strip() for p in first[0].text_frame.paragraphs if p.text.strip())
    info = [p.text.strip() for sh in first[1:] for p in sh.text_frame.paragraphs if p.text.strip()]
    L = [PREAMBLE, rf"\title{{{esc(title)}}}"]
    if info:
        L.append(rf"\author{{{esc(info[0])}}}")
    if len(info) > 1:
        L.append(r"\institute{" + r"\\[0.3em]".join(esc(x) for x in info[1:]) + "}")
    L += [r"\date{}", r"\begin{document}", r"\begin{frame}[plain]", r"\titlepage", r"\end{frame}", ""]
    n_pics = 0
    for idx, s in enumerate(slides[1:], 2):
        texts = sorted([sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()], key=lambda x: x.top)
        title_sh = next(sh for sh in texts if sh.top < 1.0 * EMU_IN)
        sub = next((sh for sh in texts if 1.3 * EMU_IN <= sh.top < 1.6 * EMU_IN and sh.height < 0.7 * EMU_IN), None)
        note = next((sh for sh in texts if sh.top >= 6.3 * EMU_IN), None)
        body = [sh for sh in texts if sh not in (title_sh, sub, note)]
        tables = [sh for sh in s.shapes if getattr(sh, "has_table", False) and sh.has_table]
        pics = [sh for sh in s.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
        L.append(r"\begin{frame}{" + esc(title_sh.text_frame.text.strip()) + "}")
        if sub:
            L.append(r"\framesubtitle{" + esc(sub.text_frame.text.strip()) + "}")
        for b in body:
            L.append(bullets_tex(b.text_frame))
        for t in tables:
            L.append(table_tex(t.table, "0.62\\textheight" if note or sub else "0.70\\textheight"))
        for p in pics:
            n_pics += 1
            name = f"figures/slide{idx:02d}_{n_pics}.{p.image.ext}"
            (out_dir / name).write_bytes(p.image.blob)
            frac = min(0.85, p.width / prs.slide_width)
            L += [r"\vspace{0.6em}", r"\begin{center}",
                  rf"\includegraphics[width={frac:.2f}\textwidth]{{{name}}}", r"\end{center}"]
        if note:
            L.append(r"\slidenote{" + esc(note.text_frame.text.strip()) + "}")
        L += [r"\end{frame}", ""]
    L += [r"\end{document}", ""]
    (out_dir / "main.tex").write_text("\n".join(L), encoding="utf-8")
    return len(slides)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx", nargs="?", default=str(HERE / "out" / "LMP_slides.pptx"))
    ap.add_argument("--out-dir", default=str(HERE / "out" / "overleaf_slides"))
    ap.add_argument("--zip", default=str(HERE / "out" / "LMP_slides_overleaf.zip"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    n = build(Path(args.pptx), out)
    with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file() and f.suffix not in (".pdf", ".aux", ".log", ".out", ".nav", ".snm", ".toc", ".fls",
                                                ".fdb_latexmk"):
                z.write(f, f.relative_to(out).as_posix())
    print(f"{n} slides -> {out / 'main.tex'} and {args.zip}")


if __name__ == "__main__":
    main()
