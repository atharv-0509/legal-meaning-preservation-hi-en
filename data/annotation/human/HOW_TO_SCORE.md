# How to score your sheet (≈ 20–30 minutes)

Each of you has **your own file** — Karan: `karan_singh.xlsx`, Atharv: `atharv_arora.xlsx`,
Jatin: `jatin_khanchi.xlsx`. Same 30 pairs, different order. **Score alone — don't discuss pairs with each
other** until everyone is finished (otherwise the agreement number is meaningless).

Open your file → **`Annotate`** tab. Each row has an **original** legal text and a **simplification**.
Fill only the **yellow** columns. The `lmp_score` column calculates itself.

## For each row
1. **bracket** — does the simplification keep the *legal meaning*?
   - **Accurate (7-10)** — same legal effect; at most small details lost
   - **Imprecise (2-6)** — a legally important element changed or lost
   - **Off-track (1)** — legal meaning lost or reversed overall
2. **Error counts** (0, 1, 2 …) — count each problem once:
   - **omissions** — something legally relevant left out (a condition, exception, time limit, actor…)
   - **hallucinations** — something added that the law does not say
   - **inconsistencies** — something contradicted or changed (shall→may, 30→15 days, "not" added/removed, every→some)
   - **confusions** — wording that makes the legal meaning unclear or misleading
3. **main_change** — pick the single most important change from the dropdown (`none` if nothing).
4. **simplicity** (1–5) — how much easier it is to read than the original.
5. **comment** — optional, one line (e.g. "shall → may").

Score = bracket maximum (10 or 6) minus 1 per error, never below 1 — the sheet does this for you.

## Watch for these legal traps
- **shall / must** (duty) vs **may** (permission) — swapping them changes the law
- **numbers and time limits** — 30 days vs 15 days, one crore vs two crore
- **"not" added or removed**
- **exceptions and conditions** — "unless…", "provided that…", "except…", "only if…"
- **scope words** — every / any / all vs some / certain

Hindi rows: judge the Hindi simplification against the Hindi original the same way.

## When done
Save the file (keep the same name) and send it back to Karan. Then run
`python src/human_validation.py` to compare the human scores with the AI labels.
