#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert the split files to Parquet for fine-tuning.
===================================================

    python to_parquet.py --indir . --outdir parquet

Two things make this more than `pd.read_json().to_parquet()`:

RAGGED SCHEMA. The rows come from two merged sources with different field sets ---
48 keys in the union, only 36 present on every row. Parquet needs one schema for
the whole file, so the union is materialised and missing values become nulls.
Left alone, pandas would infer a different column set per file and
`load_dataset` would then refuse to concatenate train with validation.

NESTED FIELD. `difficulty_features` is a dict. Parquet can store a struct, but a
struct whose keys vary by row produces a schema that some readers reject, and
HF `datasets` in particular will fail to align it across splits. It is stored as
a JSON string instead --- one `json.loads` to get it back, and every reader
handles a string column.

Also enforced: `question_id` unique and non-null, `question` non-empty. A silent
null in either would surface much later as a broken batch.
"""
from __future__ import annotations

import argparse
import json
import os

import pandas as pd

SPLITS = ("train", "validation", "test", "extra_test")


def load_any(path: str):
    with open(path, encoding="utf-8") as fh:
        head = fh.read(2048)
        fh.seek(0)
        if head.lstrip().startswith("["):
            return json.load(fh)
        return [json.loads(l) for l in fh if l.strip()]


def find(indir: str, name: str):
    for ext in (".json", ".jsonl"):
        p = os.path.join(indir, name + ext)
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=".")
    ap.add_argument("--outdir", default="parquet")
    ap.add_argument("--compression", default="snappy",
                    choices=["snappy", "zstd", "gzip", "brotli", "none"],
                    help="snappy is the default everywhere and decodes fastest; "
                         "zstd is ~30%% smaller if size matters more than speed")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)

    # ---- pass 1: union of keys across every split ---------------------
    # Done across ALL splits, not per file: if train carried a column that
    # validation lacked, the two Parquet files would have different schemas and
    # datasets.load_dataset() would fail to build one DatasetDict.
    loaded, union = {}, set()
    for s in SPLITS:
        p = find(a.indir, s)
        if not p:
            continue
        rows = load_any(p)
        loaded[s] = rows
        for r in rows:
            union |= set(r)
    if not loaded:
        raise SystemExit("no split files found in %s" % a.indir)

    cols = sorted(union)
    print("splits found : %s" % ", ".join(loaded))
    print("union columns: %d" % len(cols))

    nested = set()
    for rows in loaded.values():
        for r in rows[:500]:
            for k, v in r.items():
                if isinstance(v, (dict, list)):
                    nested.add(k)
    if nested:
        print("nested -> JSON string: %s" % sorted(nested))

    # ---- pass 2: write ------------------------------------------------
    manifest = {}
    for s, rows in loaded.items():
        flat = []
        for r in rows:
            out = {}
            for c in cols:
                v = r.get(c)
                out[c] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            flat.append(out)

        df = pd.DataFrame(flat, columns=cols)

        # integrity, before anything downstream depends on it
        assert df["question_id"].notna().all(), "%s: null question_id" % s
        assert df["question_id"].is_unique, "%s: duplicate question_id" % s
        assert df["question"].fillna("").str.strip().ne("").all(), \
            "%s: empty question text" % s

        # object columns holding only strings/None -> pandas string dtype, so
        # the Parquet schema says UTF8 rather than a generic binary blob
        for c in cols:
            if df[c].dtype == object:
                sample = df[c].dropna()
                if len(sample) and sample.map(type).eq(str).all():
                    df[c] = df[c].astype("string")

        path = os.path.join(a.outdir, "%s.parquet" % s)
        df.to_parquet(path, index=False, engine="pyarrow",
                      compression=None if a.compression == "none" else a.compression)
        size = os.path.getsize(path)
        manifest[s] = {"rows": len(df), "columns": len(df.columns),
                       "bytes": size, "file": os.path.basename(path)}
        print("  %-11s %6d rows x %d cols -> %s (%.1f MB)"
              % (s, len(df), len(df.columns), os.path.basename(path), size / 1e6))

    # ---- verify by reading back ---------------------------------------
    print("\nverifying round-trip")
    schemas = {}
    for s in manifest:
        df = pd.read_parquet(os.path.join(a.outdir, "%s.parquet" % s))
        schemas[s] = tuple(df.columns)
        assert len(df) == manifest[s]["rows"], "%s: row count changed" % s
        assert df["question_id"].is_unique, "%s: duplicate id after write" % s
    if len(set(schemas.values())) != 1:
        raise SystemExit("splits have different schemas --- load_dataset would fail")
    print("  all splits share one schema of %d columns" % len(cols))
    print("  row counts preserved, ids still unique")

    json.dump({"columns": cols, "nested_as_json_string": sorted(nested),
               "splits": manifest, "compression": a.compression},
              open(os.path.join(a.outdir, "_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\nwrote %s" % a.outdir)


if __name__ == "__main__":
    main()
