#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q7 --- Final MD5 and MinHash duplicate report over the delivered splits.
========================================================================

Runs both methods twice: once WITHIN the delivered corpus (are there duplicates
left?) and once ACROSS the corpus/benchmark boundary (did anything leak in from
AyurParam?).

WHAT COUNTS AS A DUPLICATE, AND WHY IT IS NOT JUST SIMILARITY
--------------------------------------------------------------
In a templated corpus, high similarity is not duplication. Two questions about
verse 4 and verse 5 of the same chapter score ~0.996 cosine while being entirely
different questions with different answers. On the v2 corpus 98.7% of pairs above
0.97 had different gold answers, and deleting on similarity alone would have
destroyed thousands of legitimate items.

So this script reports both numbers and only treats the second as a failure:

    similar_pairs      near-identical wording       (expected, benign)
    duplicate_pairs    near-identical AND same gold answer   (a real problem)

MD5 needs no such distinction --- identical text with a different answer is a
contradiction, and is reported separately as `conflicting_stems`, which is a
data-quality bug worth fixing rather than a duplicate worth deleting.

Usage
    python Q7_md5_minhash.py --dir final --bba data/bba_en.parquet data/bba_hi.parquet \\
        --report reports/Q7_md5_minhash.json [--cache /tmp/q7.npz]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module

_mh = import_module("_minhash")

SPLITS = ("train", "validation", "test")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def ans(r):
    return str(r.get("answer_text", "")).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--bba", nargs="*", default=[])
    ap.add_argument("--report", default="Q7_md5_minhash.json")
    ap.add_argument("--jaccard", type=float, default=0.97)
    ap.add_argument("--perm", type=int, default=128)
    ap.add_argument("--shingle", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260730)
    ap.add_argument("--cache", default="")
    ap.add_argument("--bba-cache", default="")
    a = ap.parse_args()

    rows, origin = [], []
    for s in SPLITS:
        p = os.path.join(a.dir, "%s.json" % s)
        if os.path.exists(p):
            r = load(p)
            rows += r
            origin += [s] * len(r)
            print("%-11s %6d rows" % (s, len(r)))
    docs = [_mh.normalise(r.get("question", "")) for r in rows]
    n = len(rows)
    print("total       %6d rows\n" % n)

    rep = {"rows": n, "by_split": {s: origin.count(s) for s in SPLITS}}

    # ---------- MD5 within ---------------------------------------------
    g = defaultdict(list)
    for i, d in enumerate(docs):
        g[hashlib.md5(d.encode()).hexdigest()].append(i)
    md5_groups = [v for v in g.values() if len(v) > 1]
    md5_dupes = sum(len(v) - 1 for v in md5_groups)
    conflicting = sum(1 for v in md5_groups if len({ans(rows[i]) for i in v}) > 1)
    print("MD5 within corpus")
    print("   duplicate rows            : %d" % md5_dupes)
    print("   of which conflicting gold : %d groups" % conflicting)
    rep["md5_within"] = {"groups": len(md5_groups), "duplicate_rows": md5_dupes,
                         "conflicting_answer_groups": conflicting}

    # ---------- MinHash within -----------------------------------------
    sig, done = _mh.signature_matrix(docs, a.perm, a.seed, a.shingle, a.cache, 0.0)
    if done < n:
        raise SystemExit("signatures incomplete --- re-run to resume")
    b, r = _mh.choose_bands(a.perm, a.jaccard)
    pairs = [(i, j) for i, j in _mh.lsh_candidates(sig, b, r)
             if _mh.true_jaccard(docs[i], docs[j], a.shingle) >= a.jaccard]
    dupe_pairs = [(i, j) for i, j in pairs if ans(rows[i]) == ans(rows[j])]
    cross = [(i, j) for i, j in pairs if origin[i] != origin[j]]
    # Cross-split pairs split the same way: sharing a gold answer means the model
    # can memorise the answer in train and recite it at eval, which is leakage.
    # Sharing only a template means it saw the question shape, not the answer ---
    # worth reporting, not worth failing on.
    cross_leak = [(i, j) for i, j in cross if ans(rows[i]) == ans(rows[j])]
    print("\nMinHash within corpus  (Jaccard >= %.2f)" % a.jaccard)
    print("   similar pairs             : %d" % len(pairs))
    print("   of which same gold answer : %d   <- real duplicates" % len(dupe_pairs))
    print("   cross-split similar       : %d   (template overlap)" % len(cross))
    print("   cross-split AND same gold : %d   <- real leakage" % len(cross_leak))
    rep["minhash_within"] = {
        "threshold": a.jaccard, "bands": b, "rows_per_band": r,
        "similar_pairs": len(pairs), "duplicate_pairs": len(dupe_pairs),
        "cross_split_similar_pairs": len(cross),
        "cross_split_leaking_pairs": len(cross_leak),
        "note": "similarity alone is not duplication in a templated corpus. A pair "
                "must share its gold answer to be a duplicate, and a cross-split "
                "pair must share its gold answer to be leakage --- otherwise the "
                "model saw the question shape, not the answer."}

    # ---------- across the benchmark boundary ---------------------------
    if a.bba:
        import pandas as pd
        frames = [pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p)
                  for p in a.bba]
        bba = pd.concat(frames, ignore_index=True)
        bq = [_mh.normalise(q) for q in bba["question"].tolist()]
        bset = {hashlib.md5(q.encode()).hexdigest() for q in bq}
        md5_cross = sum(1 for d in docs if hashlib.md5(d.encode()).hexdigest() in bset)

        sig_b, db = _mh.signature_matrix(bq, a.perm, a.seed, a.shingle, a.bba_cache, 0.0)
        if db < len(bq):
            raise SystemExit("BBA signatures incomplete --- re-run")
        both = np.vstack([sig, sig_b])
        mh_cross, best = 0, 0.0
        for band in range(b):
            bk = defaultdict(list)
            ch = both[:, band * r:(band + 1) * r]
            for i in range(both.shape[0]):
                bk[ch[i].tobytes()].append(i)
            for idxs in bk.values():
                L = [i for i in idxs if i < n]
                R = [i - n for i in idxs if i >= n]
                for x in L:
                    for y in R:
                        s_ = _mh.true_jaccard(docs[x], bq[y], a.shingle)
                        best = max(best, s_)
                        if s_ >= a.jaccard:
                            mh_cross += 1
        cos = [r_.get("bba_max_cosine", 0.0) for r_ in rows]
        print("\nAcross the benchmark boundary")
        print("   MD5 exact matches         : %d" % md5_cross)
        print("   MinHash matches           : %d  (max Jaccard seen %.4f)"
              % (mh_cross, best))
        print("   max stored cosine         : %.4f" % (max(cos) if cos else 0.0))
        rep["across_benchmark"] = {
            "bba_questions": len(bq), "md5_matches": md5_cross,
            "minhash_matches": mh_cross, "max_jaccard_seen": round(best, 4),
            "max_stored_cosine": round(max(cos), 4) if cos else None}

    verdict = "CLEAN" if (md5_dupes == 0 and len(dupe_pairs) == 0
                          and len(cross_leak) == 0) else "ISSUES"
    rep["verdict"] = verdict
    d = os.path.dirname(a.report)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n%s | report -> %s" % (verdict, a.report))
    sys.exit(0 if verdict == "CLEAN" else 1)


if __name__ == "__main__":
    main()
