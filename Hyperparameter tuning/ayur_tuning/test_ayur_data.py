#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-flight test for the AyurLLM fine-tuning data layer. No GPU, no model download.
==================================================================================

Run this before launching a training job. It exercises every code path the
trainer will take through the data --- loading, formatting, chat-template
handling, masking, the length audit and the plotting --- against the real split
files, using a stub tokenizer that mimics a chat model closely enough to catch
schema bugs.

A schema bug found here costs seconds. The same bug found on a GPU costs however
long it takes the run to reach the first eval.

    python test_ayur_data.py --data_dir ../ayur_pipeline/final
    python test_ayur_data.py --data_dir ../ayur_pipeline/final --real-tokenizer Qwen/Qwen2.5-3B-Instruct

Exit code is 1 on any failure, so it can gate a job.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayur_data as AD


class StubTokenizer:
    """Minimal stand-in for a chat tokenizer.

    Mimics the two behaviours that matter: a chat template whose
    add_generation_prompt output is a strict prefix of the full rendering, and a
    tokenizer callable returning input_ids. Token counts are approximate --- one
    token per ~3.5 Latin characters, ~1.6 per Devanagari character, which is
    roughly how real BPE tokenizers treat these scripts and enough to make the
    length audit meaningful.
    """
    eos_token = "<|im_end|>"
    chat_template = "stub"
    pad_token = None

    def apply_chat_template(self, messages, tokenize=False,
                            add_generation_prompt=False):
        out = []
        for m in messages:
            out.append("<|im_start|>%s\n%s<|im_end|>\n" % (m["role"], m["content"]))
        s = "".join(out)
        if add_generation_prompt:
            s += "<|im_start|>assistant\n"
        return s

    def __call__(self, text, add_special_tokens=False):
        deva = len(re.findall(r"[ऀ-ॿ]", text))
        other = len(text) - deva
        n = int(deva / 1.6 + other / 3.5) + 1
        return {"input_ids": list(range(n))}


