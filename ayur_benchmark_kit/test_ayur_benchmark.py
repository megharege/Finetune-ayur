#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline self-test for ayur_benchmark.py — no GPU, no model download.

Checks that answer extraction handles the response styles real models emit, and
that the scoring path produces sane metrics end to end.
"""
import json
import random
from pathlib import Path

import ayur_benchmark as ab

DATA = Path("ayur_eval_sets")
FAILS = []


def check(name, got, want):
    if got != want:
        FAILS.append("%s: got %r, want %r" % (name, got, want))


print("=" * 72)
print("1. ANSWER EXTRACTION")
print("=" * 72)

opts = {"A": "Vamana karma", "B": "Virechana karma",
        "C": "Basti karma", "D": "Nasya karma"}

cases = [
    ("B", "B"),
    ("B.", "B"),
    ("(C)", "C"),
    ("**D**", "D"),
    ("D) Nasya karma", "D"),
    ("Answer: A", "A"),
    ("The answer is C.", "C"),
    ("Final answer: B", "B"),
    ("The correct option is D", "D"),
    ("Basti karma", "C"),                      # answered with option text only
    ("I think the answer is Virechana karma.", "B"),
    ("", ab.NO_ANSWER),
    ("I am not sure about this one.", ab.NO_ANSWER),
    # regression: the most common instruct-model shape (newline then rationale).
    # This is exactly what Phi-3 emitted in the original cardiac notebook.
    ("A\n\nExplanation: The verse describes the rasayana therapy.", "A"),
    ("C\nBecause the text states this in Sutrasthana.", "C"),
    ("D is the correct option.", "D"),
    # must NOT fire: leading "A" here is the English article, not option A
    ("A patient suffering from jvara should be treated with langhana.", ab.NO_ANSWER),
]
for raw, want in cases:
    got = ab.resolve_letter(raw, opts)
    check("resolve_letter(%r)" % raw, got, want)
    print("  %-42r -> %s" % (raw, got))

# match-the-column permutations stated in prose rather than as a letter
perm_opts = {"A": "i-a, ii-b, iii-c, iv-d", "B": "i-c, ii-a, iii-d, iv-b",
             "C": "i-b, ii-d, iii-a, iv-c", "D": "i-d, ii-c, iii-b, iv-a"}
for raw, want in [("i-c, ii-a, iii-d, iv-b", "B"),
                  ("The matches are i-b, ii-d, iii-a, iv-c.", "C"),
                  ("i - d, ii - c, iii - b, iv - a", "D")]:
    got = ab.resolve_letter(raw, perm_opts)
    check("perm(%r)" % raw, got, want)
    print("  %-42r -> %s" % (raw, got))

print("\n" + "=" * 72)
print("2. PROMPT CONSTRUCTION")
print("=" * 72)
rows = ab.load_jsonl(DATA / ab.FILENAME_MAP["mcq"])
p = ab.build_prompt(rows[0], "mcq", tokenizer=None, use_chat_template=False)
assert "Reply with ONLY the option letter" in p, "directive missing"
assert "(A)" in p and "(D)" in p, "options not rendered"
assert p.rstrip().endswith("Answer:"), "no generation cue"
print(p[:420] + "\n  ...")
print("  [ok] directive + 4 options + answer cue present")

print("\n" + "=" * 72)
print("3. SCORING PIPELINE (simulated predictions)")
print("=" * 72)


def fake_records(dtype, accuracy, style="letter", seed=0):
    """Build records as run_type would, with a controlled fraction correct."""
    rng = random.Random(seed)
    rows = ab.load_jsonl(DATA / ab.FILENAME_MAP[dtype])
    out = []
    for r in rows:
        o = json.loads(r["input"])
        gold = r["output"]
        if rng.random() < accuracy:
            letter = gold
        else:
            letter = rng.choice([L for L in "ABCD" if L != gold])
        if style == "letter":
            pred = letter
        elif style == "verbose":
            pred = "%s) %s\n\nThis follows from the classical text." % (letter, o[letter])
        elif style == "text":
            pred = o[letter]
        else:                                   # non-compliant chatter
            pred = "I cannot determine this from the passage provided."
        out.append({
            "type": dtype, "id": r["id"], "instruction": r["instruction"],
            "input": r["input"], "gold_letter": gold, "gold_text": r["output_text"],
            "pred": pred, "pred_letter": ab.resolve_letter(pred, o),
            "correct": 0, "source": r["source"], "source_book": r["source_book"],
            "difficulty": r["difficulty"], "question_subtype": r["question_subtype"],
            "subject_domain": r["subject_domain"], "language": "en",
        })
    for rec in out:
        rec["correct"] = int(rec["pred_letter"] == rec["gold_letter"])
    return out


for dtype in ab.TASK_TYPES:
    recs = fake_records(dtype, accuracy=0.6, style="verbose", seed=42)
    m, conf = ab.score_records(recs, device="cpu", skip_bertscore=True)
    print("\n  [%s] n=%d acc=%.2f f1_macro=%.3f f1_weighted=%.3f compliance=%.2f"
          % (dtype, m["n"], m["accuracy"], m["f1_macro"], m["f1_weighted"],
             m["format_compliance"]))
    print("       rouge1=%.3f rougeL=%.3f bleu=%.3f meteor=%.3f token_f1=%.3f"
          % (m["rouge1"], m["rougeL"], m["bleu"], m["meteor"], m["token_f1_macro"]))
    print("       confusion labels: %s" % conf["labels"])
    if not (0.4 <= m["accuracy"] <= 0.8):
        FAILS.append("%s: accuracy %.2f outside expected band for p=0.6" % (dtype, m["accuracy"]))
    if m["format_compliance"] != 1.0:
        FAILS.append("%s: verbose style should be 100%% parseable" % dtype)

print("\n  --- extraction robustness across response styles (mcq) ---")
for style in ("letter", "verbose", "text", "chatter"):
    recs = fake_records("mcq", accuracy=1.0, style=style, seed=1)
    m, _ = ab.score_records(recs, device="cpu", skip_bertscore=True)
    print("  %-9s accuracy=%.2f  compliance=%.2f" % (style, m["accuracy"], m["format_compliance"]))
    if style != "chatter" and m["accuracy"] < 1.0:
        FAILS.append("style=%s: perfect predictions scored %.2f" % (style, m["accuracy"]))
    if style == "chatter" and m["format_compliance"] != 0.0:
        FAILS.append("chatter should be 0% compliant")

print("\n  --- degenerate cases ---")
recs = fake_records("mcq", accuracy=0.0, style="letter", seed=7)
m, _ = ab.score_records(recs, device="cpu", skip_bertscore=True)
print("  all-wrong        accuracy=%.2f (expect 0.00)" % m["accuracy"])
check("all-wrong accuracy", m["accuracy"], 0.0)

recs = fake_records("mcq", accuracy=1.0, style="letter", seed=7)
m, _ = ab.score_records(recs, device="cpu", skip_bertscore=True)
print("  all-correct      accuracy=%.2f (expect 1.00)" % m["accuracy"])
check("all-correct accuracy", m["accuracy"], 1.0)

print("\n" + "=" * 72)
print("4. WRITE PATH (leaderboard / confusion / report)")
print("=" * 72)
import csv, os, shutil

import tempfile
tmp = Path(tempfile.mkdtemp(prefix="ayur_selftest_"))

for model, acc in [("fake/model-a", 0.6), ("fake/model-b", 0.35)]:
    all_metrics, all_records, confusions = {}, [], {}
    for dtype in ab.TASK_TYPES:
        recs = fake_records(dtype, acc, "verbose", seed=hash(model) % 1000)
        m, conf = ab.score_records(recs, "cpu", skip_bertscore=True)
        m["latency_sec"] = 10.0
        m["tokens_per_sec"] = 50.0
        all_metrics[dtype] = m
        all_records.extend(recs)
        confusions[dtype] = conf
    # replicate run_benchmark's writer
    import re as _re
    safe = _re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
    with open(tmp / ("benchmark_results_%s.csv" % safe), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_records[0].keys())); w.writeheader(); w.writerows(all_records)
    lb = tmp / "leaderboard.csv"
    rows_out = [{"model": model, "type": dt, **m} for dt, m in all_metrics.items()]
    existing = list(csv.DictReader(open(lb, encoding="utf-8"))) if lb.exists() else []
    existing = [r for r in existing if r.get("model") != model]
    combined = existing + [{k: ("" if v is None else v) for k, v in r.items()} for r in rows_out]
    keys = sorted({k for r in combined for k in r}, key=lambda k: (k != "model", k != "type", k != "n", k))
    with open(lb, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in combined:
            w.writerow({k: r.get(k, "") for k in keys})

print("  leaderboard rows:", len(list(csv.DictReader(open(tmp / 'leaderboard.csv', encoding='utf-8')))))
print("\n  recommend():")
print(ab.recommend(tmp).to_string())
print("\n  pivot_view():")
print(ab.pivot_view(tmp, values=["accuracy", "f1_macro"]).to_string())

lbdf = ab.leaderboard(tmp)
if len(lbdf) != 8:
    FAILS.append("leaderboard should have 8 rows (2 models x 4 types), got %d" % len(lbdf))
rec = ab.recommend(tmp)
if rec.index[0] != "fake/model-a":
    FAILS.append("recommend() should rank model-a (acc .6) above model-b (acc .35)")

shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 72)
print("5. METRIC SANITY (do the generation metrics actually move?)")
print("=" * 72)
gold = "Harītakī is the best among the rasāyana drugs described in this chapter."
for label, pred in [("identical", gold),
                    ("paraphrase", "Among the rasāyana drugs, Harītakī is said to be the best."),
                    ("unrelated", "The patient should be given a warm water bath at dawn.")]:
    r1, r2, rL = ab.rouge_scores(pred, gold)
    print("  %-11s rouge1=%.3f rougeL=%.3f bleu=%.3f meteor=%.3f token_f1=%.3f"
          % (label, r1, rL, ab.bleu_score(pred, gold), ab.meteor(pred, gold),
             ab.token_prf(pred, gold)[2]))
if ab.meteor(gold, gold) == 0.0:
    print("  NOTE: METEOR is returning 0 — nltk 'wordnet' corpus is unavailable here.")
    print("        On Kaggle with Internet ON it downloads automatically and works.")

print("\n" + "=" * 72)
print("6. FULL run_benchmark() INTEGRATION (stubbed model, no GPU/torch)")
print("=" * 72)
# Monkeypatch the two functions that need torch, so the rest of the pipeline
# (prompt build -> generate -> record -> score -> CSV/report writing) runs for real.
_real_load, _real_gen = ab.load_model, ab.generate_batch


class _StubTok:
    pad_token = "<pad>"
    pad_token_id = 0
    chat_template = None

    def encode(self, s):
        return s.split()


def _stub_load(*a, **k):
    return _StubTok(), object()


import re


def _stub_generate(tokenizer, model, device, prompts, max_new_tokens=24):
    """Emit a letter plus a rationale — the shape real instruct models produce."""
    out = []
    for p in prompts:
        rng = random.Random(hash(p) % 10_000)
        out.append("%s\n\nThis is stated in the classical text."
                   % rng.choice(["A", "B", "C", "D"]))
    return out


ab.load_model, ab.generate_batch = _stub_load, _stub_generate
tmp2 = Path(tempfile.mkdtemp(prefix="ayur_integration_"))
try:
    metrics = ab.run_benchmark(
        "stub/test-model", data_dir=str(DATA), results_dir=str(tmp2),
        device="cpu", batch_size=8, skip_bertscore=True, save_results=True)
    produced = sorted(p.name for p in tmp2.iterdir())
    print("\n  files written: %d" % len(produced))
    for name in produced:
        print("    -", name)
    if set(metrics) != set(ab.TASK_TYPES):
        FAILS.append("run_benchmark did not return all 4 types: %s" % list(metrics))
    if not (tmp2 / "leaderboard.csv").exists():
        FAILS.append("leaderboard.csv not written")
    if not (tmp2 / "benchmark_report.txt").exists():
        FAILS.append("benchmark_report.txt not written")
    if len([p for p in produced if p.startswith("confusion_matrix_")]) != 4:
        FAILS.append("expected 4 confusion matrices")
    # re-run must REPLACE this model's rows, not duplicate them
    ab.run_benchmark("stub/test-model", data_dir=str(DATA), results_dir=str(tmp2),
                     device="cpu", batch_size=8, skip_bertscore=True)
    n_rows = len(ab.leaderboard(tmp2))
    print("\n  leaderboard rows after re-running the same model: %d (expect 4)" % n_rows)
    if n_rows != 4:
        FAILS.append("re-run duplicated leaderboard rows: %d" % n_rows)
    print("\n  --- report head ---")
    print("\n".join(open(tmp2 / "benchmark_report.txt", encoding="utf-8").read().splitlines()[:14]))
finally:
    ab.load_model, ab.generate_batch = _real_load, _real_gen
    shutil.rmtree(tmp2, ignore_errors=True)

print("\n" + "=" * 72)
if FAILS:
    print("FAILURES (%d):" % len(FAILS))
    for f in FAILS:
        print("  -", f)
    raise SystemExit(1)
print("ALL SELF-TESTS PASSED")
print("=" * 72)
