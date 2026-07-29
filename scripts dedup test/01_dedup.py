#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 1 --- Deduplicate the question corpus.
===========================================

Removes three kinds of duplicate, in order:

  1. EXACT      identical normalised question stem
  2. FULL-ITEM  identical (stem + sorted options + answer) --- catches items whose
                stems differ only in whitespace or option ordering
  3. NEAR       cosine similarity >= --near on TF-IDF character 3-5 grams,
                compared only inside a blocking bucket so the work is
                O(n * bucket) rather than O(n^2)

Blocking: two rows are only compared when they agree on question_type,
format_variant, the first and last 40 characters of the normalised stem, and
stem length to the nearest 10. A naive prefix-only key is useless here --- our
stems are templated, so 13,605 of them share the same opening and the bucket
degenerates into an O(n^2) scan. The composite key above splits the corpus into
~58k buckets and reduces the pairwise work from 519M comparisons to 2.1M,
without being able to separate two genuinely near-identical stems: any pair that
differs only in a distractor or a digit agrees on all five components.

Survivor policy: within a duplicate group keep the row with the highest
source_richness, breaking ties on question_id so the choice is deterministic.

Usage
    python dedup.py --in ayur_qa_v2_80k.jsonl --out deduped.jsonl \
                    --report dedup_report.json [--near 0.97] [--no-near]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict

LETTERS = ["a", "b", "c", "d", "e"]


# ---------------------------------------------------------------- normalisation
def normalise(text: str) -> str:
    """Aggressive normalisation used only for comparison, never for output."""
    s = unicodedata.normalize("NFKC", text or "")
    s = s.lower()
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)   # keep Devanagari, drop punctuation
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def stem_key(row: dict) -> str:
    return hashlib.md5(normalise(row.get("question", "")).encode("utf-8")).hexdigest()


def full_item_key(row: dict) -> str:
    """Stem + option set (order-independent) + answer text."""
    opts = sorted(normalise(row.get("option_%s" % L, "")) for L in LETTERS)
    opts = [o for o in opts if o]
    payload = "|".join([normalise(row.get("question", ""))] + opts
                       + [normalise(str(row.get("answer_text", "")))])
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def richness(row: dict) -> int:
    try:
        return int(row.get("source_richness", 0) or 0)
    except (TypeError, ValueError):
        return 0


def pick_survivor(rows: list) -> dict:
    return sorted(rows, key=lambda r: (-richness(r), str(r.get("question_id", ""))))[0]


# ---------------------------------------------------------------- near duplicates
def near_duplicate_groups(rows: list, threshold: float, min_bucket: int = 2):
    """Return lists of row indices that are near-duplicates of one another."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    buckets = defaultdict(list)
    for i, r in enumerate(rows):
        n = normalise(r.get("question", ""))
        buckets[(r.get("question_type", ""), r.get("format_variant", ""),
                 n[:40], n[-40:], len(n) // 10)].append(i)

    groups = []
    for _key, idxs in buckets.items():
        if len(idxs) < min_bucket:
            continue
        texts = [normalise(rows[i].get("question", "")) for i in idxs]
        try:
            vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
            X = vec.fit_transform(texts)
        except ValueError:
            continue                                   # bucket had no usable tokens
        S = cosine_similarity(X)
        seen = set()
        for a in range(len(idxs)):
            if a in seen:
                continue
            grp = [a]
            for b in range(a + 1, len(idxs)):
                if b not in seen and S[a, b] >= threshold:
                    grp.append(b)
                    seen.add(b)
            if len(grp) > 1:
                seen.add(a)
                groups.append([idxs[g] for g in grp])
    return groups


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--report", default="dedup_report.json")
    ap.add_argument("--near", type=float, default=0.97,
                    help="cosine threshold for near-duplicates (default 0.97)")
    ap.add_argument("--no-near", action="store_true",
                    help="skip the near-duplicate pass (exact + full-item only)")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    n0 = len(rows)
    print("loaded %d rows" % n0)
    report = {"input_rows": n0, "threshold_near": a.near}

    # ---- pass 1: exact stem ----
    by_stem = defaultdict(list)
    for r in rows:
        by_stem[stem_key(r)].append(r)
    dropped_exact = sum(len(v) - 1 for v in by_stem.values() if len(v) > 1)
    rows = [pick_survivor(v) for v in by_stem.values()]
    print("pass 1 exact-stem      : removed %6d -> %d rows" % (dropped_exact, len(rows)))
    report["removed_exact_stem"] = dropped_exact

    # ---- pass 2: full item ----
    by_item = defaultdict(list)
    for r in rows:
        by_item[full_item_key(r)].append(r)
    dropped_item = sum(len(v) - 1 for v in by_item.values() if len(v) > 1)
    rows = [pick_survivor(v) for v in by_item.values()]
    print("pass 2 full-item       : removed %6d -> %d rows" % (dropped_item, len(rows)))
    report["removed_full_item"] = dropped_item

    # ---- pass 3: near duplicates ----
    dropped_near, examples = 0, []
    if not a.no_near:
        groups = near_duplicate_groups(rows, a.near)
        drop = set()
        for g in groups:
            survivor = pick_survivor([rows[i] for i in g])
            sid = id(survivor)
            losers = [i for i in g if id(rows[i]) != sid]
            drop.update(losers)
            if len(examples) < 5:
                examples.append({
                    "kept": survivor.get("question_id"),
                    "dropped": [rows[i].get("question_id") for i in losers][:3],
                    "stem": survivor.get("question", "")[:150],
                })
        dropped_near = len(drop)
        rows = [r for i, r in enumerate(rows) if i not in drop]
    print("pass 3 near-duplicate  : removed %6d -> %d rows" % (dropped_near, len(rows)))
    report["removed_near_duplicate"] = dropped_near
    report["near_examples"] = examples

    rows.sort(key=lambda r: str(r.get("question_id", "")))
    with open(a.out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    report["output_rows"] = len(rows)
    report["total_removed"] = n0 - len(rows)
    report["by_type_after"] = dict(Counter(r.get("question_type") for r in rows))
    report["distinct_facts_after"] = len({r.get("fact_id") for r in rows})
    json.dump(report, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\nTOTAL removed %d (%.2f%%) -> wrote %d rows to %s"
          % (n0 - len(rows), 100.0 * (n0 - len(rows)) / max(n0, 1), len(rows), a.out))
    print("report: %s" % a.report)


if __name__ == "__main__":
    main()
