#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integrity + quality audit for the generated Ayurveda question set."""
import json, os, re, sys, collections

OUT = "/sessions/loving-trusting-wright/mnt/outputs/ayur_question_set"
MASTER = os.path.join(OUT, "ayurbench_shloka_all_books.jsonl")
LETTERS = ["A", "B", "C", "D"]
REQUIRED = ["question_id", "question", "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "answer_text", "question_type", "difficulty",
            "subject_domain", "language", "source_book", "chunk_id"]

fails = collections.Counter()
notes = []


def fail(k, detail=None):
    fails[k] += 1
    if detail and fails[k] <= 3:
        notes.append("[%s] %s" % (k, detail[:300]))


rows = []
with open(MASTER, encoding="utf-8") as fh:
    for i, line in enumerate(fh, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            fail("invalid_json", "line %d: %s" % (i, e))

print("rows parsed:", len(rows))

qid_seen, qtext_seen = set(), set()
for r in rows:
    for k in REQUIRED:
        if k not in r:
            fail("missing_field:" + k)

    if r["question_id"] in qid_seen:
        fail("duplicate_question_id", r["question_id"])
    qid_seen.add(r["question_id"])

    qn = re.sub(r"\s+", " ", r["question"]).strip().lower()
    if qn in qtext_seen:
        fail("duplicate_question_text", r["question"])
    qtext_seen.add(qn)

    if len(r["question"].strip()) < 20:
        fail("stem_too_short", r["question"])

    opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
    has_opts = any(o.strip() for o in opts)

    if has_opts:
        if not all(o.strip() for o in opts):
            fail("partial_options", r["question_id"])
            continue
        if len({o.strip().lower() for o in opts}) != 4:
            fail("duplicate_options", " | ".join(opts))
        if r["correct_answer"] not in LETTERS:
            fail("bad_answer_letter", str(r["correct_answer"]))
            continue
        keyed = opts[LETTERS.index(r["correct_answer"])]
        if keyed.strip() != r["answer_text"].strip():
            fail("answer_key_mismatch",
                 "%s key=%s -> %r vs answer_text=%r" % (r["question_id"], r["correct_answer"],
                                                        keyed, r["answer_text"]))
        # leakage: answer visible in stem outside the options block
        stem = re.sub(r"\s+", " ", r["question"]).lower()
        for o in opts:
            stem = stem.replace(re.sub(r"\s+", " ", o).lower(), " ")
        a = re.sub(r"\s+", " ", r["answer_text"]).lower()
        if len(a) >= 5 and a in stem:
            fail("answer_leaks_into_stem", r["question_id"] + " :: " + r["answer_text"])
        # leakage via context column
        ctx = re.sub(r"\s+", " ", r.get("context", "")).lower()
        if len(a) >= 5 and ctx and a in ctx:
            fail("answer_leaks_into_context", r["question_id"])
        # verdict questions must ship no source text at all
        if ctx and (r["question_type"] == "Assertion or Reasoning"
                    or r.get("question_subtype", "").startswith("true_false")):
            fail("verdict_question_has_context", r["question_id"])
    else:
        if r["correct_answer"]:
            fail("open_ended_has_letter", r["question_id"])
        if len(r["answer_text"].strip()) < 10:
            fail("open_answer_too_short", r["question_id"])

    if r["difficulty"] not in ("Easy", "Medium", "Hard"):
        fail("bad_difficulty", str(r["difficulty"]))
    if r["question_type"] not in ("MCQ", "Fill in the blanks", "Match the column",
                                  "Assertion or Reasoning", "Assorted"):
        fail("bad_type", str(r["question_type"]))

    # fill-in-the-blank must actually contain a blank
    if r["question_type"] == "Fill in the blanks" and "____" not in r["question"]:
        fail("fib_without_blank", r["question_id"])

    # match-the-column must show both columns and a valid permutation key
    if r["question_type"] == "Match the column":
        if "Column A" not in r["question"] or "Column B" not in r["question"]:
            fail("mtc_missing_columns", r["question_id"])
        if not re.fullmatch(r"(i|ii|iii|iv)-[abcd](, (i|ii|iii|iv)-[abcd]){3}", r["answer_text"]):
            fail("mtc_bad_key", r["answer_text"])
        else:
            pairs = dict(p.split("-") for p in r["answer_text"].split(", "))
            if sorted(pairs) != ["i", "ii", "iii", "iv"] or len(set(pairs.values())) != 4:
                fail("mtc_not_bijective", r["answer_text"])

    # assertion/reasoning must carry both statements
    if r["question_type"] == "Assertion or Reasoning":
        if "Assertion (A):" not in r["question"] or "Reason (R):" not in r["question"]:
            fail("ar_missing_statements", r["question_id"])

    # provenance must be present
    if not r["chunk_id"] or not r["source_book"]:
        fail("missing_provenance", r["question_id"])

print("\n=== FAILURES ===")
if not fails:
    print("none")
for k, v in fails.most_common():
    print("%-32s %d" % (k, v))
print("\n".join(notes[:20]))

mcq_like = [r for r in rows if r["correct_answer"]]
print("\n=== DISTRIBUTIONS ===")
print("total:", len(rows), " keyed:", len(mcq_like), " open-ended:", len(rows) - len(mcq_like))
for field in ("question_type", "difficulty", "grounding", "source_book", "language"):
    c = collections.Counter(r.get(field, "?") for r in rows)
    print("\n%s:" % field)
    for k, v in c.most_common():
        print("   %-58s %6d  (%4.1f%%)" % (k, v, 100 * v / len(rows)))

print("\nsubject_domain:")
for k, v in collections.Counter(r["subject_domain"] for r in rows).most_common():
    print("   %-58s %6d  (%4.1f%%)" % (k, v, 100 * v / len(rows)))

print("\nanswer letter balance (keyed items):")
c = collections.Counter(r["correct_answer"] for r in mcq_like)
for k in LETTERS:
    print("   %s  %6d  (%4.1f%%)" % (k, c[k], 100 * c[k] / max(len(mcq_like), 1)))

print("\nquestion_subtype:")
for k, v in collections.Counter(r.get("question_subtype", "") for r in rows).most_common():
    print("   %-40s %6d" % (k or "(none)", v))

print("\nAR answer-key balance:")
ar = [r for r in rows if r["question_type"] == "Assertion or Reasoning"]
for k, v in collections.Counter(r["answer_text"][:45] for r in ar).most_common():
    print("   %-48s %5d" % (k, v))

# chunk coverage
src = collections.Counter(r["chunk_id"] for r in rows)
print("\ndistinct source chunks used:", len(src))
print("median questions per used chunk:", sorted(src.values())[len(src) // 2])

# per-book coverage vs input
IN = "/sessions/loving-trusting-wright/mnt/uploads"
BOOKFILE = {
    "Charaka Samhita": "FINAL_Charaka_Samhita.jsonl",
    "Sushruta Samhita": "FINAL_Sushruta_Samhita.jsonl",
    "Ashtanga Hridaya": "FINAL_Ashtanga_Hridaya.jsonl",
    "Sharangadhara Samhita": "FINAL_Sharangadhara_Samhita.jsonl",
    "Bhavaprakasha Nighantu": "FINAL_B01_Bhavaprakasha_Nighantu.jsonl",
    "Madhava Nidanam (Part 1)": "FINAL_B02_Madhavanidanam_Part1.jsonl",
    "Madhava Nidanam (Part 2)": "FINAL_B03_Madhavanidanam_Part2.jsonl",
    "Madhava Nidana (Laghutrayi)": "FINAL_Madhava_Nidana_LaghuTrayi.jsonl",
}
print("\n=== COVERAGE PER BOOK ===")
print("%-30s %7s %7s %8s %8s" % ("book", "chunks", "covered", "cover%", "q/chunk"))
for book, f in BOOKFILE.items():
    ids = set()
    for line in open(os.path.join(IN, f), encoding="utf-8"):
        line = line.strip()
        if line:
            ids.add(json.loads(line).get("chunk_id"))
    used = {r["chunk_id"] for r in rows if r["source_book"] == book}
    n = sum(1 for r in rows if r["source_book"] == book)
    print("%-30s %7d %7d %7.1f%% %8.2f" % (book, len(ids), len(used & ids),
                                           100 * len(used & ids) / max(len(ids), 1),
                                           n / max(len(ids), 1)))

# train/val leakage
tr = {re.sub(r"\s+", " ", json.loads(l)["question"]).lower()
      for l in open(os.path.join(OUT, "train.jsonl"), encoding="utf-8") if l.strip()}
va = {re.sub(r"\s+", " ", json.loads(l)["question"]).lower()
      for l in open(os.path.join(OUT, "validation.jsonl"), encoding="utf-8") if l.strip()}
print("\ntrain/val overlap (identical stems):", len(tr & va))
print("train:", len(tr), "validation:", len(va))
