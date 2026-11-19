"""Legal Meaning Preservation demo (English / Hindi): a Gradio app around a trained checkpoint.

    python modeling/app.py --model-dir modeling/checkpoints/demo_model          # http://127.0.0.1:7860
    python modeling/app.py --model-dir modeling/checkpoints/demo_model --share  # temporary public link

What it shows for one original/simplification pair:
  * the model's LMP score (1-10) and decision (Preserved / Partially Preserved / Not Preserved);
  * the likely legal error type with a one-line explanation: rule-based always, plus a trained classifier
    if --errcls-dir is given (modeling/error_classifier.py; metrics in reports/error_classification.md);
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
from legal_cues import EXPLANATIONS, cue_rows, lang_of, rule_error_type  # noqa: E402
from rubric import decision  # noqa: E402

EXAMPLES_FILE = ROOT / "data" / "splits" / "random_s42" / "test.jsonl"
FEATURED = ["cpa-s10_1|en|normal", "cpa-s10_1|en|perturbed", "cpa-s10_1|en|aggressive",
            "rti-s11_4|hi|normal", "rti-s11_4|hi|perturbed", "rti-s11_4|hi|aggressive"]
VARIANT_NAME = {"normal": "standard simplification", "perturbed": "one injected legal error",
                "aggressive": "explained to a 12-year-old"}

FONTS = ("https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500"
         "&family=Inter:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500&display=swap")

CSS = """
@import url('""" + FONTS + """');
:root {
  --lmp-ink:#1c1917; --lmp-muted:#78716c; --lmp-faint:#a8a29e; --lmp-line:#e7e5e4; --lmp-paper:#fafaf9;
  --lmp-card:#ffffff; --lmp-ok:#3f7a55; --lmp-mid:#b7791f; --lmp-bad:#a83232;
  --lmp-serif:'Newsreader',Georgia,'Times New Roman',serif;
  --lmp-sans:'Inter','Noto Sans Devanagari',system-ui,-apple-system,'Segoe UI',sans-serif;
}
.dark {
  --lmp-ink:#f5f5f4; --lmp-muted:#a8a29e; --lmp-faint:#78716c; --lmp-line:#2c2a28; --lmp-paper:#121110;
  --lmp-card:#1a1918; --lmp-ok:#86c49c; --lmp-mid:#e3b45f; --lmp-bad:#e58a8a;
}
.gradio-container {max-width:980px !important; margin:0 auto !important; padding:0 16px !important;
  font-family:var(--lmp-sans) !important}
footer {display:none !important}
.gradio-container .main.app {padding:0 !important}
.gradio-container .form {background:transparent !important; border:0 !important; box-shadow:none !important;
  gap:20px !important}
textarea {font-family:var(--lmp-sans) !important; font-size:15px !important; line-height:1.6 !important}

.lmp-head {padding:56px 0 28px; border-bottom:1px solid var(--lmp-line); margin-bottom:28px}
.lmp-eyebrow {font:600 11px/1 var(--lmp-sans); letter-spacing:.14em; text-transform:uppercase; color:var(--lmp-muted)}
.lmp-head h1 {font-family:var(--lmp-serif); font-weight:400; font-size:44px; line-height:1.1; letter-spacing:-.01em;
  color:var(--lmp-ink); margin:14px 0 12px}
.lmp-head p {color:var(--lmp-muted); font-size:16px; line-height:1.6; max-width:640px; margin:0}

.lmp-actions {gap:12px !important; margin-top:4px; padding:0 12px !important}

.lmp-empty {color:var(--lmp-faint); font-size:14px; padding:28px 0; text-align:center;
  border-top:1px solid var(--lmp-line); border-bottom:1px solid var(--lmp-line)}
.lmp-result {display:grid; grid-template-columns:220px 1fr; gap:40px; padding:32px 0;
  border-top:1px solid var(--lmp-line); border-bottom:1px solid var(--lmp-line); color:var(--lmp-ink)}
.lmp-num {font-family:var(--lmp-serif); font-size:84px; line-height:.95; font-weight:400; letter-spacing:-.02em;
  margin-top:14px; font-variant-numeric:tabular-nums}
