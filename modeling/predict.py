"""Score new pairs with a trained model (saved with train.py --save-model DIR): the brief's
per-pair output = LMP score (1-10) + decision (Preserved / Partially Preserved / Not Preserved).

    python modeling/predict.py --model-dir modeling/models/xlmr-da \
        --original "The officer shall reply within thirty days." --simplification "The officer may reply."
    python modeling/predict.py --model-dir DIR --input pairs.jsonl --output scored.jsonl
    python modeling/predict.py --model-dir DIR --demo        # small Gradio web demo (pip install gradio)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rubric import decision  # noqa: E402


class LMPScorer:
    def __init__(self, model_dir: str, max_len: int = 512):
        import torch
        from transformers import AutoModelForSequenceClassification
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from lmp_data import load_tokenizer
        self.torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = load_tokenizer(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device).eval()
        self.max_len = max_len

    def score(self, originals: list[str], simplifications: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(originals), 32):
            enc = self.tok(originals[i:i + 32], simplifications[i:i + 32], truncation="longest_first",
                           max_length=self.max_len, padding=True, return_tensors="pt").to(self.device)
            with self.torch.no_grad():
                preds = self.model(**enc).logits.squeeze(-1).cpu().tolist()
            for p in (preds if isinstance(preds, list) else [preds]):
                s = min(10.0, max(1.0, p))
                out.append({"lmp_score": round(s, 2), "decision": decision(s)})
        return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--original")
    ap.add_argument("--simplification")
    ap.add_argument("--input", help="JSONL with original + simplification fields")
    ap.add_argument("--output")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)
    if not (Path(args.model_dir) / "config.json").is_file():
        sys.exit(f"model folder not found: {Path(args.model_dir).resolve()}\n"
                 "It must contain config.json, model.safetensors, tokenizer.json and tokenizer_config.json.\n"
                 "The demo checkpoint is not in git (~1 GB). Fetch it with (needs your Kaggle API token):\n"
                 "  python modeling/kaggle/kaggle_client.py fetch --user atharvarora05 --slug lmp-e23-fixed --prefix demo_model/\n"
                 "then run with --model-dir modeling/checkpoints/demo_model, or download demo_model/ from the Output tab of\n"
                 "https://www.kaggle.com/code/atharvarora05/lmp-e23-fixed (HANDOVER.md section 4, item 4).")
    scorer = LMPScorer(args.model_dir)
    if args.demo:
        import gradio as gr

        def fn(o, s):
            r = scorer.score([o], [s])[0]
            return r["lmp_score"], r["decision"]
        gr.Interface(fn, [gr.Textbox(label="Original legal text", lines=5), gr.Textbox(label="Simplification", lines=5)],
                     [gr.Number(label="LMP score (1-10)"), gr.Textbox(label="Decision")],
                     title="Legal Meaning Preservation (English / Hindi)").launch()
        return
    if args.input:
        rows = [json.loads(line) for line in open(args.input, encoding="utf-8") if line.strip()]
        res = scorer.score([r["original"] for r in rows], [r["simplification"] for r in rows])
        with open(args.output or "/dev/stdout", "w", encoding="utf-8") as f:
            for r, s in zip(rows, res):
                f.write(json.dumps(dict(r, **s), ensure_ascii=False) + "\n")
        return
    if not (args.original and args.simplification):
        sys.exit("give --original and --simplification, --input, or --demo")
    print(json.dumps(scorer.score([args.original], [args.simplification])[0], ensure_ascii=False))


if __name__ == "__main__":
    main()
