#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 2 --- Quarantine anything resembling the AyurParam / BhashaBench-Ayur benchmark.
=====================================================================================

Any of our questions that resembles a published BBA question is moved to TEST and
forbidden from TRAIN, so that a model fine-tuned on TRAIN can be evaluated on BBA
without the score being inflated by having seen a paraphrase during training.

Two similarity measures:

  COSINE       L2-normalised hashed character 3-4 gram vectors (``char_wb``),
               cosine similarity. Hashing avoids building a vocabulary, which on
               92k documents is the dominant cost --- a TfidfVectorizer fit over
               the same corpus does not finish inside a minute, whereas hashing
               transforms the whole BBA side in half a second. Robust to word
               order and inflection, and works on Devanagari with no tokenizer.
               Computed for every one of our questions against every BBA
               question, in chunks.

  LEVENSHTEIN  Normalised edit similarity (``Levenshtein.ratio``). All-pairs is
               80k x 15k = 1.2e9 comparisons, which is not tractable, so it is
               evaluated only on the top-``--topk`` cosine candidates per
               question. This is safe: two strings with high edit similarity
               necessarily share most character n-grams, so a pair at
               Levenshtein >= 0.85 cannot fall outside the cosine top-k.

QUARANTINED when  cosine >= --cos-th  OR  levenshtein >= --lev-th.

Every row is annotated whether or not it matched:

    bba_max_cosine        best cosine against any BBA question
    bba_max_levenshtein   best Levenshtein among the top-k cosine candidates
    bba_match_id          id of the closest BBA question
    bba_match_question    its text, so a human can eyeball the decision
    bba_match_reason      "cosine" | "levenshtein" | "both" | ""
    split_assignment      "test_contaminated" | "train_pool"
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