.lmp-num span {font-size:24px; color:var(--lmp-faint); margin-left:4px}
.lmp-dec {display:flex; align-items:center; gap:8px; margin-top:14px; font-size:15px; font-weight:500}
.lmp-dec i {width:8px; height:8px; border-radius:50%; display:inline-block}
.lmp-scale {position:relative; display:flex; height:4px; gap:3px; margin:6px 0 10px}
.lmp-scale div {height:4px; border-radius:2px; background:var(--lmp-line)}
.lmp-scale .on {background:var(--lmp-ink)}
.lmp-marker {position:absolute; top:-6px; width:2px; height:16px; background:var(--lmp-ink); border-radius:1px}
.lmp-marker.ref {background:none; border-left:2px dotted var(--lmp-muted); width:0}
.lmp-scale-labels {position:relative; height:16px; font-size:12px; color:var(--lmp-faint);
  font-variant-numeric:tabular-nums}
.lmp-scale-labels span {position:absolute; top:0}
.lmp-scale-key {display:flex; gap:18px; flex-wrap:wrap; font-size:12px; color:var(--lmp-muted); margin-top:8px}
.lmp-scale-key i {width:6px; height:6px; border-radius:50%; display:inline-block; margin-right:6px;
  vertical-align:middle}
.lmp-block {margin-top:26px}
.lmp-block h3 {font:600 11px/1 var(--lmp-sans); letter-spacing:.14em; text-transform:uppercase;
  color:var(--lmp-muted); margin:0 0 10px}
.lmp-type {font-family:var(--lmp-serif); font-size:22px; line-height:1.3}
.lmp-why {color:var(--lmp-muted); font-size:14px; line-height:1.6; margin-top:6px}
.lmp-meta {color:var(--lmp-faint); font-size:12.5px; line-height:1.6; margin-top:10px}

.lmp-cues table {width:100%; border-collapse:collapse; font-size:13.5px; border:0 !important}
.lmp-cues tr, .lmp-cues th, .lmp-cues td {border-left:0 !important; border-right:0 !important; border-top:0 !important;
  background:transparent !important}
.lmp-cues th {font:600 11px/1 var(--lmp-sans); letter-spacing:.1em; text-transform:uppercase; color:var(--lmp-muted);
  text-align:left; padding:10px 8px; border-bottom:1px solid var(--lmp-line)}
.lmp-cues td {padding:10px 8px; border-bottom:1px solid var(--lmp-line); vertical-align:top; color:var(--lmp-ink)}
.lmp-cues .flag {color:var(--lmp-bad)} .lmp-cues .ok {color:var(--lmp-faint)}
.lmp-cues p {color:var(--lmp-muted); font-size:13px; margin:4px 0 8px}

.lmp-foot {margin:40px 0 48px; padding-top:20px; border-top:1px solid var(--lmp-line); color:var(--lmp-faint);
  font-size:12.5px; line-height:1.7}
.lmp-foot b {color:var(--lmp-muted); font-weight:500}
.lmp-foot a {color:var(--lmp-muted)}

