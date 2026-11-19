# Paper and slides build

One command produces every document deliverable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File paper/build.ps1
```

Outputs land in `paper/out/`:

| File | What it is |
|---|---|
| `LMP_paper_IEEE.docx` | the IEEE-format paper (the Word deliverable) |
| `LMP_paper_IEEE.pdf` | the same document exported by Word (the PDF deliverable) |
| `LMP_slides.pptx` | the final deck |
| `paper_ieee.md` | a generated reading/diffing copy of the paper text |

## Where the content lives

`paper/content.py` is the single source of truth for the paper: title, abstract, every section, and
the reference list. `paper/build_slides.py` holds the deck's own (terser) wording but imports the
labelling-disclosure statement and all tables from the same place, so the deck cannot contradict
the paper. **Edit `content.py`, never the files in `out/`** — they are overwritten on every build.

## Where the numbers come from

`paper/tables.py` resolves every table from files our own code produced:

* results tables from `reports/tables/<key>.tsv` (`e1`, `e2`, `e3`, `e4`, `diag`, `dataset`);
* the source/provenance table from `sources.json` plus the real unit counts in `data/interim/`.

A table whose file is absent renders with its expected header and a single `[TBD]` row, and the
build prints exactly which files were missing. No number in these documents is typed by hand.
`EXPECTED_HEADERS` in `tables.py` is the contract the results pipeline writes against.

`data/` and `reports/` are git-ignored, so in a git worktree they are not present. The build looks
for them in this checkout, then in a sibling `legal-meaning-preservation-hi-en` checkout;
`-DataRoot` or `LMP_DATA_ROOT` overrides.

Note for whoever runs this: `dataset.tsv` must be written by the data track from `pairs.jsonl`.
`tables.py` deliberately does not read `pairs.jsonl` itself, because the agent that builds the
paper also serves as a blinded annotator and must never see the pair-level answer key.

## Requirements

`pip install -r paper/requirements-paper.txt` (python-docx, python-pptx). The PDF step uses the
installed Microsoft Word through COM automation, inside a job with a 300 s timeout, so a missing or
stuck Word degrades to "PDF not produced" instead of hanging the build; `-SkipPdf` skips it.
