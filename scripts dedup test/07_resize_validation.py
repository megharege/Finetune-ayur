1#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 7 --- Shrink validation to a target row count, return the rest to train.
=============================================================================

A 4,954-row validation split is larger than early stopping needs. This moves
most of it into train and keeps a small, representative held-out set.

TWO INVARIANTS, both load-bearing:

  1. FACTS MOVE WHOLE. Selection is at ``fact_id`` granularity, never row.
     A fact renders into ~2.3 questions; if half stay in validation and half
     go to train, the model has seen the answer under a different question
     shape and validation loss stops meaning anything. So the target row count
     is approximate --- facts are added until the target is reached, and the
     result lands near it rather than exactly on it.

  2. THE MIX IS PRESERVED. Facts are drawn stratum by stratum over
     (question_type x difficulty_bba), proportional to the stratum's share of
     the current validation split, so the small validation set has the same
     format and difficulty profile as the large one it replaces.

TEST IS NOT TOUCHED --- not read for selection, not rewritten.

Moving rows into train can create fresh near-duplicate leakage against the
evaluation splits, so 05_check_leakage.py MUST be run afterwards. Because the
eval splits are now fixed sizes the caller wants to keep, repair should drop
from the train side (05's --repair-side train).

Usage
    python 07_resize_validation.py --train train.json --val validation.json \
        --target 1000 --outdir out/07_resized --report 07_resize_report.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
from collections import Counter, defaultdict


def load(path):
    """Read .json (array) or .jsonl (one object per line)."""
    with open(path, encoding="utf-8") as fh:
        if path.endswith(".jsonl"):
            return [json.loads(l) for l in fh if l.strip()]
        return json.load(fh)


def dump(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        if path.endswith(".jsonl"):
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            fh.write("[\n")
            fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
            fh.write("\n]\n")


def profile(rows):
    return {
        "rows": len(rows),
        "facts": len({r.get("fact_id") for r in rows}),
        "by_type": dict(Counter(r.get("question_type") for r in rows).most_common()),
        "by_difficulty_bba": dict(Counter(r.get("difficulty_bba") for r in rows)),
        "by_book": dict(Counter(r.get("source_book") for r in rows).most_common()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--target", type=int, default=1000,
                    help="target validation row count (approximate --- facts move whole)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", default="07_resize_report.json")
    ap.add_argument("--seed", type=int, default=20260729)
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    train, val = load(a.train), load(a.val)
    print("train %6d rows | validation %6d rows" % (len(train), len(val)))

    # ---- group validation rows by fact --------------------------------
    by_fact = defaultdict(list)
    for r in val:
        by_fact[r["fact_id"]].append(r)

    def stratum(fid):
        c = Counter((r.get("question_type"), r.get("difficulty_bba", "Medium"))
                    for r in by_fact[fid])
        return c.most_common(1)[0][0]

    strata = defaultdict(list)
    for fid in by_fact:
        strata[stratum(fid)].append(fid)

    # ---- how many rows each stratum should contribute -----------------
    strat_rows = {s: sum(len(by_fact[f]) for f in fids) for s, fids in strata.items()}
    total_rows = sum(strat_rows.values())

    rng = random.Random(a.seed)
    keep_facts = set()
    kept_rows = 0

    # proportional pass: each stratum gives its fair share of the target
    for s in sorted(strata, key=lambda k: (str(k[0]), str(k[1]))):
        fids = sorted(strata[s])
        rng.shuffle(fids)
        quota = a.target * strat_rows[s] / total_rows
        got = 0
        for f in fids:
            if got >= quota:
                break
            keep_facts.add(f)
            got += len(by_fact[f])
        kept_rows += got

    # top-up pass: rounding leaves us slightly short of the target
    if kept_rows < a.target:
        spare = sorted(set(by_fact) - keep_facts)
        rng.shuffle(spare)
        for f in spare:
            if kept_rows >= a.target:
                break
            keep_facts.add(f)
            kept_rows += len(by_fact[f])

    new_val, moved = [], []
    for fid, rows in by_fact.items():
        (new_val if fid in keep_facts else moved).extend(rows)

    new_train = train + moved
    for lst in (new_train, new_val):
        lst.sort(key=lambda r: str(r.get("question_id")))

    # ---- invariants ---------------------------------------------------
    tf = {r["fact_id"] for r in new_train}
    vf = {r["fact_id"] for r in new_val}
    assert not (tf & vf), "a fact ended up in both train and validation"
    assert len(new_train) + len(new_val) == len(train) + len(val), "rows lost"

    dump(os.path.join(a.outdir, "train.json"), new_train)
    dump(os.path.join(a.outdir, "validation.json"), new_val)

    rep = {
        "seed": a.seed, "target": a.target,
        "before": {"train": profile(train), "validation": profile(val)},
        "after": {"train": profile(new_train), "validation": profile(new_val)},
        "moved_to_train": {"rows": len(moved), "facts": len(set(by_fact) - keep_facts)},
        "fact_overlap_train_val": len(tf & vf),
        "note": "test not read or modified; run 05_check_leakage.py next",
    }
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("moved  %6d rows / %d facts into train" % (len(moved), len(set(by_fact) - keep_facts)))
    print("train  %6d rows / %6d facts" % (len(new_train), len(tf)))
    print("val    %6d rows / %6d facts" % (len(new_val), len(vf)))
    print("fact overlap train/val: %d (must be 0)" % len(tf & vf))


if __name__ == "__main__":
    main()
