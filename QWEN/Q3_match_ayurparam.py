#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q3 --- Score every question against the AyurParam / BhashaBench-Ayur benchmark.
===============================================================================

Annotates, does not filter. Q4 decides what to do with the scores.

  COSINE       L2-normalised hashed character 3-4 gram vectors, computed for
               every one of our questions against every benchmark question.
               Hashing rather than TF-IDF because fitting a vocabulary over
               ~95k documents is the dominant cost and does not finish inside a
               minute, whereas hashing transforms the benchmark side in under a
               second. Robust to word order and inflection, and works on
               Devanagari with no tokenizer --- which matters, since 37.5% of the
               generated corpus is Hindi.

  LEVENSHTEIN  Normalised edit similarity on the top-k cosine candidates only.
               All-pairs would be ~1.2e9 edit-distance computations. Restricting
               to the cosine top-k is safe rather than a shortcut: two strings
               with high edit similarity necessarily share most of their
               character n-grams, so a pair at Levenshtein >= 0.85 cannot fall
               outside the cosine top-20.

Fields written on every row:

    bba_max_cosine        best cosine against any benchmark question
    bba_max_levenshtein   best Levenshtein among the top-k cosine candidates
    bba_match_id          id of the closest benchmark question
    bba_match_question    its text, so a human can eyeball the decision
    bba_match_topic       its topic, used by Q4 to mirror the benchmark's mix
    bba_match_domain      its subject_domain, likewise
    bba_similar           True if cosine >= --cos-th or levenshtein >= --lev-th

--ckpt saves after every chunk and --budget stops cleanly on a clock, so a long
run survives a session limit; re-running the same command resumes.

Usage
    python Q3_match_ayurparam.py --in out/Q2_deduped.jsonl \\
        --bba data/bba_en.parquet data/bba_hi.parquet \\
        --out out/Q3_annotated.jsonl --report reports/Q3_match.json \\
        [--ckpt /tmp/q3.npz] [--budget 30]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from collections import Counter

import numpy as np


def normalise(text):
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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


def load_bba(paths):
    import pandas as pd
    frames = []
    for p in paths:
        d = (pd.read_parquet(p) if p.endswith(".parquet")
             else pd.read_csv(p) if p.endswith(".csv")
             else pd.read_json(p, lines=True))
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    if "question" not in df.columns:
        raise SystemExit("BBA file has no 'question' column: %s" % list(df.columns))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--bba", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default="Q3_match.json")
    ap.add_argument("--cos-th", type=float, default=0.80)
    ap.add_argument("--lev-th", type=float, default=0.85)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--ckpt", default="")
    ap.add_argument("--budget", type=float, default=0.0)
    a = ap.parse_args()

    from sklearn.feature_extraction.text import HashingVectorizer
    import Levenshtein

    rows = load(a.inp)
    ours = [normalise(r.get("question", "")) for r in rows]
    n = len(rows)
    print("ours : %d questions" % n)

    bba = load_bba(a.bba)
    bq = [normalise(q) for q in bba["question"].tolist()]
    bid = [str(x) for x in (bba["id"].tolist() if "id" in bba.columns
                            else list(range(len(bba))))]
    braw = [str(x) for x in bba["question"].tolist()]
    btopic = [str(x) for x in (bba["topic"].tolist() if "topic" in bba.columns
                               else [""] * len(bba))]
    bdom = [str(x) for x in (bba["subject_domain"].tolist()
                             if "subject_domain" in bba.columns else [""] * len(bba))]
    print("BBA  : %d questions" % len(bq))
    if "language" in bba.columns:
        print("       languages: %s" % dict(Counter(bba["language"])))

    vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 4),
                            n_features=2 ** 18, norm="l2", alternate_sign=False)
    Xb = vec.transform(bq)
    XbT = Xb.T.tocsc()
    Xo = vec.transform(ours)
    print("vectors: ours nnz=%d bba nnz=%d" % (Xo.nnz, Xb.nnz))

    best_cos = np.zeros(n, dtype=np.float32)
    best_idx = np.full(n, -1, dtype=np.int32)
    best_lev = np.zeros(n, dtype=np.float32)

    done = 0
    if a.ckpt and os.path.exists(a.ckpt):
        z = np.load(a.ckpt)
        if int(z["n"]) == n:
            best_cos, best_idx, best_lev = z["cos"], z["idx"], z["lev"]
            done = int(z["done"])
            print("resumed at row %d" % done)

    k = min(a.topk, len(bq))
    t0 = time.time()
    stopped = False
    for s in range(done, n, a.chunk):
        if a.budget and time.time() - t0 > a.budget:
            stopped = True
            break
        e = min(s + a.chunk, n)
        S = (Xo[s:e] @ XbT).toarray()
        best_cos[s:e] = S.max(axis=1)
        best_idx[s:e] = S.argmax(axis=1)
        top = np.argpartition(-S, kth=k - 1, axis=1)[:, :k]
        for i in range(e - s):
            o = ours[s + i]
            best_lev[s + i] = max(Levenshtein.ratio(o, bq[j]) for j in top[i])
        if a.ckpt:
            np.savez(a.ckpt, n=n, done=e, cos=best_cos, idx=best_idx, lev=best_lev)
        print("  scored %6d / %d  (%.0fs)" % (e, n, time.time() - t0), flush=True)

    if stopped:
        print("\nCHECKPOINTED --- re-run the same command to continue.")
        return

    flagged = 0
    for i, r in enumerate(rows):
        j = int(best_idx[i])
        r["bba_max_cosine"] = round(float(best_cos[i]), 4)
        r["bba_max_levenshtein"] = round(float(best_lev[i]), 4)
        r["bba_match_id"] = bid[j] if j >= 0 else ""
        r["bba_match_question"] = braw[j] if j >= 0 else ""
        r["bba_match_topic"] = btopic[j] if j >= 0 else ""
        r["bba_match_domain"] = bdom[j] if j >= 0 else ""
        sim = (best_cos[i] >= a.cos_th) or (best_lev[i] >= a.lev_th)
        r["bba_similar"] = bool(sim)
        flagged += int(sim)

    dump(a.out, rows)

    c = best_cos
    ladder = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    rep = {
        "ours": n, "bba": len(bq),
        "thresholds": {"cosine": a.cos_th, "levenshtein": a.lev_th},
        "flagged_similar": flagged,
        "cosine": {"mean": round(float(c.mean()), 4), "max": round(float(c.max()), 4),
                   "p50": round(float(np.percentile(c, 50)), 4),
                   "p99": round(float(np.percentile(c, 99)), 4),
                   "p99_9": round(float(np.percentile(c, 99.9)), 4)},
        "levenshtein": {"mean": round(float(best_lev.mean()), 4),
                        "max": round(float(best_lev.max()), 4)},
        "threshold_sweep": {str(t): int((c >= t).sum()) for t in ladder},
        "closest_examples": [
            {"cosine": round(float(best_cos[i]), 4),
             "ours": rows[i].get("question", "")[:140],
             "bba": rows[i].get("bba_match_question", "")[:140]}
            for i in np.argsort(-best_cos)[:5]],
    }
    d = os.path.dirname(a.report)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\nflagged similar to BBA : %d" % flagged)
    print("max cosine %.4f | max levenshtein %.4f" % (c.max(), best_lev.max()))
    print("sweep:", rep["threshold_sweep"])
    print("wrote %s | report -> %s" % (a.out, a.report))


if __name__ == "__main__":
    main()