@media (max-width:720px) {
  .gradio-container {padding:0 4px !important}
  .lmp-pair {flex-direction:column !important}
  .lmp-pair > * {min-width:100% !important}
  .lmp-head {padding:32px 0 20px} .lmp-head h1 {font-size:32px}
  .lmp-result {grid-template-columns:1fr; gap:8px}
  .lmp-num {font-size:64px}
}
"""


def theme():
    import gradio as gr
    stone = gr.themes.colors.stone
    return gr.themes.Base(
        primary_hue=stone, neutral_hue=stone, radius_size=gr.themes.sizes.radius_sm,
        font=[gr.themes.GoogleFont("Inter"), gr.themes.GoogleFont("Noto Sans Devanagari"), "system-ui", "sans-serif"],
    ).set(
        body_background_fill="#fafaf9", body_background_fill_dark="#121110",
        background_fill_primary="#fafaf9", background_fill_primary_dark="#121110",
        block_background_fill="transparent", block_background_fill_dark="transparent",
        block_border_width="0px", block_shadow="none", block_shadow_dark="none",
        block_label_background_fill="transparent", block_label_background_fill_dark="transparent",
        block_label_text_color="#78716c", block_label_text_color_dark="#a8a29e",
        block_label_text_size="13px", block_label_text_weight="500",
        input_background_fill="#ffffff", input_background_fill_dark="#1a1918",
        input_border_color="#e7e5e4", input_border_color_dark="#2c2a28",
        input_border_color_focus="#1c1917", input_border_color_focus_dark="#f5f5f4",
        input_shadow="none", input_shadow_focus="none", input_padding="14px", input_border_width="1px",
        button_primary_background_fill="#1c1917", button_primary_background_fill_dark="#f5f5f4",
        button_primary_background_fill_hover="#44403c", button_primary_background_fill_hover_dark="#d6d3d1",
        button_primary_text_color="#fafaf9", button_primary_text_color_dark="#1c1917",
        button_primary_border_color="#1c1917", button_primary_border_color_dark="#f5f5f4",
        button_secondary_background_fill="transparent", button_secondary_background_fill_dark="transparent",
        button_secondary_background_fill_hover="#f5f5f4", button_secondary_background_fill_hover_dark="#1f1d1c",
        button_secondary_border_color="#e7e5e4", button_secondary_border_color_dark="#2c2a28",
        button_secondary_text_color="#44403c", button_secondary_text_color_dark="#d6d3d1",
        button_large_padding="12px 22px", button_large_text_weight="500", button_large_text_size="14px",
        border_color_primary="#e7e5e4", border_color_primary_dark="#2c2a28",
    )


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


DEC_COLOUR = {"Preserved": "var(--lmp-ok)", "Partially Preserved": "var(--lmp-mid)", "Not Preserved": "var(--lmp-bad)"}
TYPE_LABEL = {"none": "No legal error of a known type", "modality": "Obligation turned into permission, or back",
              "negation": "Negation added or removed", "number": "A number or time limit changed",
              "exception_drop": "An exception or proviso dropped", "scope": "Scope changed (all → some)"}
EMPTY = '<div class="lmp-empty">Paste a provision and its simplification, then score.</div>'


def _pct(x: float) -> float:
    return max(0.0, min(100.0, (x - 1) / 9 * 100))


def result_html(score: float, ref: float | None, rule: tuple[str, str], neural: tuple[str, float] | None) -> str:
    """One quiet panel: the score and decision, the 1-10 scale, and the likely legal error."""
    dec = decision(score)
    # scale segments follow the rubric brackets: 1-2 Not, 2-7 Partially, 7-10 Preserved
    segs = [(11.1, "Not Preserved"), (55.6, "Partially Preserved"), (33.3, "Preserved")]
    bar = "".join(f'<div class="{"on" if name == dec else ""}" style="width:{w}%"></div>' for w, name in segs)
    bar += f'<span class="lmp-marker" style="left:calc({_pct(score):.1f}% - 1px)"></span>'
    if ref is not None:
        bar += f'<span class="lmp-marker ref" style="left:calc({_pct(ref):.1f}% - 1px)" title="reference label"></span>'
    rt, why = rule
    if neural:
        nt, conf = neural
        etype, expl = TYPE_LABEL[nt], EXPLANATIONS[nt]
        emeta = (f"Trained classifier, {conf:.0%} confident. Rule check: "
                 f"{'agrees' if nt == rt else html.escape(TYPE_LABEL[rt].lower())}.")
    else:
        etype, expl, emeta = TYPE_LABEL[rt], why, "Rule-based check."
    ref_txt = (f"Reference label {ref:.1f} ({html.escape(decision(ref))}), the mean of two disclosed LLM "
               "annotators, shown as the dotted mark." if ref is not None else "Your own text: no reference label.")
    return (
        '<div class="lmp-result">'
        f'<div><div class="lmp-eyebrow">LMP score</div>'
        f'<div class="lmp-num">{score:.1f}<span>/ 10</span></div>'
        f'<div class="lmp-dec"><i style="background:{DEC_COLOUR[dec]}"></i>{html.escape(dec)}</div></div>'
        '<div>'
        f'<div class="lmp-scale">{bar}</div>'
        '<div class="lmp-scale-labels"><span style="left:0">1</span><span style="left:11.1%">2</span>'
        '<span style="left:66.7%">7</span><span style="right:0">10</span></div>'
        '<div class="lmp-scale-key"><span><i style="background:var(--lmp-bad)"></i>Not preserved</span>'
        '<span><i style="background:var(--lmp-mid)"></i>Partially preserved</span>'
        '<span><i style="background:var(--lmp-ok)"></i>Preserved</span></div>'
        f'<div class="lmp-block"><h3>Likely legal error</h3><div class="lmp-type">{html.escape(etype)}</div>'
        f'<div class="lmp-why">{html.escape(expl)}</div>'
        f'<div class="lmp-meta">{emeta} Types cover the five injected errors only (shall/may, negation, number, '
        f'exception, scope).<br>{ref_txt}</div></div>'
        '</div></div>')


def cue_table(original: str, simplification: str) -> str:
    rows = cue_rows(original, simplification)
    if not rows:
        return '<div class="lmp-cues"><p>No legal cues detected by the rules.</p></div>'
    flags = sum(bool(r[3]) for r in rows)
    body = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td>"
        f"<td class='{'flag' if d else 'ok'}'>{html.escape(d) if d else 'consistent'}</td></tr>"
        for a, b, c, d in rows)
    head = (f"<p>{flags} potential issue{'s' if flags != 1 else ''}. Simple rules, an explanation aid only: "
            "they are not the model and miss paraphrases.</p>")
    return (f'<div class="lmp-cues">{head}<table><tr><th>Cue</th><th>Original</th><th>Simplification</th>'
            f"<th>Check</th></tr>{body}</table></div>")


class ErrorTyper:
    """Optional trained error-type classifier (modeling/error_classifier.py --save-model DIR)."""

    def __init__(self, model_dir: str):
        import torch
        from transformers import AutoModelForSequenceClassification
        from lmp_data import load_tokenizer
        self.torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = load_tokenizer(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device).eval()
        self.labels = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]

    def __call__(self, original: str, simplification: str) -> tuple[str, float]:
        enc = self.tok([original], [simplification], truncation="longest_first", max_length=512,
                       return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            p = self.torch.softmax(self.model(**enc).logits[0].float(), -1).cpu().tolist()
        i = max(range(len(p)), key=p.__getitem__)
        return self.labels[i], p[i]


# Known demo checkpoints: backbone (from config.json model_type) -> (description, held-out test Pearson on random_s42)
CHECKPOINTS = {
    "bert": ("MuRIL-base (google/muril-base-cased), first trained on FrJUDGE, then fine-tuned with data augmentation "
             "on our split random_s42 (Kaggle kernel lmp-muril-demo)", 0.682),
    "xlm-roberta": ("XLM-RoBERTa-base, first trained on FrJUDGE, then fine-tuned on our split random_s42 "
                    "(Kaggle kernel lmp-e23-fixed)", 0.479),
}


def checkpoint_info(model_dir: str) -> tuple[str, float | None]:
    try:
        mtype = json.loads((Path(model_dir) / "config.json").read_text(encoding="utf-8")).get("model_type", "")
    except (OSError, ValueError):
        mtype = ""
    return CHECKPOINTS.get(mtype, (f"checkpoint of type '{mtype or 'unknown'}'", None))


def build(model_dir: str, errcls_dir: str | None = None):
    import gradio as gr
    from predict import LMPScorer

    scorer = LMPScorer(model_dir)
    desc, test_r = checkpoint_info(model_dir)
    pearson_txt = (f"Test Pearson {test_r:.2f} on held-out pairs of the same Acts;" if test_r is not None
                   else "Accuracy of this checkpoint is not recorded here;")
    typer = ErrorTyper(errcls_dir) if errcls_dir else None
    examples = load_examples()
    llm_ready = bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL"))

    def run(original, simplification, ref):
        original, simplification = (original or "").strip(), (simplification or "").strip()
        if not original or not simplification:
            raise gr.Error("Paste both the original legal text and a simplification to score.")
        if original == simplification:
            gr.Info("The two texts are identical; a good metric should score this near 10.")
        s = scorer.score([original], [simplification])[0]["lmp_score"]
        rule = rule_error_type(original, simplification)
        neural = typer(original, simplification) if typer else None
        return result_html(s, ref, rule, neural), cue_table(original, simplification)

    def pick(name):
        r = examples.get(name)
        if not r:
            return gr.update(), gr.update(), None, gr.update(), gr.update()
        return r["original"], r["simplification"], float(r["label"]), EMPTY, ""

    def generate(original, mode):
        original = (original or "").strip()
        if not original:
            raise gr.Error("Paste the original legal text first.")
        from simplify import LLMClient, PROMPTS, clean_output
        lang = lang_of(original)
        _pid, tmpl = PROMPTS[(lang, "aggressive" if mode.startswith("For a 12") else "normal")]
        client = LLMClient(os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
                           os.environ["LLM_API_KEY"], os.environ["LLM_MODEL"])
        out = client.chat(tmpl.format(text=original), temperature=1.0, top_p=0.9,
                          max_tokens=200 if lang == "en" else 500)
        return clean_output(out["text"]), None

    with gr.Blocks(title="Legal Meaning Preservation") as demo:
        gr.HTML('<header class="lmp-head"><div class="lmp-eyebrow">Legal meaning preservation · English / हिन्दी'
                '</div><h1>Does the simplification keep the law?</h1><p>Compare an Indian statutory provision '
                'with a plain-language version. The model scores how much of the legal meaning survives, '
                'from 1 to 10, and names the likely legal error.</p></header>')
        ref = gr.State(None)
        ex = gr.Dropdown(choices=list(examples), value=None, label="Try an example from the held-out test set")
        with gr.Row(equal_height=True, elem_classes="lmp-pair"):
            orig = gr.Textbox(label="Original provision", lines=8, max_lines=16,
                              placeholder="Paste the statutory text, in English or Hindi")
            simp = gr.Textbox(label="Simplification", lines=8, max_lines=16,
                              placeholder="Paste the plain-language version to check")
        with gr.Row(elem_classes="lmp-actions"):
            go = gr.Button("Score", variant="primary", size="lg", scale=0, min_width=140)
            clear = gr.Button("Clear", variant="secondary", size="lg", scale=0, min_width=100)
            if llm_ready:
                mode = gr.Radio(["Standard", "For a 12-year-old"], value="Standard", show_label=False,
                                container=False, scale=0)
                gen = gr.Button("Draft a simplification", variant="secondary", size="lg", scale=0)
        card = gr.HTML(EMPTY)
        with gr.Accordion("Rule-based cue check", open=False):
            cues = gr.HTML('<div class="lmp-cues"><p>Score a pair to compare negations, obligations, '
                           'exceptions, conditions, time limits and numbers.</p></div>')
        gr.HTML(f'<div class="lmp-foot"><b>Research prototype, not legal advice.</b> Trained on about 200 pairs '
                "from two Acts (RTI 2005, Consumer Protection 2019), labelled by two disclosed LLM annotators rather "
                f"than lawyers. {pearson_txt} weaker on unseen Acts and on Hindi, and it can miss reversed meanings."
                f"<br>Model: {html.escape(desc)}. Cross-encoder on original [SEP] simplification, after JUDGEBERT "
                '(EMNLP 2025). <a href="https://github.com/atharv-0509/legal-meaning-preservation-hi-en" '
                'target="_blank">Code and paper</a></div>')

        ex.change(pick, ex, [orig, simp, ref, card, cues])
        go.click(run, [orig, simp, ref], [card, cues])
        clear.click(lambda: ("", "", None, None, EMPTY, ""), None, [orig, simp, ref, ex, card, cues])
        simp.input(lambda: None, None, ref)        # edited text: the reference label no longer applies
        orig.input(lambda: None, None, ref)
        if llm_ready:
            gen.click(generate, [orig, mode], [simp, ref])
    return demo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", default="modeling/checkpoints/demo_model")
    ap.add_argument("--errcls-dir", default=None, help="optional trained error-type classifier (error_classifier.py --save-model)")
    ap.add_argument("--share", action="store_true", help="create a temporary public link")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args(argv)
    if not (Path(args.model_dir) / "config.json").is_file():
        sys.exit(f"model folder not found: {Path(args.model_dir).resolve()} (see HANDOVER.md section 4, item 4)")
    build(args.model_dir, args.errcls_dir).launch(share=args.share, server_port=args.port, css=CSS, theme=theme())


if __name__ == "__main__":
    main()
