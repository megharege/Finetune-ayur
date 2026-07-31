#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q6 --- Re-emit the splits partitioned by question type and by language.
=======================================================================

Three views of the same rows, none of them a new dataset:

    by_type/<split>/<type>.json        six files per split
    by_language/<split>/<lang>.json    en / hi per split
    by_type_language/<split>/<type>__<lang>.json   the cross, when --cross

Every partition is asserted lossless --- the parts sum to the input row count
exactly, and no question_id appears twice. Rows keep every field, so
`source_book`, `subject_domain` and the AyurParam annotations travel with them
and any other grouping is one groupby away.

Usage
    python Q6_partition.py --dir final --outdir out/Q6_partitions \\
        --report reports/Q6_partitions.json [--cross]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict

SPLITS = ("train", "validation", "test")


def load(p):
    with open(p, encoding="utf-8") as fh:
        return ([json.loads(l) for l in fh if l.strip()]
                if p.endswith(".jsonl") else json.load(fh))


def dump(p, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("[\n")
        fh.write(",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows))
        fh.write("\n]\n")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_") or "unknown"


def partition(rows, keyfn, outdir, label):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    manifest, total = {}, 0
    for k, g in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        name = "%s.json" % slug(k)
        dump(os.path.join(outdir, name), g)
        manifest[str(k)] = {
            "file": name, "rows": len(g),
            "facts": len({r.get("fact_id") for r in g}),
            "by_language": dict(Counter(r.get("language") for r in g)),
            "by_book": dict(Counter(r.get("source_book") for r in g).most_common()),
        }
        total += len(g)
        print("    %-34s %6d rows -> %s" % (str(k)[:34], len(g), name))
    assert total == len(rows), "%s partition lost rows: %d != %d" % (label, total, len(rows))
    ids = [r["question_id"] for r in rows]
    assert len(ids) == len(set(ids)), "%s: duplicate question_id" % label
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="folder holding train/validation/test.json")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--report", default="Q6_partitions.json")
    ap.add_argument("--cross", action="store_true",
                    help="also emit the type x language cross-partition")
    a = ap.parse_args()

    rep = {}
    grand = 0
    for split in SPLITS:
        p = os.path.join(a.dir, "%s.json" % split)
        if not os.path.exists(p):
            print("skip %s (not found)" % split)
            continue
        rows = load(p)
        grand += len(rows)
        print("\n%s  (%d rows)" % (split, len(rows)))

        print("  by question type")
        t = partition(rows, lambda r: r.get("question_type", "unknown"),
                      os.path.join(a.outdir, "by_type", split), "%s/type" % split)

        print("  by language")
        l = partition(rows, lambda r: r.get("language", "unknown"),
                      os.path.join(a.outdir, "by_language", split), "%s/lang" % split)

        rep[split] = {"rows": len(rows), "by_type": t, "by_language": l}

        if a.cross:
            print("  by type x language")
            c = partition(rows,
                          lambda r: "%s__%s" % (r.get("question_type", "unknown"),
                                                r.get("language", "unknown")),
                          os.path.join(a.outdir, "by_type_language", split),
                          "%s/cross" % split)
            rep[split]["by_type_language"] = c

    rep["_total_rows"] = grand
    d = os.path.dirname(a.report)
    if d:
        os.makedirs(d, exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\ntotal rows partitioned: %d | report -> %s" % (grand, a.report))


if __name__ == "__main__":
    main()
