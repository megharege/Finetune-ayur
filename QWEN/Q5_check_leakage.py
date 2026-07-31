#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 5 --- Cross-split leakage audit.
=====================================

Checks five ways a training item can contaminate an evaluation split, from
strictest to loosest:

  1. QUESTION_ID   the same row present in two splits
  2. EXACT STEM    identical normalised question text
  3. FULL ITEM     identical stem + option set + answer
  4. FACT_ID       two renderings of the same underlying fact --- the leak that
                   row-level splitting silently creates and that hash-based
                   dedup cannot see
  5. NEAR-DUP      cosine >= --near on hashed char 3-4 grams, train-vs-eval.
                   This matters more than it looks: two *different* facts can
                   render into near-identical stems (same template, similar
                   heading), so splitting on fact_id does NOT prevent it. Rows
                   are blocked on (question_type, format_variant, first/last 40
                   chars, length band) and only compared inside a block, which
                   turns a 66k x 6k dense product into a few thousand small ones.

With --repair, near-duplicate pairs are broken by dropping one side:

  --repair-side eval   (default) drop the offending EVAL rows. Correct when the
                       eval splits are still being sized and train is the asset.
  --repair-side train  drop the offending TRAIN rows instead. Correct once the
                       eval splits are fixed at sizes you intend to keep ---
                       e.g. a test set already reported on, or a validation set
                       deliberately cut to a target size. Train is large enough
                       to absorb the loss; the eval splits come out byte-stable.

Cleaned files are written alongside the originals as *_clean.jsonl / *_clean.json.

Also re-checks that TRAIN contains nothing resembling BhashaBench-Ayur, since
that guarantee is the whole point of step 2 and must survive the split.

Exit code is 1 if any leak is found, so this can gate a pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

import numpy as np

LETTERS = ["a", "b", "c", "d", "e"]


def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sऀ-ॿ]", " ", s)).strip()


def stem_h(r):
    return hashlib.md5(norm(r.get("question", "")).encode()).hexdigest()


def item_h(r):
    o = sorted(norm(r.get("option_%s" % L, "")) for L in LETTERS)
    o = [x for x in o if x]
    return hashlib.md5("|".join([norm(r.get("question", ""))] + o +
                                [norm(r.get("answer_text", ""))]).encode()).hexdigest()


def load(p):
    """Accept .json (array) or .jsonl (one object per line)."""
    with open(p, encoding="utf-8") as fh:
        if p.endswith(".jsonl"):
            return [json.loads(l) for l in fh if l.strip()]
        return json.load(fh)


