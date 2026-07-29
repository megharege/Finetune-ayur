#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 4 --- Build train / validation / test.
===========================================

Two rules govern the split.

RULE 1 --- nothing resembling BhashaBench-Ayur may enter TRAIN.
Step 2 assigned every row a ``split_assignment``. Rows marked
``test_contaminated`` are forced into TEST regardless of anything else. (On the
current corpus that set is empty --- max cosine against BBA was 0.740, below any
sane threshold --- but the rule is enforced unconditionally so it still holds if
the corpus or the benchmark changes.)

RULE 2 --- no fact may straddle a split.
Splitting by row would put an MCQ and a cloze built from the *same* underlying
fact on both sides, which is leakage: the model would have memorised the answer
under a different question shape. Splits are therefore assigned at ``fact_id``
granularity, and every rendering of a fact travels with it.

Stratification is over (question_type x difficulty_bba), applied to facts rather
than rows, so each split carries the same format and difficulty mix.

A second training file is also written. Our corpus is 26% fill-in-the-blank and
23% MCQ, whereas BhashaBench-Ayur is 98.4% MCQ --- so training on our natural
distribution spends most of its capacity on a format the benchmark barely tests.
``train_bba_aligned.jsonl`` upsamples MCQ toward the benchmark's mix while
keeping the other formats present. Use it when the objective is the leaderboard;
use ``train.jsonl`` when the objective is a generally capable model.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--test-frac", type=float, default=0.08)
    ap.add_argument("--val-frac", type=float, default=0.07)
    ap.add_argument("--seed", type=int, default=20260729)
    ap.add_argument("--mcq-target", type=float, default=0.55,
                    help="MCQ share in train_bba_aligned.jsonl")
    a = ap.parse_args()

    import os
    os.makedirs(a.outdir, exist_ok=True)
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    print("loaded %d rows" % len(rows))

    # ---- rule 1: forced-test rows -------------------------------------
    forced = [r for r in rows if r.get("split_assignment") == "test_contaminated"]
    forced_facts = {r["fact_id"] for r in forced}
    print("forced into TEST by BBA similarity: %d rows / %d facts"
          % (len(forced), len(forced_facts)))

    # ---- group rows by fact ------------------------------------------
    by_fact = defaultdict(list)
    for r in rows:
        by_fact[r["fact_id"]].append(r)

    # stratum of a fact = its most common (type, difficulty) pair
    def stratum(fid):
        c = Counter((r.get("question_type"), r.get("difficulty_bba", "Medium"))
                    for r in by_fact[fid])
        return c.most_common(1)[0][0]

    strata = defaultdict(list)
    for fid in by_fact:
        if fid not in forced_facts:
            strata[stratum(fid)].append(fid)

    rng = random.Random(a.seed)
    test_f, val_f, train_f = set(forced_facts), set(), set()
    for s, fids in strata.items():
        fids = sorted(fids)
        rng.shuffle(fids)
        n = len(fids)
        n_test = int(round(n * a.test_frac))
        n_val = int(round(n * a.val_frac))
        test_f.update(fids[:n_test])
        val_f.update(fids[n_test:n_test + n_val])
        train_f.update(fids[n_test + n_val:])

    def collect(fs):
        out = []
        for f in fs:
            out.extend(by_fact.get(f, []))
        out.sort(key=lambda r: str(r.get("question_id")))
        return out

    train, val, test = collect(train_f), collect(val_f), collect(test_f)

    # ---- BBA-aligned training mix -------------------------------------
    mcq = [r for r in train if r.get("question_type") == "MCQ"]
    rest = [r for r in train if r.get("question_type") != "MCQ"]
    # keep every MCQ, then take as many non-MCQ as the target share allows
    keep_rest = int(len(mcq) * (1 - a.mcq_target) / max(a.mcq_target, 1e-9))
    rng.shuffle(rest)
    aligned = mcq + rest[:keep_rest]
    rng.shuffle(aligned)

    def dump(name, data):
        p = os.path.join(a.outdir, name)
        with open(p, "w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p

    dump("train.jsonl", train)
    dump("validation.jsonl", val)
    dump("test.jsonl", test)
    dump("train_bba_aligned.jsonl", aligned)
    dump("test_bba_contaminated.jsonl", forced)

    def prof(d):
        return {"rows": len(d), "facts": len({r["fact_id"] for r in d}),
                "by_type": dict(Counter(r.get("question_type") for r in d)),
                "by_difficulty_bba": dict(Counter(r.get("difficulty_bba") for r in d)),
                "by_book": dict(Counter(r.get("source_book") for r in d))}

    rep = {"seed": a.seed, "input_rows": len(rows),
           "rule_1_forced_test_rows": len(forced),
           "train": prof(train), "validation": prof(val), "test": prof(test),
           "train_bba_aligned": prof(aligned),
           "fact_overlap_train_val": len(train_f & val_f),
           "fact_overlap_train_test": len(train_f & test_f),
           "fact_overlap_val_test": len(val_f & test_f)}
    json.dump(rep, open(os.path.join(a.outdir, "04_split_report.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)

    print("train %6d rows / %6d facts" % (len(train), len(train_f)))
    print("val   %6d rows / %6d facts" % (len(val), len(val_f)))
    print("test  %6d rows / %6d facts" % (len(test), len(test_f)))
    print("train_bba_aligned %6d rows (MCQ share %.1f%%)"
          % (len(aligned), 100.0 * len(mcq) / max(len(aligned), 1)))
    print("fact overlaps (must all be 0): tr/val=%d tr/te=%d val/te=%d"
          % (rep["fact_overlap_train_val"], rep["fact_overlap_train_test"],
             rep["fact_overlap_val_test"]))


if __name__ == "__main__":
    main()
