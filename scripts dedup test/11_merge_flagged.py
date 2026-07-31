#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 11 --- Merge the MD5 and MinHash flagged sets, then optionally fold into test.
===================================================================================

Deduplicates the union of the two flagged sets on ``question_id``, keeping the
richer annotation when a question appears in both (MD5 rows carry no
``dup_jaccard_to_survivor``, MinHash rows do), and records provenance:

    dup_found_by   "md5" | "minhash" | "both"

MERGING IS NOT THE HARD PART. Since every exact duplicate is also a Jaccard-1.0
duplicate, the MD5 set is a subset of the MinHash set and the union equals the
MinHash set. The dedup here is a correctness guarantee, not a size reduction.

--collapse-groups keeps ONE row per duplicate group --- the survivor
01_dedup.py would have chosen. Use it when injecting into an evaluation set:
a test set containing three renderings of one question triple-counts it, and
inflates or deflates the score depending on whether the model happens to know
that item.

--into-test merges the result into an existing test split. Three guards run
before anything is written, and any failure aborts:

  1. Nothing being added may already be in train (by question_id or fact_id) ---
     otherwise this hands the model its own training data as an exam.
  2. Nothing may already be in validation, same reasoning.
  3. Nothing may duplicate a row already in test.

Rows whose fact_id is present in train are reported and dropped rather than
silently added, because the alternative is a test set that scores memorisation.
Removing them from train instead is also defensible, but that is a training-set
change and this script does not make one.

Usage
    python 11_merge_flagged.py \\
        --sets out/10_flagged_scored/md5_scored.json \\
               out/10_flagged_scored/minhash_scored.json \\
        --out out/11_merged/flagged_union.json \\
        --report reports/14_merge_flagged.json [--collapse-groups]

    python 11_merge_flagged.py --sets ... --out ... --collapse-groups \\
        --into-test final/test.json --train final/train.json \\
        --val final/validation.json --test-out final/test_plus_flagged.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def dump(p, rows):
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        if p.endswith(".jsonl"):
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            fh.write("[\n")
            fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
            fh.write("\n]\n")


def richness(r):
    try:
        return int(r.get("source_richness", 0) or 0)
    except (TypeError, ValueError):
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default="14_merge_flagged.json")
    ap.add_argument("--collapse-groups", action="store_true",
                    help="keep only the survivor of each duplicate group")
    ap.add_argument("--into-test", default="", help="existing test split to extend")
    ap.add_argument("--train", default="", help="train split, for the leakage guard")
    ap.add_argument("--val", default="", help="validation split, for the leakage guard")
    ap.add_argument("--test-out", default="", help="where to write the extended test split")
    a = ap.parse_args()

    # ---------------- merge ------------------------------------------
    merged, seen_from = {}, {}
    for path in a.sets:
        tag = ("md5" if "md5" in os.path.basename(path).lower()
               else "minhash" if "minhash" in os.path.basename(path).lower()
               else os.path.basename(path))
        for r in load(path):
            qid = r["question_id"]
            seen_from.setdefault(qid, set()).add(tag)
            prev = merged.get(qid)
            # prefer the row carrying more annotation
            if prev is None or len(r) > len(prev):
                merged[qid] = dict(r)

    for qid, tags in seen_from.items():
        merged[qid]["dup_found_by"] = ("both" if len(tags) > 1 else next(iter(tags)))

    rows = sorted(merged.values(), key=lambda r: str(r["question_id"]))
    print("merged            : %d questions from %d sets" % (len(rows), len(a.sets)))
    print("  provenance      : %s" % dict(Counter(r["dup_found_by"] for r in rows)))

    # ---------------- collapse ---------------------------------------
    if a.collapse_groups:
        by_group = {}
        for r in rows:
            g = r.get("dup_group_id", r["question_id"])
            cur = by_group.get(g)
            if cur is None or (richness(r), str(r["question_id"])) > (
                    richness(cur), str(cur["question_id"])):
                by_group[g] = r
        rows = sorted(by_group.values(), key=lambda r: str(r["question_id"]))
        print("collapsed         : %d groups -> %d rows (one per group)"
              % (len(by_group), len(rows)))

    dump(a.out, rows)
    rep = {
        "inputs": [os.path.basename(p) for p in a.sets],
        "merged_questions": len(merged),
        "provenance": dict(Counter(r["dup_found_by"] for r in rows)),
        "collapsed_groups": bool(a.collapse_groups),
        "output_rows": len(rows), "output_file": os.path.basename(a.out),
    }

    # ---------------- optional injection into test --------------------
    if a.into_test:
        if not (a.train and a.test_out):
            raise SystemExit("--into-test requires --train and --test-out")
        test = load(a.into_test)
        train = load(a.train)
        val = load(a.val) if a.val else []

        tr_ids = {r["question_id"] for r in train}
        tr_facts = {r.get("fact_id") for r in train}
        va_ids = {r["question_id"] for r in val}
        va_facts = {r.get("fact_id") for r in val}
        te_ids = {r["question_id"] for r in test}

        add, blocked = [], {"already_in_test": 0, "in_train_id": 0, "in_train_fact": 0,
                            "in_val_id": 0, "in_val_fact": 0}
        for r in rows:
            if r["question_id"] in te_ids:
                blocked["already_in_test"] += 1
            elif r["question_id"] in tr_ids:
                blocked["in_train_id"] += 1
            elif r.get("fact_id") in tr_facts:
                blocked["in_train_fact"] += 1
            elif r["question_id"] in va_ids:
                blocked["in_val_id"] += 1
            elif r.get("fact_id") in va_facts:
                blocked["in_val_fact"] += 1
            else:
                add.append(r)

        print("\ninjection into test")
        for k, v in blocked.items():
            print("  blocked %-18s %5d" % (k, v))
        print("  admitted           %5d" % len(add))

        new_test = test + add
        new_test.sort(key=lambda r: str(r["question_id"]))
        ids = [r["question_id"] for r in new_test]
        assert len(ids) == len(set(ids)), "duplicate question_id in extended test"
        nf = {r.get("fact_id") for r in new_test}
        assert not (nf & tr_facts), "a fact now spans train and test"
        assert not (nf & va_facts), "a fact now spans validation and test"

        dump(a.test_out, new_test)
        print("  test %d -> %d rows -> %s"
              % (len(test), len(new_test), os.path.basename(a.test_out)))
        rep["injection"] = {"blocked": blocked, "admitted": len(add),
                            "test_before": len(test), "test_after": len(new_test),
                            "file": os.path.basename(a.test_out)}

    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nreport -> %s" % a.report)


if __name__ == "__main__":
    main()
