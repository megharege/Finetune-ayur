#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 3 --- Rank every question by difficulty, in BhashaBench's Easy/Medium/Hard scheme.
=======================================================================================

BhashaBench-Ayur reports accuracy split by question_level (Easy / Medium / Hard),
so our questions need a comparable label. The label the generator assigned was a
crude rule (format + commentary length). This replaces it with a scored ranking.

Difficulty here means "how hard is this to answer correctly", estimated from
properties of the item itself. Six signals, each z-scored then weighted:

  1. format_prior     (w .30) Empirical, from our own 4-model benchmark: no model
                              exceeded chance on assertion-reason or match-the-
                              column, while MCQ was solved well above chance. The
                              format itself is the strongest single predictor.
  2. distractor_conf  (w .25) Mean character-trigram cosine between the correct
                              option and the distractors. Confusable options make
                              an item hard; an obviously-odd distractor makes it
                              easy. This is the main *within-format* signal.
  3. evidence_thin    (w .15) Inverse source_richness. Fewer characters of source
                              behind a fact means a thinner basis for answering.
  4. devanagari       (w .15) Fraction of the stem in Devanagari. Items requiring
                              the verse to be read are harder for models whose
                              Indic pretraining is limited.
  5. option_length    (w .10) Longer options carry more to disambiguate.
  6. multi_answer     (w .05) Multiple-selection items require every correct
                              option to be found, so they are strictly harder.

Three labels are emitted so you can choose:

  difficulty_score        continuous 0-1, the raw ranking
  difficulty_tertile      Easy/Medium/Hard at equal thirds
  difficulty_bba          Easy/Medium/Hard calibrated to BhashaBench-Ayur's own
                          published proportions (53.1 / 42.2 / 4.7), so a
                          per-difficulty table is comparable to theirs

If --validate is given a row-level results CSV from the model benchmark, the
script reports observed accuracy per predicted band --- which is the only honest
check that the ranking means anything.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np

LETTERS = ["a", "b", "c", "d", "e"]
DEVA = re.compile(r"[ऀ-ॿ]")

# Empirical per-format difficulty, from the 4-model selection benchmark:
# mean accuracy across Qwen2.5-3B, Phi-3-mini, gemma-2-2b, Llama-3.2-3B.
# Higher prior = harder.
FORMAT_PRIOR = {
    "Match the column":       1.00,   # mean acc .29, at chance
    "Assertion or Reasoning": 0.95,   # mean acc .26, at chance
    "Multiple selection":     0.85,   # every correct option must be found
    "Fill in the blanks":     0.55,   # mean acc .48
    "MCQ":                    0.40,   # mean acc .52, best solved
    "Assorted":               0.60,
}
# BhashaBench-Ayur published difficulty mix (7944 / 6314 / 705 of 14963)
BBA_MIX = (0.5309, 0.4220, 0.0471)


def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\sऀ-ॿ]", " ", s)).strip()


