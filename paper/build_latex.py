"""Build the IEEE paper as an Overleaf-ready LaTeX project from the same sources as the Word build.

    python paper/build_latex.py        # -> paper/out/overleaf/ and paper/out/LMP_paper_overleaf.zip

Text comes from `content.py`, tables from `reports/tables/*.tsv` (via tables.py) and the E5 cases from e5.py, exactly
as in build_paper.py, so the LaTeX and Word versions cannot disagree; rebuild both after any change (including when
the human validation sheets are scored: run src/human_validation.py first).

On Overleaf: New Project -> Upload Project -> the zip. The included `latexmkrc` selects XeLaTeX, which the Hindi in
the E5 cases needs (pdfLaTeX cannot shape Devanagari); the Devanagari font is bundled under fonts/ (Noto Serif
Devanagari, SIL Open Font License), so nothing has to be installed.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import content  # noqa: E402
import e5  # noqa: E402
import tables  # noqa: E402
from build_paper import _clip, e5_rows  # noqa: E402

FONT_NAME = "NotoSerifDevanagari-Regular.ttf"
FONT_SOURCES = [Path("/usr/share/fonts/truetype/noto") / FONT_NAME, HERE / "fonts" / FONT_NAME]

PREAMBLE = r"""%% Compile with XeLaTeX (Overleaf: Menu -> Compiler -> XeLaTeX).
\documentclass[conference]{IEEEtran}
\usepackage{iftex}
\RequireXeTeX   % Overleaf: Menu -> Compiler -> XeLaTeX (pdfLaTeX cannot typeset the Hindi quotations)
\usepackage{fontspec}
\setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular, BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
% Devanagari font for the Hindi: the bundled file if present (zip upload), else a font Overleaf already has.
\IfFileExists{fonts/NotoSerifDevanagari-Regular.ttf}{%
  \newfontfamily\devfont[Path=fonts/, Script=Devanagari, Scale=0.92]{NotoSerifDevanagari-Regular.ttf}}{%
  \IfFontExistsTF{Noto Serif Devanagari}{%
    \newfontfamily\devfont[Script=Devanagari, Scale=0.92]{Noto Serif Devanagari}}{%
    \newfontfamily\devfont[Script=Devanagari]{FreeSerif}}}
