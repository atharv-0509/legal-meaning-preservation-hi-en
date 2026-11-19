"""Step 1: PDF -> sub-section units.

    python src/extract.py                         # every act and language in sources.json
    python src/extract.py --act rti --lang hi --backend ocr

Backends:
  text  pdftotext (poppler) text layer, preserving physical line breaks.
  gazette  PyMuPDF extraction for the CPA 2019 Gazette's marginal headings.
  ocr-bill  OCR for a scanned Bill as introduced (marginal headings + line-number margins); see
        pdf_ocr_bill_pages. Used for the Hindi CPA 2019 Bill text.
  ocr   pdftoppm -> tesseract. Needed for scanned or legacy-font Hindi PDFs.
        Use the tessdata_best `hin.traineddata` (the fast model misreads legal words);
        point --tessdata-dir at it if it is not the system default.
  auto  text first; for Hindi, switch to OCR when the text layer looks broken
        (low Devanagari ratio or a high "bad-matra" ratio).

Output: data/interim/<act>_<lang>_units.jsonl with
    act_id, lang, section, subsection, key ("s7_1"), heading, text, n_words, n_sents
EN and HI rows of the same provision share `key`, which select_clauses.py uses to align them.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DEV_DIGITS, ROOT, count_sentences, count_words, data_paths, devanagari_ratio,  # noqa: E402
                    load_sources, normalize_text, one_line, units_path, write_jsonl)

DASH = "—"
MATRAS = "ािीुूृॄॅॆेैॉॊोौ्ॢॣ"


# --------------------------------------------------------------------------- PDF -> pages
def pdf_text_pages(pdf: Path) -> list[str]:
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found: install poppler-utils (apt) / poppler (brew).")
    out = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, check=True)
    pages = out.stdout.decode("utf-8", errors="replace").split("\f")
    return [p for p in pages if p.strip()] or [""]


def pdf_gazette_pages(pdf: Path) -> list[str]:
    import pymupdf

    pages = []
    with pymupdf.open(pdf) as document:
        for page in document:
            # shortcut: CPA 2019 Gazette body occupies x=110..480 points; recalibrate for another edition.
            blocks = sorted(page.get_text("blocks", clip=pymupdf.Rect(110, 85, 480, page.rect.height)),
                            key=lambda block: (block[1], block[0]))
            starts = [block for block in blocks if re.match(r"^\d+\.\s", block[4])]
            margins = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    left, top, right, bottom = line["bbox"]
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if top > 85 and (right < 110 or left > 480) and not re.fullmatch(r"\d+ of \d{4}\.", text):
                        margins.append((top, text))
            output = []
            for block in blocks:
                text = block[4]
                if block in starts:
                    index = starts.index(block)
                    end = starts[index + 1][1] - 8 if index + 1 < len(starts) else page.rect.height
                    heading = " ".join(text for top, text in sorted(margins) if block[1] - 8 <= top < end)
                    if not heading:
                        raise ValueError(f"page {page.number + 1}: missing marginal heading; check Gazette layout")
                    text = re.sub(r"^(\d+)\.\s*", lambda match: f"{match[1]}. {heading}{DASH}", text, count=1)
                output.append(text)
            pages.append("\n".join(output))
    return pages


def pdf_ocr_pages(pdf: Path, lang: str, dpi: int = 300, tessdata_dir: str | None = None,
                  cache_dir: Path | None = None) -> list[str]:
    for tool in ("tesseract",):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: OCR needs poppler-utils and tesseract-ocr "
                     "(plus tessdata_best hin.traineddata for Hindi).")
    tlang = "hin+eng" if lang == "hi" else "eng"
    if cache_dir:
        cache = cache_dir / f"{pdf.stem}_{tlang}_{dpi}"
        if cache.exists():
            files = sorted(cache.glob("page-*.txt"))
            if files:
                print(f"  using OCR cache {cache}")
                return [f.read_text(encoding="utf-8") for f in files]
    with tempfile.TemporaryDirectory() as tmp:
        if shutil.which("pdftoppm"):
            subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), f"{tmp}/page"], check=True)
        else:
            import pymupdf

            with pymupdf.open(pdf) as document:
                for index, page in enumerate(document, 1):
                    page.get_pixmap(dpi=dpi).save(f"{tmp}/page-{index:04d}.png")
        images = sorted(Path(tmp).glob("page-*.png"))
        pages = []
        for i, img in enumerate(images, 1):
            cmd = ["tesseract", str(img), "stdout", "-l", tlang, "--psm", "4"]
            if tessdata_dir:
                cmd += ["--tessdata-dir", tessdata_dir]
            r = subprocess.run(cmd, capture_output=True, check=True)
            pages.append(r.stdout.decode("utf-8", errors="replace"))
            print(f"  OCR page {i}/{len(images)}", end="\r")
        print()
    if cache_dir:
        cache.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(pages, 1):
            (cache / f"page-{i:04d}.txt").write_text(p, encoding="utf-8")
    return pages


BILL_BODY_START = re.compile(r"अधिनियमित\s*हो|BE\s+it\s+enacted", re.I)
BILL_BODY_END = re.compile(r"उद्देश्यों\s*और\s*कारणों\s*का\s*कथन|STATEMENT\s+OF\s+OBJECTS\s+AND\s+REASONS", re.I)
_BILL_START = re.compile(r"^\s*(?P<num>\d{0,3})\s*\.\s+(?=\S)")
# OCR variants: "52," for "52.", or one short junk token before the number ("दर 87. (1)"); only with
# digits present, and only accepted when the number is the next in sequence.
_BILL_START_LOOSE = re.compile(r"^\s*(?:\S{1,3}\s+)?(?P<num>\d{1,3})\s*[.,]\s+(?=\S)")
_MARGIN_CITATION = re.compile(r"^[\d\s]+(?:का|of)\s+[\d\s]+$")       # "1860 का 21": an Act cited in the margin


# Systematic misreadings of the conjuncts द्व / द्ध by the Hindi model on the scanned CPA Bill. Only whole
# words that do not exist in Hindi are replaced; every replacement is counted and printed.
OCR_CONJUNCT_FIXES = [
    (re.compile(r"द[ुूृ]वारा"), "द्वारा"),
    (re.compile(r"विरुद[ुूृ]?ध"), "विरुद्ध"),
    (re.compile(r"पद[ुूृ][धच]ति"), "पद्धति"),
]


def fix_ocr_conjuncts(text: str, counts: Counter | None = None) -> str:
    for pat, repl in OCR_CONJUNCT_FIXES:
        text, n = pat.subn(repl, text)
        if counts is not None and n:
            counts[repl] += n
    return text


def bill_number_variants(n: int) -> set[str]:
    """Like ocr_number_variants, plus the digit 1 misread as 4 or 7 (observed on the scanned Hindi
    CPA Bill: 15 -> "45", 51 -> "57", 101 -> "07"). Only used where the sequence check also applies."""
    from itertools import product
    s = str(n)
    options = [("1", "", "0", "4", "7") if c == "1" else (c,) for c in s]
    return {"".join(p) for p in product(*options)} | ocr_number_variants(n)


def _tsv_lines(tsv: str) -> list[dict]:
    """Tesseract TSV -> lines, each with its words' boxes: {top, left, right, words: [(left, right, text)]}."""
    import csv
    import io
    lines: dict[tuple, dict] = {}
    for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if r.get("level") != "5" or not (r.get("text") or "").strip():
            continue
        left, top, w = int(r["left"]), int(r["top"]), int(r["width"])
        k = (int(r["block_num"]), int(r["par_num"]), int(r["line_num"]))
        ln = lines.setdefault(k, {"top": top, "words": []})
        ln["top"] = min(ln["top"], top)
        ln["words"].append((left, left + w, r["text"]))
    out = list(lines.values())
    for ln in out:
        ln["left"], ln["right"] = min(w[0] for w in ln["words"]), max(w[1] for w in ln["words"])
    return out


