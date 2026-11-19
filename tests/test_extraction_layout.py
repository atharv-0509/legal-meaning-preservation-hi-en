"""Synthetic regressions for physical lines, marginal headings and source flags."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import extract
import select_clauses
from common import data_paths, units_path, write_jsonl


def test_contents_schedule_does_not_hide_act():
    pages = ["ARRANGEMENT OF SECTIONS\n" + "Contents entry.\n" * 150 + "THE FIRST SCHEDULE\n",
             "1. Application.—The synthetic rule applies.\n"
             "2. Repeal.—The synthetic prior rule is repealed.\n"
             "THE FIRST SCHEDULE\n3. Schedule entry.—Not a section."]
    units = extract.units_from_pages(pages, "synthetic", "en")
    assert [unit["key"] for unit in units] == ["s1", "s2"]
    assert units[-1]["text"] == "The synthetic prior rule is repealed."
    assert extract._FOOTNOTE_EN.match("1. Cl. (a) was omitted.")
    assert extract._FOOTNOTE_EN.match("2. Rep. by a later synthetic Act.")


def test_text_backend_preserves_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(extract.shutil, "which", lambda name: name)

    def run(command, **kwargs):
        assert "-layout" in command
        assert kwargs == {"capture_output": True, "check": True}
        return SimpleNamespace(stdout=b"page one\fpage two\f")

    monkeypatch.setattr(extract.subprocess, "run", run)
    assert extract.pdf_text_pages(tmp_path / "synthetic.pdf") == ["page one", "page two"]


def test_gazette_margins_and_cross_page_body(tmp_path):
    import pymupdf

    pdf = tmp_path / "synthetic.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=595, height=842)
        page.insert_text((120, 75), "RUNNING HEADER", fontsize=10)
        page.insert_text((120, 110), "3. (1) The synthetic officer shall keep records.", fontsize=10)
        page.insert_text((55, 110), "Records.", fontsize=8)
        page.insert_text((55, 145), "5 of 2000.", fontsize=8)
        page.insert_text((120, 160), "(2) Those records shall remain available.", fontsize=10)
        page = document.new_page(width=595, height=842)
        page.insert_text((120, 110), "The synthetic exception applies.", fontsize=10)
        page.insert_text((120, 180), "4. An applicant may seek review.", fontsize=10)
        page.insert_text((490, 180), "Review.", fontsize=8)
        document.save(pdf)
    units = extract.units_from_pages(extract.pdf_gazette_pages(pdf), "synthetic", "en")
    assert [unit["key"] for unit in units] == ["s3_1", "s3_2", "s4"]
    assert units[0]["heading"] == "Records"
    assert units[-1]["heading"] == "Review"
    assert units[1]["text"].endswith("The synthetic exception applies.")
    assert all("HEADER" not in unit["text"] and "5 of 2000" not in unit["text"] for unit in units)


def test_source_flags_reach_candidates(tmp_path):
    paths = data_paths(tmp_path)
    unit = {"key": "s8_1", "section": "8", "subsection": "1", "heading": "Synthetic procedure",
            "text": "The synthetic authority shall determine the request within thirty days of its receipt."}
    write_jsonl(units_path(paths, "synthetic", "en"), [unit])
    act = {"act_id": "synthetic", "domain": "test", "pdf": {"en": "test.pdf", "hi": "missing.pdf"},
           "review_flags": ["hi_ocr_required"], "section_review_flags": {"8": ["en_hi_version_mismatch"]}}
    args = SimpleNamespace(allow_missing_hi=True, min_words=1, max_words=100, max_sents=5, max_reading_ease=100)
    candidates, _ = select_clauses.candidates_for_act(act, paths, args)
    assert candidates[0]["auto_flags"] == ["no_hi", "hi_ocr_required", "en_hi_version_mismatch"]


def test_gazette_rejects_missing_heading(tmp_path):
    import pymupdf
    import pytest

    pdf = tmp_path / "synthetic.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=595, height=842)
        page.insert_text((120, 110), "3. A synthetic rule without its marginal heading.", fontsize=10)
        document.save(pdf)
    with pytest.raises(ValueError, match="missing marginal heading"):
        extract.pdf_gazette_pages(pdf)
