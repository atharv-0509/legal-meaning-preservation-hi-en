# Source provenance and extraction readiness

Inspection date: 19 November 2026. These are source and parser observations, not model results.
Canonical download URLs and source warnings are recorded in `sources.json` and copied into selected clauses.

| Source | Edition evidence | Extraction |
|---|---|---|
| RTI English, DoPT, 25 PDF pages | Cover says "As on the 18th November, 2025"; amendment list includes 2019 and 2023 Acts | 31 sections, 109 units |
| RTI Hindi, DoPT, 21 PDF pages | Footnotes include the 2019 amendments; consolidation date remains [TBD] | 31 sections, 102 provisional units; text is unsuitable for annotation |
| CPA English, Gazette of India, 40 PDF pages | Act No. 35 of 2019, Gazette dated 9 August 2019; original enactment | 107 sections, 229 units |
| CPA Hindi | Missing | No extraction or bilingual alignment possible |

The RTI copies are not equivalent editions: Hindi PDF page 8 retains the longer personal-information
exception, while English section 8(1)(j) has the shorter amended wording. Hindi footnotes show that
2019 amendments are present, so it must not simply be described as an unamended 2005 copy.
All RTI selections carry `amendment_version_review`; section 8 also carries `en_hi_version_mismatch`.
These are review warnings, not human decisions to keep or drop clauses.

The RTI Hindi raw text has bad-matra ratio 0.129; extracted units have ratio approximately 0.065.
Visual inspection confirms a readable printed page but faulty Unicode text extraction.
All RTI selections carry `hi_ocr_required`. Installed Tesseract has only `eng` and `osd`,
so Hindi OCR was not run. A human must supply the approved Hindi OCR language data/tooling or
a usable official Hindi source. No extracted Hindi should enter simplification or annotation yet.

The CPA Gazette puts headings in side margins. `extract.py --backend gazette` uses PyMuPDF to
separate those headings and marginal statute citations from the body. Its body coordinates are
specific to this Gazette edition. A different layout requires calibration and visual review.
The ordinary `text` backend preserves physical lines with Poppler's `-layout` option.

## Reproduce the provisional review pack on this Windows machine

```powershell
$env:PATH = 'C:/Program Files/Git/mingw64/bin;' + $env:PATH
$env:PYTHONUTF8 = '1'
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe src/extract.py --act rti --lang en --backend text
.venv/Scripts/python.exe src/extract.py --act rti --lang hi --backend text
.venv/Scripts/python.exe src/extract.py --act cpa --lang en --backend gazette
.venv/Scripts/python.exe src/select_clauses.py --allow-missing-hi
```

Only regenerate outputs when they contain no human edits. The provisional pack contains 78 rows
(39 per act), all flagged: 39 RTI rows require OCR and version review, and 39 CPA rows lack Hindi.
Six selected RTI rows also lack a matching parsed Hindi unit. The default `keep` values were not
reviewed or changed by an agent. No `--finalize`, simplification, or annotation scoring was run.
The 78 rows are candidates, not completed pairs or a claim that the required dataset size is met.