def _segments(words: list[tuple], gap: int) -> list[list[tuple]]:
    """Split a line's words where the horizontal gap exceeds `gap` pixels (margin note | body | line no.)."""
    words = sorted(words)
    segs = [[words[0]]]
    for w in words[1:]:
        if w[0] - segs[-1][-1][1] > gap:
            segs.append([])
        segs[-1].append(w)
    return segs


def split_bill_page(tsv: str, gap: int = 60) -> tuple[list[dict], list[dict]]:
    """Separate a Bill page into body lines (the main text column) and margin notes (marginal headings).
    Tesseract sometimes reads a margin note and the body line beside it as one line, so each line is
    split at wide gaps (body word spacing is ~15-25 px at 300 dpi; the margin gutter is >100 px). The
    column is the span of the longest segments of full lines (low-percentile left, modal right edge);
    a segment wholly outside it is margin. Line numbers, page numbers and Act citations are dropped."""
    lines = _tsv_lines(tsv)
    if not lines:
        return [], []
    for ln in lines:
        ln["segs"] = _segments(ln["words"], gap)
    mains = [max(ln["segs"], key=len) for ln in lines]
    full = [m for m in mains if len(m) >= 5] or mains
    # Justified text: most lines end at the same x, so the right edge is the most common line end (20 px
    # bins); a high percentile would land on the line numbers, which one line in five carries.
    def mode_edge(xs: list[int]) -> int:
        bins = Counter(x // 20 for x in xs)
        b = max(k for k, v in bins.items() if v == max(bins.values()))
        return max(x for x in xs if x // 20 == b)
    col_l = sorted(m[0][0] for m in full)[len(full) // 10]    # left: indents vary, so a low percentile
    col_r = mode_edge([m[-1][1] for m in full])
    body, margin = [], []
    for ln in lines:
        inside = []
        for seg in ln["segs"]:
            text = " ".join(w[2] for w in seg)
            if seg[-1][1] < col_l - 10 or seg[0][0] > col_r + 10:
                if (re.search(r"[ऀ-ॿ]{2}|[A-Za-z]{3}", text)
                        and not _MARGIN_CITATION.match(text.translate(DEV_DIGITS))):
                    margin.append({"top": ln["top"], "text": text})
            else:
                inside += [w for w in seg if not (re.fullmatch(r"[\W\d०-९lIoO]{1,4}", w[2])
                                                   and not col_l <= (w[0] + w[1]) / 2 <= col_r)]
        text = " ".join(w[2] for w in inside)
        if inside and not re.fullmatch(r"[\W\d०-९\[\]]{0,4}", text.replace(" ", "")):   # page numbers "[6"
            body.append({"top": ln["top"], "left": inside[0][0], "text": text})
    body.sort(key=lambda x: (x["top"], x["left"]))
    return body, sorted(margin, key=lambda m: m["top"])


def pdf_ocr_bill_pages(pdf: Path, lang: str, dpi: int = 300, tessdata_dir: str | None = None,
                       cache_dir: Path | None = None) -> list[str]:
    """OCR for a Bill as introduced (two margins: marginal headings on one side, line numbers on the
    other, alternating by page). Uses Tesseract's page layout analysis (--psm 3) so that margin notes
    come out as separate blocks, keeps the text column, and rewrites each section start as
    "N. <marginal heading>—..." so that parse_sections reads it like an Act. Section numbers are
    accepted only in sequence (the digit 1 is often dropped or misread). Only the enacted text
    between the enacting formula and the Statement of Objects and Reasons is kept."""
    if not shutil.which("tesseract"):
        sys.exit("tesseract not found: OCR needs poppler-utils and tesseract-ocr.")
    # Hindi only: with hin+eng, about half of the CPA Bill units got Latin junk for Hindi words
    # ("gan"/"gar" for द्वारा); the Bill has no English text in the body.
    tlang = "hin" if lang == "hi" else "eng"
    cache = cache_dir / f"{pdf.stem}_{tlang}_{dpi}_bill" if cache_dir else None
    tsvs: list[str] = []
    if cache and cache.exists() and sorted(cache.glob("page-*.tsv")):
        print(f"  using OCR cache {cache}")
        tsvs = [f.read_text(encoding="utf-8") for f in sorted(cache.glob("page-*.tsv"))]
    else:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), f"{tmp}/page"], check=True)
            images = sorted(Path(tmp).glob("page-*.png"))
            for i, img in enumerate(images, 1):
                cmd = ["tesseract", str(img), f"{tmp}/out", "-l", tlang, "--psm", "3",
                       "-c", "tessedit_create_tsv=1", "-c", "tessedit_create_txt=0"]
                if tessdata_dir:
                    cmd += ["--tessdata-dir", tessdata_dir]
                subprocess.run(cmd, capture_output=True, check=True)
                tsvs.append(Path(f"{tmp}/out.tsv").read_text(encoding="utf-8"))
                print(f"  OCR page {i}/{len(images)}", end="\r")
            print()
        if cache:
            cache.mkdir(parents=True, exist_ok=True)
            for i, t in enumerate(tsvs, 1):
                (cache / f"page-{i:04d}.tsv").write_text(t, encoding="utf-8")
    pages = [split_bill_page(t) for t in tsvs]
    # Body = from the enacting formula to the Statement of Objects and Reasons.
    started, ended, kept = False, False, []
    for body, margin in pages:
        if ended:
            break
        lines = []
        for ln in body:
            if not started:
                if BILL_BODY_START.search(ln["text"]):
                    started = True
                continue
            if BILL_BODY_END.search(ln["text"]):
                ended = True
                break
            lines.append(ln)
        if lines:
            kept.append((lines, margin))
    if not started:
        raise ValueError("enacting formula not found: is this a Bill?")
    expected, out_pages, n_fallback = 1, [], 0
    for lines, margin in kept:
        starts = []
        for idx, ln in enumerate(lines):
            m = _BILL_START.match(ln["text"])
            loose = _BILL_START_LOOSE.match(ln["text"])
            if loose and (not m or loose.group("num") == str(expected)):
                if loose.group("num") == str(expected) or loose.group("num") in bill_number_variants(expected):
                    m = loose
            if not m:
                continue
            num = m.group("num")
            if num == str(expected) or num in bill_number_variants(expected):
                starts.append((idx, expected, m.end()))
                expected += 1
            elif num.isdigit() and expected < int(num) <= expected + 3:    # a start was missed: resync
                print(f"  bill layout: no start found for section(s) {expected}..{int(num) - 1}")
                starts.append((idx, int(num), m.end()))
                expected = int(num) + 1
        start_at = {idx: (num, cut) for idx, num, cut in starts}
        tops = [lines[idx]["top"] for idx, _, _ in starts] + [10 ** 9]
        text_lines = []
        for idx, ln in enumerate(lines):
            if idx not in start_at:
                text_lines.append(ln["text"])
                continue
            num, cut = start_at[idx]
            k = [i for i, _, _ in starts].index(idx)
            lo, hi = ln["top"] - 25, tops[k + 1] - 25
            heading = " ".join(m["text"] for m in margin if lo <= m["top"] < hi).strip(" ।|.")
            heading = heading.replace(DASH, " ").replace("--", " ")
            if len(heading) < 2:
                heading, n_fallback = f"खंड {num}" if lang == "hi" else f"Clause {num}", n_fallback + 1
            text_lines.append(f"{num}. {heading}{DASH}{ln['text'][cut:]}")
        out_pages.append("\n".join(text_lines))
    print(f"  bill layout: {expected - 1} sections in sequence, {n_fallback} without a marginal heading")
    if lang == "hi":
        fixes: Counter = Counter()
        out_pages = [fix_ocr_conjuncts(p, fixes) for p in out_pages]
        print(f"  OCR conjunct repairs: {dict(fixes)}")
    return out_pages


