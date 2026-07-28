#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integrity + quality audit for the 80k v2 question set."""
import json
import os
import re
import collections

D = "/sessions/loving-trusting-wright/mnt/outputs/ayur_qa_v2"
MASTER = os.path.join(D, "ayur_qa_v2_80k.jsonl")
LETTERS = ["A", "B", "C", "D", "E"]
REQUIRED = ["question_id", "fact_id", "format_variant", "question", "correct_answer",
            "answer_text", "question_type", "difficulty", "n_options", "n_correct",
            "subject_domain", "source_book", "chunk_id", "source_richness"]
TYPES = {"MCQ", "Fill in the blanks", "Multiple selection",
         "Assertion or Reasoning", "Match the column", "Assorted"}

fails = collections.Counter()
notes = []


def fail(k, d=None):
    fails[k] += 1
    if d and fails[k] <= 3:
        notes.append("[%s] %s" % (k, str(d)[:220]))


rows = [json.loads(l) for l in open(MASTER, encoding="utf-8") if l.strip()]
print("rows parsed:", len(rows))

qid, stems = set(), set()
for r in rows:
    for k in REQUIRED:
        if k not in r:
            fail("missing_field:" + k)
    if r["question_id"] in qid:
        fail("duplicate_question_id", r["question_id"])
    qid.add(r["question_id"])

    st = re.sub(r"\s+", " ", r["question"]).strip().lower()
    if st in stems:
        fail("DUPLICATE_STEM", r["question"])
    stems.add(st)
    if len(r["question"].strip()) < 20:
        fail("stem_too_short", r["question_id"])

    opts = [r.get("option_%s" % L.lower(), "") for L in LETTERS]
    filled = [o for o in opts if str(o).strip()]
    keys = [k for k in str(r["correct_answer"]).split(",") if k]

    if r["question_type"] == "Assorted" and not filled:
        if keys:
            fail("open_ended_has_key", r["question_id"])
        if len(str(r["answer_text"]).strip()) < 10:
            fail("open_answer_too_short", r["question_id"])
        continue

    if len(filled) != r["n_options"]:
        fail("n_options_mismatch", r["question_id"])
    if len(filled) < 4:
        fail("too_few_options", r["question_id"])
    if len({str(o).strip().lower() for o in filled}) != len(filled):
        fail("duplicate_options", r["question_id"])
    if not keys:
        fail("no_answer_key", r["question_id"])
        continue
    if len(keys) != r["n_correct"]:
        fail("n_correct_mismatch", r["question_id"])
    for k in keys:
        if k not in LETTERS[:len(filled)]:
            fail("key_out_of_range", "%s -> %s" % (r["question_id"], k))

    # single vs multi answer
    if r["question_type"] == "Multiple selection":
        if len(keys) < 2:
            fail("multiselect_single_key", r["question_id"])
        if len(filled) != 5:
            fail("multiselect_not_5_options", r["question_id"])
        if len(keys) >= len(filled):
            fail("multiselect_all_correct", r["question_id"])
    else:
        if len(keys) != 1:
            fail("single_answer_has_multiple_keys", r["question_id"])

    # key text must match the keyed options
    keyed = [filled[LETTERS.index(k)] for k in keys if k in LETTERS[:len(filled)]]
    if len(keys) == 1:
        if str(keyed[0]).strip() != str(r["answer_text"]).strip():
            fail("answer_text_mismatch", r["question_id"])
    else:
        want = {s.strip() for s in str(r["answer_text"]).split(" || ")}
        got = {str(k).strip() for k in keyed}
        if want != got:
            fail("multi_answer_text_mismatch",
                 "%s want=%s got=%s" % (r["question_id"], list(want)[:1], list(got)[:1]))
        if "answer_texts" in r and {str(x).strip() for x in r["answer_texts"]} != got:
            fail("answer_texts_list_mismatch", r["question_id"])

    # leakage: key visible in stem outside the option block
    body = re.sub(r"\s+", " ", r["question"]).lower()
    for o in filled:
        body = body.replace(re.sub(r"\s+", " ", str(o)).lower(), " ")
    for kt in keyed:
        a = re.sub(r"\s+", " ", str(kt)).lower()
        if len(a) >= 6 and a in body:
            fail("answer_leaks_into_stem", r["question_id"])
            break
    ctx = re.sub(r"\s+", " ", r.get("context", "")).lower()
    if ctx:
        for kt in keyed:
            a = re.sub(r"\s+", " ", str(kt)).lower()
            if len(a) >= 6 and a in ctx:
                fail("answer_leaks_into_context", r["question_id"])
                break
    if ctx and r["question_type"] == "Assertion or Reasoning":
        fail("verdict_question_has_context", r["question_id"])

    if r["difficulty"] not in ("Easy", "Medium", "Hard"):
        fail("bad_difficulty", r["difficulty"])
    if r["question_type"] not in TYPES:
        fail("bad_type", r["question_type"])
    if r["question_type"] == "Fill in the blanks" and "____" not in r["question"]:
        fail("fib_without_blank", r["question_id"])
    if r["question_type"] == "Match the column":
        if "Column A" not in r["question"] or "Column B" not in r["question"]:
            fail("mtc_missing_columns", r["question_id"])
        if not re.fullmatch(r"(i|ii|iii|iv)-[abcd](, (i|ii|iii|iv)-[abcd]){3}", r["answer_text"]):
            fail("mtc_bad_key", r["answer_text"])
    if r["question_type"] == "Assertion or Reasoning":
        if "Assertion (A):" not in r["question"] or "Reason (R):" not in r["question"]:
            fail("ar_missing_statements", r["question_id"])
    if r["question_type"] == "Multiple selection" and "Select ALL that apply" not in r["question"]:
        fail("multiselect_missing_instruction", r["question_id"])
    if not r["chunk_id"] or not r["source_book"]:
        fail("missing_provenance", r["question_id"])
    if not isinstance(r["source_richness"], int) or r["source_richness"] < 0:
        fail("bad_richness", r["question_id"])

