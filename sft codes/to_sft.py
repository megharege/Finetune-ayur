#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert the BBA-style question set into AyurParam SFT prompt strings.

Prompt template follows the AyurParam model card:
    <context> ... <user> ... <assistant> ...
`context` is only emitted when it is non-empty (it never contains the answer).
"""
import json, os

OUT = "/sessions/loving-trusting-wright/mnt/outputs/ayur_question_set"
SFT = os.path.join(OUT, "sft")
LETTERS = ["a", "b", "c", "d"]


def render(r):
    q = r["question"]
    if r["option_a"]:
        opts = "\n".join("(%s) %s" % (L.upper(), r["option_" + L]) for L in LETTERS)
        user = "%s\n%s" % (q, opts)
        ans = "%s) %s" % (r["correct_answer"], r["answer_text"])
    else:
        user = q
        ans = r["answer_text"]
    if r.get("explanation"):
        ans += "\n\n" + r["explanation"]
    ctx = (r.get("context") or "").strip()
    head = "<context> %s " % ctx if ctx else ""
    return {
        "text": "%s<user> %s <assistant> %s" % (head, user, ans),
        "question_type": r["question_type"],
        "source_book": r["source_book"],
        "chunk_id": r["chunk_id"],
    }


def main():
    os.makedirs(SFT, exist_ok=True)
    for split in ("train", "validation"):
        src = os.path.join(OUT, "%s.jsonl" % split)
        dst = os.path.join(SFT, "%s_sft.jsonl" % split)
        n = 0
        with open(src, encoding="utf-8") as fi, open(dst, "w", encoding="utf-8") as fo:
            for line in fi:
                if not line.strip():
                    continue
                fo.write(json.dumps(render(json.loads(line)), ensure_ascii=False) + "\n")
                n += 1
        print("%-12s -> %s  (%d rows)" % (split, os.path.basename(dst), n))


if __name__ == "__main__":
    main()