# --------------------------------------------------------------------------- quality checks
def bad_matra_ratio(text: str) -> float:
    """Share of Devanagari words that START with a dependent vowel sign or virama.

    In correctly encoded Unicode Hindi this is ~0. Text extracted in visual glyph order
    (e.g. the short-i matra placed before its consonant) produces many such words.
    """
    words = re.findall(r"[ऀ-ॣ०-ॿ]+", text)
    if not words:
        return 0.0
    return sum(w[0] in MATRAS for w in words) / len(words)


def text_quality(pages: list[str], lang: str) -> dict:
    t = "\n".join(pages)
    q = {"chars": len(t), "pages": len(pages)}
    if lang == "hi":
        q["devanagari_ratio"] = round(devanagari_ratio(t), 3)
        q["bad_matra_ratio"] = round(bad_matra_ratio(t), 3)
        q["ok"] = q["chars"] > 500 and q["devanagari_ratio"] >= 0.5 and q["bad_matra_ratio"] <= 0.03
    else:
        q["ok"] = q["chars"] > 500
    return q


# --------------------------------------------------------------------------- cleaning
def fix_hindi_spacing(text: str) -> str:
    """Repair common Hindi PDF/OCR artefacts without changing wording."""
    t = text
    t = re.sub(r"\s*\|\|\s*", " ॥ ", t)
    t = re.sub(r"(?<=[ऀ-ॿ\s])\|", "।", t)          # | -> danda
    t = re.sub(r"\s+।", "।", t)
    t = t.replace("--", DASH).replace("––", DASH)
    # spaces before matras / virama / nukta / anusvara / candrabindu / visarga
    t = re.sub(r"(?<=[ऀ-ॿ])\s+(?=[ऺ-ॏ॑-ॗॢॣँ-ः़])", "", t)
    # split future endings: "करे गा" -> "करेगा", "जाए गी" -> "जाएगी", "हों गे" -> "होंगे"
    t = re.sub(r"(?<=[ेैंएओोँ])\s+(?=(?:गा|गी|गे)(?=[\s।,;:.)\-—]|$))", "", t)
    return t


