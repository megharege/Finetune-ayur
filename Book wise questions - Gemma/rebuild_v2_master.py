#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the 80k master from the per-book pool, applying the two fixes:

  1. multiple-selection `answer_text` is re-derived from the keyed options using a
     delimiter that cannot occur inside them (option text may contain ';'), and a
     structured `answer_texts` list is added;
  2. open-ended items whose answer is OCR junk are dropped.

The per-book files are the unchanged generator output, so this is a normalisation
pass, not a regeneration.
"""
import hashlib
import json
import os
import random
import collections

import generate_v2 as V
import generate_questions as G

MS_SEP = " || "
LETTERS = ["A", "B", "C", "D", "E"]
OUT = V.OUT_DIR


def degenerate(text):
    t = G.norm_ws(text)
    return len(t) < 25 or sum(c.isalpha() for c in t) < 0.5 * len(t)


def main():
    pool, seen = [], set()
    dropped_junk = fixed_ms = 0
    for _f, book, _c in V.BOOKS:
        for line in open(V.outfile(book), encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            opts = [r.get("option_%s" % L.lower(), "") for L in LETTERS]
            filled = [o for o in opts if str(o).strip()]
            keys = [k for k in str(r["correct_answer"]).split(",") if k]

            if not filled:
                if degenerate(r["answer_text"]):
                    dropped_junk += 1
                    continue
            elif r["question_type"] == "Multiple selection":
                keyed = [filled[LETTERS.index(k)] for k in keys]
                new = MS_SEP.join(keyed)
                if new != r["answer_text"]:
                    fixed_ms += 1
                r["answer_text"] = new
                r["answer_texts"] = keyed
            k = hashlib.md5(G.norm_ws(r["question"]).lower().encode("utf-8")).hexdigest()
            if k in seen:
                continue
            seen.add(k)
            pool.append(r)

    print("pool after normalisation: %d  (junk dropped %d, multi-select answers fixed %d)"
          % (len(pool), dropped_junk, fixed_ms))

    kept, note = V.select(pool, V.TARGET_TOTAL)
    print(note)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "ayur_qa_v2_80k.jsonl"), "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    facts = sorted({r["fact_id"] for r in kept})
    random.Random(V.SEED).shuffle(facts)
    val = set(facts[:max(1, int(len(facts) * 0.10))])
    train = [r for r in kept if r["fact_id"] not in val]
    valid = [r for r in kept if r["fact_id"] in val]
    for name, rr in (("train.jsonl", train), ("validation.jsonl", valid)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            for r in rr:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "total": len(kept),
        "by_type": dict(collections.Counter(r["question_type"] for r in kept)),
        "by_variant": dict(collections.Counter(r["format_variant"] for r in kept).most_common()),
        "by_book": dict(collections.Counter(r["source_book"] for r in kept)),
        "by_difficulty": dict(collections.Counter(r["difficulty"] for r in kept)),
        "by_fact_kind": dict(collections.Counter(r["fact_kind"] for r in kept)),
        "distinct_facts": len({r["fact_id"] for r in kept}),
        "distinct_chunks": len({(r["source_book"], r["chunk_id"]) for r in kept}),
        "train": len(train), "validation": len(valid),
        "multi_select_separator": MS_SEP,
    }
    with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)
    print("train=%d validation=%d facts=%d chunks=%d"
          % (len(train), len(valid), stats["distinct_facts"], stats["distinct_chunks"]))
    print(json.dumps(stats["by_type"], indent=2))


if __name__ == "__main__":
    main()
