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
    rows = cue_rows(original, simplification)
    if not rows:
        return '<div class="lmp-empty">No legal cues detected by the rules.</div>'
    flags = sum(bool(r[3]) for r in rows)
    body = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td>"
        f"<td class='{'lmp-flag' if d else 'lmp-ok'}'>{html.escape(d) if d else 'consistent'}</td></tr>"
        for a, b, c, d in rows)
    head = (f"<p><b>{flags}</b> potential issue{'s' if flags != 1 else ''} flagged by simple rules. "
            "These rules are an explanation aid only — they are not the model and miss paraphrases.</p>")
    return (f'<div class="lmp-cues">{head}<table><tr><th>Legal cue</th><th>Original</th><th>Simplification</th>'
            f"<th>Check</th></tr>{body}</table></div>")


TYPE_LABEL = {"none": "No injected-type error", "modality": "Obligation ↔ permission (shall/may)",
              "negation": "Negation added or removed", "number": "Number / time limit changed",
              "exception_drop": "Exception or proviso dropped", "scope": "Scope changed (all → some)"}


def error_card(rule: tuple[str, str], neural: tuple[str, float] | None) -> str:
    rt, why = rule
    parts = [f"<p><b>Rule-based:</b> {html.escape(TYPE_LABEL[rt])}<br><span style='opacity:.85'>{html.escape(why)}</span></p>"]
    if neural:
        nt, conf = neural
        parts.append(f"<p><b>Trained classifier:</b> {html.escape(TYPE_LABEL[nt])} "
                     f"<span style='opacity:.8'>(confidence {conf:.0%})</span><br><span style='opacity:.85'>"
                     f"{html.escape(EXPLANATIONS[nt])}</span></p>")
    parts.append("<p style='font-size:12px;opacity:.75'>Types follow the injected errors of the dataset (shall/may, "
                 "negation, number, exception, scope); omissions of other kinds are not typed. "
                 "See reports/error_classification.md for precision/recall/F1.</p>")
    return '<div class="lmp-cues">' + "".join(parts) + "</div>"


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
    pearson_txt = (f"Test Pearson {test_r:.2f} on held-out pairs of the same acts;" if test_r is not None
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
        return score_card(s, ref), error_card(rule, neural), cue_table(original, simplification)

    def pick(name):
        r = examples.get(name)
        if not r:
            return gr.update(), gr.update(), None, "", "", ""
        return r["original"], r["simplification"], float(r["label"]), "", "", ""

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
                f"human lawyers. {pearson_txt} much weaker on unseen acts and "
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
                gr.Markdown("### Likely legal error")
                errbox = gr.HTML('<div class="lmp-empty">The predicted error type and a short explanation appear here.</div>')
                gr.Markdown("### Legal cue check (rule-based)")
                cues = gr.HTML('<div class="lmp-empty">Cues compared between the two texts appear here.</div>')
        with gr.Accordion("About the model", open=False):
            gr.Markdown(f"Checkpoint: `{model_dir}` — {desc}. Cross-encoder regression on "
                        "`original [SEP] simplification`. FrJUDGE: French insurance forms (JUDGEBERT, EMNLP 2025). "
                        "Code, paper and evaluation: https://github.com/atharv-0509/legal-meaning-preservation-hi-en")

        ex.change(pick, ex, [orig, simp, ref, card, errbox, cues])
        go.click(run, [orig, simp, ref], [card, errbox, cues])
        clear.click(lambda: ("", "", None, None, '<div class="lmp-empty">The score appears here.</div>', "", ""),
                    None, [orig, simp, ref, ex, card, errbox, cues])
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
    import gradio as gr
    build(args.model_dir, args.errcls_dir).launch(share=args.share, server_port=args.port, css=CSS, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