_FOOTNOTE_EN = re.compile(
    r"^\s*\d{1,2}\s*\.?\s*(?:Subs\.?|Ins\.?|Omitted|Added|Rep\.?|Renumbered|Inserted|Substituted|The words?|"
    r"Vide|Came into force|w\.e\.f|Cl\.|Section \d+ (?:was|of)|Sub-section)(?!\w)", re.I)
_FOOTNOTE_HI = re.compile(
    r"^\s*[\d०-९]{1,2}\s*\.?\s*.{0,80}(?:द्वारा प्रतिस्थापित|द्वारा अंतःस्थापित|द्वारा अंत:स्थापित|का लोप किया गया|"
    r"द्वारा लोप|द्वारा जोड़ा गया|द्वारा निरसित|से प्रवृत्त)")
_CHAPTER = re.compile(r"^\s*(?:CHAPTER|अध्याय)\s+[IVXLC\d०-९]+[A-Z]?\s*$", re.I)
_PAGE_NUM = re.compile(r"^\s*(?:Page\s*)?[\d०-९]{1,3}\s*$|^\s*[-–]\s*\d+\s*[-–]\s*$")


def strip_amendment_markers(text: str) -> str:
    """'1[text]' -> 'text'; '2***' / '3* * *' -> ''."""
    t = re.sub(r"(?<![\w(])[\d०-९]{1,2}\s?\[", "", text)
    t = re.sub(r"[\d०-९]{0,2}\s?\*(?:\s?\*){2,}", " ", t)
    t = t.replace("[", "").replace("]", "")
    return t