def save(p, rows):
    with open(p, "w", encoding="utf-8") as fh:
        if p.endswith(".jsonl"):
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            fh.write("[\n")
            fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
            fh.write("\n]\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--report", default="05_leakage_report.json")
    ap.add_argument("--near", type=float, default=0.95)
    ap.add_argument("--bba-cos-th", type=float, default=0.80)
    ap.add_argument("--skip-near", action="store_true")
    ap.add_argument("--repair", action="store_true",
                    help="write *_clean files with near-duplicates removed")
    ap.add_argument("--repair-side", choices=("eval", "train"), default="eval",
                    help="which side of a near-duplicate pair to drop (default eval)")
    a = ap.parse_args()

    S = {"train": load(a.train), "validation": load(a.val), "test": load(a.test)}
    for k, v in S.items():
        print("%-11s %6d rows" % (k, len(v)))

    rep, leaks = {"rows": {k: len(v) for k, v in S.items()}}, 0
    pairs = [("train", "validation"), ("train", "test"), ("validation", "test")]

    for name, fn in (("question_id", lambda r: r.get("question_id")),
                     ("exact_stem", stem_h),
                     ("full_item", item_h),
                     ("fact_id", lambda r: r.get("fact_id"))):
        res = {}
        for x, y in pairs:
            ov = {fn(r) for r in S[x]} & {fn(r) for r in S[y]}
            ov.discard(None)
            res["%s|%s" % (x, y)] = len(ov)
            leaks += len(ov)
        rep[name] = res
        print("%-12s %s" % (name, res))

    # ---- near-duplicate, train vs each eval split ----------------------
    # Both sides of every offending pair are recorded, so --repair-side can
    # drop whichever one the caller wants to give up.
    contaminated = {"validation": set(), "test": set()}
    train_bad = set()
    if not a.skip_near:
        from sklearn.feature_extraction.text import HashingVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 4),
                                n_features=2 ** 18, norm="l2", alternate_sign=False)

        def block(r):
            n = norm(r.get("question", ""))
            return (r.get("question_type", ""), r.get("format_variant", ""),
                    n[:40], n[-40:], len(n) // 10)

        tr_blocks = defaultdict(list)
        for i, r in enumerate(S["train"]):
            tr_blocks[block(r)].append(i)

        near = {}
        for other in ("validation", "test"):
            hits, worst = 0, 0.0
            groups = defaultdict(list)
            for i, r in enumerate(S[other]):
                groups[block(r)].append(i)
            for b, idxs in groups.items():
                cand = tr_blocks.get(b)
                if not cand:
                    continue
                qs = [norm(S[other][i].get("question", "")) for i in idxs]
                ct = [norm(S["train"][i].get("question", "")) for i in cand]
                M = cosine_similarity(vec.transform(qs), vec.transform(ct))
                mx = M.max(axis=1)
                worst = max(worst, float(mx.max()))
                for j, i in enumerate(idxs):
                    if mx[j] >= a.near:
                        hits += 1
                        contaminated[other].add(i)
                        # every train row implicated in this pair
                        for k in (M[j] >= a.near).nonzero()[0]:
                            train_bad.add(cand[int(k)])
            near["train|%s" % other] = {"above_threshold": hits,
                                        "max_cosine": round(worst, 4)}
            leaks += hits
            print("near-dup train|%-10s hits=%d  max_cos=%.4f" % (other, hits, worst))
        rep["near_duplicate"] = {"threshold": a.near, **near,
                                 "train_rows_implicated": len(train_bad)}

    # ---- BBA guarantee must survive the split -------------------------
    if S["train"] and "bba_max_cosine" in S["train"][0]:
        c = np.array([r.get("bba_max_cosine", 0.0) for r in S["train"]], dtype=float)
        bad = int((c >= a.bba_cos_th).sum())
        rep["bba_contamination_in_train"] = {
            "threshold": a.bba_cos_th, "rows_above": bad,
            "max_cosine_in_train": round(float(c.max()), 4)}
        leaks += bad
        print("BBA contamination in train: %d rows (max cosine %.4f)" % (bad, c.max()))

    def clean_name(path):
        base, ext = os.path.splitext(path)
        return base + "_clean" + ext

    if a.repair and (any(contaminated.values()) or train_bad):
        if a.repair_side == "train":
            clean = [r for i, r in enumerate(S["train"]) if i not in train_bad]
            out = clean_name(a.train)
            save(out, clean)
            print("repaired %-11s %d -> %d rows  -> %s"
                  % ("train", len(S["train"]), len(clean), os.path.basename(out)))
            rep["repair"] = {"side": "train", "train": {
                "dropped": len(train_bad), "kept": len(clean),
                "file": os.path.basename(out)}}
            print("           validation and test left untouched")
        else:
            rep["repair"] = {"side": "eval"}
            for other, path in (("validation", a.val), ("test", a.test)):
                bad = contaminated[other]
                clean = [r for i, r in enumerate(S[other]) if i not in bad]
                out = clean_name(path)
                save(out, clean)
                print("repaired %-11s %d -> %d rows  -> %s"
                      % (other, len(S[other]), len(clean), os.path.basename(out)))
                rep["repair"][other] = {
                    "dropped": len(bad), "kept": len(clean),
                    "file": os.path.basename(out)}

    rep["total_leaks"] = leaks
    rep["verdict"] = "CLEAN" if leaks == 0 else "LEAKAGE DETECTED"
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n%s  (total leaks: %d)" % (rep["verdict"], leaks))
    sys.exit(0 if leaks == 0 else 1)


if __name__ == "__main__":
    main()