print("\n=== FAILURES ===")
print("none" if not fails else "")
for k, v in fails.most_common():
    print("%-38s %d" % (k, v))
for n in notes[:12]:
    print("  ", n)

print("\n=== DISTRIBUTIONS ===")
for f in ("question_type", "difficulty", "source_book"):
    print("\n%s:" % f)
    for k, v in collections.Counter(r[f] for r in rows).most_common():
        print("   %-46s %6d  (%4.1f%%)" % (k, v, 100 * v / len(rows)))

keyed_rows = [r for r in rows if r["correct_answer"]]
single = [r for r in keyed_rows if r["question_type"] != "Multiple selection"]
print("\nanswer-letter balance (single-answer items, n=%d):" % len(single))
c = collections.Counter(r["correct_answer"] for r in single)
for k in LETTERS[:4]:
    print("   %s  %6d  (%4.1f%%)" % (k, c[k], 100 * c[k] / max(len(single), 1)))

ms = [r for r in rows if r["question_type"] == "Multiple selection"]
print("\nmulti-select: n=%d  correct-per-item: %s"
      % (len(ms), dict(collections.Counter(r["n_correct"] for r in ms))))

print("\n=== MULTI-FORMAT REUSE (the point of fact_id) ===")
byfact = collections.Counter(r["fact_id"] for r in rows)
print("distinct facts            :", len(byfact))
print("mean questions per fact   : %.2f" % (len(rows) / len(byfact)))
print("facts rendered in >1 format:",
      sum(1 for f, n in byfact.items() if n > 1))
spread = collections.Counter()
tmp = collections.defaultdict(set)
for r in rows:
    tmp[r["fact_id"]].add(r["question_type"])
for f, s in tmp.items():
    spread[len(s)] += 1
print("distinct FORMATS per fact :", dict(sorted(spread.items())))

print("\n=== COVERAGE ===")
IN = "/sessions/loving-trusting-wright/mnt/uploads"
BF = {"Charaka Samhita": "FINAL_Charaka_Samhita.jsonl",
      "Sushruta Samhita": "FINAL_Sushruta_Samhita.jsonl",
      "Ashtanga Hridaya": "FINAL_Ashtanga_Hridaya.jsonl",
      "Sharangadhara Samhita": "FINAL_Sharangadhara_Samhita.jsonl",
      "Bhavaprakasha Nighantu": "FINAL_B01_Bhavaprakasha_Nighantu.jsonl",
      "Madhava Nidanam (Part 1)": "FINAL_B02_Madhavanidanam_Part1.jsonl",
      "Madhava Nidanam (Part 2)": "FINAL_B03_Madhavanidanam_Part2.jsonl",
      "Madhava Nidana (Laghutrayi)": "FINAL_Madhava_Nidana_LaghuTrayi.jsonl"}
print("%-30s %7s %8s %8s %9s" % ("book", "chunks", "covered", "cover%", "questions"))
tc = tu = 0
for b, f in BF.items():
    ids = {json.loads(l)["chunk_id"] for l in open(os.path.join(IN, f), encoding="utf-8") if l.strip()}
    used = {r["chunk_id"] for r in rows if r["source_book"] == b}
    n = sum(1 for r in rows if r["source_book"] == b)
    tc += len(ids); tu += len(used & ids)
    print("%-30s %7d %8d %7.1f%% %9d" % (b, len(ids), len(used & ids),
                                         100 * len(used & ids) / len(ids), n))
print("%-30s %7d %8d %7.1f%%" % ("TOTAL", tc, tu, 100 * tu / tc))

tr = {r["fact_id"] for r in (json.loads(l) for l in open(os.path.join(D, "train.jsonl"), encoding="utf-8") if l.strip())}
va = {r["fact_id"] for r in (json.loads(l) for l in open(os.path.join(D, "validation.jsonl"), encoding="utf-8") if l.strip())}
print("\ntrain facts=%d  val facts=%d  OVERLAP=%d" % (len(tr), len(va), len(tr & va)))
if tr & va:
    fail("train_val_fact_overlap")

print("\n" + ("ALL CHECKS PASSED" if not fails else "FAILURES PRESENT (see above)"))