def clean_pages(pages: list[str], lang: str, footnotes: bool = True) -> list[str]:
    """Remove running headers/footers, page numbers, chapter lines, bottom-of-page footnotes
    (footnotes=False for a Bill, which has no amendment footnotes; the Hindi footnote pattern would
    otherwise match the repeal section "... इसके द्वारा निरसित ...")."""
    lines_per_page = [[ln.strip() for ln in normalize_text(p).split("\n")] for p in pages]
    # Lines repeated on many pages are running headers/footers.
    freq = Counter(ln for page in lines_per_page for ln in set(page) if ln)
    min_rep = max(3, int(0.3 * len(pages)))
    repeated = {ln for ln, c in freq.items() if c >= min_rep and len(ln) < 80}
    footnote = _FOOTNOTE_HI if lang == "hi" else _FOOTNOTE_EN
    out = []
    for page in lines_per_page:
        kept = []
        n = len(page)
        for i, ln in enumerate(page):
            if not ln or ln in repeated or _PAGE_NUM.match(ln):
                continue
            # Footnotes sit at the bottom of a page: drop from the first footnote line onwards
            # when it occurs in the lower part of the page.
            if footnotes and footnote.match(ln) and i >= 0.4 * n:
                break
            if re.fullmatch(r"_{3,}|-{5,}", ln):
                continue
            if _CHAPTER.match(ln):
                kept.append("<CHAPTER>")
                continue
            kept.append(ln)
        out.append("\n".join(kept))
    return out


