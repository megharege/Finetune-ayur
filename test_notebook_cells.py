#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execute the notebook's non-GPU cells for real, with the model stubbed out.

Proves that the config cell, validation, prompt preview, run, leaderboard, pivot,
recommend, confusion-matrix and error-analysis cells all actually run - rather than
just parsing.
"""
import json
import random
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

import ayur_benchmark as ab

NB = json.load(open("ayur_model_testing.ipynb", encoding="utf-8"))
CODE = [("\n".join(c["source"])) for c in NB["cells"] if c["cell_type"] == "code"]

DATA_DIR = Path("ayur_eval_sets")
RESULTS_DIR = Path(tempfile.mkdtemp(prefix="nb_cells_"))
MODEL_NAME = "stub/qwen-like"
FAILS = []


# ---- stub out the two GPU-bound functions -------------------------------
class _Tok:
    pad_token, pad_token_id, chat_template = "<pad>", 0, "{{ messages }}"

    def encode(self, s):
        return s.split()

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "<|user|>\n%s<|assistant|>\n" % messages[0]["content"]


def _stub_load(*a, **k):
    return _Tok(), object()


def _stub_gen(tokenizer, model, device, prompts, max_new_tokens=24):
    """Deliberately biased: right ~55% of the time, else defaults to 'A'
    (mimics the position bias real small models show)."""
    out = []
    for p in prompts:
        rng = random.Random(hash(p) % 100000)
        out.append("%s\n\nThis is stated in the classical text."
                   % (rng.choice("ABCD") if rng.random() < 0.75 else "A"))
    return out


ab.load_model, ab.generate_batch = _stub_load, _stub_gen

print("=" * 74)
print("CELL 5  — import + validate_data()")
print("=" * 74)
ok = ab.validate_data(DATA_DIR)
if not ok:
    FAILS.append("validate_data reported issues")

print("\n" + "=" * 74)
print("CELL 6  — item inspection")
print("=" * 74)
import textwrap
for dtype in ab.TASK_TYPES:
    rows = ab.load_jsonl(DATA_DIR / ab.FILENAME_MAP[dtype])
    r = rows[0]
    print("%-13s %-52s ans=%s" % (dtype, r["source"][:52], r["output"]))
    opts = json.loads(r["input"])
    if len(opts) != 4:
        FAILS.append("%s row 0 does not have 4 options" % dtype)

print("\n" + "=" * 74)
print("CELL 7  — prompt preview (chat template on/off)")
print("=" * 74)
_row = ab.load_jsonl(DATA_DIR / ab.FILENAME_MAP["mcq"])[0]
p_chat = ab.build_prompt(_row, "mcq", _Tok(), use_chat_template=True)
p_plain = ab.build_prompt(_row, "mcq", _Tok(), use_chat_template=False)
print("chat  :", p_chat[:110].replace("\n", " | "))
print("plain :", p_plain[:110].replace("\n", " | "))
if "<|user|>" not in p_chat:
    FAILS.append("chat template not applied")
if "<|user|>" in p_plain:
    FAILS.append("chat template applied when it should not be")

print("\n" + "=" * 74)
print("CELLS 8/9 — sanity run + full run")
print("=" * 74)
ab.run_benchmark(MODEL_NAME, data_dir=DATA_DIR, results_dir=RESULTS_DIR,
                 device="cpu", limit=4, batch_size=4, skip_bertscore=True,
                 save_results=False)
metrics = ab.run_benchmark(MODEL_NAME, data_dir=DATA_DIR, results_dir=RESULTS_DIR,
                           device="cpu", batch_size=4, skip_bertscore=True)
# add a second model so the comparison cells have something to compare
ab.run_benchmark("stub/weaker-model", data_dir=DATA_DIR, results_dir=RESULTS_DIR,
                 device="cpu", batch_size=4, skip_bertscore=True)

print("\n" + "=" * 74)
print("CELL 10 — report")
print("=" * 74)
report = open(RESULTS_DIR / "benchmark_report.txt", encoding="utf-8").read()
print("\n".join(report.splitlines()[:8]))

print("\n" + "=" * 74)
print("CELL 11 — leaderboard")
print("=" * 74)
lb = ab.leaderboard(RESULTS_DIR)
print(lb[["model", "type", "n", "accuracy", "f1_macro", "format_compliance"]].to_string(index=False))
if len(lb) != 8:
    FAILS.append("leaderboard should have 8 rows, got %d" % len(lb))

print("\n" + "=" * 74)
print("CELL 12 — pivot_view")
print("=" * 74)
print(ab.pivot_view(RESULTS_DIR, values=["accuracy", "format_compliance"]).to_string())

print("\n" + "=" * 74)
print("CELL 13 — recommend")
print("=" * 74)
rec = ab.recommend(RESULTS_DIR)
print(rec.to_string())
for col in ["weighted_accuracy", "lift_over_random", "composite", "mean_format_compliance"]:
    if col not in rec.columns:
        FAILS.append("recommend() missing column %s" % col)

print("\n" + "=" * 74)
print("CELL 14 — confusion matrices")
print("=" * 74)
safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", MODEL_NAME)
for dtype in ab.TASK_TYPES:
    p = RESULTS_DIR / ("confusion_matrix_%s_%s.csv" % (dtype, safe))
    if not p.exists():
        FAILS.append("missing confusion matrix for %s" % dtype)
        continue
    cm = pd.read_csv(p, index_col=0)
    print("\n=== %s ===" % dtype)
    print(cm.to_string())

print("\n" + "=" * 74)
print("CELL 15 — error analysis")
print("=" * 74)
rows = pd.read_csv(RESULTS_DIR / ("benchmark_results_%s.csv" % safe))
for col in ["correct", "question_subtype", "source_book", "difficulty", "type"]:
    if col not in rows.columns:
        FAILS.append("row CSV missing column needed by cell 15: %s" % col)
print("by type:\n%s" % rows.groupby("type")["correct"].agg(["mean", "count"]).round(3).to_string())
print("\nby difficulty:\n%s" % rows.groupby("difficulty")["correct"].agg(["mean", "count"]).round(3).to_string())
print("\nby source_book (worst 4):\n%s"
      % rows.groupby("source_book")["correct"].agg(["mean", "count"]).round(3)
            .sort_values("mean").head(4).to_string())
print("\nby subtype (worst 5):\n%s"
      % rows.groupby("question_subtype")["correct"].agg(["mean", "count"]).round(3)
            .sort_values("mean").head(5).to_string())

print("\n" + "=" * 74)
print("CELL 16 — row-level view")
print("=" * 74)
cols = ["type", "id", "gold_letter", "pred_letter", "correct"]
print(rows[cols].head(6).to_string(index=False))
wrong = rows[rows["correct"] == 0]
print("\nwrong: %d / %d" % (len(wrong), len(rows)))

print("\n" + "=" * 74)
print("CELL 18 — zip")
print("=" * 74)
zp = shutil.make_archive(str(RESULTS_DIR.parent / "ayur_benchmark_results"), "zip", RESULTS_DIR)
print("archive:", Path(zp).name, "%.1f KB" % (Path(zp).stat().st_size / 1024))

shutil.rmtree(RESULTS_DIR, ignore_errors=True)
Path(zp).unlink(missing_ok=True)

print("\n" + "=" * 74)
if FAILS:
    print("FAILURES (%d):" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    raise SystemExit(1)
print("ALL NOTEBOOK CELLS EXECUTED SUCCESSFULLY")
print("=" * 74)
