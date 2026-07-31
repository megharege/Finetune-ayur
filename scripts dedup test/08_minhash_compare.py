#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinHash + LSH deduplication --- REFERENCE / COMPARISON ONLY.
============================================================

NOT part of the pipeline. 01_dedup.py remains the deduplicator of record.
This exists to answer one question honestly: would MinHash have found anything
the MD5 + cosine approach missed, and at what cost? It writes a report and
never writes a deduplicated corpus.

WHAT MINHASH IS
---------------
Jaccard similarity between two documents is |A n B| / |A u B| over their shingle
sets. Computing it exactly for every pair is the same O(n^2) problem cosine has.

MinHash makes it cheap. Hash every shingle with a permutation h_i and keep only
the minimum value: min(h_i(A)). The probability that min(h_i(A)) == min(h_i(B))
is exactly the Jaccard similarity of A and B --- the minimum is equally likely to
fall on any element of the union, and the pair agrees only when it falls in the
intersection. Do this with 128 independent permutations and the fraction of
positions where the two signatures agree estimates Jaccard with standard error
~1/sqrt(128) ~ 0.09. A document of any length collapses to 128 integers.

LSH then avoids comparing all signature pairs. Cut the 128 rows into b bands of
r rows and hash each band. Two documents become candidates if any band matches
exactly. The probability of that is 1 - (1 - s^r)^b --- an S-curve with its
steep part near s ~ (1/b)^(1/r), which is how the threshold is tuned. Pairs far
below the threshold are almost never even looked at.

HOW IT DIFFERS FROM WHAT THE PIPELINE USES
------------------------------------------
  MD5        exact identity only. Binary answer, no notion of "close".
  MinHash    estimates Jaccard on SETS of shingles. Order-blind and
             count-blind: a shingle appearing once or five times is the same
             set element, and reordering the text changes nothing.
  Cosine     exact, on WEIGHTED vectors. Repetition and rare-gram overlap both
             carry signal, and the value is exact rather than sampled.

The distinction matters for templated exam questions. Two items sharing a long
stem and differing only in one distractor have near-identical shingle SETS, so
MinHash rates them extremely similar; weighted cosine gives the differing region
proportionally more influence. MinHash is therefore the more aggressive of the
two at this task --- which is a liability when the difference between two rows is
exactly the thing being tested.

WHY THE PIPELINE DOES NOT USE IT
--------------------------------
MinHash pays off when the corpus is too large to block cheaply --- billions of
web documents. At 80k rows with a discriminative blocking key already available
(question_type, format_variant, stem head/tail, length band), exact cosine
inside blocks is both cheaper and exact. MinHash would add a sampling error of
about +/-0.09 on every similarity, on a decision made at a 0.97 threshold.

Usage
    python 08_minhash_compare.py --in master_80k.jsonl \
        --report reports/08_minhash_comparison.json \
        [--perm 128] [--threshold 0.97] [--shingle 5]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict

import numpy as np

MERSENNE = (1 << 61) - 1