def join_lines(text: str, lang: str) -> str:
    t = re.sub(r"(?<=[a-z])-\n(?=[a-z])", "", text) if lang == "en" else text  # de-hyphenate
    t = t.replace("\n", " ")
    t = strip_amendment_markers(t)
    if lang == "hi":
        t = fix_hindi_spacing(t)
    return one_line(t)


# --------------------------------------------------------------------------- parsing
_NUM = r"[\d०-९]+"
# "7. Disposal of request.—(1) ..."  /  "7. अनुरोध का निपटारा—(1) ..."
SECTION_RE = re.compile(
    # The heading may wrap onto a second line, but may not run into the next numbered line.
    rf"(?:^|\n)\s*(?P<num>{_NUM}[A-Z]?|{_NUM}[क-ह]?)\s*\.\s+"
    rf"(?P<head>(?:(?!\n\s*{_NUM}\s*\.\s)(?!<CHAPTER>)[^{DASH}]){{2,220}}?)\s*[.।:]?\s*"
    rf"(?:{DASH}|–|--|:-|\.-)\s*")
SCHEDULE_RE = re.compile(r"\n\s*(?:THE\s+)?(?:FIRST\s+|SECOND\s+|THIRD\s+)?SCHEDULE\b|\n\s*(?:पहली\s+|दूसरी\s+)?अनुसूची\s*\n")
CROSSREF_WORDS = ("sub-section", "sub-sections", "subsection", "section", "sections", "clause", "clauses",
                  "and", "or", "to", "of", "under", "उपधारा", "उपधाराओं", "धारा", "धाराओं", "खंड", "और", "या", "से")
SUB_TERMINATORS = (".", "।", ":", ";", DASH, "–", "-", ")")


def ocr_number_variants(n: int) -> set[str]:
    """How Tesseract's Hindi model renders the number n when it drops or misreads the digit 1
    (observed on the DoPT RTI Hindi PDF: 12 -> "2", 13 -> "03", 1 -> "")."""
    s = str(n)
    out = {s, s.replace("1", ""), s.replace("1", "0")}
    out |= {s[:i] + s[i + 1:] for i, c in enumerate(s) if c == "1"}
    out |= {s[:i] + "0" + s[i + 1:] for i, c in enumerate(s) if c == "1"}
    return out


_OCR_SECTION_HEAD = re.compile(
    rf"(?m)^(?P<lead>[ \t]*)(?P<num>\d*)(?P<sep>[ \t]*\.[ \t]+)(?=[^\n{DASH}]{{2,220}}?(?:{DASH}|–|--|:-|\.-))")


def repair_ocr_numbering(text: str) -> str:
    """Restore section numbers that OCR lost, using the fact that sections are numbered in sequence.
    A header number is rewritten only when it equals the expected next number with a dropped or
    misread "1" (see ocr_number_variants); anything else is left untouched. Also maps "(I)", "(l)",
    "(|)" to "(1)". Only used for OCR output."""
    text = re.sub(r"\((?:I|l|\||!)\)", "(1)", text)
    expected, pieces, pos = 1, [], 0
    for m in _OCR_SECTION_HEAD.finditer(text):
        num = m.group("num")
        if num.isdigit() and int(num) == expected:
            expected += 1
            continue
        if num in ocr_number_variants(expected):
            pieces += [text[pos:m.start("num")], str(expected)]
            pos = m.end("num")
            expected += 1
        elif num.isdigit() and (expected == 1 or expected < int(num) <= expected + 3):
            expected = int(num) + 1      # first header seen, or omitted sections in between
    pieces.append(text[pos:])
    return "".join(pieces)


