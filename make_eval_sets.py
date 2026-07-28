#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Carve four 25-question evaluation sets out of the AyurShloka-QA validation split.

Sets are drawn from `validation.jsonl` only, so they stay disjoint from `train.jsonl`
and can be used to score a base model *before* you fine-tune on the rest.

Output schema (matches what ayur_benchmark.py expects):
    id, type, instruction, input, output, output_text, context,
    source, source_book, language, difficulty, subject_domain,
    question_subtype, chunk_id
`input` is a JSON *string* mapping option letters to option text, e.g.
    {"A": "...", "B": "...", "C": "...", "D": "..."}
"""
import json
import os
import random
from collections import defaultdict

SEED = 20260728
N_PER_TYPE = 25

SRC = "/sessions/loving-trusting-wright/mnt/outputs/ayur_question_set/validation.jsonl"
OUT_DIR = "/sessions/loving-trusting-wright/mnt/outputs/ayur_eval_sets"

# our question_type  ->  benchmark task-type file name
TYPE_MAP = {
    "Assertion or Reasoning": "assertion",
    "MCQ": "mcq",
    "Fill in the blanks": "fill_blanks",
    "Match the column": "match_column",
}


def balanced_sample(rows, n, rng):
    """Round-robin over (book, subtype) buckets so no book or subtype dominates."""
    buckets = defaultdict(list)
    for r in rows:
        buckets[(r["source_book"], r["question_subtype"])].append(r)
    for k in buckets:
        rng.shuffle(buckets[k])

    keys = sorted(buckets)
    rng.shuffle(keys)
    picked, i = [], 0
    while len(picked) < n and any(buckets[k] for k in keys):
        k = keys[i % len(keys)]
        if buckets[k]:
            picked.append(buckets[k].pop())
        i += 1
    return picked[:n]


def to_row(r, task_type):
    options = {L.upper(): r["option_" + L] for L in "abcd" if r.get("option_" + L)}
    return {
        "id": r["question_id"],
        "type": task_type,
        "instruction": r["question"],
        "input": json.dumps(options, ensure_ascii=False) if options else "",
        "output": r["correct_answer"],          # the letter: A / B / C / D
        "output_text": r["answer_text"],        # the full text of the keyed option
        "context": r.get("context", ""),
        "source": r.get("citation", ""),
        "source_book": r["source_book"],
        "language": "en",
        "difficulty": r["difficulty"],
        "subject_domain": r["subject_domain"],
        "question_subtype": r["question_subtype"],
        "chunk_id": r["chunk_id"],
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]

    manifest = {}
    for qtype, task_type in TYPE_MAP.items():
        pool = [r for r in rows if r["question_type"] == qtype and r["correct_answer"]]
        rng = random.Random(SEED + sum(ord(c) for c in task_type))
        picked = balanced_sample(pool, N_PER_TYPE, rng)
        rng.shuffle(picked)

        out = os.path.join(OUT_DIR, "ayur_%s_25.jsonl" % task_type)
        with open(out, "w", encoding="utf-8") as fh:
            for r in picked:
                fh.write(json.dumps(to_row(r, task_type), ensure_ascii=False) + "\n")

        books = sorted({r["source_book"] for r in picked})
        subs = sorted({r["question_subtype"] for r in picked})
        manifest[task_type] = {
            "file": os.path.basename(out),
            "n": len(picked),
            "pool_size": len(pool),
            "books": books,
            "subtypes": subs,
            "answer_letters": {L: sum(1 for r in picked if r["correct_answer"] == L)
                               for L in "ABCD"},
        }
        print("%-14s n=%d  books=%d  subtypes=%s" % (task_type, len(picked), len(books), subs))

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
