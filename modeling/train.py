"""JUDGEBERT-style cross-encoder: `original [SEP] simplification` -> LMP score (regression, MSE).

    python modeling/train.py --split-dir data/splits/random_s42 --model xlm-roberta-base --da --seed 42
    python modeling/train.py --split-dir data/splits/random_s42 --model google/muril-base-cased \
        --train-langs en --test-langs hi          # E2: zero-shot EN -> HI
    python modeling/train.py --split-dir data/splits/ood_rti_to_cpa --model xlm-roberta-base --da   # E3

Hyper-parameters follow JUDGEBERT (lr 5e-5, batch 16, up to 100 epochs, linear decay, no warmup).
Model selection: the epoch with the lowest dev MSE. The paper text says patience 5; the released
training script has early stopping commented out and keeps the best-dev-loss checkpoint over all
100 epochs. --patience 5 (default) follows the paper text; --patience 0 follows the released code.

Dev set: --dev-set human (default) selects on human-annotated dev pairs only; --dev-set da uses
dev_da.jsonl like the paper's DA runs. The test set is always human-annotated pairs only.

Writes modeling/runs/<run-name>/<split>[__train-X_test-Y]/preds_{test,holdout_identical,holdout_unrelated}.jsonl,
metrics.json and config.json. Fits a Colab T4; use --fp16 there.
"""
from __future__ import annotations

import argparse
import copy
import math
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lmp_data import holdout_files, load_split, read_jsonl, run_dir, write_json, write_preds  # noqa: E402
from metrics import evaluate_rows, sanity_metrics  # noqa: E402


def set_seed(seed: int):
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class PairData:
    def __init__(self, rows, tokenizer, max_len):
        self.rows = rows
        self.enc = tokenizer([r["original"] for r in rows], [r["simplification"] for r in rows],
                             truncation="longest_first", max_length=max_len)
        self.labels = [float(r["label"]) for r in rows]

    def batches(self, batch_size, shuffle, tokenizer, rng=None):
        import torch
        idx = list(range(len(self.rows)))
        if shuffle:
            rng.shuffle(idx)
        for i in range(0, len(idx), batch_size):
            b = idx[i:i + batch_size]
            feats = tokenizer.pad([{k: v[j] for k, v in self.enc.items()} for j in b], return_tensors="pt")
            yield feats, torch.tensor([self.labels[j] for j in b], dtype=torch.float32)