def parse_sections(text: str, lang: str) -> list[dict]:
    """Find numbered sections. The table of contents is skipped because its entries have no dash
    after the heading; if a number still repeats, the occurrence with the longest body wins."""
    first_section = SECTION_RE.search(text)
    m = SCHEDULE_RE.search(text, pos=first_section.end()) if first_section else None
    if m:
        text = text[:m.start()]
    matches = list(SECTION_RE.finditer(text))
    found: dict[str, dict] = {}
    for i, mt in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        num = mt.group("num").translate(DEV_DIGITS)
        body_raw = text[mt.end():end]
        body_raw = body_raw.split("<CHAPTER>")[0]   # chapter heading ends the section
        body = join_lines(body_raw, lang)
        heading = join_lines(mt.group("head"), lang).rstrip(".। ")
        if num not in found or len(body) > len(found[num]["body"]):
            found[num] = {"section": num, "heading": heading, "body": body}
    def sort_key(s):
        m2 = re.match(r"(\d+)(.*)", s)
        return (int(m2.group(1)), m2.group(2)) if m2 else (10 ** 6, s)
    return [found[k] for k in sorted(found, key=sort_key)]


BILL_SUB_TERMINATORS = (".", "।", ":", DASH, "–", "-")


def split_subsections(body: str, ocr: bool = False, bill: bool = False) -> list[tuple[str, str]]:
    """Split a section body at "(1)", "(2)", ... Only sequential numbers that start a sentence
    count; "(3)" right after "sub-section"/"section"/"उपधारा"/"धारा"/"and"/"or" is a cross-reference.
    With ocr=True a sub-section number may also be the expected number with a dropped/misread "1"
    ("()" for (1), "(2)" for (12)); it is then recorded as the expected number.
    With bill=True (scanned Bill text, see pdf_ocr_bill_pages) the digit 1 may also read as 4 or 7 or a
    danda/bar ("(7)", "(।)", "(॥)"), a sub-section must follow ".", "।", ":" or a dash (not ";", which
    ends list items, where OCR can turn "(ण)" into "(3)"), and one short junk token after the terminator
    is tolerated (stray margin marks).
    Returns [(subsection_number, text)], or [("", body)] when the section has no sub-sections."""
    num_pat = r"[\d०-९]*" if ocr else rf"{_NUM}[A-Z]?"
    if bill:
        num_pat = r"[\d०-९।॥|\]Il]*"
    cands = list(re.finditer(rf"\(({num_pat})\)", body))
    variants = bill_number_variants if bill else ocr_number_variants
    terminators = BILL_SUB_TERMINATORS if bill else SUB_TERMINATORS
    starts: list[tuple[int, int, str]] = []
    expected = 1
    for m in cands:
        num = m.group(1).translate(DEV_DIGITS)
        if bill and expected == 1 and num in ("।", "॥", "|", "]", "I", "l", "7", "4"):
            num = "1"
        if ocr and num != str(expected) and num in variants(expected):
            num = str(expected)
        digits = re.match(r"\d+", num)
        if not digits or int(digits.group()) != expected or num != digits.group():
            continue
        before = body[:m.start()].rstrip()
        prev_word = re.findall(r"[\w\-ऀ-ॿ]+", before[-30:].lower())
        if prev_word and prev_word[-1] in CROSSREF_WORDS:
            continue
        verb_semicolon = bill and re.search(r"(?:गा|गी|गे|है|हैं)\s*;$", before)   # "... दंडनीय होगा ; (2)"
        if bill and before and not before.endswith(terminators) and not verb_semicolon:
            before = re.sub(r"\s+\S{1,6}$", "", before)          # one stray junk token
        if before and not before.endswith(terminators) and not verb_semicolon:
            continue
        if expected == 1 and len(before) > 5:   # (1) must open the section body
            continue
        starts.append((m.start(), m.end(), num))
        expected += 1
    if not starts:
        return [("", body.strip())]
    out = []
    for i, (s, e, num) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(body)
        out.append((num, body[e:end].strip()))
    return out


