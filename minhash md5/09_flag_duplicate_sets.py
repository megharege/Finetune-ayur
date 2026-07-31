#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 9 --- Emit the duplicate sets found by MD5 and by MinHash, separately.
===========================================================================

Produces two files that can be inspected, compared, and later merged:

  md5_flagged.json      every question that shares an identical normalised stem
                        with at least one other question
  minhash_flagged.json  every question in a near-duplicate group at
                        Jaccard >= --threshold, found by MinHash + LSH

"Flagged" means "is a member of a duplicate group", not "would be deleted".
A group of 3 contributes all 3 rows; which one survives is a separate decision,
so each row carries:

    dup_method     "md5" | "minhash"
    dup_group_id   stable id, shared by every member of the group
    dup_group_size
    dup_is_survivor  True for the highest source_richness member (ties on
                     question_id), i.e. the one 01_dedup.py would have kept
    dup_jaccard_to_survivor   MinHash sets only --- exact Jaccard, not the estimate

The two sets are NOT disjoint, and by construction cannot be: an exact duplicate
has Jaccard 1.0, so everything MD5 finds MinHash also finds. Use
11_merge_flagged.py to combine them without double-counting.

Usage
    python 09_flag_duplicate_sets.py --in master_80k.jsonl --outdir out/09_flagged \\
        --report reports/12_flagged_sets.json [--cache /tmp/mh.npz] [--threshold 0.97]
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

_mh = import_module("08_minhash_compare") if os.path.exists(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "08_minhash_compare.py")) else None


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def dump(p, rows):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("[\n")
        fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
        fh.write("\n]\n")


def richness(r):
    try:
        return int(r.get("source_richness", 0) or 0)
    except (TypeError, ValueError):
        return 0


def survivor_index(group, rows):
    """The row 01_dedup.py would keep: highest richness, ties on question_id."""
    return sorted(group, key=lambda i: (-richness(rows[i]),
                                        str(rows[i].get("question_id", ""))))[0]


def emit(groups, rows, docs, method, jaccard_fn=None):
    out = []
    for gid, g in enumerate(sorted(groups, key=lambda x: min(x))):
        keep = survivor_index(g, rows)
        for i in g:
            r = dict(rows[i])
            r["dup_method"] = method
            r["dup_group_id"] = "%s-%05d" % (method, gid)
            r["dup_group_size"] = len(g)
            r["dup_is_survivor"] = (i == keep)
            if jaccard_fn is not None:
                r["dup_jaccard_to_survivor"] = (
                    1.0 if i == keep else round(jaccard_fn(docs[i], docs[keep]), 4))
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", default="12_flagged_sets.json")
    ap.add_argument("--threshold", type=float, default=0.97)
    ap.add_argument("--perm", type=int, default=128)
    ap.add_argument("--shingle", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260729)
    ap.add_argument("--cache", default="", help="MinHash signature .npz (reused if present)")
    a = ap.parse_args()

    if _mh is None:
        raise SystemExit("08_minhash_compare.py must sit beside this script")
    os.makedirs(a.outdir, exist_ok=True)

    rows = load(a.inp)
    docs = [_mh.normalise(r.get("question", "")) for r in rows]
    n = len(rows)
    print("corpus            : %d questions" % n)

    # ---------------- MD5: identical normalised stem --------------------
    buckets = defaultdict(list)
    for i, d in enumerate(docs):
        buckets[hashlib.md5(d.encode()).hexdigest()].append(i)
    md5_groups = [v for v in buckets.values() if len(v) > 1]
    md5_rows = emit(md5_groups, rows, docs, "md5")
    print("MD5     groups %4d  questions %5d" % (len(md5_groups), len(md5_rows)))

    # ---------------- MinHash: near-duplicate groups --------------------
    sig, done = _mh.signature_matrix(docs, a.perm, a.seed, a.shingle, a.cache, 0.0)
    if done < n:
        raise SystemExit("signature generation incomplete --- re-run to resume")
    b, r = _mh.choose_bands(a.perm, a.threshold)
    confirmed = [(i, j) for i, j in _mh.lsh_candidates(sig, b, r)
                 if _mh.true_jaccard(docs[i], docs[j], a.shingle) >= a.threshold]

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in confirmed:
        x, y = find(i), find(j)
        if x != y:
            parent[max(x, y)] = min(x, y)
    comp = defaultdict(list)
    for i in range(n):
        comp[find(i)].append(i)
    mh_groups = [v for v in comp.values() if len(v) > 1]
    mh_rows = emit(mh_groups, rows, docs, "minhash",
                   lambda x, y: _mh.true_jaccard(x, y, a.shingle))
    print("MinHash groups %4d  questions %5d  (from %d confirmed pairs)"
          % (len(mh_groups), len(mh_rows), len(confirmed)))

    dump(os.path.join(a.outdir, "md5_flagged.json"), md5_rows)
    dump(os.path.join(a.outdir, "minhash_flagged.json"), mh_rows)

    md5_ids = {r["question_id"] for r in md5_rows}
    mh_ids = {r["question_id"] for r in mh_rows}
    rep = {
        "corpus": n, "threshold": a.threshold,
        "md5": {"groups": len(md5_groups), "questions": len(md5_rows),
                "would_remove": len(md5_rows) - len(md5_groups),
                "file": "md5_flagged.json"},
        "minhash": {"groups": len(mh_groups), "questions": len(mh_rows),
                    "confirmed_pairs": len(confirmed),
                    "would_remove": len(mh_rows) - len(mh_groups),
                    "params": {"permutations": a.perm, "bands": b, "rows_per_band": r,
                               "shingle": a.shingle},
                    "file": "minhash_flagged.json"},
        "set_relationship": {
            "in_both": len(md5_ids & mh_ids),
            "md5_only": len(md5_ids - mh_ids),
            "minhash_only": len(mh_ids - md5_ids),
            "union": len(md5_ids | mh_ids),
            "md5_is_subset_of_minhash": md5_ids <= mh_ids,
        },
    }
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\nin both %d | md5 only %d | minhash only %d | union %d"
          % (len(md5_ids & mh_ids), len(md5_ids - mh_ids),
             len(mh_ids - md5_ids), len(md5_ids | mh_ids)))
    print("MD5 set is a subset of the MinHash set: %s" % (md5_ids <= mh_ids))


if __name__ == "__main__":
    main()