def predict(model, data: PairData, tokenizer, device, batch_size=64, fp16=False):
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for feats, _ in data.batches(batch_size, False, tokenizer):
            feats = {k: v.to(device) for k, v in feats.items()}
            with torch.autocast(device_type=device.type, enabled=fp16 and device.type == "cuda"):
                logits = model(**feats).logits.squeeze(-1)
            out.extend(logits.float().cpu().tolist())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split-dir", required=True)
    ap.add_argument("--model", default="xlm-roberta-base", help="HF checkpoint or local path")
    ap.add_argument("--run-name", default=None, help="system name under modeling/runs (default: model[-da])")
    ap.add_argument("--da", action="store_true", help="train on train_da.jsonl (identical + unrelated pairs)")
    ap.add_argument("--dev-set", choices=["human", "da"], default="human")
    ap.add_argument("--train-langs", nargs="+", default=None, help="default: all languages")
    ap.add_argument("--test-langs", nargs="+", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--patience", type=int, default=5, help="0 = no early stopping (released JUDGEBERT code)")
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--clip-min", type=float, default=1.0, help="predictions are clipped to [clip-min, 10]")
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--save-model", default=None, help="directory to save the best model + tokenizer")
    ap.add_argument("--extra-test", nargs="*", default=[],
                    help="other files in the split dir to score, e.g. test_da (FrJUDGE's DA test set)")
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args(argv)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    set_seed(args.seed)
    split_dir = Path(args.split_dir)
    train_rows = load_split(split_dir, "train_da" if args.da else "train", args.train_langs)
    dev_rows = load_split(split_dir, "dev_da" if args.dev_set == "da" else "dev", args.train_langs)
    test_rows = load_split(split_dir, "test", args.test_langs)
    if not train_rows or not dev_rows or not test_rows:
        sys.exit(f"empty train/dev/test in {split_dir} (train={len(train_rows)}, dev={len(dev_rows)}, test={len(test_rows)})")

    split_name = split_dir.name
    if not re.search(r"_s\d+$", split_name):
        split_name += f"_s{args.seed}"          # fixed splits (OOD, FrJUDGE): one run per model seed
    if args.train_langs or args.test_langs:
        split_name += f"__train-{'+'.join(args.train_langs or ['all'])}_test-{'+'.join(args.test_langs or ['all'])}"
    system = args.run_name or (Path(args.model).name + ("-da" if args.da else ""))
    out_dir = run_dir(system, split_name, Path(args.runs_dir) if args.runs_dir else None)
    print(f"{system} on {split_name}: train {len(train_rows)}, dev {len(dev_rows)}, test {len(test_rows)} -> {out_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=1).to(device)
    train, dev, test = (PairData(r, tok, args.max_len) for r in (train_rows, dev_rows, test_rows))

    steps_per_epoch = math.ceil(len(train_rows) / args.batch_size)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = get_linear_schedule_with_warmup(opt, 0, steps_per_epoch * args.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=args.fp16 and device.type == "cuda")
    loss_fn = torch.nn.MSELoss()
    rng = random.Random(args.seed)

    best, best_state, best_epoch, bad, history = float("inf"), None, -1, 0, []
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for feats, y in train.batches(args.batch_size, True, tok, rng):
            feats, y = {k: v.to(device) for k, v in feats.items()}, y.to(device)
            with torch.autocast(device_type=device.type, enabled=args.fp16 and device.type == "cuda"):
                pred = model(**feats).logits.squeeze(-1)
                loss = loss_fn(pred.float(), y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += loss.item() * len(y)
        dev_pred = predict(model, dev, tok, device, fp16=args.fp16)
        dev_mse = sum((p - y) ** 2 for p, y in zip(dev_pred, dev.labels)) / len(dev.labels)
        history.append({"epoch": epoch, "train_mse": tot / len(train_rows), "dev_mse": dev_mse})
        print(f"epoch {epoch:3d} train_mse {tot / len(train_rows):.3f} dev_mse {dev_mse:.3f}")
        if dev_mse < best - 1e-6:
            best, best_epoch, bad = dev_mse, epoch, 0
            best_state = copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
        else:
            bad += 1
            if args.patience and bad >= args.patience:
                print(f"early stop (patience {args.patience}); best epoch {best_epoch}")
                break
    model.load_state_dict(best_state)

    test_pred = predict(model, test, tok, device, fp16=args.fp16)
    write_preds(out_dir / "preds_test.jsonl", test_rows, test_pred, lo=args.clip_min)
    metrics = {"test": evaluate_rows([dict(r, pred=min(10, max(args.clip_min, p))) for r, p in zip(test_rows, test_pred)])}
    for name, path in holdout_files(split_dir).items():
        rows = read_jsonl(path)
        if args.test_langs:
            rows = [r for r in rows if r["lang"] in args.test_langs]
        if not rows:
            continue
        p = predict(model, PairData(rows, tok, args.max_len), tok, device, fp16=args.fp16)
        write_preds(out_dir / f"preds_{name}.jsonl", rows, p, lo=args.clip_min)
        metrics[name] = sanity_metrics([min(10, max(args.clip_min, x)) for x in p], name.split("_")[1])
    for name in args.extra_test:
        rows = load_split(split_dir, name, args.test_langs)
        p = predict(model, PairData(rows, tok, args.max_len), tok, device, fp16=args.fp16)
        write_preds(out_dir / f"preds_{name}.jsonl", rows, p, lo=args.clip_min)
        metrics[name] = evaluate_rows([dict(r, pred=min(10, max(args.clip_min, x))) for r, x in zip(rows, p)])
    write_json(out_dir / "metrics.json", metrics)
    write_json(out_dir / "config.json", dict(vars(args), system=system, split_name=split_name, best_epoch=best_epoch,
                                              best_dev_mse=best, history=history, seconds=round(time.time() - t0),
                                              device=str(device)))
    o = metrics["test"]["overall"]
    print(f"TEST pearson {o['pearson']:.3f} spearman {o['spearman']:.3f} rmse {o['rmse']:.3f} mae {o['mae']:.3f} "
          f"(best epoch {best_epoch})")
    if args.save_model:
        model.save_pretrained(args.save_model)
        tok.save_pretrained(args.save_model)


if __name__ == "__main__":
    main()
