"""Shared helpers: paths, JSONL I/O, text normalisation, a Devanagari-aware tokeniser,
ROUGE / BLEU on that tokeniser, legal-marker detection and sentence splitting.

Why our own ROUGE: the `rouge_score` package drops every non-ASCII character, so every Hindi
pair would look "unrelated". The tokeniser below keeps Devanagari words whole, including
matras (vowel signs), virama, nukta and anusvara.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data"
DEFAULT_SOURCES = ROOT / "sources.json"
LANGS = ("en", "hi")


# --------------------------------------------------------------------------- paths
def data_paths(data_dir: str | Path | None = None) -> SimpleNamespace:
    """All pipeline locations under one data directory (tests pass a temp dir)."""
    d = Path(data_dir) if data_dir else DEFAULT_DATA
    p = SimpleNamespace(
        data=d,
        raw=d / "raw",
        interim=d / "interim",
        processed=d / "processed",
        annotation=d / "annotation",
        pilot=d / "annotation" / "pilot",
        splits=d / "splits",
        reports=(d.parent / "reports") if d == DEFAULT_DATA else d / "reports",
    )
    p.clauses = p.processed / "clauses.jsonl"
    p.review_csv = p.processed / "clauses_review.csv"
    p.clauses_final = p.processed / "clauses_final.jsonl"
    p.simplifications = p.processed / "simplifications.jsonl"
    p.perturbations = p.processed / "perturbations.jsonl"
    p.augment = p.processed / "augment_pairs.jsonl"
    p.holdout_identical = p.processed / "holdout_identical.jsonl"
    p.holdout_unrelated = p.processed / "holdout_unrelated.jsonl"
    p.pairs = p.processed / "pairs.jsonl"
    p.assignment = p.processed / "assignment.jsonl"
    p.labeled = p.processed / "labeled_pairs.jsonl"
    p.annotations = p.processed / "annotations.jsonl"
    return p


def units_path(paths: SimpleNamespace, act_id: str, lang: str) -> Path:
    return paths.interim / f"{act_id}_{lang}_units.jsonl"


def load_sources(path: str | Path | None = None) -> list[dict]:
    with open(path or DEFAULT_SOURCES, encoding="utf-8") as f:
        return json.load(f)["acts"]


# --------------------------------------------------------------------------- I/O
def read_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def iter_jsonl(path: str | Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(path: str | Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def write_csv(path: str | Path, rows: list[dict], fields: list[str]) -> None:
    """CSV with a BOM (utf-8-sig) so Excel on Windows shows Hindi correctly."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in fields})


def read_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _csv_cell(v):
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return "" if v is None else v


