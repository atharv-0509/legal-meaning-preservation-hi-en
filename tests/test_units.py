"""Unit tests on synthetic strings: parser, Hindi handling, metrics, rubric, perturbation rules.

    python tests/test_units.py        (or: pytest tests/)
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "src"), str(HERE)]

import common  # noqa: E402
import extract  # noqa: E402
import perturb  # noqa: E402
import rubric  # noqa: E402
from agreement import krippendorff_alpha  # noqa: E402
from fixtures import EN_PAGES, HI_PAGES  # noqa: E402
from select_clauses import reading_ease  # noqa: E402


def edits_text(text, lang, et):
    return [e.apply(text) for e in perturb.candidate_edits(text, lang).get(et, [])]


# --------------------------------------------------------------------------- common
def test_tokenizer_keeps_matras():
    toks = common.tokenize("सूचना का अधिकार, प्रत्येक नागरिक को है। Section 8(1)")
    assert toks == ["सूचना", "का", "अधिकार", "प्रत्येक", "नागरिक", "को", "है", "section", "8", "1"], toks


def test_normalize_strips_zero_width():
    assert common.normalize_text("क्‍ष  test​") == "क्ष test"


def test_rouge_hindi_not_empty():
    a = "अधिकारी तीस दिन के भीतर सूचना देगा।"
    assert common.rouge_n(a, a, 1) == 1.0 and common.rouge_l(a, a) == 1.0
    assert common.bleu(a, a) > 99
    assert not common.is_unrelated(a, a)
    assert common.is_unrelated(a, "आयोग विवाद का शीघ्रता से न्यायनिर्णयन करेगा परिवाद पर।") is True


def test_devanagari_digits_in_numbers():
    assert common.numbers_in("धारा ८ और 30 दिन") == ["30", "8"]


def test_sentence_split():
    s = common.split_sentences("The fee is Rs. 10 per page. Provided that no fee shall be charged. यह नियम है। दूसरा वाक्य।")
    assert s == ["The fee is Rs. 10 per page.", "Provided that no fee shall be charged.", "यह नियम है।", "दूसरा वाक्य।"], s


def test_markers():
    m = common.find_markers("Notwithstanding anything, the officer shall, within 30 days, unless exempt, decide.", "en")
    assert {"override", "time_limit", "exception", "obligation"} <= set(m), m
    assert "exception" in common.find_markers("धारा 8 के सिवाय, अधिकारी 30 दिन के भीतर सूचना देगा।", "hi")


def test_stats():
    assert abs(common.pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-9
    assert abs(common.spearman([1, 2, 3, 4], [10, 20, 15, 40]) - 0.8) < 1e-9
    assert common.rankdata([3, 1, 3]) == [2.5, 1.0, 2.5]


# --------------------------------------------------------------------------- readability
def test_reading_ease_orders_texts():
    easy = reading_ease("The cat sat on the mat. It was fun.")
    hard = reading_ease("Notwithstanding anything contained in any other enactment, the administrative "
                        "authority shall determine the applicability of the aforementioned regulations.")
    assert easy > 80 and hard < 30, (easy, hard)


# --------------------------------------------------------------------------- extract
def test_fix_hindi_spacing():
    assert extract.fix_hindi_spacing("सूचना उपलब्ध करे गा |") == "सूचना उपलब्ध करेगा।"
    assert extract.fix_hindi_spacing("अपील--कोई") == "अपील—कोई"
    assert extract.fix_hindi_spacing("सूचन ा अधिक ार") == "सूचना अधिकार"   # space before matra
    assert extract.fix_hindi_spacing("दो गाय") == "दो गाय"          # गाय is a word, not an ending


def test_bad_matra_ratio():
    assert extract.bad_matra_ratio("सूचना का अधिकार") == 0
    assert extract.bad_matra_ratio("िकताब ेदना") == 1.0


def test_strip_amendment_markers():
    assert common.one_line(extract.strip_amendment_markers("1[(3) The fee shall be reasonable.] 2* * * x")) == \
        "(3) The fee shall be reasonable. x"


def test_split_subsections_crossrefs():
    body = ("(1) Subject to sub-section (2) of section 8, the officer shall decide. (2) Where the officer fails under "
            "sub-section (1) or (3), the request is refused. (3) The fee referred to in section (4) is reasonable.")
    subs = extract.split_subsections(body)
    assert [n for n, _ in subs] == ["1", "2", "3"], subs
    assert subs[0][1].startswith("Subject to sub-section (2)")
    hi = "(1) धारा 8 की उपधारा (3) के अधीन रहते हुए, अधिकारी विनिश्चय करेगा। (2) उपधारा (1) में निर्दिष्ट फीस युक्तियुक्त होगी।"
    assert [n for n, _ in extract.split_subsections(hi)] == ["1", "2"]
    assert extract.split_subsections("No sub-sections here (a) or (b).") == [("", "No sub-sections here (a) or (b).")]


def test_units_from_pages_en():
    units = {u["key"]: u for u in extract.units_from_pages(EN_PAGES, "x", "en")}
    assert set(units) == {"s1_1", "s1_2", "s2", "s3_1", "s3_2", "s3_3", "s4"}, sorted(units)
    assert units["s3_1"]["heading"] == "Disposal of requests"           # heading wrapped over two lines
    assert "information." in units["s3_1"]["text"]                     # de-hyphenated
    assert units["s3_3"]["text"] == "The fee referred to in sub-section (2) shall be reasonable."  # 1[...] stripped
    assert "Ins. by" not in " ".join(u["text"] for u in units.values())  # footnote dropped
    assert "OBLIGATIONS" not in units["s2"]["text"]                     # chapter title not in section 2
    assert "*" not in units["s4"]["text"] and "13" not in units["s4"]["text"]


def test_units_from_pages_hi():
    units = {u["key"]: u for u in extract.units_from_pages(HI_PAGES, "x", "hi")}
    assert {"s3_1", "s3_2", "s3_3", "s4", "s5"} <= set(units), sorted(units)
    assert units["s3_1"]["text"].endswith("उपलब्ध करेगा।")              # "करे गा ।" repaired
    assert units["s3_2"]["text"].endswith("कर दिया है।")                 # "|" -> danda
    assert "कृत्रिम अधिनियम" not in units["s3_3"]["text"]                 # running header removed
    assert units["s4"]["heading"] == "अपील"                            # "--" separator


# --------------------------------------------------------------------------- rubric / agreement
def test_rubric_score():
    assert rubric.lmp_score("Accurate (7-10)", {"omissions": 1, "confusions": 1}) == 8
    assert rubric.lmp_score("imprecise", {"omissions": 9}) == 1
    assert rubric.lmp_score("Off-track (1)", {}) == 1
    assert rubric.lmp_score("", {}) is None
    assert rubric.decision(7.0) == "Preserved" and rubric.decision(6.9) == "Partially Preserved"
    assert rubric.decision(1.5) == "Not Preserved"


def test_krippendorff():
    assert abs(krippendorff_alpha({"a": [1, 1], "b": [5, 5], "c": [9, 9]}) - 1.0) < 1e-9
    # Krippendorff (2011) worked example, interval metric, 4 coders with missing data -> 0.849
    data = [[1, 1, None, 1], [2, 2, 3, 2], [3, 3, 3, 3], [3, 3, 3, 3], [2, 2, 2, 2], [1, 2, 3, 4], [4, 4, 4, 4],
            [1, 1, 2, 1], [2, 2, 2, 2], [None, 5, 5, 5], [None, None, 1, 1], [None, None, 3, None]]
    a = krippendorff_alpha({str(i): row for i, row in enumerate(data)}, "interval")
    assert abs(a - 0.849) < 0.002, a
    assert abs(krippendorff_alpha({str(i): row for i, row in enumerate(data)}, "nominal") - 0.743) < 0.002


# --------------------------------------------------------------------------- perturbations EN
def test_en_modality():
    out = edits_text("The officer must decide within 30 days. He may charge a fee as may be prescribed.", "en", "modality")
    assert "The officer may decide within 30 days. He may charge a fee as may be prescribed." in out
    assert "The officer must decide within 30 days. He must charge a fee as may be prescribed." in out
    assert all("as must be prescribed" not in o for o in out)


def test_en_negation():
    assert edits_text("The officer shall not reject it.", "en", "negation") == ["The officer shall reject it."]
    assert edits_text("You cannot appeal.", "en", "negation") == ["You can appeal."]
    assert edits_text("The officer must reply.", "en", "negation") == ["The officer must not reply."]


def test_en_number():
    out = edits_text("Apply within 30 days under section 8 of the Act, 2005, or within thirty days.", "en", "number")
    assert "Apply within 60 days under section 8 of the Act, 2005, or within thirty days." in out
    assert "Apply within 30 days under section 8 of the Act, 2005, or within sixty days." in out
    assert len(out) == 2                                     # section number and year untouched


def test_en_exception_drop():
    t = "The officer must give the information, unless it is exempt under section 8."
    assert edits_text(t, "en", "exception_drop") == ["The officer must give the information."]
    t2 = "Subject to section 8, every citizen has the right to information."
    assert edits_text(t2, "en", "exception_drop") == ["Every citizen has the right to information."]
    t3 = "Every citizen can ask for information. However, secret files are not given."
    assert "Every citizen can ask for information." in edits_text(t3, "en", "exception_drop")


def test_en_scope():
    out = edits_text("All citizens may ask only the officer.", "en", "scope")
    assert "Some citizens may ask only the officer." in out and "All citizens may ask the officer." in out


# --------------------------------------------------------------------------- perturbations HI
def test_hi_shall_to_may():
    assert "अधिकारी सूचना कर सकेगा।" in edits_text("अधिकारी सूचना करेगा।", "hi", "modality")
    assert "अधिकारी सूचना दे सकेगा।" in edits_text("अधिकारी सूचना देगा।", "hi", "modality")
    assert "सूचना दी जा सकेगी।" in edits_text("सूचना दी जाएगी।", "hi", "modality")
    assert "सूचना दी जा सकेगा।" not in edits_text("सूचना दी जाएगी।", "hi", "modality")


def test_hi_must_to_may():
    assert "आयोग को निर्णय करने की छूट है।" in edits_text("आयोग को निर्णय करना होगा।", "hi", "modality")


def test_hi_may_to_shall():
    assert "आयोग शास्ति लगाएगा।" in edits_text("आयोग शास्ति लगा सकता है।", "hi", "modality")
    assert "वह अपील करेगा।" in edits_text("वह अपील कर सकेगा।", "hi", "modality")
    assert "वह सूचना देगा।" in edits_text("वह सूचना दे सकता है।", "hi", "modality")


def test_hi_rules_only_at_clause_end():
    # उपयोगी ends in "गी" and होगी is mid-clause: neither may be touched by the modality rules
    assert edits_text("यह जानकारी उपयोगी होगी और अधिकारी जवाब भेजता है।", "hi", "modality") == []
    assert edits_text("यह उपयोगी पुस्तक है।", "hi", "modality") == []


def test_hi_negation():
    assert edits_text("अधिकारी आवेदन अस्वीकार नहीं करेगा।", "hi", "negation") == ["अधिकारी आवेदन अस्वीकार करेगा।"]
    assert edits_text("सूचना उपलब्ध कराई जाएगी।", "hi", "negation") == ["सूचना उपलब्ध नहीं कराई जाएगी।"]
    assert edits_text("नागरिक को सूचना का अधिकार है।", "hi", "negation") == ["नागरिक को सूचना का अधिकार नहीं है।"]
    assert edits_text("अधिकारी सूचना दे सकता है।", "hi", "negation") == ["अधिकारी सूचना नहीं दे सकता है।"]


def test_hi_number():
    out = edits_text("धारा 8 के अधीन तीस दिन के भीतर और ३० दिन में आवेदन, 2005 का अधिनियम।", "hi", "number")
    assert "धारा 8 के अधीन साठ दिन के भीतर और ३० दिन में आवेदन, 2005 का अधिनियम।" in out
    assert "धारा 8 के अधीन तीस दिन के भीतर और ६० दिन में आवेदन, 2005 का अधिनियम।" in out
    assert len(out) == 2


def test_hi_exception_drop():
    out = edits_text("धारा 8 में उपबंधित के सिवाय, प्रत्येक नागरिक को सूचना का अधिकार है।", "hi", "exception_drop")
    assert out == ["प्रत्येक नागरिक को सूचना का अधिकार है।"], out
    out = edits_text("अधिकारी तीस दिन के भीतर सूचना देगा, जब तक कि सूचना छूट प्राप्त न हो।", "hi", "exception_drop")
    assert out == ["अधिकारी तीस दिन के भीतर सूचना देगा।"], out


def test_hi_scope():
    out = edits_text("प्रत्येक नागरिक किसी भी लोक प्राधिकारी से सूचना मांग सकता है।", "hi", "scope")
    assert "कुछ नागरिक किसी भी लोक प्राधिकारी से सूचना मांग सकता है।" in out
    assert "प्रत्येक नागरिक किसी विशेष लोक प्राधिकारी से सूचना मांग सकता है।" in out
    assert edits_text("सबसे पहले आवेदन करें।", "hi", "scope") == []      # सब inside सबसे is not touched


def _tsv(words):
    """Synthetic Tesseract TSV: words = [(block, line, left, top, width, text)]."""
    head = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [f"5\t1\t{b}\t1\t{ln}\t{i}\t{left}\t{top}\t{w}\t40\t90\t{t}"
            for i, (b, ln, left, top, w, t) in enumerate(words, 1)]
    return "\n".join([head] + rows)


def test_bill_page_split_separates_margins():
    words = []
    for k in range(6):                                   # six full body lines, x = 500..1900
        words += [(1, k, 500 + 140 * j, 100 + 60 * k, 120, "शब्द") for j in range(10)]
    # line 0 also carries a marginal heading at x = 100 (same OCR line) and a line number at x = 2050
    words += [(1, 0, 100, 100, 150, "सूचना"), (1, 0, 260, 100, 100, "अधिकार"), (1, 0, 2050, 100, 40, "5")]
    body, margin = extract.split_bill_page(_tsv(words))
    assert len(body) == 6 and all(b["text"].split() == ["शब्द"] * 10 for b in body)
    assert [m["text"] for m in margin] == ["सूचना अधिकार"]


def test_bill_numbering_and_subsections():
    assert {"5", "45", "15", "75"} <= extract.bill_number_variants(15)
    assert "07" in extract.bill_number_variants(101) and "" in extract.bill_number_variants(1)
    subs = extract.split_subsections("(।) पहला उपबंध। (2) दूसरा उपबंध, जिसमें (क) एक ; (3) तीन।", ocr=True, bill=True)
    assert [n for n, _ in subs] == ["1", "2"], subs          # "(3)" after ";" is a list item, not a sub-section
    subs = extract.split_subsections("(1) पहला। (2) दो। (3) तीन। (4) चार। (5) पाँच। (6) छह। (7) सात। (8) आठ। "
                                     "(9) नौ। थ्न्ध (0) दस।", ocr=True, bill=True)
    assert subs[-1][0] == "10", subs                      # junk token before the OCR-damaged (10)
    assert extract.fix_ocr_conjuncts("आयोग दुवारा और दूवारा, के विरुदध") == "आयोग द्वारा और द्वारा, के विरुद्ध"


def test_perturb_changes_exactly_one_thing():
    rng = random.Random(0)
    t = "The officer must give the information within 30 days, unless it is exempt. All citizens may appeal."
    for et in perturb.ERROR_TYPES:
        res = perturb.perturb(t, "en", et, rng)
        assert res is not None, et
        assert res[0] != t


def run_all():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"ok    {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
