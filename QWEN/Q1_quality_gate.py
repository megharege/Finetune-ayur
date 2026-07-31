#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q1 --- Quality gate for LLM-generated questions.
================================================

The notebook validates each generation as it is produced, but that check runs on
one item at a time and cannot see the corpus. This pass sees everything, and
catches the failure modes that only show up in aggregate.

CHECKS, in the order they fire:

  schema         required fields present, option count matches the format
  answer_in_opts the gold answer is one of the options --- an item whose answer
                 is not among its choices is unanswerable and silently poisons
                 both training and evaluation
  answer_leak    the answer string appears inside the question stem
  hidden_context "according to the passage above" and friends; at inference time
                 there is no passage, so the item is unanswerable
  option_dupes   two options identical after normalisation, which makes the item
                 either trivially wrong or ambiguous
  degenerate     option shorter than 2 characters, or a stem that is mostly
                 punctuation
  position_bias  CORPUS-LEVEL. If the correct answer sits at option A far more
                 often than chance, a model can score well by always answering A
                 and learn nothing. Reported, and optionally repaired by
                 shuffling options (--fix-position).
  devanagari     rows marked language=hi whose stem has almost no Devanagari, and
                 vice versa --- the language label is used downstream to build
                 per-language files, so a wrong label propagates

Rows failing anything except position_bias are dropped and written to
``--rejects`` so the loss is inspectable rather than silent.

Usage
    python Q1_quality_gate.py --in master_80k_qwen.jsonl --out out/Q1_clean.jsonl \\
        --rejects out/Q1_rejects.jsonl --report reports/Q1_quality.json [--fix-position]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import unicodedata
from collections import Counter, defaultdict

LETTERS = ["a", "b", "c", "d", "e"]
DEVA = re.compile(r"[ऀ-ॿ]")
HIDDEN = re.compile(
    r"(according to the (above|given|following) (passage|text|verse)"
    r"|in the (above|given) (passage|text)"
    r"|as (stated|mentioned) above"
    r"|उपरोक्त गद्यांश|दिए गए गद्यांश)", re.I)
REQUIRED = ["question_id", "fact_id", "question", "question_type",
            "correct_answer", "answer_text", "language", "source_book"]


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


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


def options(r):
    return {L: norm(r.get("option_%s" % L)) for L in LETTERS
            if norm(r.get("option_%s" % L))}