def trigrams(s):
    s = " " + norm(s) + " "
    return {s[i:i + 3] for i in range(max(1, len(s) - 2))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def zscore(v):
    v = np.asarray(v, dtype=np.float64)
    sd = v.std()
    return np.zeros_like(v) if sd < 1e-9 else (v - v.mean()) / sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default="03_difficulty_report.json")
    ap.add_argument("--validate", default="",
                    help="row-level benchmark CSV to sanity-check the ranking")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    n = len(rows)
    print("loaded %d rows" % n)

    f_prior, f_conf, f_thin, f_deva, f_optlen, f_multi = ([] for _ in range(6))

    for r in rows:
        f_prior.append(FORMAT_PRIOR.get(r.get("question_type", ""), 0.6))

        opts = [r.get("option_%s" % L, "") for L in LETTERS]
        opts = [o for o in opts if str(o).strip()]
        keys = [k for k in str(r.get("correct_answer", "")).split(",") if k]
        correct, wrong = [], []
        for i, o in enumerate(opts):
            (correct if LETTERS[i].upper() in keys else wrong).append(o)
        if correct and wrong:
            cg = trigrams(correct[0])
            f_conf.append(float(np.mean([jaccard(cg, trigrams(w)) for w in wrong])))
        else:
            f_conf.append(0.35)                       # open-ended: neutral

        rich = float(r.get("source_richness", 0) or 0)
        f_thin.append(1.0 / np.log1p(max(rich, 1.0)))

        q = str(r.get("question", ""))
        f_deva.append(len(DEVA.findall(q)) / max(len(q), 1))

        f_optlen.append(float(np.mean([len(str(o)) for o in opts])) if opts else 60.0)
        f_multi.append(1.0 if int(r.get("n_correct", 1) or 1) > 1 else 0.0)

    score = (0.30 * zscore(f_prior) + 0.25 * zscore(f_conf) + 0.15 * zscore(f_thin)
             + 0.15 * zscore(f_deva) + 0.10 * zscore(f_optlen) + 0.05 * zscore(f_multi))
    lo, hi = score.min(), score.max()
    score01 = (score - lo) / (hi - lo) if hi > lo else np.zeros_like(score)

    order = np.argsort(score01)
    rank = np.empty(n, dtype=np.int64)
    rank[order] = np.arange(n)
    pct = rank / max(n - 1, 1)

    t1, t2 = 1 / 3, 2 / 3
    b1, b2 = BBA_MIX[0], BBA_MIX[0] + BBA_MIX[1]

    for i, r in enumerate(rows):
        r["difficulty_score"] = round(float(score01[i]), 4)
        r["difficulty_percentile"] = round(float(pct[i]), 4)
        r["difficulty_tertile"] = ("Easy" if pct[i] < t1 else
                                   "Medium" if pct[i] < t2 else "Hard")
        r["difficulty_bba"] = ("Easy" if pct[i] < b1 else
                               "Medium" if pct[i] < b2 else "Hard")
        r["difficulty_features"] = {
            "format_prior": round(float(f_prior[i]), 3),
            "distractor_confusability": round(float(f_conf[i]), 4),
            "evidence_thinness": round(float(f_thin[i]), 4),
            "devanagari_fraction": round(float(f_deva[i]), 4),
            "mean_option_len": round(float(f_optlen[i]), 1),
            "multi_answer": int(f_multi[i]),
        }

    with open(a.out, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    rep = {
        "rows": n,
        "weights": {"format_prior": .30, "distractor_confusability": .25,
                    "evidence_thinness": .15, "devanagari_fraction": .15,
                    "mean_option_len": .10, "multi_answer": .05},
        "tertile_counts": dict(Counter(r["difficulty_tertile"] for r in rows)),
        "bba_calibrated_counts": dict(Counter(r["difficulty_bba"] for r in rows)),
        "bba_target_mix": {"Easy": BBA_MIX[0], "Medium": BBA_MIX[1], "Hard": BBA_MIX[2]},
        "mean_score_by_type": {
            t: round(float(np.mean([r["difficulty_score"] for r in rows
                                    if r.get("question_type") == t])), 4)
            for t in sorted({r.get("question_type") for r in rows})},
    }

    # ---- empirical validation against observed model accuracy ----
    if a.validate:
        import csv
        obs = list(csv.DictReader(open(a.validate, encoding="utf-8")))
        by_id = {r.get("question_id"): r for r in rows}
        buckets = defaultdict(list)
        hit = 0
        for o in obs:
            q = by_id.get(o.get("id"))
            if q is not None:
                buckets[q["difficulty_tertile"]].append(int(o.get("correct", 0)))
                hit += 1
        rep["validation"] = {
            "matched_items": hit,
            "observed_accuracy_by_predicted_band": {
                k: {"n": len(v), "accuracy": round(sum(v) / len(v), 3)}
                for k, v in sorted(buckets.items()) if v},
            "note": "monotonically decreasing accuracy Easy>Medium>Hard means the "
                    "ranking predicts real difficulty",
        }

    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("tertile      :", rep["tertile_counts"])
    print("BBA-calibrated:", rep["bba_calibrated_counts"])
    print("mean score by type:")
    for t, v in sorted(rep["mean_score_by_type"].items(), key=lambda x: -x[1]):
        print("   %-26s %.4f" % (t, v))
    if a.validate and "validation" in rep:
        print("validation:", rep["validation"]["observed_accuracy_by_predicted_band"])
    print("wrote %s" % a.out)


if __name__ == "__main__":
    main()
