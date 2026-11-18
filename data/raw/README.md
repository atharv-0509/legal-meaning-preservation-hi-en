# Source PDFs (download by hand)

India Code disallows scripted downloads (robots.txt), so a team member must download these in a browser
and save them **with exactly these names**:

| File | Act | Page |
|---|---|---|
| `rti_en.pdf` | Right to Information Act, 2005 (English) | https://www.indiacode.nic.in/handle/123456789/2065 |
| `rti_hi.pdf` | सूचना का अधिकार अधिनियम, 2005 (Hindi version on the same page) | same |
| `cpa_en.pdf` | Consumer Protection Act, 2019 (English) | https://www.indiacode.nic.in/handle/123456789/15256 |
| `cpa_hi.pdf` | उपभोक्ता संरक्षण अधिनियम, 2019 (Hindi version on the same page) | same |

On each page, use the act's main PDF (not a notification or rules file) and the Hindi version listed
on the same page.

After downloading, write in `sources.json` → `version_note` the date or amendment the PDF says it is
current to (e.g. "as on 2023-..."). The RTI Act was amended in 2019 and 2023, so the English and Hindi PDFs may be
different versions; mismatched clauses are dropped at review (step 2b), not "fixed".

PDFs are ignored by git (`.gitignore`); do not commit them.