def short_hash(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


# --------------------------------------------------------------------------- text
ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", " ": " "})
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_text(text: str) -> str:
    """NFC, strip zero-width joiners / soft hyphens, unify quotes, collapse whitespace."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).translate(ZERO_WIDTH).translate(_QUOTES)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    return t.strip()


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(text)).strip()


def devanagari_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha() or "ऀ" <= c <= "ॿ"]
    if not letters:
        return 0.0
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters)


# Devanagari letters + signs + digits, excluding the dandas U+0964/U+0965 (punctuation).
_DEV = "ऀ-ॣ०-ॿ"
_TOKEN_RE = re.compile(rf"[{_DEV}]+|[A-Za-z0-9]+(?:['.][A-Za-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lower-cased word tokens; Devanagari words keep their matras/virama/nukta."""
    t = normalize_text(text).lower().translate(DEV_DIGITS)
    return _TOKEN_RE.findall(t)


def count_words(text: str) -> int:
    return len(tokenize(text))


# --------------------------------------------------------------------------- overlap metrics
def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _f1(overlap: float, n_ref: float, n_hyp: float) -> float:
    if n_ref == 0 or n_hyp == 0 or overlap == 0:
        return 0.0
    p, r = overlap / n_hyp, overlap / n_ref
    return 2 * p * r / (p + r)


def rouge_n(ref: str, hyp: str, n: int = 1) -> float:
    r, h = _ngrams(tokenize(ref), n), _ngrams(tokenize(hyp), n)
    return _f1(sum((r & h).values()), sum(r.values()), sum(h.values()))


def _lcs(a: list[str], b: list[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def rouge_l(ref: str, hyp: str) -> float:
    r, h = tokenize(ref), tokenize(hyp)
    return _f1(_lcs(r, h), len(r), len(h))


def bleu(ref: str, hyp: str, max_n: int = 4) -> float:
    """Sentence BLEU (0-100) with add-one smoothing for n>1 (Lin & Och 2004)."""
    r, h = tokenize(ref), tokenize(hyp)
    if not h or not r:
        return 0.0
    log_p = 0.0
    for n in range(1, max_n + 1):
        hn, rn = _ngrams(h, n), _ngrams(r, n)
        match, total = sum((hn & rn).values()), max(sum(hn.values()), 0)
        if n == 1:
            if match == 0:
                return 0.0
            p = match / total
        else:
            p = (match + 1) / (total + 1)
        log_p += math.log(p) / max_n
    bp = 1.0 if len(h) > len(r) else math.exp(1 - len(r) / len(h))
    return 100.0 * bp * math.exp(log_p)


def overlap_scores(a: str, b: str) -> dict:
    return {
        "rouge1": rouge_n(a, b, 1), "rouge2": rouge_n(a, b, 2),
        "rougeL": rouge_l(a, b), "bleu": bleu(a, b),
    }


def is_unrelated(a: str, b: str, rouge_max: float = 0.25, bleu_max: float = 25.0) -> bool:
    """JUDGEBERT's criterion for unrelated pairs: ROUGE-1/2/L < 0.25 and BLEU < 25."""
    s = overlap_scores(a, b)
    return s["rouge1"] < rouge_max and s["rouge2"] < rouge_max and s["rougeL"] < rouge_max and s["bleu"] < bleu_max


# --------------------------------------------------------------------------- sentences
_ABBREV = r"(?:No|Nos|Sec|Secs|Cl|Art|Govt|Ltd|Co|Rs|viz|i\.e|e\.g|etc|Dr|Mr|Mrs|Ms|St|Sub|Ch|Vol|Hon|Ord|Notfn|S)"


def split_sentences(text: str) -> list[str]:
    """Rule-based splitter for English and Hindi legal text.

    Splits after '.', '?', '!', '।' when followed by space + an upper-case letter, a Devanagari
    letter, a quote or an opening bracket. Common legal abbreviations ("No.", "Rs.", "i.e.")
    and enumerations like "(a)." are protected.
    """
    t = one_line(text)
    if not t:
        return []
    protected = re.sub(rf"\b({_ABBREV})\.(?=\s)", lambda m: m.group(1) + "<DOT>", t)
    protected = re.sub(r"\b([A-Z])\.(?=\s?[A-Z]\.)", r"\1<DOT>", protected)  # initials
    parts = re.split(r"(?<=[.?!।])\s+(?=[A-Zऀ-ॿ\"'(‘“])", protected)
    out = [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]
    return out


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


# --------------------------------------------------------------------------- legal markers
# Used for clause weighting (select_clauses) and as review metadata. Patterns are lower-case.
LEGAL_MARKERS = {
    "en": {
        "exception": [r"\bexcept\b", r"\bunless\b", r"\bprovided that\b", r"\bother than\b",
                      r"\bsave as\b", r"\bexcluding\b", r"\bshall not apply\b", r"\bexplanation\b"],
        "override": [r"\bnotwithstanding\b", r"\bsubject to\b", r"\bin addition to\b",
                     r"\bin derogation of\b", r"\boverrid"],
        "condition": [r"\bif\b", r"\bwhere\b", r"\bin case\b", r"\bwhen\b", r"\bon (?:the )?(?:receipt|payment)\b"],
        "time_limit": [r"\bwithin\s+\w+(?:-\w+)?\s+(?:\(\d+\)\s+)?(?:days|months|years|hours)\b",
                       r"\b\d+\s+(?:days|months|years|hours)\b", r"\bnot later than\b", r"\bforthwith\b"],
        "obligation": [r"\bshall\b(?!\s+not)", r"\bmust\b", r"\bis required to\b"],
        "permission": [r"\bmay\b"],
        "prohibition": [r"\bshall not\b", r"\bno\s+\w+\s+shall\b", r"\bmay not\b"],
        "number": [r"\b\d+\b", r"\brupees\b", r"\bper cent\b"],
    },
    "hi": {
        "exception": [r"सिवाय", r"को छोड़कर", r"जब तक कि", r"परंतु", r"परन्तु", r"स्पष्टीकरण",
                      r"लागू नहीं होगा", r"अपवाद"],
        "override": [r"के होते हुए भी", r"के अधीन रहते हुए", r"के अतिरिक्त", r"अल्पीकरण"],
        "condition": [r"यदि", r"जहां", r"जहाँ", r"की दशा में", r"जब", r"की प्राप्ति पर"],
        "time_limit": [r"\d+\s+(?:दिन|मास|महीने|वर्ष|घंटे)", r"दिन के भीतर", r"दिनों के भीतर", r"के भीतर",
                       r"तुरंत", r"अविलंब"],
        "obligation": [r"करेगा", r"करेगी", r"करेंगे", r"जाएगा", r"जाएगी", r"होगा", r"देगा", r"ना होगा"],
        "permission": [r"सकेगा", r"सकेगी", r"सकता", r"सकती", r"सकते"],
        "prohibition": [r"नहीं करेगा", r"नहीं किया जाएगा", r"कोई .{0,20} नहीं"],
        "number": [r"[0-9०-९]+", r"रुपए", r"रुपये", r"प्रतिशत"],
    },
}
_MARKER_RE = {lang: {k: re.compile("|".join(v), re.I) for k, v in d.items()} for lang, d in LEGAL_MARKERS.items()}


def find_markers(text: str, lang: str) -> list[str]:
    t = one_line(text).lower()
    return [k for k, rx in _MARKER_RE[lang].items() if rx.search(t)]


def numbers_in(text: str) -> list[str]:
    """Numbers in the text (Devanagari digits converted), for EN/HI consistency checks."""
    return sorted(re.findall(r"\d+", one_line(text).translate(DEV_DIGITS)))


# --------------------------------------------------------------------------- statistics (no scipy)
def mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def std(xs, ddof: int = 0) -> float:
    xs = list(xs)
    if len(xs) - ddof <= 0:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - ddof))


def pearson(x, y) -> float:
    x, y = list(x), list(y)
    if len(x) < 2:
        return float("nan")
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else float("nan")


def rankdata(xs) -> list[float]:
    """Average ranks for ties (1-based)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y) -> float:
    return pearson(rankdata(list(x)), rankdata(list(y)))
