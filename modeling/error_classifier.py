"""Legal-error type classifier (the brief's optional "legal error type" output, scored with P/R/F1).

    python modeling/error_classifier.py --split-dir data/splits/random_s42 --model xlm-roberta-base --seed 42

Task: given (original, simplification), predict which legal error the simplification contains:
    none | modality | negation | number | exception_drop | scope
Data: the `normal` pairs (label "none") and the `perturbed` pairs (label = the rule-injected error type,
known by construction from src/perturb.py) of each clause-grouped split. These targets do NOT come from
the LLM annotators. `aggressive` pairs have no known error type and are left out. "none" means "no injected
error", not "no error at all": a normal simplification can still omit something.

Model: cross-encoder (`original [SEP] simplification`) with a 6-way classification head, class-weighted
cross-entropy, AdamW + linear decay, gradient clipping 1.0; the epoch with the best dev macro-F1 is kept.
--augment K adds, for the TRAIN clauses only, up to K extra injected-error pairs per type per standard simplification
(same rules as src/perturb.py, labels known by construction); --cue-features appends the rule cues
(legal_cues.compare) to the input. Both mirror the injection rules, so they suit this diagnostic task, not natural errors.
Writes <runs-dir>/<run-name>/<split>/errcls_preds_test.jsonl, errcls_metrics.json, errcls_config.json.
(`--patience` is accepted for compatibility with the Kaggle runner; 0 = no early stopping.)
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_cues import ERROR_CLASSES, compare  # noqa: E402
from lmp_data import load_split, load_tokenizer, write_json  # noqa: E402

LABEL2ID = {c: i for i, c in enumerate(ERROR_CLASSES)}
VARIANTS = ("normal", "perturbed")


def target(row: dict) -> str | None:
    if row.get("variant") == "normal":
        return "none"
    if row.get("variant") == "perturbed" and row.get("error_type") in LABEL2ID:
        return row["error_type"]
    return None


def rows_for(split_dir: Path, name: str, langs=None) -> list[dict]:
    return [dict(r, gold=target(r)) for r in load_split(split_dir, name, langs) if target(r) is not None]


def augment_rows(train: list[dict], k: int, seed: int, from_originals: bool = False) -> list[dict]:
    """Extra training pairs from the TRAIN split only: for every standard simplification, inject each applicable
    error type up to k times with the same rules as src/perturb.py (labels known by construction). Texts that equal
    an existing training simplification are skipped. Dev/test are never augmented."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from perturb import _cap_first, candidate_edits
    rng = random.Random(seed)
    seen = {(r["original"], r["simplification"]) for r in train}
    out = []
    bases = [r for r in train if r["gold"] == "none"]
    if from_originals:                  # the statute text itself as the "simplification": identical = none
        firsts = {}
        for r in train:
            firsts.setdefault((r["clause_id"], r["lang"]), r)
        for r in firsts.values():
            base = dict(r, pair_id=f"{r['clause_id']}|{r['lang']}|orig", simplification=r["original"], gold="none",
                        error_type=None, variant="augmented")
            if (r["original"], r["original"]) not in seen:
                seen.add((r["original"], r["original"]))
                out.append(base)
            bases.append(base)
    for r in bases:
        for et, edits in sorted(candidate_edits(r["simplification"], r["lang"]).items()):
            for i, e in enumerate(rng.sample(edits, min(k, len(edits)))):
                new = e.apply(r["simplification"])
                if et == "exception_drop" and r["lang"] == "en":
                    new = _cap_first(new)
                if (r["original"], new) in seen:
                    continue
                seen.add((r["original"], new))
                out.append(dict(r, pair_id=f"{r['pair_id']}#aug-{et}-{i}", variant="augmented", simplification=new,
                                gold=et, error_type=et))
    return out