def normalise(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_bba(paths):
    import pandas as pd
    frames = []
    for p in paths:
        if p.endswith(".parquet"):
            d = pd.read_parquet(p)
        elif p.endswith(".csv"):
            d = pd.read_csv(p)
        else:
            d = pd.read_json(p, lines=True)
        d["__src"] = os.path.basename(p)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    if "question" not in df.columns:
        raise SystemExit("BBA file has no 'question' column; found %s" % list(df.columns))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--bba", nargs="+", required=True)
    ap.add_argument("--out-annotated", required=True)
    ap.add_argument("--out-test", required=True)
    ap.add_argument("--out-pool", required=True)
    ap.add_argument("--report", default="02_match_report.json")
    ap.add_argument("--cos-th", type=float, default=0.80)
    ap.add_argument("--lev-th", type=float, default=0.85)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--ckpt", default="",
                    help="checkpoint .npz; scoring resumes from it and saves after "
                         "each chunk, so a long run can be done in several passes")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="stop after this many seconds and checkpoint (0 = no limit)")
    a = ap.parse_args()

    from sklearn.feature_extraction.text import HashingVectorizer
    from scipy import sparse
    import Levenshtein

    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    ours = [normalise(r.get("question", "")) for r in rows]
    print("ours : %d questions" % len(rows))

    bba = load_bba(a.bba)
    bba_q = [normalise(q) for q in bba["question"].tolist()]
    bba_id = [str(x) for x in (bba["id"].tolist() if "id" in bba.columns
                               else list(range(len(bba))))]
    bba_raw = [str(x) for x in bba["question"].tolist()]
    print("BBA  : %d questions" % len(bba_q))
    if "language" in bba.columns:
        print("       languages: %s" % dict(Counter(bba["language"])))

    # vectorising all 92k documents costs ~12s, so cache it next to the
    # checkpoint; a resumed pass then starts scoring immediately
    cache = (a.ckpt + ".vec.npz") if a.ckpt else ""
    if cache and os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        Xo = sparse.csr_matrix((z["od"], z["oi"], z["op"]), shape=tuple(z["os"]))
        Xb = sparse.csr_matrix((z["bd"], z["bi"], z["bp"]), shape=tuple(z["bs"]))
        print("vectors: loaded from cache")
    else:
        vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 4),
                                n_features=2 ** 18, norm="l2",
                                alternate_sign=False)
        Xb = vec.transform(bba_q)
        Xo = vec.transform(ours)
        print("vectors: hashed, ours nnz=%d bba nnz=%d" % (Xo.nnz, Xb.nnz))
        if cache:
            np.savez(cache, od=Xo.data, oi=Xo.indices, op=Xo.indptr, os=Xo.shape,
                     bd=Xb.data, bi=Xb.indices, bp=Xb.indptr, bs=Xb.shape)

    n = len(rows)
    best_cos = np.zeros(n, dtype=np.float32)
    best_idx = np.full(n, -1, dtype=np.int32)
    best_lev = np.zeros(n, dtype=np.float32)
    best_lev_idx = np.full(n, -1, dtype=np.int32)

    XbT = Xb.T.tocsc()
    k = min(a.topk, len(bba_q))

    done = 0
    if a.ckpt and os.path.exists(a.ckpt):
        z = np.load(a.ckpt)
        if int(z["n"]) == n:
            best_cos, best_idx = z["cos"], z["idx"]
            best_lev, best_lev_idx = z["lev"], z["lidx"]
            done = int(z["done"])
            print("resumed from %s at row %d" % (a.ckpt, done))

    t_start = time.time()
    stopped_early = False

    for s in range(done, n, a.chunk):
        if a.budget and (time.time() - t_start) > a.budget:
            stopped_early = True
            break
        e = min(s + a.chunk, n)
        S = (Xo[s:e] @ XbT).toarray()
        best_cos[s:e] = S.max(axis=1)
        best_idx[s:e] = S.argmax(axis=1)
        top = np.argpartition(-S, kth=k - 1, axis=1)[:, :k]
        for i in range(e - s):
            o = ours[s + i]
            bl, bj = 0.0, -1
            for j in top[i]:
                r = Levenshtein.ratio(o, bba_q[j])
                if r > bl:
                    bl, bj = r, int(j)
            best_lev[s + i] = bl
            best_lev_idx[s + i] = bj
        if a.ckpt:
            np.savez(a.ckpt, n=n, done=e, cos=best_cos, idx=best_idx,
                     lev=best_lev, lidx=best_lev_idx)
        print("  scored %6d / %d  (%.0fs)" % (e, n, time.time() - t_start), flush=True)

    if stopped_early or (a.ckpt and done < n and
                         int(np.load(a.ckpt)["done"]) < n if a.ckpt else False):
        z = np.load(a.ckpt)
        print("\nCHECKPOINTED at row %d of %d --- re-run the same command to continue."
              % (int(z["done"]), n))
        return

    reasons, kept, quarantined = [], [], []
    for i, r in enumerate(rows):
        c, l = float(best_cos[i]), float(best_lev[i])
        by_cos, by_lev = c >= a.cos_th, l >= a.lev_th
        reason = ("both" if (by_cos and by_lev) else
                  "cosine" if by_cos else "levenshtein" if by_lev else "")
        j = int(best_idx[i]) if c >= l else int(best_lev_idx[i])
        if j < 0:
            j = int(best_idx[i])
        r["bba_max_cosine"] = round(c, 4)
        r["bba_max_levenshtein"] = round(l, 4)
        r["bba_match_id"] = bba_id[j] if j >= 0 else ""
        r["bba_match_question"] = bba_raw[j][:300] if j >= 0 else ""
        r["bba_match_reason"] = reason
        r["split_assignment"] = "test_contaminated" if reason else "train_pool"
        reasons.append(reason)
        (quarantined if reason else kept).append(r)

    sweep = []
    for ct in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95):
        for lt in (0.75, 0.80, 0.85, 0.90, 0.95):
            m = int(((best_cos >= ct) | (best_lev >= lt)).sum())
            sweep.append({"cosine_th": ct, "levenshtein_th": lt,
                          "quarantined": m, "pct": round(100.0 * m / n, 2)})

    for path, data in ((a.out_annotated, rows), (a.out_test, quarantined),
                       (a.out_pool, kept)):
        with open(path, "w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = {
        "ours_in": n,
        "bba_questions": len(bba_q),
        "cosine_threshold": a.cos_th,
        "levenshtein_threshold": a.lev_th,
        "topk_for_levenshtein": a.topk,
        "quarantined_to_test": len(quarantined),
        "remaining_train_pool": len(kept),
        "quarantined_pct": round(100.0 * len(quarantined) / n, 3),
        "reason_counts": dict(Counter(x for x in reasons if x)),
        "cosine_percentiles": {str(p): round(float(np.percentile(best_cos, p)), 4)
                               for p in (50, 75, 90, 95, 99, 99.9)},
        "levenshtein_percentiles": {str(p): round(float(np.percentile(best_lev, p)), 4)
                                    for p in (50, 75, 90, 95, 99, 99.9)},
        "max_cosine_observed": round(float(best_cos.max()), 4),
        "max_levenshtein_observed": round(float(best_lev.max()), 4),
        "threshold_sweep": sweep,
        "closest_15": sorted(
            [{"our_id": r["question_id"], "cos": r["bba_max_cosine"],
              "lev": r["bba_max_levenshtein"], "ours": r["question"][:140],
              "bba": r["bba_match_question"][:140]} for r in rows],
            key=lambda x: -x["cos"])[:15],
    }
    json.dump(report, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\nquarantined to TEST : %d (%.3f%%)" % (len(quarantined), report["quarantined_pct"]))
    print("remaining TRAIN pool: %d" % len(kept))
    print("max cosine %.4f   max levenshtein %.4f" % (best_cos.max(), best_lev.max()))


if __name__ == "__main__":
    main()
