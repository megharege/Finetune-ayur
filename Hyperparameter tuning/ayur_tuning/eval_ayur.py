#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Score a model on an Ayurvedic question set.
===========================================

    # baseline, before any training
    python eval_ayur.py --model Qwen/Qwen2.5-3B-Instruct \\
        --test_file /kaggle/input/ayur/test_25.json --out baseline.json

    # after training, same command plus the adapter
    python eval_ayur.py --model Qwen/Qwen2.5-3B-Instruct \\
        --adapter /kaggle/working/ayur_qlora \\
        --test_file /kaggle/input/ayur/test_25.json --out tuned.json

THE PROMPT MUST MATCH TRAINING, EXACTLY
---------------------------------------
Prompts are built by ``ayur_data.build_user_prompt`` --- the same function the
trainer used. This is not tidiness. A model fine-tuned on one prompt shape and
evaluated on another scores far below what it learned, and the gap looks like a
training failure rather than an evaluation bug. Sharing the code makes the two
impossible to drift apart.

SCORING
-------
Constrained to the letters that exist as options, by comparing the logprob of
each candidate letter rather than free-generating and parsing. Free generation
needs a parser, and a parser turns "The answer is B." and "B" into different
outcomes --- measuring instruction-following, not knowledge. Scoring by logprob
removes the parser entirely.

Multiple-selection items are scored as an exact set match: all correct letters
and no extra ones. Partial credit would flatter the model on precisely the
format it finds hardest.

Open-ended rows (no options) are skipped and counted separately --- they need
free-text metrics, not accuracy.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayur_data as AD


def load(p):
    with open(p, encoding="utf-8") as fh:
        head = fh.read(2048)
        fh.seek(0)
        if head.lstrip().startswith("["):
            return json.load(fh)
        return [json.loads(l) for l in fh if l.strip()]


@torch.no_grad()
def letter_logprobs(model, tok, prompt: str, letters, device):
    """Mean logprob of each candidate letter as the continuation of `prompt`."""
    out = {}
    base = tok(prompt, return_tensors="pt").to(device)
    for L in letters:
        cand = tok(L, add_special_tokens=False)["input_ids"]
        ids = torch.cat([base["input_ids"],
                         torch.tensor([cand], device=device)], dim=1)
        logits = model(ids).logits[0]
        lp = 0.0
        for k, tid in enumerate(cand):
            pos = base["input_ids"].shape[1] + k - 1
            lp += torch.log_softmax(logits[pos], -1)[tid].item()
        out[L] = lp / max(len(cand), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default="", help="LoRA dir; omit for the baseline")
    ap.add_argument("--test_file", required=True)
    ap.add_argument("--out", default="eval_results.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--use_4bit", action="store_true", default=True)
    ap.add_argument("--no_system", action="store_true")
    a = ap.parse_args()

    rows = load(a.test_file)
    if a.limit:
        rows = rows[:a.limit]
    print("loaded %d rows from %s" % (len(rows), os.path.basename(a.test_file)))

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.float16,
                               bnb_4bit_use_double_quant=True) if a.use_4bit else None
    model = AutoModelForCausalLM.from_pretrained(
        a.model, quantization_config=quant, device_map="auto",
        torch_dtype=torch.float16, trust_remote_code=True)

    tag = "baseline"
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
        tag = os.path.basename(a.adapter.rstrip("/"))
        print("adapter loaded: %s" % a.adapter)
    model.eval()
    device = next(model.parameters()).device

    n_ok = n_scored = n_skipped = 0
    by_type = defaultdict(lambda: [0, 0])
    by_lang = defaultdict(lambda: [0, 0])
    details = []

    for i, r in enumerate(rows):
        opts = AD.options_of(r)
        gold = AD.answer_keys(r, opts)
        if len(opts) < 2 or not gold:
            n_skipped += 1
            continue

        user = AD.build_user_prompt(r, allow_open=False)
        lang = AD.infer_language(r)
        msgs = ([] if a.no_system else [{"role": "system", "content": AD.SYSTEM[lang]}])
        msgs.append({"role": "user", "content": user})
        prompt = (tok.apply_chat_template(msgs, tokenize=False,
                                          add_generation_prompt=True)
                  if tok.chat_template else "User: %s\nAnswer:" % user)

        letters = [L.upper() for L in AD.LETTERS if L in opts]
        lp = letter_logprobs(model, tok, prompt, letters, device)

        if len(gold) > 1:
            # exact set match: take the top-k letters, k = number of gold answers
            pred = sorted(sorted(lp, key=lp.get, reverse=True)[:len(gold)])
        else:
            pred = [max(lp, key=lp.get)]

        ok = sorted(pred) == sorted(gold)
        n_ok += int(ok)
        n_scored += 1
        t = r.get("question_type", "?")
        by_type[t][0] += int(ok); by_type[t][1] += 1
        by_lang[lang][0] += int(ok); by_lang[lang][1] += 1
        details.append({"question_id": r.get("question_id"), "type": t,
                        "language": lang, "gold": gold, "pred": pred,
                        "correct": ok})
        if (i + 1) % 25 == 0 or i + 1 == len(rows):
            print("  %4d/%d scored, running accuracy %.1f%%"
                  % (i + 1, len(rows), 100 * n_ok / max(n_scored, 1)), flush=True)

    acc = n_ok / max(n_scored, 1)
    print("\n%s --- %d/%d correct = %.1f%%   (%d open-ended rows skipped)"
          % (tag, n_ok, n_scored, 100 * acc, n_skipped))
    print("\nby question type")
    for t, (c, n) in sorted(by_type.items(), key=lambda kv: -kv[1][1]):
        print("   %-26s %3d/%-3d  %5.1f%%" % (t, c, n, 100 * c / max(n, 1)))
    print("by language")
    for l, (c, n) in sorted(by_lang.items()):
        print("   %-26s %3d/%-3d  %5.1f%%" % (l, c, n, 100 * c / max(n, 1)))

    # A 25-row set is small. Say so, rather than letting a 4-point move look real.
    if n_scored < 100:
        import math
        se = math.sqrt(max(acc * (1 - acc), 1e-9) / n_scored)
        print("\n  n=%d, standard error +/-%.1f points. Treat anything under "
              "%.0f points as noise." % (n_scored, 100 * se, 100 * 2 * se))

    json.dump({"model": a.model, "adapter": a.adapter or None, "tag": tag,
               "test_file": os.path.basename(a.test_file),
               "scored": n_scored, "correct": n_ok, "accuracy": round(acc, 4),
               "open_ended_skipped": n_skipped,
               "by_type": {t: {"correct": c, "n": n, "acc": round(c / max(n, 1), 4)}
                           for t, (c, n) in by_type.items()},
               "by_language": {l: {"correct": c, "n": n, "acc": round(c / max(n, 1), 4)}
                               for l, (c, n) in by_lang.items()},
               "details": details},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nwrote %s" % a.out)


if __name__ == "__main__":
    main()