def check(r):
    """Return a reason string if the row should be dropped, else None."""
    for f in REQUIRED:
        if not str(r.get(f, "")).strip():
            return "missing_field:%s" % f

    q = norm(r.get("question"))
    if len(q) < 25:
        return "question_too_short"
    if len(re.sub(r"[^\w\sऀ-ॿ]", "", q)) < 0.5 * len(q):
        return "stem_mostly_punctuation"
    if HIDDEN.search(q):
        return "hidden_context"

    opts = options(r)
    need = 5 if r.get("question_type") == "Multiple selection" else 4
    if len(opts) < need:
        return "too_few_options"
    if any(len(v) < 2 for v in opts.values()):
        return "degenerate_option"
    if len({v.lower() for v in opts.values()}) < len(opts):
        return "duplicate_options"

    keys = [k.strip().lower() for k in str(r.get("correct_answer", "")).split(",")
            if k.strip()]
    if not keys or any(k not in opts for k in keys):
        return "answer_key_not_an_option"
    if r.get("question_type") == "Multiple selection" and len(keys) < 2:
        return "multiselect_single_answer"
    if r.get("question_type") != "Multiple selection" and len(keys) != 1:
        return "singleselect_multi_answer"

    ans = norm(r.get("answer_text"))
    if r.get("question_type") == "Multiple selection":
        # answer_text for a multi-answer item is a join of several options, so
        # membership in the option set is the wrong test. The keys were already
        # checked against the options above, which is the real guarantee.
        pass
    elif ans.lower() not in {v.lower() for v in opts.values()}:
        return "answer_text_not_an_option"

    # The leak check must not fire on closed-vocabulary option sets. A true/false
    # item legitimately contains the words "true" and "false" in its stem
    # ("state whether the following is TRUE or FALSE"), and a match-the-column
    # item's options are pairings that reference list labels in the stem. Neither
    # gives the answer away.
    closed = {"true", "false", "partially true", "cannot be determined",
              "सही", "गलत", "आंशिक रूप से सही", "निर्धारित नहीं किया जा सकता"}
    opt_vals = {v.lower() for v in opts.values()}
    is_closed_set = len(opt_vals - closed) == 0
    is_pairing = bool(re.match(r"^\s*[ivx]+\s*[-–—]\s*[a-e]", ans.strip(), re.I))
    if not (is_closed_set or is_pairing
            or r.get("question_type") == "Match the column"):
        if len(ans) > 3 and ans.lower() in q.lower():
            return "answer_leaked_into_question"

    # Language label sanity. Judged on the ASKING text, not the whole stem: an
    # English question that quotes a Sanskrit verse is still an English question,
    # and questions in this corpus quote verses constantly. So a row is only
    # flagged when the script it claims is essentially absent.
    lang = str(r.get("language", "")).lower()
    deva = len(DEVA.findall(q))
    latin = len(re.findall(r"[A-Za-z]", q))
    if lang == "hi" and deva < 10 and latin > 3 * max(deva, 1):
        return "labelled_hindi_but_no_devanagari"
    if lang == "en" and latin < 10 and deva > 3 * max(latin, 1):
        return "labelled_english_but_no_latin"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rejects", default="")
    ap.add_argument("--report", default="Q1_quality.json")
    ap.add_argument("--fix-position", action="store_true",
                    help="shuffle options to flatten answer-position bias")
    ap.add_argument("--seed", type=int, default=20260730)
    a = ap.parse_args()

    rows = load(a.inp)
    print("input             : %d rows" % len(rows))

    # Normalise the language label to the two codes BhashaBench-Ayur uses. The
    # downstream partition and the test-set mirror both key on this field, so a
    # corpus written with "English"/"Hindi" (or nothing at all) would silently
    # produce a mirror that matches on zero percent of rows. Where the label is
    # absent or unrecognised it is inferred from the script of the stem.
    LANG_MAP = {"en": "en", "eng": "en", "english": "en", "अंग्रेज़ी": "en",
                "hi": "hi", "hin": "hi", "hindi": "hi", "हिन्दी": "hi", "हिंदी": "hi"}
    relabelled = Counter()
    for r in rows:
        raw = str(r.get("language", "")).strip().lower()
        lang = LANG_MAP.get(raw)
        if lang is None:
            q = norm(r.get("question"))
            lang = "hi" if len(DEVA.findall(q)) / max(len(q), 1) > 0.30 else "en"
            relabelled[raw or "<empty>"] += 1
        r["language"] = lang
    if relabelled:
        print("language inferred : %s" % dict(relabelled.most_common(5)))

    keep, rej = [], []
    reasons = Counter()
    for r in rows:
        why = check(r)
        if why:
            reasons[why] += 1
            rr = dict(r)
            rr["reject_reason"] = why
            rej.append(rr)
        else:
            keep.append(r)

    print("passed            : %d" % len(keep))
    print("rejected          : %d" % len(rej))
    for k, v in reasons.most_common():
        print("    %-32s %6d" % (k, v))

    # ---- corpus-level: answer position bias --------------------------
    def pos_hist(rs):
        c = Counter()
        for r in rs:
            ks = [k.strip().lower() for k in str(r.get("correct_answer", "")).split(",")
                  if k.strip()]
            for k in ks:
                c[k] += 1
        return c

    before = pos_hist(keep)
    tot = sum(before.values()) or 1
    print("\nanswer position before: %s"
          % {k: "%.1f%%" % (100 * v / tot) for k, v in sorted(before.items())})

    fixed = 0
    if a.fix_position:
        rng = random.Random(a.seed)
        for r in keep:
            opts = options(r)
            if len(opts) < 2:
                continue
            ks = [k.strip().lower() for k in str(r.get("correct_answer", "")).split(",")
                  if k.strip()]
            correct_vals = [opts[k] for k in ks if k in opts]
            vals = list(opts.values())
            rng.shuffle(vals)
            letters = LETTERS[:len(vals)]
            for L, v in zip(letters, vals):
                r["option_%s" % L] = v
            for L in LETTERS[len(vals):]:
                r["option_%s" % L] = ""
            newk = [L.upper() for L, v in zip(letters, vals) if v in correct_vals]
            if newk:
                r["correct_answer"] = ",".join(sorted(newk))
                fixed += 1
        after = pos_hist(keep)
        tot2 = sum(after.values()) or 1
        print("answer position after : %s"
              % {k: "%.1f%%" % (100 * v / tot2) for k, v in sorted(after.items())})
    else:
        after = before

    dump(a.out, keep)
    if a.rejects and rej:
        dump(a.rejects, rej)

    rep = {
        "input_rows": len(rows), "passed": len(keep), "rejected": len(rej),
        "pass_rate": round(len(keep) / max(len(rows), 1), 4),
        "reject_reasons": dict(reasons.most_common()),
        "answer_position_before": {k: v for k, v in sorted(before.items())},
        "answer_position_after": {k: v for k, v in sorted(after.items())},
        "position_fixed_rows": fixed,
        "by_type": dict(Counter(r.get("question_type") for r in keep).most_common()),
        "by_language": dict(Counter(r.get("language") for r in keep)),
        "by_book": dict(Counter(r.get("source_book") for r in keep).most_common()),
        "distinct_facts": len({r.get("fact_id") for r in keep}),
        "distinct_stems": len({norm(r.get("question")) for r in keep}),
    }
    d = os.path.dirname(a.report)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nwrote %s (%d rows) | report -> %s" % (a.out, len(keep), a.report))


if __name__ == "__main__":
    main()
