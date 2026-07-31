#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q4 --- Build train / validation / test.
=======================================

TEST IS BUILT TO MIRROR AYURPARAM, NOT BY PER-QUESTION SIMILARITY.

The original plan was "test contains only questions similar to AyurParam". That
rule cannot be satisfied: across three independent measures --- MD5, MinHash and
cosine --- nothing in a corpus generated from these eight treatises resembles the
benchmark, whose questions come from Indian exam papers with no common ancestor.
The maximum cosine observed on the v2 corpus was 0.7401 against a 0.80 threshold,
and MD5 and MinHash both returned zero. Enforcing the rule literally produces an
empty test set.

So test is built to resemble the benchmark where it actually matters --- its
composition. Questions are selected so that the test split matches
BhashaBench-Ayur's own distribution over:

    subject_domain   (16 domains, led by Kayachikitsa and Dravyaguna)
    question_type    (98.4% MCQ)
    language         (62.5% en / 37.5% hi)

A test score on that split predicts an AyurParam score far better than a random
split does, which is the actual objective. Per-question similarity would only
have measured contamination, and there is none.

RULE 1 --- anything flagged bba_similar goes to test unconditionally, before the
mirroring runs. Currently empty, but enforced so the guarantee survives a
benchmark update.

RULE 2 --- splits are assigned at fact_id granularity. A fact renders into
several questions; splitting one across train and test is leakage dressed as
generalisation.

THE MIRROR HAS A CEILING, AND IT IS RULE 2.
Facts move whole, and a fact's questions span several formats. Selecting a fact
because it is mostly MCQ still drags its fill-in-the-blank and assertion
siblings along. So the achieved test mix cannot match the benchmark exactly ---
the benchmark is 98.4% MCQ, and no fact-level selection from a corpus with mixed
facts will reach that. The report prints the achieved fit per dimension with the
delta, so the gap is visible rather than assumed away. Raising the MCQ share in
generation (TYPE_MIX in the notebook) lifts the ceiling; going to row-level
selection would reach the target exactly and reintroduce the leak, which is a bad
trade.

RULE 3 --- validation lands on exactly --val-rows. Facts move whole, so the count
would normally land near the target; the last fact is chosen to be exactly the
size of the remaining gap.

Usage
    python Q4_build_splits.py --in out/Q3_annotated.jsonl \\
        --bba data/bba_en.parquet data/bba_hi.parquet \\
        --outdir final --val-rows 1000 --test-frac 0.08 --report reports/Q4_splits.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter, defaultdict


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def dump(p, rows):
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("[\n")
        fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
        fh.write("\n]\n")


def load_bba(paths):
    import pandas as pd
    frames = []
    for p in paths:
        d = (pd.read_parquet(p) if p.endswith(".parquet")
             else pd.read_csv(p) if p.endswith(".csv")
             else pd.read_json(p, lines=True))
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def profile(rows):
    return {"rows": len(rows), "facts": len({r.get("fact_id") for r in rows}),
            "by_type": dict(Counter(r.get("question_type") for r in rows).most_common()),
            "by_language": dict(Counter(r.get("language") for r in rows)),
            "by_domain": dict(Counter(r.get("subject_domain") for r in rows).most_common()),
            "by_book": dict(Counter(r.get("source_book") for r in rows).most_common()),
            "max_bba_cosine": round(max((r.get("bba_max_cosine", 0.0) for r in rows),
                                        default=0.0), 4)}