def units_from_pages(pages: list[str], act_id: str, lang: str, ocr: bool = False, bill: bool = False) -> list[dict]:
    cleaned = clean_pages(pages, lang, footnotes=not bill)
    text = "\n".join(cleaned)
    if ocr:
        text = repair_ocr_numbering(text)
    units = []
    for sec in parse_sections(text, lang):
        for sub, t in split_subsections(sec["body"], ocr=ocr, bill=bill):
            t = t.strip()
            if not t or re.fullmatch(r"(?:Omitted|\[?Omitted\.?\]?|लोप किया गया)\W*", t, re.I):
                continue
            key = f"s{sec['section']}_{sub}" if sub else f"s{sec['section']}"
            units.append({
                "act_id": act_id, "lang": lang, "section": sec["section"], "subsection": sub, "key": key,
                "heading": sec["heading"], "text": t, "n_words": count_words(t), "n_sents": count_sentences(t),
            })
    return units


# --------------------------------------------------------------------------- CLI
def extract_one(act: dict, lang: str, backend: str, paths, args) -> list[dict]:
    pdf = ROOT / act["pdf"][lang] if not Path(act["pdf"][lang]).is_absolute() else Path(act["pdf"][lang])
    if args.raw_dir:
        pdf = Path(args.raw_dir) / Path(act["pdf"][lang]).name
    if not pdf.exists():
        print(f"[{act['act_id']}/{lang}] missing {pdf} — download it by hand (see data/raw/README.md).")
        return []
    print(f"[{act['act_id']}/{lang}] {pdf.name} backend={backend}")
    pages = pdf_gazette_pages(pdf) if backend == "gazette" else None
    if backend == "ocr-bill":
        pages = pdf_ocr_bill_pages(pdf, lang, args.dpi, args.tessdata_dir, paths.data / "ocr_cache")
        print(f"  OCR: {text_quality(pages, lang)}")
    if backend in ("text", "auto"):
        pages = pdf_text_pages(pdf)
        q = text_quality(pages, lang)
        print(f"  text layer: {q}")
        if not q["ok"]:
            msg = ("  text layer looks broken (scanned / legacy font / visual glyph order)."
                   " Use --backend ocr.")
            if backend == "auto" and shutil.which("tesseract"):
                print(msg + " Switching to OCR (auto).")
                pages = None
            else:
                print(msg)
    used_ocr = pages is None or backend == "ocr-bill"
    if pages is None:
        pages = pdf_ocr_pages(pdf, lang, args.dpi, args.tessdata_dir, paths.data / "ocr_cache")
        print(f"  OCR: {text_quality(pages, lang)}")
    units = units_from_pages(pages, act["act_id"], lang, ocr=used_ocr, bill=backend == "ocr-bill")
    out = units_path(paths, act["act_id"], lang)
    write_jsonl(out, units)
    n_sec = len({u["section"] for u in units})
    print(f"  -> {out}  ({n_sec} sections, {len(units)} units)")
    if lang == "hi":
        bm = bad_matra_ratio(" ".join(u["text"] for u in units))
        print(f"  bad-matra ratio in units: {bm:.3f}" + ("  <-- high: try --backend ocr" if bm > 0.03 else ""))
    return units


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--act", help="act_id from sources.json (default: all)")
    ap.add_argument("--lang", choices=["en", "hi"], help="default: both")
    ap.add_argument("--backend", choices=["auto", "text", "gazette", "ocr", "ocr-bill"], default="auto")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--tessdata-dir", help="directory holding tessdata_best hin.traineddata / eng.traineddata")
    ap.add_argument("--sources", default=None)
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--raw-dir", default=None, help="override PDF directory (default: paths in sources.json)")
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    acts = [a for a in load_sources(args.sources) if not args.act or a["act_id"] == args.act]
    if not acts:
        sys.exit(f"unknown act {args.act!r}")
    for act in acts:
        for lang in ([args.lang] if args.lang else ["en", "hi"]):
            extract_one(act, lang, args.backend, paths, args)


if __name__ == "__main__":
    main()
