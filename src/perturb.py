"""Step 4: inject ONE rule-based legal error into each `normal` simplification (EN + HI).

    python src/perturb.py [--seed 7]

Error types (balanced across the set; each output row records `error_type` and `change`):
  modality        obligation -> permission (shall/must -> may) or permission -> obligation (may -> must)
  negation        remove or insert a negation
  number          change a number / time limit / amount
  exception_drop  delete an exception, proviso or override clause
  scope           all/every/any -> some/certain, drop "only" (EN); सभी/प्रत्येक/किसी भी -> कुछ/किसी विशेष (HI)

Annotators score these blind; the known error type makes them a labelled diagnostic set (E5).
Hindi verb rules only fire at clause ends (before । , ; or end of text), so words like उपयोगी
are never touched. Add a unit test in tests/test_units.py for any new rule.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEV_DIGITS, data_paths, one_line, read_jsonl, split_sentences, write_jsonl  # noqa: E402

ERROR_TYPES = ("modality", "negation", "number", "exception_drop", "scope")


@dataclass
class Edit:
    start: int
    end: int
    repl: str
    rule: str

    def apply(self, text: str) -> str:
        out = text[: self.start] + self.repl + text[self.end:]
        out = re.sub(r"\s{2,}", " ", out)
        out = re.sub(r"\s+([,.;:।])", r"\1", out)
        out = re.sub(r"^[\s,;]+", "", out)
        out = re.sub(r"([.।])\s*[,;]\s*", r"\1 ", out)
        out = re.sub(r",\s*([.।])", r"\1", out)
        return out.strip()


def _case(src: str, repl: str) -> str:
    if repl and src[:1].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def _cap_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


# Hindi word boundaries (\b is unreliable with combining matras)
HB = r"(?<![ऀ-ॿ\w])"
HE = r"(?![ऀ-ॿ\w])"
HI_END = r"(?=\s*(?:[।,;:.!?|]|$))"   # clause end


# =========================================================================== modality
EN_OBLIG = re.compile(r"\b(shall|must|has to|have to|is required to|are required to|is obliged to|"
                      r"are obliged to|needs to|need to|is bound to|are bound to)\b(?!\s+not\b)", re.I)
EN_PERM = re.compile(r"\b(may|can|is allowed to|are allowed to|is permitted to|are permitted to|"
                     r"is free to|are free to)\b(?!\s+not\b)", re.I)
EN_PERM_SKIP_BEFORE = re.compile(r"(?:\bas|\bcase|\bwhich|\bthat|\bwhat)\s*$", re.I)
EN_PERM_SKIP_AFTER = re.compile(r"^\s+be\s+(?:prescribed|specified|notified|necessary|required|determined)", re.I)


def en_modality(text: str) -> list[Edit]:
    edits = []
    for m in EN_OBLIG.finditer(text):
        edits.append(Edit(m.start(), m.end(), _case(m.group(), "may"), f"obligation->permission ({m.group()}->may)"))
    for m in EN_PERM.finditer(text):
        if EN_PERM_SKIP_BEFORE.search(text[: m.start()]) or EN_PERM_SKIP_AFTER.match(text[m.end():]):
            continue
        edits.append(Edit(m.start(), m.end(), _case(m.group(), "must"), f"permission->obligation ({m.group()}->must)"))
    return edits


HI_FUT = {"m": ("ेगा", "एगा", "गा", "सकेगा"), "f": ("ेगी", "एगी", "गी", "सकेगी"), "p": ("ेंगे", "एंगे", "ंगे", "सकेंगे")}
HI_SHALL_LEXICON = {
    "होगा": "हो सकेगा", "होगी": "हो सकेगी", "होंगे": "हो सकेंगे",
    "देगा": "दे सकेगा", "देगी": "दे सकेगी", "देंगे": "दे सकेंगे",
    "लेगा": "ले सकेगा", "लेगी": "ले सकेगी", "लेंगे": "ले सकेंगे",
}


def hi_future(stem: str, gn: str) -> str:
    """Future (shall) form of a verb stem: कर->करेगा, लगा->लगाएगा, दे->देगा, जा->जाएगा."""
    cons, vowel, short, _ = HI_FUT[gn]
    if stem.endswith(("ा", "आ")):
        return stem + vowel
    if stem.endswith(("े", "ो", "ी", "ू")):
        return stem + short
    return stem + cons


def _hi_shall_to_may(word: str) -> str | None:
    if word in HI_SHALL_LEXICON:
        return HI_SHALL_LEXICON[word]
    for gn, (cons, vowel, _short, may) in HI_FUT.items():
        for suf in (vowel, vowel.replace("ए", "ये")):
            if word.endswith(suf) and len(word) > len(suf):
                return word[: -len(suf)] + " " + may          # जाएगा -> जा सकेगा
        if word.endswith(cons) and len(word) - len(cons) >= 2:
            return word[: -len(cons)] + " " + may             # करेगा -> कर सकेगा
    return None


def hi_modality(text: str) -> list[Edit]:
    edits = []
    # must -> may: करना होगा -> करने की छूट है
    for m in re.finditer(HB + r"(\S+?)(?:ना|नी|ने)\s+(?:होगा|होगी|होंगे)" + HI_END, text):
        edits.append(Edit(m.start(), m.end(), m.group(1) + "ने की छूट है", f"must->may ({m.group()})"))
    must_spans = [(e.start, e.end) for e in edits]
    # may -> shall: लगा सकता है -> लगाएगा, कर सकेगा -> करेगा
    for m in re.finditer(HB + r"(\S+)\s+(सकता है|सकती है|सकते हैं|सकेगा|सकेगी|सकेंगे)" + HI_END, text):
        aux = m.group(2)
        gn = "f" if ("ती" in aux or "गी" in aux) else "p" if ("ते" in aux or "गे" in aux) else "m"
        if m.group(1) == "नहीं":
            continue
        edits.append(Edit(m.start(), m.end(), hi_future(m.group(1), gn), f"may->shall ({m.group()})"))
    # shall -> may: करेगा -> कर सकेगा (clause-final verbs only)
    for m in re.finditer(HB + r"([^\s\u0964,;:.!?|]+)" + HI_END, text):
        w = m.group(1)
        if any(s <= m.start() < e for s, e in must_spans) or w.startswith(("सक",)):
            continue
        before = text[: m.start()].split()
        if before and before[-1] == "नहीं":
            continue
        if w in ("होगा", "होगी", "होंगे") and before and before[-1].endswith(("ना", "नी", "ने")):
            continue
        new = _hi_shall_to_may(w)
        if new:
            edits.append(Edit(m.start(), m.end(), new, f"shall->may ({w}->{new})"))
    return edits


# =========================================================================== negation
EN_NEG = re.compile(r"\b(shall|must|may|will|does|do|did|is|are|was|were|can|could|should|would|has|have|need)\s+not\b", re.I)
EN_NEG_CONTR = {"cannot": "can", "can't": "can", "won't": "will", "doesn't": "does", "don't": "do",
                "isn't": "is", "aren't": "are", "shouldn't": "should", "mustn't": "must", "didn't": "did"}
EN_INS_MODAL = re.compile(r"\b(shall|must|may|will|can|should)\b(?!\s+not\b)", re.I)
EN_INS_COPULA = re.compile(r"\b(is|are)\b(?!\s+not\b)", re.I)


def en_negation(text: str) -> list[Edit]:
    edits = [Edit(m.start(), m.end(), m.group(1), f"remove negation ({m.group()})") for m in EN_NEG.finditer(text)]
    for w, r in EN_NEG_CONTR.items():
        for m in re.finditer(rf"\b{re.escape(w)}\b", text, re.I):
            edits.append(Edit(m.start(), m.end(), _case(m.group(), r), f"remove negation ({m.group()})"))
    if edits:
        return edits
    ins = list(EN_INS_MODAL.finditer(text)) or list(EN_INS_COPULA.finditer(text))
    for m in ins:
        if EN_PERM_SKIP_BEFORE.search(text[: m.start()]) or EN_PERM_SKIP_AFTER.match(text[m.end():]):
            continue                                          # "as may be prescribed" is not a rule
        repl = "cannot" if m.group().lower() == "can" else m.group() + " not"
        edits.append(Edit(m.start(), m.end(), _case(m.group(), repl), f"insert negation ({m.group()}->{repl})"))
    return edits


HI_AUX = {"है", "हैं", "था", "थी", "थे", "जाएगा", "जाएगी", "जाएंगे", "जाएँगे", "जायेगा", "जायेगी", "सकेगा", "सकेगी",
          "सकेंगे", "सकता", "सकती", "सकते", "जाता", "जाती", "जाते", "जा", "गया", "गई", "गए", "रहा", "रही", "रहे"}
HI_VERBISH = re.compile(r"(?:गा|गी|गे|है|हैं|था|थी|थे)$")


def hi_negation(text: str) -> list[Edit]:
    edits = [Edit(m.start(), m.end(), "", "remove negation (नहीं)")
             for m in re.finditer(HB + r"नहीं\s*" + HE, text)]
    if edits:
        return edits
    # insert नहीं before the main verb of each clause-final verb group
    for clause in re.finditer(r"[^।;|]+", text):
        words = list(re.finditer(r"\S+", clause.group()))
        if not words:
            continue
        last = words[-1].group().rstrip(",.:!?")
        if not HI_VERBISH.search(last):
            continue
        i = len(words) - 1
        if last in ("है", "हैं") and (len(words) < 2 or words[-2].group() not in HI_AUX):
            target = i                                       # अधिकार है -> अधिकार नहीं है
        else:
            while i > 0 and words[i].group().rstrip(",.:!?") in HI_AUX:
                i -= 1
            target = i                                       # किया जाएगा -> नहीं किया जाएगा
        pos = clause.start() + words[target].start()
        edits.append(Edit(pos, pos, "नहीं ", f"insert negation (before {words[target].group()})"))
    return edits


# =========================================================================== numbers
NUM_MAP = {1: 2, 2: 3, 3: 5, 4: 6, 5: 10, 6: 3, 7: 15, 8: 4, 10: 15, 12: 6, 14: 21, 15: 30, 20: 30, 21: 14,
           24: 48, 25: 50, 30: 60, 35: 45, 40: 30, 45: 90, 48: 72, 50: 25, 60: 90, 90: 120, 100: 500,
           120: 90, 180: 90, 500: 1000, 1000: 5000}
EN_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "ten": 10, "twelve": 12, "fourteen": 14, "fifteen": 15, "twenty": 20, "twenty-one": 21,
                "twenty-four": 24, "twenty-five": 25, "thirty": 30, "thirty-five": 35, "forty": 40,
                "forty-five": 45, "forty-eight": 48, "fifty": 50, "sixty": 60, "ninety": 90, "hundred": 100}
HI_NUM_WORDS = {"एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "दस": 10,
                "बारह": 12, "चौदह": 14, "पंद्रह": 15, "बीस": 20, "इक्कीस": 21, "चौबीस": 24, "पच्चीस": 25, "तीस": 30,
                "पैंतीस": 35, "चालीस": 40, "पैंतालीस": 45, "अड़तालीस": 48, "पचास": 50, "साठ": 60, "नब्बे": 90, "सौ": 100}
EN_UNITS = r"(?:days?|months?|years?|hours?|weeks?|rupees|lakhs?|crores?|per\s*cent|percent|%|members?|persons?|times)"
HI_UNITS = r"(?:दिन|दिनों|मास|महीने|महीनों|माह|वर्ष|वर्षों|साल|घंटे|घंटों|सप्ताह|रुपए|रुपये|लाख|करोड़|प्रतिशत|सदस्य|सदस्यों|व्यक्ति)"
REF_BEFORE = re.compile(r"(?:section|sections|sub-section|sub-sections|clause|clauses|rule|rules|article|chapter|"
                        r"schedule|item|para|paragraph|form|no\.|धारा|धाराओं|उपधारा|उपधाराओं|खंड|नियम|अनुच्छेद|अध्याय|"
                        r"अनुसूची|प्ररूप)\s*\(?\s*$", re.I)


def _new_value(n: int) -> int:
    return NUM_MAP.get(n, n * 2 if n < 1000 else n // 2)


def _render(n: int, like: str, words: dict) -> str:
    inv = {v: k for k, v in words.items()}
    if like.strip().isdigit():
        s = str(n)
        if any("०" <= c <= "९" for c in like):
            s = s.translate(str.maketrans("0123456789", "०१२३४५६७८९"))
        return s
    return inv.get(n, str(n))


def numbers_edits(text: str, lang: str) -> list[Edit]:
    words = HI_NUM_WORDS if lang == "hi" else EN_NUM_WORDS
    units = HI_UNITS if lang == "hi" else EN_UNITS
    word_alt = "|".join(sorted(map(re.escape, words), key=len, reverse=True))
    if lang == "hi":
        rx = re.compile(HB + rf"([\d०-९]+(?:,[\d]+)*|{word_alt})" + HE)
    else:
        rx = re.compile(rf"\b(\d+(?:,\d{{3}})*|{word_alt})\b", re.I)
    unit_edits, other_edits = [], []
    for m in rx.finditer(text):
        tok = m.group(1)
        digits = tok.replace(",", "").translate(DEV_DIGITS)
        is_digit = digits.isdigit()
        n = int(digits) if is_digit else words.get(tok.lower() if lang == "en" else tok)
        if n is None:
            continue
        before, after = text[: m.start()], text[m.end():]
        if REF_BEFORE.search(before):
            continue
        if is_digit and 1900 <= n <= 2099 and len(digits) == 4:
            continue                                          # years (e.g. Act, 2005)
        if before.rstrip().endswith("(") and after.lstrip().startswith(")"):
            continue                                          # (1), (a) enumerations
        has_unit = re.match(r"\s*(?:\(\s*\d+\s*\)\s*)?" + units, after, re.I) is not None
        if not is_digit and not has_unit:
            continue                                          # "one of", "एक व्यक्ति" are not quantities
        new = _new_value(n)
        repl = _case(tok, _render(new, tok, words)) if lang == "en" else _render(new, tok, words)
        e = Edit(m.start(), m.end(), repl, f"number {tok}->{repl}")
        (unit_edits if has_unit else other_edits).append(e)
    return unit_edits or other_edits


# =========================================================================== exception drop
EN_EXC_SENT = re.compile(r"^(?:Provided(?: that)?|However|But|Except|Unless|This (?:rule )?does not apply|"
                         r"There (?:is|are) (?:an )?exceptions?|An exception|Exceptions?)\b", re.I)
EN_EXC_LEAD = re.compile(r"(?:(?<=^)|(?<=[.;:]\s))(?:Except|Unless|Subject to|Notwithstanding|Other than|Apart from|"
                         r"Save as)\b[^,.;]{3,160},\s*", re.I)
EN_EXC_MID = re.compile(r",?\s*\b(?:except|unless|other than|excluding|save for|apart from|but not|subject to)\b"
                        r"[^.;,]{3,160}(?=[.;,]|$)", re.I)


def _sentence_spans(text: str, splitter) -> list[tuple[int, int]]:
    spans, pos = [], 0
    for s in splitter(text):
        i = text.find(s, pos)
        if i < 0:
            continue
        spans.append((i, i + len(s)))
        pos = i + len(s)
    return spans


def en_exception(text: str) -> list[Edit]:
    edits = []
    spans = _sentence_spans(text, split_sentences)
    if len(spans) >= 2:
        for s, e in spans:
            if EN_EXC_SENT.match(text[s:e]):
                edits.append(Edit(s, e, "", f"drop exception sentence ({text[s:e][:40]}...)"))
    for m in EN_EXC_LEAD.finditer(text):
        nxt = text[m.end(): m.end() + 1]
        edits.append(Edit(m.start(), m.end() + (1 if nxt else 0), nxt.upper(), f"drop leading exception ({m.group().strip()[:40]})"))
    for m in EN_EXC_MID.finditer(text):
        if any(s <= m.start() < e for s, e in [(x.start, x.end) for x in edits]):
            continue
        edits.append(Edit(m.start(), m.end(), "", f"drop exception ({m.group().strip(', ')[:40]})"))
    return [e for e in edits if len(e.apply(text).split()) >= 5]


HI_EXC_SENT = re.compile(r"^\s*(?:परंतु|परन्तु|लेकिन|किंतु|किन्तु|हालांकि|हालाँकि|सिवाय|अपवाद|यह\s.{0,40}लागू नहीं)")
HI_EXC_PHRASE = re.compile(r"(?:(?<=^)|(?<=[।,;]\s)|(?<=[।,;]))[^।,;]{3,160}?"
                           r"(?:के सिवाय|को छोड़कर|के अधीन रहते हुए|के होते हुए भी|के अलावा|से भिन्न|के सिवा)\s*,?\s*")
HI_EXC_UNLESS = re.compile(r",?\s*जब तक कि[^।,;]{3,160}")


def hi_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[।?!])\s+", text) if s.strip()]


def hi_exception(text: str) -> list[Edit]:
    edits = []
    spans = _sentence_spans(text, hi_sentences)
    if len(spans) >= 2:
        for s, e in spans:
            if HI_EXC_SENT.match(text[s:e]):
                edits.append(Edit(s, e, "", f"drop exception sentence ({text[s:e][:30]}...)"))
    for rx, name in ((HI_EXC_PHRASE, "drop exception phrase"), (HI_EXC_UNLESS, "drop unless-clause")):
        for m in rx.finditer(text):
            edits.append(Edit(m.start(), m.end(), "", f"{name} ({m.group().strip(', ')[:30]})"))
    return [e for e in edits if len(e.apply(text).split()) >= 5]


# =========================================================================== scope
EN_SCOPE = {"all": "some", "every": "some", "each": "some", "any": "certain", "anyone": "some people",
            "everyone": "some people", "anybody": "some people", "everybody": "some people",
            "always": "sometimes", "whole": "part of the", "entire": "part of the", "only": ""}
HI_SCOPE = {"सभी": "कुछ", "सब": "कुछ", "प्रत्येक": "कुछ", "हर": "कुछ", "किसी भी": "किसी विशेष", "कोई भी": "कोई विशेष",
            "सदैव": "कभी-कभी", "हमेशा": "कभी-कभी", "केवल": "", "संपूर्ण": "आंशिक", "पूरी": "आंशिक"}


def en_scope(text: str) -> list[Edit]:
    edits = []
    for w, r in EN_SCOPE.items():
        for m in re.finditer(rf"\b{w}\b", text, re.I):
            edits.append(Edit(m.start(), m.end(), _case(m.group(), r), f"scope {m.group()}->{r or '(deleted)'}"))
    return edits


def hi_scope(text: str) -> list[Edit]:
    edits = []
    for w, r in HI_SCOPE.items():
        for m in re.finditer(HB + re.escape(w) + HE, text):
            edits.append(Edit(m.start(), m.end(), r, f"scope {w}->{r or '(deleted)'}"))
    return edits


# =========================================================================== registry
RULES = {
    "en": {"modality": en_modality, "negation": en_negation, "number": lambda t: numbers_edits(t, "en"),
           "exception_drop": en_exception, "scope": en_scope},
    "hi": {"modality": hi_modality, "negation": hi_negation, "number": lambda t: numbers_edits(t, "hi"),
           "exception_drop": hi_exception, "scope": hi_scope},
}


def candidate_edits(text: str, lang: str) -> dict[str, list[Edit]]:
    out = {}
    for et, fn in RULES[lang].items():
        valid = []
        for e in fn(text):
            new = e.apply(text)
            if new and new != text and one_line(new) != one_line(text):
                valid.append(e)
        if valid:
            out[et] = valid
    return out


def perturb(text: str, lang: str, error_type: str, rng: random.Random) -> tuple[str, Edit] | None:
    cands = candidate_edits(text, lang).get(error_type)
    if not cands:
        return None
    e = rng.choice(cands)
    new = e.apply(text)
    if error_type == "exception_drop" and lang == "en":
        new = _cap_first(new)
    return new, e


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--types", nargs="+", default=list(ERROR_TYPES), choices=ERROR_TYPES)
    ap.add_argument("--data-dir", default=None)
    args = ap.parse_args(argv)
    paths = data_paths(args.data_dir)
    rng = random.Random(args.seed)
    sims = [s for s in read_jsonl(paths.simplifications) if s["variant"] == "normal" and s.get("simplification")]
    if not sims:
        sys.exit("no `normal` simplifications — run simplify.py first")
    rng.shuffle(sims)
    counts, out, skipped = Counter({t: 0 for t in args.types}), [], []
    for s in sims:
        cands = candidate_edits(s["simplification"], s["lang"])
        applicable = [t for t in args.types if t in cands]
        if not applicable:
            skipped.append(s["sim_id"])
            continue
        low = min(counts[t] for t in applicable)
        et = rng.choice([t for t in applicable if counts[t] == low])
        new, e = perturb(s["simplification"], s["lang"], et, rng)
        counts[et] += 1
        out.append({
            "sim_id": f"{s['clause_id']}|{s['lang']}|perturbed", "base_sim_id": s["sim_id"],
            "clause_id": s["clause_id"], "act_id": s["act_id"], "lang": s["lang"], "variant": "perturbed",
            "original": s["original"], "simplification": new, "error_type": et,
            "change": f"{e.rule}", "span": [e.start, e.end], "model": s.get("model"), "prompt_id": s.get("prompt_id"),
        })
    out.sort(key=lambda r: r["sim_id"])
    write_jsonl(paths.perturbations, out)
    print(f"wrote {paths.perturbations}: {len(out)} perturbed, error types {dict(counts)}")
    by_lang = Counter((r["lang"], r["error_type"]) for r in out)
    print("by language:", dict(sorted(by_lang.items())))
    if skipped:
        print(f"{len(skipped)} simplifications had no applicable rule (no perturbed pair): {skipped[:10]}")


if __name__ == "__main__":
    main()