\newcommand{\dev}[1]{{\devfont #1}}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,tabularx,array}
\usepackage[hyphens]{url}
\usepackage[hidelinks]{hyperref}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\renewcommand{\arraystretch}{1.12}
\setlength{\tabcolsep}{3.5pt}
\begin{document}
"""

SYMBOLS = {"±": r"\ensuremath{\pm}", "→": r"\ensuremath{\rightarrow}", "←": r"\ensuremath{\leftarrow}",
           "↔": r"\ensuremath{\leftrightarrow}", "≥": r"\ensuremath{\geq}", "≤": r"\ensuremath{\leq}",
           "×": r"\ensuremath{\times}", "−": r"\ensuremath{-}", "α": r"\ensuremath{\alpha}", "≈": r"\ensuremath{\approx}"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]+(?:[\s\d(),;:.\-–—।॥'\"“”‘’]+[ऀ-ॿ]+)*[।॥]?")


def esc(text: str) -> str:
    """Plain text -> LaTeX: escape specials, typeset symbols, put Devanagari runs in the Devanagari font."""
    text = str(text).replace("+/-", "±")
    text = re.sub(r'"([^"\n]*)"', "“\\1”", text)          # ASCII "quotes" -> curly (LaTeX would print ” twice)
    out, pos = [], 0
    for m in DEVANAGARI.finditer(text):
        out += [_esc_latin(text[pos:m.start()]), r"\dev{" + _esc_latin(m.group()) + "}"]
        pos = m.end()
    out.append(_esc_latin(text[pos:]))
    return "".join(out)


def _esc_latin(t: str) -> str:
    t = (t.replace("\\", "\x00").replace("{", r"\{").replace("}", r"\}").replace("$", r"\$").replace("&", r"\&")
          .replace("#", r"\#").replace("_", r"\_").replace("%", r"\%").replace("~", r"\textasciitilde{}")
          .replace("^", r"\textasciicircum{}").replace("\x00", r"\textbackslash{}"))
    for k, v in SYMBOLS.items():
        t = t.replace(k, v)
    return t


NUMERIC = re.compile(r"^[\s\d.,+\-±%/()]*(?:n/a|--|—)?[\s\d.,+\-±%/()]*$")
COLUMN_PT, TEXT_PT = 252.0, 516.0          # IEEEtran conference column and text widths


def _width_pt(cell: str, size: str) -> float:
    return len(cell) * (4.15 if size == "footnotesize" else 3.6) + 7    # glyphs + \tabcolsep both sides


def latex_table(rows: list[list[str]], caption: str, label: str) -> str:
    """A booktabs table. Numeric columns (numbers, "0.576 ± 0.102") keep their natural width; text columns wrap
    (tabularx Y) with a 58pt minimum. If that does not fit one column the table spans both (table*), and if it
    does not fit the text width either the font drops to scriptsize."""
    rows = [[str(c) for c in r] for r in rows]
    ncols = len(rows[0])
    numeric = [all(NUMERIC.match(r[i].replace("+/-", "±")) for r in rows[1:]) for i in range(ncols)]
    numeric[0] = numeric[0] and ncols > 1 and False                 # the first column holds labels: let it wrap
    def widths(size):
        """Width of each numeric column: its widest cell or its longest header word (headers wrap)."""
        out = []
        for i in range(ncols):
            nat = max(_width_pt(r[i], size) for r in rows[1:]) if len(rows) > 1 else 40
            head = max((_width_pt(w, size) for w in rows[0][i].split()), default=20)
            out.append(max(nat, head) if numeric[i] else max(58.0, head))
        return out
    size, env, width = "footnotesize", "table", r"\columnwidth"
    if sum(widths(size)) > COLUMN_PT:
        env, width = "table*", r"\textwidth"
        if sum(widths(size)) > TEXT_PT:
            size = "scriptsize"
    w = widths(size)
    spec = "".join(rf">{{\centering\arraybackslash}}p{{{w[i] - 7:.0f}pt}}" if numeric[i] else "Y"
                   for i in range(ncols))
    lines = [rf"\begin{{{env}}}[!t]", r"\centering", rf"\caption{{{esc(caption)}}}", rf"\label{{{label}}}",
             rf"\{size}", rf"\begin{{tabularx}}{{{width}}}{{{spec}}}", r"\toprule",
             " & ".join(r"\textbf{" + esc(c) + "}" for c in rows[0]) + r" \\", r"\midrule"]
    lines += [" & ".join(esc(c) for c in r) + r" \\" for r in rows[1:]]
    lines += [r"\bottomrule", r"\end{tabularx}", rf"\end{{{env}}}", ""]
    return "\n".join(lines)


def build(out_dir: Path) -> list[str]:
    L = [PREAMBLE]
    L.append(rf"\title{{{esc(content.TITLE)}}}")
    names = ", ".join(f"{a['name']} ({a['roll']})" for a in content.AUTHORS)
    aff = r"\\ ".join(esc(x) for x in content.AFFILIATION)
    L.append(rf"\author{{\IEEEauthorblockN{{{esc(names)}}}\IEEEauthorblockA{{{aff}\\ \textit{{{esc(content.COURSE)}}}}}}}")
    L += [r"\maketitle", r"\begin{abstract}", esc(content.ABSTRACT), r"\end{abstract}",
          r"\begin{IEEEkeywords}", esc(content.KEYWORDS), r"\end{IEEEkeywords}", ""]
    caption, n_table = None, 0
    for kind, value in content.BODY:
        if kind == "h1":
            L += [rf"\section{{{esc(value)}}}", ""]
        elif kind == "h2":
            L += [rf"\subsection{{{esc(value)}}}", ""]
        elif kind == "p":
            L += [esc(value), ""]
        elif kind == "bullets":
            L += [r"\begin{itemize}"] + [rf"\item {esc(item)}" for item in value] + [r"\end{itemize}", ""]
        elif kind == "caption":
            caption = value
        elif kind in ("table", "cases"):
            n_table += 1
            rows = e5_rows() if kind == "cases" else tables.get(value)
            L.append(latex_table(rows, caption or "", f"tab:{value if kind == 'table' else 'e5'}"))
            caption = None
            if kind == "cases":
                L.append(r"{\footnotesize")
                for case in e5.cases():
                    L += [rf"\noindent\textbf{{{esc(case['clause'])} ({esc(case['lang'])}, {esc(case['variant'])}).}} "
                          f"Original: ``{esc(_clip(case['original']))}'' Simplification: "
                          f"``{esc(_clip(case['simplification']))}'' {esc(case['explanation'])}", ""]
                L.append("}")
        else:
            raise ValueError(f"unknown block kind {kind!r}")
    L += [r"\begin{thebibliography}{99}"]
    unverified = 0
    for i, ref in enumerate(content.REFERENCES, 1):
        mark = ""
        if ref.get("status") != "verified":
            unverified += 1
            mark = r" \textbf{[UNVERIFIED]}"
        L.append(rf"\bibitem{{ref{i}}} {esc(ref['text'])}{mark}")
    L += [r"\end{thebibliography}", "", r"\end{document}", ""]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "main.tex").write_text("\n".join(L), encoding="utf-8")
    (out_dir / "latexmkrc").write_text("# Overleaf and latexmk: compile with XeLaTeX (needed for the Hindi text)\n"
                                       "$pdf_mode = 5;\n", encoding="utf-8")
    fonts = out_dir / "fonts"
    fonts.mkdir(exist_ok=True)
    src = next((p for p in FONT_SOURCES if p.exists()), None)
    if src is None:
        sys.exit(f"{FONT_NAME} not found (install fonts-noto-core, or put it in paper/fonts/)")
    shutil.copy(src, fonts / FONT_NAME)
    (fonts / "README.txt").write_text("Noto Serif Devanagari (Google), SIL Open Font License 1.1: "
                                      "https://openfontlicense.org. Used for the Hindi quotations.\n", encoding="utf-8")
    warnings = [f"{m} not found -> table rendered as [TBD]" for m in tables.missing()]
    if unverified:
        warnings.append(f"{unverified}/{len(content.REFERENCES)} references still marked UNVERIFIED")
    return warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(HERE / "out" / "overleaf"))
    ap.add_argument("--zip", default=str(HERE / "out" / "LMP_paper_overleaf.zip"))
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    for w in build(out):
        print("WARNING:", w)
    with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file() and f.suffix not in (".pdf", ".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".xdv"):
                z.write(f, f.relative_to(out).as_posix())
    print(f"wrote {out / 'main.tex'} and {args.zip}")


if __name__ == "__main__":
    main()
