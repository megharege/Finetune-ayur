#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 10 --- Score the MD5 and MinHash flagged sets against AyurParam, and compare.
==================================================================================

Answers two questions:

  1. How many questions in each flagged set resemble a BhashaBench-Ayur item?
  2. Which method is the better source of test-set candidates?

Scoring is identical to 02_match_ayurparam.py --- hashed character 3-4 gram
cosine against every BBA question, plus exact Levenshtein on the top-k cosine
candidates --- so the numbers here are directly comparable to the corpus-wide
guarantee reported there.

ON READING THE RESULT
---------------------
A binary count at cosine >= 0.80 is likely to be zero for both sets, because it
is zero for the whole corpus. A zero-versus-zero table says nothing, so the
comparison is also made on the CONTINUOUS similarity: mean, max, and the count
above a ladder of thresholds. That shows which set leans closer to the benchmark
even when neither crosses the line.

A caveat worth keeping in view: both sets are duplicate groups. Members of one
group are near-identical to each other, so their similarity scores against BBA
are near-identical too. Treating 1,911 rows as 1,911 independent observations
overstates the evidence --- the report therefore also gives per-GROUP statistics,
which are the honest denominator.

Usage
    python 10_flagged_vs_ayurparam.py \\
        --sets out/09_flagged/md5_flagged.json out/09_flagged/minhash_flagged.json \\
        --bba data/bba_en.parquet data/bba_hi.parquet \\
        --outdir out/10_flagged_scored --report reports/13_flagged_vs_ayurparam.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from collections import Counter

import numpy as np


def normalise(text: str) -> str:
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    s = re.sub(r"[‘’“”]", "'", s)
    s = re.sub(r"[^\w\sऀ-ॿ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def dump(p, rows):
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
    df = pd.concat(frames, ignore_index=True)
    if "question" not in df.columns:
        raise SystemExit("BBA file has no 'question' column")
    return df


def score(rows, bba_q, bba_id, bba_raw, vec, topk):
    """Best cosine against all of BBA, best Levenshtein among top-k candidates."""
    import Levenshtein
    ours = [normalise(r.get("question", "")) for r in rows]
    Xo, Xb = vec.transform(ours), vec.transform(bba_q)
    S = (Xo @ Xb.T).toarray()
    best_cos = S.max(axis=1)
    best_idx = S.argmax(axis=1)
    k = min(topk, len(bba_q))
    top = np.argpartition(-S, kth=k - 1, axis=1)[:, :k]
    best_lev = np.zeros(len(rows))
    for i in range(len(rows)):
        best_lev[i] = max(Levenshtein.ratio(ours[i], bba_q[j]) for j in top[i])
    out = []
    for i, r in enumerate(rows):
        r = dict(r)
        r["bba_max_cosine"] = round(float(best_cos[i]), 4)
        r["bba_max_levenshtein"] = round(float(best_lev[i]), 4)
        r["bba_match_id"] = bba_id[int(best_idx[i])]
        r["bba_match_question"] = bba_raw[int(best_idx[i])]
        out.append(r)
    return out


def summarise(rows, cos_th, lev_th, ladder):
    c = np.array([r["bba_max_cosine"] for r in rows])
    l = np.array([r["bba_max_levenshtein"] for r in rows])
    groups = {}
    for r in rows:
        g = r.get("dup_group_id", r.get("question_id"))
        groups[g] = max(groups.get(g, 0.0), r["bba_max_cosine"])
    gv = np.array(list(groups.values()))
    return {
        "questions": len(rows),
        "groups": len(groups),
        "matches_at_operating_threshold": int(((c >= cos_th) | (l >= lev_th)).sum()),
        "cosine": {"mean": round(float(c.mean()), 4), "max": round(float(c.max()), 4),
                   "p50": round(float(np.percentile(c, 50)), 4),
                   "p95": round(float(np.percentile(c, 95)), 4),
                   "p99": round(float(np.percentile(c, 99)), 4)},
        "levenshtein": {"mean": round(float(l.mean()), 4), "max": round(float(l.max()), 4)},
        "questions_above": {str(t): int((c >= t).sum()) for t in ladder},
        "groups_above": {str(t): int((gv >= t).sum()) for t in ladder},
        "group_cosine_mean": round(float(gv.mean()), 4),
        "by_question_type": dict(Counter(r.get("question_type") for r in rows).most_common()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--bba", nargs="+", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", default="13_flagged_vs_ayurparam.json")
    ap.add_argument("--cos-th", type=float, default=0.80)
    ap.add_argument("--lev-th", type=float, default=0.85)
    ap.add_argument("--topk", type=int, default=20)
    a = ap.parse_args()

    from sklearn.feature_extraction.text import HashingVectorizer
    os.makedirs(a.outdir, exist_ok=True)
    vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 4),
                            n_features=2 ** 18, norm="l2", alternate_sign=False)

    bba = load_bba(a.bba)
    bba_q = [normalise(q) for q in bba["question"].tolist()]
    bba_id = [str(x) for x in (bba["id"].tolist() if "id" in bba.columns
                               else list(range(len(bba))))]
    bba_raw = [str(x) for x in bba["question"].tolist()]
    print("BBA: %d questions" % len(bba_q))

    ladder = [0.50, 0.60, 0.65, 0.70, 0.75, 0.80]
    rep, scored = {"bba_questions": len(bba_q), "operating_threshold":
                   {"cosine": a.cos_th, "levenshtein": a.lev_th}, "sets": {}}, {}

    for path in a.sets:
        name = os.path.basename(path).replace("_flagged.json", "").replace(".json", "")
        rows = load(path)
        out = score(rows, bba_q, bba_id, bba_raw, vec, a.topk)
        dump(os.path.join(a.outdir, "%s_scored.json" % name), out)
        rep["sets"][name] = summarise(out, a.cos_th, a.lev_th, ladder)
        scored[name] = out
        s = rep["sets"][name]
        print("\n%-9s %5d questions / %4d groups | matches %d | cos mean %.4f max %.4f"
              % (name, s["questions"], s["groups"],
                 s["matches_at_operating_threshold"], s["cosine"]["mean"], s["cosine"]["max"]))
        print("           above:", s["questions_above"])

    # ---- head-to-head ------------------------------------------------
    if len(scored) == 2:
        (n1, r1), (n2, r2) = list(scored.items())
        i1 = {r["question_id"] for r in r1}
        i2 = {r["question_id"] for r in r2}
        s1, s2 = rep["sets"][n1], rep["sets"][n2]
        better = (n1 if s1["group_cosine_mean"] > s2["group_cosine_mean"] else n2)
        rep["head_to_head"] = {
            "a": n1, "b": n2,
            "a_is_subset_of_b": i1 <= i2, "b_is_subset_of_a": i2 <= i1,
            "shared_questions": len(i1 & i2),
            "only_a": len(i1 - i2), "only_b": len(i2 - i1),
            "closer_to_benchmark_by_group_mean_cosine": better,
            "verdict": ("%s is a strict superset of %s, so it dominates on coverage; "
                        "neither reaches the operating threshold." % (n2, n1)
                        if i1 <= i2 else "neither set contains the other"),
        }
        print("\nshared %d | only %s %d | only %s %d"
              % (len(i1 & i2), n1, len(i1 - i2), n2, len(i2 - i1)))
        print("closer to benchmark (group mean cosine): %s" % better)

    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nreport -> %s" % a.report)


if __name__ == "__main__":
    main()
