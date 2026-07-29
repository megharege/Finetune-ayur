#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEP 6 --- Re-partition the corpus by question type instead of by book.
=======================================================================

The corpus was originally emitted one file per source text. This re-emits it one
file per question type, which is the axis you actually train and evaluate on.
Nothing is dropped and nothing is duplicated: the six output files partition the
input exactly.

Every row keeps its ``source_book`` field, so the by-book view is still one
groupby away --- the change is which axis is the filename.

With --per-split, the same partition is applied inside train / validation / test
separately, giving <split>/<type>.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def partition(rows, outdir, tag=""):
    os.makedirs(outdir, exist_ok=True)
    groups = defaultdict(list)
    for r in rows:
        groups[r.get("question_type", "unknown")].append(r)
    manifest = {}
    for t, g in sorted(groups.items()):
        name = "%s.jsonl" % slug(t)
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as fh:
            for r in g:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        manifest[t] = {
            "file": name, "rows": len(g),
            "facts": len({r.get("fact_id") for r in g}),
            "books": len({r.get("source_book") for r in g}),
            "by_book": dict(Counter(r.get("source_book") for r in g).most_common()),
            "by_difficulty_bba": dict(Counter(r.get("difficulty_bba") for r in g)),
        }
        print("  %-26s %6d rows -> %s" % (t, len(g), name))
    total = sum(v["rows"] for v in manifest.values())
    assert total == len(rows), "partition lost rows: %d != %d" % (total, len(rows))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True,
                    help="single jsonl, or a directory when --per-split is used")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--per-split", action="store_true",
                    help="treat --in as a directory of train/validation/test files")
    ap.add_argument("--report", default="06_by_type_report.json")
    a = ap.parse_args()

    rep = {}
    if a.per_split:
        for split in ("train", "validation", "test"):
            for cand in ("%s_clean.jsonl" % split, "%s.jsonl" % split):
                p = os.path.join(a.inp, cand)
                if os.path.exists(p):
                    break
            else:
                print("skip %s (not found)" % split)
                continue
            rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
            print("\n%s  (%s, %d rows)" % (split, os.path.basename(p), len(rows)))
            rep[split] = partition(rows, os.path.join(a.outdir, split))
    else:
        rows = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
        print("all  (%d rows)" % len(rows))
        rep["all"] = partition(rows, a.outdir)

    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nreport -> %s" % a.report)


if __name__ == "__main__":
    main()