def cue_text(original: str, simplification: str) -> str:
    """Rule cues rendered as text and appended to the model input (hybrid model, --cue-features)."""
    c = compare(original, simplification)
    (mo, ms), (no, ns) = c["markers"], c["neg"]
    numo, nums = c["numbers"]
    parts = [f"neg {no}>{ns}"]
    for cat in ("obligation", "permission", "prohibition", "exception", "override", "condition", "time_limit"):
        if (cat in mo) != (cat in ms):
            parts.append(f"{cat} {'lost' if cat in mo else 'added'}")
    new, lost = sorted(set(nums) - set(numo)), sorted(set(numo) - set(nums))
    if new or lost:
        parts.append(f"numbers new {','.join(new) or '-'} lost {','.join(lost) or '-'}")
    (wo, ws), (nao, nas) = c["scope_wide"], c["scope_narrow"]
    if (wo, nao) != (ws, nas):
        parts.append(f"scope wide {wo}>{ws} narrow {nao}>{nas}")
    return " [CUES] " + "; ".join(parts)


def prf(gold: list[str], pred: list[str], classes=ERROR_CLASSES) -> dict:
    """Per-class precision/recall/F1, macro-F1 over classes present in gold or pred, accuracy, confusion."""
    out, f1s = {}, []
    for c in classes:
        tp = sum(g == c and p == c for g, p in zip(gold, pred))
        fp = sum(g != c and p == c for g, p in zip(gold, pred))
        fn = sum(g == c and p != c for g, p in zip(gold, pred))
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[c] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        f1s.append(f1)
    conf = {g: dict(Counter(p for gg, p in zip(gold, pred) if gg == g)) for g in sorted(set(gold))}
    return {"n": len(gold), "accuracy": sum(g == p for g, p in zip(gold, pred)) / max(1, len(gold)),
            "macro_f1": sum(f1s) / len(f1s) if f1s else float("nan"), "per_class": out, "confusion": conf}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split-dir", required=True)
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--run-name", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--patience", type=int, default=0)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--max-grad-norm", type=float, default=1.0)
    ap.add_argument("--langs", nargs="+", default=None)
    ap.add_argument("--augment", type=int, default=0, help="extra injected-error pairs per type per standard "
                    "simplification of the training split (0 = off)")
    ap.add_argument("--augment-originals", action="store_true", help="also inject errors into the training clauses' "
                    "original texts (original vs original-with-one-error), and add original-vs-original as none")
    ap.add_argument("--cue-features", action="store_true", help="append rule cues to the input (hybrid model)")
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--save-model", default=None)
    ap.add_argument("--runs-dir", default=str(Path(__file__).resolve().parent / "runs_err"))
    args, _unknown = ap.parse_known_args(argv)        # tolerate regression-only flags from the shared runner

    import numpy as np
    import torch
    from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    split_dir = Path(args.split_dir)
    train, dev, test = (rows_for(split_dir, n, args.langs) for n in ("train", "dev", "test"))
    if not train or not dev or not test:
        sys.exit(f"empty train/dev/test in {split_dir}")
    n_aug = 0
    if args.augment:
        extra = augment_rows(train, args.augment, args.seed, args.augment_originals)
        n_aug = len(extra)
        train = train + extra
    split_name = split_dir.name if re.search(r"_s\d+$", split_dir.name) else f"{split_dir.name}_s{args.seed}"
    system = args.run_name or f"errcls-{Path(args.model).name}"
    out_dir = Path(args.runs_dir) / system / split_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{system} on {split_name}: train {len(train)} (augmented {n_aug}) {dict(Counter(r['gold'] for r in train))}, "
          f"dev {len(dev)}, test {len(test)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = load_tokenizer(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(ERROR_CLASSES), id2label=dict(enumerate(ERROR_CLASSES)), label2id=LABEL2ID,
        problem_type="single_label_classification", ignore_mismatched_sizes=True).to(device)

    def encode(rows):
        second = [r["simplification"] + (cue_text(r["original"], r["simplification"]) if args.cue_features else "")
                  for r in rows]
        return tok([r["original"] for r in rows], second, truncation="longest_first", max_length=args.max_len)

    enc = {"train": encode(train), "dev": encode(dev), "test": encode(test)}

    def batches(name, rows, shuffle, rng=None):
        idx = list(range(len(rows)))
        if shuffle:
            rng.shuffle(idx)
        for i in range(0, len(idx), args.batch_size):
            b = idx[i:i + args.batch_size]
            feats = tok.pad([{k: v[j] for k, v in enc[name].items()} for j in b], return_tensors="pt")
            yield {k: v.to(device) for k, v in feats.items()}, torch.tensor([LABEL2ID[rows[j]["gold"]] for j in b],
                                                                            device=device)

    def predict(name, rows):
        model.eval()
        probs = []
        with torch.no_grad():
            for feats, _ in batches(name, rows, False):
                with torch.autocast(device_type=device.type, enabled=args.fp16 and device.type == "cuda"):
                    logits = model(**feats).logits
                probs.extend(torch.softmax(logits.float(), -1).cpu().tolist())
        return probs

    counts = Counter(r["gold"] for r in train)
    weights = torch.tensor([len(train) / (len(ERROR_CLASSES) * counts[c]) if counts[c] else 0.0
                            for c in ERROR_CLASSES], dtype=torch.float32, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    steps = math.ceil(len(train) / args.batch_size) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, 0, steps)
    scaler = torch.amp.GradScaler("cuda", enabled=args.fp16 and device.type == "cuda")
    rng = random.Random(args.seed)
    best, best_state, best_epoch, bad, history, t0 = (-1.0, float("inf")), None, -1, 0, [], time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for feats, y in batches("train", train, True, rng):
            with torch.autocast(device_type=device.type, enabled=args.fp16 and device.type == "cuda"):
                loss = loss_fn(model(**feats).logits.float(), y)
            opt.zero_grad()
            scaler.scale(loss).backward()
            if args.max_grad_norm:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            scaler.step(opt)
            scaler.update()
            sched.step()
            tot += loss.item() * len(y)
        probs = predict("dev", dev)
        pred = [ERROR_CLASSES[max(range(len(p)), key=p.__getitem__)] for p in probs]
        m = prf([r["gold"] for r in dev], pred)
        dev_loss = -sum(math.log(max(1e-9, p[LABEL2ID[r["gold"]]])) for p, r in zip(probs, dev)) / len(dev)
        history.append({"epoch": epoch, "train_loss": tot / len(train), "dev_macro_f1": m["macro_f1"],
                        "dev_loss": dev_loss})
        print(f"epoch {epoch:3d} train_loss {tot / len(train):.3f} dev_macro_f1 {m['macro_f1']:.3f} dev_loss {dev_loss:.3f}")
        key = (m["macro_f1"], -dev_loss)
        if key > (best[0], -best[1]):
            best, best_epoch, bad = (m["macro_f1"], dev_loss), epoch, 0
            best_state = copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
        else:
            bad += 1
            if args.patience and bad >= args.patience:
                break
    model.load_state_dict(best_state)
    probs = predict("test", test)
    pred = [ERROR_CLASSES[max(range(len(p)), key=p.__getitem__)] for p in probs]
    with open(out_dir / "errcls_preds_test.jsonl", "w", encoding="utf-8") as f:
        for r, p, pr in zip(test, pred, probs):
            f.write(json.dumps({"pair_id": r["pair_id"], "clause_id": r["clause_id"], "act_id": r["act_id"],
                                "lang": r["lang"], "variant": r["variant"], "gold": r["gold"], "pred": p,
                                "probs": dict(zip(ERROR_CLASSES, [round(x, 4) for x in pr]))},
                               ensure_ascii=False) + "\n")
    metrics = {"test": prf([r["gold"] for r in test], pred),
               "by_lang": {lg: prf([r["gold"] for r in test if r["lang"] == lg],
                                   [p for r, p in zip(test, pred) if r["lang"] == lg])
                           for lg in sorted({r["lang"] for r in test})}}
    write_json(out_dir / "errcls_metrics.json", metrics)
    write_json(out_dir / "errcls_config.json", dict(vars(args), system=system, split_name=split_name,
                                                    best_epoch=best_epoch, best_dev_macro_f1=best[0],
                                                    history=history, seconds=round(time.time() - t0),
                                                    n_train=len(train), n_augmented=n_aug,
                                                    train_classes=dict(Counter(r["gold"] for r in train)),
                                                    classes=ERROR_CLASSES))
    print(f"ERRCLS TEST macro_f1 {metrics['test']['macro_f1']:.3f} acc {metrics['test']['accuracy']:.3f} "
          f"(best epoch {best_epoch})")
    if args.save_model:
        model.save_pretrained(args.save_model)
        tok.save_pretrained(args.save_model)


if __name__ == "__main__":
    main()
