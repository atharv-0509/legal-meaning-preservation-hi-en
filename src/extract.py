"""Step 1: PDF -> sub-section units.

    python src/extract.py                         # every act and language in sources.json
    python src/extract.py --act rti --lang hi --backend ocr

Backends:
  text  pdftotext (poppler) text layer, preserving physical line breaks.
  gazette  PyMuPDF extraction for the CPA 2019 Gazette's marginal headings.
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
    for tool in ("pdftoppm", "tesseract"):
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
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), f"{tmp}/page"], check=True)
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


def clean_pages(pages: list[str], lang: str) -> list[str]:
    """Remove running headers/footers, page numbers, chapter lines, bottom-of-page footnotes."""
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
            if footnote.match(ln) and i >= 0.4 * n:
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


def split_subsections(body: str) -> list[tuple[str, str]]:
    """Split a section body at "(1)", "(2)", ... Only sequential numbers that start a sentence
    count; "(3)" right after "sub-section"/"section"/"उपधारा"/"धारा"/"and"/"or" is a cross-reference.
    Returns [(subsection_number, text)], or [("", body)] when the section has no sub-sections."""
    cands = list(re.finditer(rf"\(({_NUM}[A-Z]?)\)", body))
    starts: list[tuple[int, int, str]] = []
    expected = 1
    for m in cands:
        num = m.group(1).translate(DEV_DIGITS)
        digits = re.match(r"\d+", num)
        if not digits or int(digits.group()) != expected or num != digits.group():
            continue
        before = body[:m.start()].rstrip()
        prev_word = re.findall(r"[\w\-ऀ-ॿ]+", before[-30:].lower())
        if prev_word and prev_word[-1] in CROSSREF_WORDS:
            continue
        if before and not before.endswith(SUB_TERMINATORS):
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


def units_from_pages(pages: list[str], act_id: str, lang: str) -> list[dict]:
    cleaned = clean_pages(pages, lang)
    text = "\n".join(cleaned)
    units = []
    for sec in parse_sections(text, lang):
        for sub, t in split_subsections(sec["body"]):
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
    if pages is None:
        pages = pdf_ocr_pages(pdf, lang, args.dpi, args.tessdata_dir, paths.data / "ocr_cache")
        print(f"  OCR: {text_quality(pages, lang)}")
    units = units_from_pages(pages, act["act_id"], lang)
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
    ap.add_argument("--backend", choices=["auto", "text", "gazette", "ocr"], default="auto")
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