def share(counter):
    t = sum(counter.values()) or 1
    return {k: v / t for k, v in counter.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--bba", nargs="+", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", default="Q4_splits.json")
    ap.add_argument("--val-rows", type=int, default=1000)
    ap.add_argument("--test-frac", type=float, default=0.08)
    ap.add_argument("--seed", type=int, default=20260730)
    a = ap.parse_args()

    rng = random.Random(a.seed)
    rows = load(a.inp)
    print("input             : %d rows / %d facts"
          % (len(rows), len({r["fact_id"] for r in rows})))

    bba = load_bba(a.bba)
    tgt_domain = share(Counter(bba["subject_domain"])) if "subject_domain" in bba else {}
    tgt_type = share(Counter(bba["question_type"])) if "question_type" in bba else {}
    tgt_lang = share(Counter(bba["language"])) if "language" in bba else {}
    print("benchmark mix     : %d questions" % len(bba))
    print("  top domains     : %s"
          % {k: "%.1f%%" % (100 * v) for k, v in
             sorted(tgt_domain.items(), key=lambda x: -x[1])[:4]})
    print("  types           : %s"
          % {k: "%.1f%%" % (100 * v) for k, v in
             sorted(tgt_type.items(), key=lambda x: -x[1])})
    print("  languages       : %s"
          % {k: "%.1f%%" % (100 * v) for k, v in tgt_lang.items()})

    by_fact = defaultdict(list)
    for r in rows:
        by_fact[r["fact_id"]].append(r)

    # ---- RULE 1: forced test ------------------------------------------
    forced_facts = {r["fact_id"] for r in rows if r.get("bba_similar")}
    forced_rows = sum(len(by_fact[f]) for f in forced_facts)
    print("\nforced to test by similarity: %d rows / %d facts"
          % (forced_rows, len(forced_facts)))

    # ---- RULE 2 + mirroring: pick test facts --------------------------
    # A fact's "cell" is (domain, type, language) of its most common member.
    def cell(fid):
        c = Counter((r.get("subject_domain"), r.get("question_type"),
                     r.get("language")) for r in by_fact[fid])
        return c.most_common(1)[0][0]

    avail = defaultdict(list)
    for fid in by_fact:
        if fid not in forced_facts:
            avail[cell(fid)].append(fid)
    for v in avail.values():
        rng.shuffle(v)

    n_test = int(round(len(rows) * a.test_frac))
    print("test target       : %d rows" % n_test)

    # desired rows per cell = product of the three marginal shares, renormalised
    # over cells we can actually fill
    want = {}
    for c in avail:
        dom, typ, lang = c
        w = (tgt_domain.get(dom, 0.001) * tgt_type.get(typ, 0.001)
             * tgt_lang.get(lang, 0.001))
        want[c] = w
    tot_w = sum(want.values()) or 1
    want = {c: w / tot_w for c, w in want.items()}

    test_f, got = set(), 0
    order = sorted(avail, key=lambda c: -want[c])
    for c in order:
        quota = want[c] * n_test
        take = 0
        for fid in avail[c]:
            if take >= quota or got >= n_test:
                break
            test_f.add(fid)
            take += len(by_fact[fid])
            got += len(by_fact[fid])
    # top up from the largest cells if rounding left us short
    if got < n_test:
        for c in order:
            for fid in avail[c]:
                if got >= n_test:
                    break
                if fid not in test_f:
                    test_f.add(fid)
                    got += len(by_fact[fid])
            if got >= n_test:
                break
    test_f |= forced_facts
    print("test selected     : %d rows / %d facts"
          % (sum(len(by_fact[f]) for f in test_f), len(test_f)))

    # ---- RULE 3: validation, exactly val-rows --------------------------
    pool = sorted(set(by_fact) - test_f)
    rng.shuffle(pool)
    val_f, vgot = set(), 0
    for fid in pool:
        k = len(by_fact[fid])
        if vgot + k <= a.val_rows - 1:
            val_f.add(fid)
            vgot += k
    gap = a.val_rows - vgot
    if gap:
        exact = [f for f in pool if f not in val_f and len(by_fact[f]) == gap]
        if not exact:
            raise SystemExit("cannot hit %d exactly: need a fact of size %d. "
                             "Nearest is %d." % (a.val_rows, gap, vgot))
        val_f.add(exact[0])
        vgot += gap
    assert vgot == a.val_rows

    train_f = set(by_fact) - test_f - val_f

    def collect(fs):
        out = []
        for f in fs:
            out.extend(by_fact[f])
        out.sort(key=lambda r: str(r.get("question_id")))
        return out

    train, val, test = collect(train_f), collect(val_f), collect(test_f)
    assert not (train_f & val_f) and not (train_f & test_f) and not (val_f & test_f)
    assert len(train) + len(val) + len(test) == len(rows)
    assert len(val) == a.val_rows

    dump(os.path.join(a.outdir, "train.json"), train)
    dump(os.path.join(a.outdir, "validation.json"), val)
    dump(os.path.join(a.outdir, "test.json"), test)

    # ---- how close did the mirror get? --------------------------------
    def fit(rows_, target, key):
        got_ = share(Counter(r.get(key) for r in rows_))
        keys = set(got_) | set(target)
        return {k: {"benchmark": round(100 * target.get(k, 0), 2),
                    "test": round(100 * got_.get(k, 0), 2),
                    "delta": round(100 * (got_.get(k, 0) - target.get(k, 0)), 2)}
                for k in sorted(keys, key=lambda x: -target.get(x, 0))}

    rep = {
        "seed": a.seed, "input_rows": len(rows),
        "test_strategy": "distribution mirror of BhashaBench-Ayur "
                         "(domain x type x language); per-question similarity "
                         "yields an empty set on this corpus",
        "forced_to_test_by_similarity": forced_rows,
        "splits": {"train": profile(train), "validation": profile(val),
                   "test": profile(test)},
        "mirror_fit": {"question_type": fit(test, tgt_type, "question_type"),
                       "language": fit(test, tgt_lang, "language"),
                       "subject_domain": fit(test, tgt_domain, "subject_domain")},
        "fact_overlaps": {"train_val": len(train_f & val_f),
                          "train_test": len(train_f & test_f),
                          "val_test": len(val_f & test_f)},
        "next_step": "Q5_check_leakage.py --dir <outdir> --repair",
    }
    d = os.path.dirname(a.report)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\ntrain %6d rows / %6d facts" % (len(train), len(train_f)))
    print("val   %6d rows / %6d facts   (exact target %d)"
          % (len(val), len(val_f), a.val_rows))
    print("test  %6d rows / %6d facts" % (len(test), len(test_f)))
    print("fact overlaps (0,0,0): %d %d %d"
          % (len(train_f & val_f), len(train_f & test_f), len(val_f & test_f)))
    print("\nmirror fit, question_type:")
    for k, v in list(rep["mirror_fit"]["question_type"].items())[:6]:
        print("   %-26s benchmark %5.1f%%  test %5.1f%%  delta %+5.1f"
              % (k, v["benchmark"], v["test"], v["delta"]))
    print("mirror fit, language:")
    for k, v in rep["mirror_fit"]["language"].items():
        print("   %-26s benchmark %5.1f%%  test %5.1f%%  delta %+5.1f"
              % (k, v["benchmark"], v["test"], v["delta"]))


if __name__ == "__main__":
    main()