def normalise(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def shingles(text: str, k: int) -> set:
    """Character k-shingles. Character-level so Devanagari needs no tokenizer."""
    if len(text) < k:
        return {text} if text else set()
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def signature_matrix(docs, perm, seed, k, cache="", budget=0.0):
    """
    One row per document, `perm` columns, each the minimum of a hashed shingle.

    Shingles are hashed once to 64 bits, then permuted arithmetically as
    (a*h + b) mod p, which is far cheaper than hashing each shingle `perm`
    times and is the standard construction.

    Hashing ~36M shingles at 80k documents takes longer than a single
    constrained run allows, so progress is checkpointed to `cache` after every
    chunk. With `budget` seconds set, the function returns early having saved
    what it has; re-running the same command resumes. Returns (sig, done).
    """
    rng = np.random.RandomState(seed)
    a = rng.randint(1, MERSENNE, size=perm, dtype=np.int64)
    b = rng.randint(0, MERSENNE, size=perm, dtype=np.int64)

    n = len(docs)
    sig = np.full((n, perm), np.iinfo(np.int64).max, dtype=np.int64)
    done = 0
    if cache and os.path.exists(cache):
        z = np.load(cache)
        if z["sig"].shape == sig.shape:
            sig, done = z["sig"], int(z["done"])
            print("resumed signatures at %d/%d" % (done, n))
    if done >= n:
        return sig, n

    t0, chunk = time.time(), 2000
    for s in range(done, n, chunk):
        e = min(s + chunk, n)
        for i in range(s, e):
            sh = shingles(docs[i], k)
            if not sh:
                continue
            h = np.fromiter(
                (int.from_bytes(hashlib.blake2b(x.encode("utf-8"), digest_size=8).digest(),
                                "big") & 0x7FFFFFFFFFFFFFFF for x in sh),
                dtype=np.int64, count=len(sh))
            sig[i] = ((h[:, None] * a[None, :] + b[None, :]) % MERSENNE).min(axis=0)
        done = e
        if cache:
            np.savez(cache, sig=sig, done=done)
        print("  signed %6d / %d  (%.0fs)" % (done, n, time.time() - t0), flush=True)
        if budget and (time.time() - t0) > budget and done < n:
            return sig, done
    return sig, done


def choose_bands(perm, threshold):
    """Pick (b, r) with b*r == perm whose S-curve knee is closest to threshold."""
    best, best_err = None, 1e9
    for r in range(1, perm + 1):
        if perm % r:
            continue
        b = perm // r
        knee = (1.0 / b) ** (1.0 / r)
        if abs(knee - threshold) < best_err:
            best, best_err = (b, r), abs(knee - threshold)
    return best


def lsh_candidates(sig, b, r):
    """Documents sharing an identical band become candidate pairs."""
    n = sig.shape[0]
    pairs = set()
    for band in range(b):
        buckets = defaultdict(list)
        chunk = sig[:, band * r:(band + 1) * r]
        for i in range(n):
            buckets[chunk[i].tobytes()].append(i)
        for idxs in buckets.values():
            if len(idxs) < 2 or len(idxs) > 400:      # skip degenerate buckets
                continue
            for x in range(len(idxs)):
                for y in range(x + 1, len(idxs)):
                    pairs.add((idxs[x], idxs[y]))
    return pairs


def true_jaccard(x, y, k):
    A, B = shingles(x, k), shingles(y, k)
    return len(A & B) / len(A | B) if (A or B) else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--report", default="08_minhash_comparison.json")
    ap.add_argument("--perm", type=int, default=128)
    ap.add_argument("--threshold", type=float, default=0.97)
    ap.add_argument("--shingle", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="0 = whole corpus")
    ap.add_argument("--seed", type=int, default=20260729)
    ap.add_argument("--cache", default="", help="signature checkpoint .npz")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="stop signing after N seconds and checkpoint (0 = no limit)")
    a = ap.parse_args()

    with open(a.inp, encoding="utf-8") as fh:
        rows = ([json.loads(l) for l in fh if l.strip()]
                if a.inp.endswith(".jsonl") else json.load(fh))
    if a.limit:
        rows = rows[:a.limit]
    docs = [normalise(r.get("question", "")) for r in rows]
    n = len(docs)
    print("documents        : %d" % n)

    # ---- MD5 baseline, for reference ----------------------------------
    md5 = Counter(hashlib.md5(d.encode()).hexdigest() for d in docs)
    exact_dupes = sum(v - 1 for v in md5.values() if v > 1)
    print("MD5 exact dupes  : %d" % exact_dupes)

    b, r = choose_bands(a.perm, a.threshold)
    knee = (1.0 / b) ** (1.0 / r)
    print("bands            : b=%d r=%d  (S-curve knee %.3f)" % (b, r, knee))

    t0 = time.time()
    sig, done = signature_matrix(docs, a.perm, a.seed, a.shingle, a.cache, a.budget)
    t_sig = time.time() - t0
    if done < n:
        print("\nCHECKPOINTED at %d of %d --- re-run the same command to continue." % (done, n))
        return
    print("signatures       : %.1fs  (%d x %d int64 = %.1f MB)"
          % (t_sig, n, a.perm, sig.nbytes / 1e6))

    t0 = time.time()
    cand = lsh_candidates(sig, b, r)
    t_lsh = time.time() - t0
    print("candidate pairs  : %d  (%.1fs)" % (len(cand), t_lsh))

    # ---- verify candidates with exact Jaccard -------------------------
    t0 = time.time()
    confirmed, est_err = [], []
    for i, j in cand:
        jac = true_jaccard(docs[i], docs[j], a.shingle)
        est = float((sig[i] == sig[j]).mean())
        est_err.append(abs(est - jac))
        if jac >= a.threshold:
            confirmed.append((i, j, jac))
    t_ver = time.time() - t0
    print("confirmed >= %.2f : %d  (%.1fs)" % (a.threshold, len(confirmed), t_ver))

    # ---- what kind of match is it? ------------------------------------
    # A matched pair drawn from two different fact_ids is NOT a MinHash error.
    # It is the same phenomenon 05_check_leakage.py found: two different source
    # facts rendering through one template into near-identical stems. Splitting
    # those two rows apart is the leak; keeping both is the ambiguity.
    #
    # The subset that matters is CONFLICTING: near-identical stem, different
    # gold answer. Those questions are unanswerable as written --- a model
    # cannot distinguish them, so whichever it answers, one is marked wrong.
    cross_fact, conflicting = [], []
    for i, j, s in confirmed:
        if rows[i].get("fact_id") != rows[j].get("fact_id"):
            cross_fact.append((i, j, s))
            if (str(rows[i].get("answer_text", "")).strip().lower()
                    != str(rows[j].get("answer_text", "")).strip().lower()):
                conflicting.append((i, j, s))
    print("  different fact_id          : %d (%.1f%%)"
          % (len(cross_fact), 100.0 * len(cross_fact) / max(len(confirmed), 1)))
    print("  AND conflicting gold answer: %d (%.1f%%)  <- ambiguous as written"
          % (len(conflicting), 100.0 * len(conflicting) / max(len(confirmed), 1)))

    ambiguous = []
    for i, j, s in sorted(conflicting, key=lambda x: -x[2])[:5]:
        ambiguous.append({
            "jaccard": round(s, 4),
            "a": rows[i].get("question_id"), "b": rows[j].get("question_id"),
            "verse_a": rows[i].get("verse_id"), "verse_b": rows[j].get("verse_id"),
            "answer_a": str(rows[i].get("answer_text", ""))[:80],
            "answer_b": str(rows[j].get("answer_text", ""))[:80],
            "stem_a": rows[i].get("question", "")[:130],
            "stem_b": rows[j].get("question", "")[:130],
        })

    # rows that would be dropped: keep one member of each connected group
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j, _ in confirmed:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    would_drop = sum(len(g) - 1 for g in groups.values() if len(g) > 1)
    print("would remove     : %d rows -> %d remain" % (would_drop, n - would_drop))

    examples = []
    for i, j, jac in sorted(confirmed, key=lambda x: -x[2])[:5]:
        examples.append({
            "jaccard": round(jac, 4),
            "minhash_estimate": round(float((sig[i] == sig[j]).mean()), 4),
            "a": rows[i].get("question_id"), "b": rows[j].get("question_id"),
            "stem_a": rows[i].get("question", "")[:130],
            "stem_b": rows[j].get("question", "")[:130],
        })

    rep = {
        "note": "REFERENCE ONLY --- not used by the pipeline; 01_dedup.py is authoritative",
        "documents": n,
        "params": {"permutations": a.perm, "bands": b, "rows_per_band": r,
                   "s_curve_knee": round(knee, 4), "shingle_size": a.shingle,
                   "threshold": a.threshold, "seed": a.seed},
        "md5_exact_duplicates": exact_dupes,
        "candidate_pairs_from_lsh": len(cand),
        "confirmed_pairs": len(confirmed),
        "confirmed_pairs_different_fact_id": len(cross_fact),
        "confirmed_pairs_conflicting_answer": len(conflicting),
        "would_remove_rows": would_drop,
        "would_leave_rows": n - would_drop,
        "ambiguous_examples": ambiguous,
        "signature_estimate_error": {
            "mean_abs": round(float(np.mean(est_err)), 4) if est_err else None,
            "p95_abs": round(float(np.percentile(est_err, 95)), 4) if est_err else None,
            "theoretical_stderr": round(1.0 / a.perm ** 0.5, 4),
        },
        "timing_seconds": {"signatures": round(t_sig, 1), "lsh": round(t_lsh, 1),
                           "verification": round(t_ver, 1),
                           "total": round(t_sig + t_lsh + t_ver, 1)},
        "signature_memory_mb": round(sig.nbytes / 1e6, 1),
        "examples": examples,
    }
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nreport -> %s" % a.report)


if __name__ == "__main__":
    main()
