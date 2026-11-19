"""Legal Meaning Preservation demo (English / Hindi): a Gradio app around a trained checkpoint.

    python modeling/app.py --model-dir modeling/checkpoints/demo_model          # http://127.0.0.1:7860
    python modeling/app.py --model-dir modeling/checkpoints/demo_model --share  # temporary public link

What it shows for one original/simplification pair:
  * the model's LMP score (1-10) and decision (Preserved / Partially Preserved / Not Preserved);
  * a rule-based "legal cue check" (negation, obligation/permission, exceptions, conditions, time limits,
    numbers) comparing the two texts. This is a heuristic explanation aid, NOT the model's reasoning;
  * optional: "Generate simplification" with an LLM, only if LLM_API_KEY and LLM_MODEL (exact model id;
    LLM_BASE_URL for non-OpenAI endpoints) are set.
Examples come from the test split the demo model was NOT trained on (data/splits/random_s42/test.jsonl),
with their reference labels (disclosed LLM-annotator labels, not human legal judgements).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "modeling")]
from common import devanagari_ratio, find_markers, numbers_in  # noqa: E402
from rubric import decision  # noqa: E402

EXAMPLES_FILE = ROOT / "data" / "splits" / "random_s42" / "test.jsonl"
FEATURED = ["cpa-s10_1|en|normal", "cpa-s10_1|en|perturbed", "cpa-s10_1|en|aggressive",
            "rti-s11_4|hi|normal", "rti-s11_4|hi|perturbed", "rti-s11_4|hi|aggressive"]
VARIANT_NAME = {"normal": "standard simplification", "perturbed": "one injected legal error",
                "aggressive": "explained to a 12-year-old"}

CUES = [  # (marker category from common.find_markers, label shown to the user)
    ("prohibition", "Prohibition (shall not / नहीं …)"),
    ("obligation", "Obligation (shall / must / करेगा)"),
    ("permission", "Permission (may / सकेगा)"),
    ("exception", "Exception / proviso"),
    ("override", "Override (notwithstanding / subject to)"),
    ("condition", "Condition (if / where / यदि)"),
    ("time_limit", "Time limit"),
]
# English modality in plain-language simplifications: "will"/"has to" usually carry the obligation of "shall",
# and "may" inside drafting idioms ("as it may specify", "may be prescribed") is not a permission.
EN_OBLIG = re.compile(r"\b(shall|must|will|has to|have to|is required to|are required to|needs? to)\b(?!\s+not)", re.I)
EN_PERM = re.compile(r"\b(may|can|is allowed to|are allowed to|is entitled to|are entitled to)\b(?!\s+not)", re.I)
EN_PERM_IDIOM = re.compile(r"\b(as|which|that)\s+(\w+\s+){0,3}may\b|\bmay\s+be\s+(prescribed|specified|notified|"
                           r"determined|necessary|required)|\bcase\s+may\s+be\b", re.I)


def en_modality(text: str) -> set[str]:
    out = set()
    if EN_OBLIG.search(text):
        out.add("obligation")
    if EN_PERM.search(EN_PERM_IDIOM.sub(" ", text)):
        out.add("permission")
    return out


NEG = {"en": re.compile(r"\b(not|no|never|cannot|can't|won't|neither|nor)\b", re.I),
       "hi": re.compile(r"(?<![ऀ-ॿ])(नहीं|न|मत)(?![ऀ-ॿ])")}

CSS = """
.lmp-banner {background:#fff7e6;border:1px solid #f0c36d;color:#5c4400;border-radius:10px;padding:10px 14px;font-size:14px}
.dark .lmp-banner {background:#3a2f12;border-color:#8a6d1f;color:#f5deb0}
.lmp-card {border-radius:14px;padding:18px 20px;color:#fff}
.lmp-card .score {font-size:46px;font-weight:700;line-height:1}
.lmp-card .dec {font-size:20px;font-weight:600;margin-top:6px}
.lmp-card .sub {font-size:13px;opacity:.9;margin-top:6px}
.lmp-bar {height:10px;border-radius:5px;background:rgba(255,255,255,.35);margin-top:12px;position:relative}
.lmp-bar > div {height:10px;border-radius:5px;background:#fff}
.lmp-cues table {width:100%;border-collapse:collapse;font-size:14px}
.lmp-cues th,.lmp-cues td {padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.25);text-align:left;vertical-align:top}
.lmp-flag {color:#c0392b;font-weight:600}
.lmp-ok {color:#2e8b57}
.lmp-empty {opacity:.7;font-size:14px}
"""


def lang_of(text: str) -> str:
    return "hi" if devanagari_ratio(text) > 0.3 else "en"


def load_examples() -> dict[str, dict]:
    rows = {}
    if EXAMPLES_FILE.exists():
        for line in EXAMPLES_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["pair_id"]] = r
    out = {}
    for pid in FEATURED + sorted(rows):
        r = rows.get(pid)
        if r is None or len(out) >= 40:
            continue
        clause, lang, variant = pid.split("|")
        name = f"{clause} · {'English' if lang == 'en' else 'Hindi'} · {VARIANT_NAME.get(variant, variant)}"
        out[name] = r
    return out


def score_card(score: float, ref: float | None) -> str:
    dec = decision(score)
    colour = {"Preserved": "#2e8b57", "Partially Preserved": "#d68910", "Not Preserved": "#c0392b"}[dec]
    pct = (score - 1) / 9 * 100
    ref_txt = (f"Reference label for this test pair: {ref:.1f} ({html.escape(decision(ref))}) — "
               "mean of two disclosed LLM annotators") if ref is not None else "No reference label (your own text)"
    return (f'<div class="lmp-card" style="background:{colour}"><div class="score">{score:.1f}<span '
            f'style="font-size:20px;opacity:.8"> / 10</span></div><div class="dec">{dec}</div>'
            f'<div class="lmp-bar"><div style="width:{pct:.0f}%"></div></div>'
            f'<div class="sub">{ref_txt}</div></div>')


def cue_table(original: str, simplification: str) -> str:
    lo, ls = lang_of(original), lang_of(simplification)
    mo, ms = set(find_markers(original, lo)), set(find_markers(simplification, ls))
    for markers, text, lang in ((mo, original, lo), (ms, simplification, ls)):
        if lang == "en":                     # replace the generic English modality markers (see en_modality)
            markers -= {"obligation", "permission"}
            markers |= en_modality(text)
    rows, flags = [], 0
    no, ns = len(NEG[lo].findall(original)), len(NEG[ls].findall(simplification))
    if no != ns:
        flags += 1
        rows.append(("Negation words", f"{no}", f"{ns}", "Negation count differs: meaning may be reversed"))
    for cat, label in CUES:
        a, b = cat in mo, cat in ms
        if a or b:
            note = ""
            if a and not b:
                note, flags = "Present in original, missing in simplification", flags + 1
            elif b and not a:
                note, flags = "Added in simplification", flags + 1
            rows.append((label, "yes" if a else "—", "yes" if b else "—", note))
    numo, nums = numbers_in(original), numbers_in(simplification)
    if numo or nums:
        lost = sorted(set(numo) - set(nums))
        new = sorted(set(nums) - set(numo))
        note = "; ".join(x for x in (f"missing: {', '.join(lost)}" if lost else "",
                                     f"new: {', '.join(new)}" if new else "") if x)
        flags += bool(note)
        rows.append(("Numbers", ", ".join(numo) or "—", ", ".join(nums) or "—", note))
    if not rows:
        return '<div class="lmp-empty">No legal cues detected by the rules.</div>'
    body = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td>"
        f"<td class='{'lmp-flag' if d else 'lmp-ok'}'>{html.escape(d) if d else 'consistent'}</td></tr>"
        for a, b, c, d in rows)
    head = (f"<p><b>{flags}</b> potential issue{'s' if flags != 1 else ''} flagged by simple rules. "
            "These rules are an explanation aid only — they are not the model and miss paraphrases.</p>")
    return (f'<div class="lmp-cues">{head}<table><tr><th>Legal cue</th><th>Original</th><th>Simplification</th>'
            f"<th>Check</th></tr>{body}</table></div>")


def build(model_dir: str):
    import gradio as gr
    from predict import LMPScorer

    scorer = LMPScorer(model_dir)
    examples = load_examples()
    llm_ready = bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL"))

    def run(original, simplification, ref):
        original, simplification = (original or "").strip(), (simplification or "").strip()
        if not original or not simplification:
            raise gr.Error("Paste both the original legal text and a simplification to score.")
        if original == simplification:
            gr.Info("The two texts are identical; a good metric should score this near 10.")
        s = scorer.score([original], [simplification])[0]["lmp_score"]
        return score_card(s, ref), cue_table(original, simplification)

    def pick(name):
        r = examples.get(name)
        if not r:
            return gr.update(), gr.update(), None, "", ""
        return r["original"], r["simplification"], float(r["label"]), "", ""

    def generate(original, mode):
        original = (original or "").strip()
        if not original:
            raise gr.Error("Paste the original legal text first.")
        from simplify import LLMClient, PROMPTS, clean_output
        lang = lang_of(original)
        _pid, tmpl = PROMPTS[(lang, "aggressive" if mode.startswith("Aggressive") else "normal")]
        client = LLMClient(os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                           os.environ["LLM_API_KEY"], os.environ["LLM_MODEL"])
        out = client.chat(tmpl.format(text=original), temperature=1.0, top_p=0.9,
                          max_tokens=200 if lang == "en" else 500)
        return clean_output(out["text"]), None

    with gr.Blocks(title="Legal Meaning Preservation") as demo:
        gr.Markdown("# Legal Meaning Preservation — English / Hindi\n"
                    "Does a simplification of an Indian statutory provision keep its **legal** meaning? "
                    "Paste a provision and a simplified version; the model returns a score from 1 to 10.")
        gr.HTML('<div class="lmp-banner"><b>Research prototype.</b> Trained on about 200 pairs from two acts '
                "(RTI Act 2005, Consumer Protection Act 2019) with labels from two disclosed LLM annotators, not "
                "human lawyers. Test Pearson 0.48 on held-out pairs of the same acts; much weaker on unseen acts and "
                "on Hindi, and it can miss reversed meanings there. Do not rely on it for legal decisions.</div>")
        ref = gr.State(None)
        with gr.Row():
            ex = gr.Dropdown(choices=list(examples), label="Load an example from the held-out test set",
                             value=None, scale=3)
            clear = gr.Button("Clear", scale=1)
        with gr.Row(equal_height=True):
            orig = gr.Textbox(label="Original legal text", lines=9, placeholder="Paste a provision (English or Hindi)…")
            simp = gr.Textbox(label="Simplification to check", lines=9,
                              placeholder="Paste a simplified version of the provision…")
        with gr.Row():
            go = gr.Button("Score legal meaning", variant="primary", scale=3)
            if llm_ready:
                mode = gr.Radio(["Standard", "Aggressive (12-year-old)"], value="Standard", show_label=False, scale=2)
                gen = gr.Button("Generate simplification with LLM", scale=2)
        with gr.Row():
            with gr.Column(scale=2):
                card = gr.HTML('<div class="lmp-empty">The score appears here.</div>')
                gr.Markdown("**Scale** (JUDGEBERT rubric): 7–10 Preserved · 2–6.9 Partially Preserved · "
                            "below 2 Not Preserved.")
            with gr.Column(scale=3):
                gr.Markdown("### Legal cue check (rule-based)")
                cues = gr.HTML('<div class="lmp-empty">Cues compared between the two texts appear here.</div>')
        with gr.Accordion("About the model", open=False):
            gr.Markdown(f"Checkpoint: `{model_dir}`. XLM-RoBERTa-base, first trained on FrJUDGE (French insurance "
                        "forms, JUDGEBERT, EMNLP 2025), then fine-tuned on our clause-grouped split `random_s42`. "
                        "Cross-encoder regression on `original [SEP] simplification`. Code and paper: "
                        "https://github.com/atharv-0509/legal-meaning-preservation-hi-en")

        ex.change(pick, ex, [orig, simp, ref, card, cues])
        go.click(run, [orig, simp, ref], [card, cues])
        clear.click(lambda: ("", "", None, None, '<div class="lmp-empty">The score appears here.</div>', ""),
                    None, [orig, simp, ref, ex, card, cues])
        simp.input(lambda: None, None, ref)        # edited text: the reference label no longer applies
        orig.input(lambda: None, None, ref)
        if llm_ready:
            gen.click(generate, [orig, mode], [simp, ref])
    return demo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", default="modeling/checkpoints/demo_model")
    ap.add_argument("--share", action="store_true", help="create a temporary public link")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args(argv)
    if not (Path(args.model_dir) / "config.json").is_file():
        sys.exit(f"model folder not found: {Path(args.model_dir).resolve()} (see HANDOVER.md section 4, item 4)")
    import gradio as gr
    build(args.model_dir).launch(share=args.share, server_port=args.port, css=CSS, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