def check(cond, msg, failures):
    if not cond:
        failures.append(msg)
        print("   FAIL  %s" % msg)
    return cond


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--train_file", default="", help="explicit filename; needed "
                    "when the file is not called train.json/.jsonl")
    ap.add_argument("--eval_file", default="")
    ap.add_argument("--test_file", default="")
    ap.add_argument("--max_seq_length", type=int, default=768)
    ap.add_argument("--completion_style", default="letter",
                    choices=["letter", "letter_text"])
    ap.add_argument("--real-tokenizer", dest="real_tokenizer", default="",
                    help="HF model id; uses the real tokenizer instead of the stub")
    ap.add_argument("--plot", default="", help="write a token-length PNG here")
    ap.add_argument("--no-open-ended", dest="no_open_ended", action="store_true",
                    help="drop option-less rows instead of training them free-text")
    a = ap.parse_args()

    failures = []

    if a.real_tokenizer:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(a.real_tokenizer, trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        print("Using real tokenizer: %s" % a.real_tokenizer)
    else:
        tok = StubTokenizer()
        print("Using stub tokenizer (no network needed)")

    # ---------------- 1. files load --------------------------------------
    print("\n1. Loading splits")
    # Explicit filenames win. Real datasets rarely use the tidy default names ---
    # "train - Hybrid.jsonl" is a perfectly ordinary thing to have --- and silently
    # skipping the file because it is not called train.json is a useless failure.
    explicit = {"train": a.train_file, "validation": a.eval_file, "test": a.test_file}
    splits = {}
    for name in ("train", "validation", "test"):
        cands = []
        if explicit.get(name):
            cands.append(os.path.join(a.data_dir, explicit[name]))
        cands += [os.path.join(a.data_dir, "%s.json" % name),
                  os.path.join(a.data_dir, "%s.jsonl" % name)]
        p = next((c for c in cands if os.path.exists(c)), None)
        if p is None:
            print("   skip %s (not found)" % name)
            continue
        rows = AD.load_split(p)
        splits[name] = rows
        print("   %-11s %6d rows  %2d fields   <- %s"
              % (name, len(rows), len(rows[0]), os.path.basename(p)))
    # Stop here rather than continue. Every check below indexes splits["train"],
    # so carrying on turns one clear "file not found" into a KeyError traceback
    # that hides the actual problem.
    if not splits.get("train"):
        print("\n   FAIL  no train split found in %s" % a.data_dir)
        print("\n   What is actually in that folder:")
        if os.path.isdir(a.data_dir):
            found = sorted(os.listdir(a.data_dir))
            if found:
                for f in found[:30]:
                    full = os.path.join(a.data_dir, f)
                    kind = "dir " if os.path.isdir(full) else "file"
                    size = "" if os.path.isdir(full) else " %8.1f MB" % (os.path.getsize(full) / 1e6)
                    print("     %s  %s%s" % (kind, f, size))
                print("\n   This script wants train.json (or .jsonl) directly inside")
                print("   --data_dir. If your files sit in a subfolder, point")
                print("   --data_dir at that subfolder. If they are named")
                print("   differently, rename them or pass --train_file.")
            else:
                print("     (the folder is empty)")
        else:
            print("     that path does not exist at all.")
            parent = "/kaggle/input"
            if os.path.isdir(parent):
                print("\n   Datasets currently attached under %s:" % parent)
                for d in sorted(os.listdir(parent)):
                    print("     %s/%s" % (parent, d))
                    sub = os.path.join(parent, d)
                    if os.path.isdir(sub):
                        for f in sorted(os.listdir(sub))[:8]:
                            print("        %s" % f)
            else:
                print("     and /kaggle/input does not exist --- no dataset attached.")
        print("\nFAIL --- fix DATA_DIR and re-run.")
        sys.exit(1)

    # ---------------- 1b. which schema? ----------------------------------
    schema = AD.detect_schema(splits.get("train", []))
    print("\n   detected schema: %s" % schema)

    if schema == "chunk":
        # Raw treatise rows have no options and no answer key, so every QA check
        # below is meaningless on them. Run the chunk-specific checks instead.
        print("\n2. Chunk-task audit")
        ok = True
        for name, rows in splits.items():
            pairs, info = AD.prepare_any(rows, tok)
            print("   %-11s %5d chunks -> %5d pairs | skipped %d | %s"
                  % (name, len(rows), len(pairs), info.get("chunks_skipped", 0),
                     info.get("by_task")))
            check(len(pairs) > 0, "%s: no chunk tasks produced" % name, failures)
            check(info.get("chunks_skipped", 0) < 0.5 * max(len(rows), 1),
                  "%s: over half the chunks yielded nothing" % name, failures)
            if name == "train":
                empty = 0
                for pr in pairs[:2000]:
                    pl = len(tok(pr["prompt"], add_special_tokens=False)["input_ids"])
                    fl = len(tok(pr["prompt"] + pr["completion"],
                                 add_special_tokens=False)["input_ids"])
                    if fl - pl <= 0:
                        empty += 1
                print("   masking: %d of %d with an empty completion span"
                      % (empty, min(len(pairs), 2000)))
                check(empty == 0, "%d chunk pairs have no completion" % empty, failures)
                la = AD.token_length_audit(pairs, tok, a.max_seq_length)
                print("   lengths: p50 %d | p90 %d | p99 %d | over cap %.2f%%"
                      % (la["total_tokens_p50"], la["total_tokens_p90"],
                         la["total_tokens_p99"], la["pct_over_max_seq_length"]))
                for pr in pairs[:2]:
                    print("   --- sample ---")
                    print("   prompt tail: ...%s" % pr["prompt"][-150:].replace("\n", " | "))
                    print("   completion : %s" % pr["completion"][:110].replace("\n", " "))
        print("\n%s" % ("PASS --- chunk data layer is sound" if not failures
                        else "FAIL --- %d problem(s):" % len(failures)))
        for f in failures:
            print("  - %s" % f)
        sys.exit(0 if not failures else 1)

    # ---------------- 2. schema audit ------------------------------------
    print("\n2. Schema audit")
    for name, rows in splits.items():
        au = AD.audit_rows(rows)
        print("   %-11s types=%d langs=%s multi_answer=%d"
              % (name, len(au["by_type"]), au["by_language"], au["multi_answer_rows"]))
        print("               unusable: no options=%d, no answer key=%d"
              % (au["unusable_missing_options"], au["unusable_missing_answer_key"]))
        bad = au["unusable_missing_options"] + au["unusable_missing_answer_key"]
        check(bad < 0.20 * max(len(rows), 1),
              "%s: %d/%d rows unusable (>20%%)" % (name, bad, len(rows)), failures)
        pos = au["answer_position"]
        if pos:
            top = max(pos.values()) / max(sum(pos.values()), 1)
            print("               answer position: %s  (max share %.1f%%)"
                  % (pos, 100 * top))
            if top > 0.40:
                print("   WARN  one letter holds %.1f%% of answers --- a model can "
                      "score well by always picking it" % (100 * top))

    # ---------------- 3. formatting --------------------------------------
    print("\n3. Formatting to prompt/completion")
    pairs = {}
    for name, rows in splits.items():
        p, dropped, n_open = AD.prepare(rows, tok, a.completion_style,
                                        allow_open=not a.no_open_ended)
        pairs[name] = p
        print("   %-11s %6d formatted, %d dropped, %d open-ended"
              % (name, len(p), dropped, n_open))
        check(len(p) > 0, "%s: nothing formatted" % name, failures)
        check(dropped < 0.20 * max(len(rows), 1),
              "%s: dropped %d/%d (>20%%)" % (name, dropped, len(rows)), failures)

    # ---------------- 4. masking integrity -------------------------------
    print("\n4. Masking integrity (completion span must be non-empty)")
    tr = pairs.get("train", [])
    empty = 0
    for p in tr[:2000]:
        pl = len(tok(p["prompt"], add_special_tokens=False)["input_ids"])
        fl = len(tok(p["prompt"] + p["completion"],
                     add_special_tokens=False)["input_ids"])
        if fl - pl <= 0:
            empty += 1
    print("   checked %d rows, %d with an empty completion span" % (min(len(tr), 2000), empty))
    check(empty == 0, "%d rows have a zero-length completion span" % empty, failures)

    # ---------------- 5. answer correctness ------------------------------
    print("\n5. Completion content")
    bad_letter = 0
    multi_seen = 0
    for row in splits["train"][:5000]:
        opts = AD.options_of(row)
        keys = AD.answer_keys(row, opts)
        if not keys:
            continue
        if len(keys) > 1:
            multi_seen += 1
        pc = AD.format_example(row, tok, a.completion_style)
        if not pc["completion"]:
            continue
        # every key letter must appear in the completion
        if not all(k in pc["completion"] for k in keys):
            bad_letter += 1
    print("   multi-answer rows seen: %d | completions missing a key letter: %d"
          % (multi_seen, bad_letter))
    check(bad_letter == 0, "%d completions omit a correct-answer letter" % bad_letter,
          failures)

    # ---------------- 6. language routing --------------------------------
    print("\n6. Language routing")
    mism = 0
    for row in splits["train"][:5000]:
        lang = AD.infer_language(row)
        up = AD.build_user_prompt(row)
        if up is None:
            continue
        # Open-ended rows use their own instruction table, so check that one.
        if AD.is_open_ended(row):
            instr = AD.OPEN_INSTRUCTION[lang]
        else:
            instr = AD.INSTRUCTION[lang].get(row.get("question_type"),
                                             AD.INSTRUCTION[lang]["MCQ"])
        if instr not in up:
            mism += 1
    print("   prompts whose instruction language does not match the item: %d" % mism)
    check(mism == 0, "%d prompts have a mismatched instruction language" % mism,
          failures)

    # ---------------- 7. length audit ------------------------------------
    print("\n7. Token length audit")
    la = AD.token_length_audit(tr, tok, a.max_seq_length)
    print("   p50 %d | p90 %d | p99 %d | max %d"
          % (la["total_tokens_p50"], la["total_tokens_p90"],
             la["total_tokens_p99"], la["total_tokens_max"]))
    print("   completion tokens: mean %.2f, min %d"
          % (la["completion_tokens_mean"], la["completion_tokens_min"]))
    print("   over max_seq_length=%d: %d rows (%.2f%%)"
          % (a.max_seq_length, la["rows_over_max_seq_length"],
             la["pct_over_max_seq_length"]))
    check(la["completion_tokens_min"] > 0,
          "some completions tokenize to zero tokens", failures)
    if la["pct_over_max_seq_length"] > 5:
        print("   WARN  more than 5%% would be truncated; raise --max_seq_length "
              "to about %d" % la["total_tokens_p99"])

    # ---------------- 8. sample rendering --------------------------------
    print("\n8. Sample rendering (one per question type)")
    seen = set()
    for row in splits["train"]:
        t = row.get("question_type")
        if t in seen:
            continue
        pc = AD.format_example(row, tok, a.completion_style)
        if not pc["completion"]:
            continue
        seen.add(t)
        print("   --- %s [%s] ---" % (t, AD.infer_language(row)))
        print("   prompt tail : ...%s"
              % pc["prompt"][-160:].replace("\n", " | "))
        print("   completion  : %r" % pc["completion"][:80])
        if len(seen) >= 6:
            break

    # ---------------- 9. plotting path -----------------------------------
    if a.plot:
        print("\n9. Plot")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 5))
        plt.hist(la["all_token_lengths"], bins=50, color="tab:olive")
        plt.axvline(a.max_seq_length, color="tab:red", ls="--",
                    label="max_seq_length=%d" % a.max_seq_length)
        plt.axvline(la["total_tokens_p99"], color="tab:orange", ls=":",
                    label="p99=%d" % la["total_tokens_p99"])
        plt.xlabel("Tokens (prompt + completion)"); plt.ylabel("Rows")
        plt.title("Token length distribution"); plt.legend(); plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(a.plot, dpi=140)
        plt.close()
        print("   wrote %s" % a.plot)

    print("\n%s" % ("PASS --- data layer is sound" if not failures
                    else "FAIL --- %d problem(s):" % len(failures)))
    for f in failures:
        print("  - %s" % f)
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
