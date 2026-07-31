# AyurShloka-QA v3 — Qwen generation + full pipeline

Generate 80,000 Ayurvedic questions with Qwen2.5-7B-Instruct, then take them
through quality gating, deduplication, AyurParam matching, splitting, leakage
auditing and reporting.

```
qwen_generate_80k.ipynb          run this on Kaggle/Colab — needs a GPU
build_generation_notebook.py     rebuilds the notebook if you want to edit prompts
scripts/Q1 … Q8                  the downstream pipeline, all dry-run already
data/                            bba_en.parquet, bba_hi.parquet
dryrun/                          worked example: every report, produced from real data
```

## Why the notebook, and not a script here

This sandbox has 2 CPUs, 3 GB RAM, no PyTorch, and HuggingFace is blocked at the
proxy. Qwen cannot run here. Everything *downstream* of generation does run here,
and has — `dryrun/` holds the reports from an actual end-to-end execution against
8,000 real rows, so the code is proven before you spend GPU hours on it.

## Step 0 — generate

Upload the eight `FINAL_*.jsonl` files as a Kaggle dataset named `ayur-books`,
open `qwen_generate_80k.ipynb`, set the accelerator to GPU, run all.

Roughly 6–9 hours for 80k on a T4 x2 with vLLM. It checkpoints after every batch,
so re-running after a session timeout resumes rather than restarting. Output:
`master_80k_qwen.jsonl`.

**Watch the reject rate printed at the end.** Above ~15% means the prompts need
work, not that the model is bad — fix it before committing to the full run.

## Steps 1–8 — the pipeline

```bash
python scripts/Q1_quality_gate.py    --in master_80k_qwen.jsonl \
    --out out/Q1_clean.jsonl --rejects out/Q1_rejects.jsonl \
    --report reports/Q1_quality.json --fix-position

python scripts/Q2_dedup.py           --in out/Q1_clean.jsonl \
    --out out/Q2_deduped.jsonl --report reports/Q2_dedup.json

python scripts/Q3_match_ayurparam.py --in out/Q2_deduped.jsonl \
    --bba data/bba_en.parquet data/bba_hi.parquet \
    --out out/Q3_annotated.jsonl --report reports/Q3_match.json

python scripts/Q4_build_splits.py    --in out/Q3_annotated.jsonl \
    --bba data/bba_en.parquet data/bba_hi.parquet \
    --outdir final --val-rows 1000 --report reports/Q4_splits.json

python scripts/Q5_check_leakage.py   --train final/train.json \
    --val final/validation.json --test final/test.json \
    --report reports/Q5_leakage_before.json --repair --repair-side train
mv final/train_clean.json final/train.json
python scripts/Q5_check_leakage.py   --train final/train.json \
    --val final/validation.json --test final/test.json \
    --report reports/Q5_leakage_after.json          # must print CLEAN

python scripts/Q6_partition.py       --dir final --outdir out/Q6_partitions \
    --report reports/Q6_partitions.json --cross

python scripts/Q7_md5_minhash.py     --dir final \
    --bba data/bba_en.parquet data/bba_hi.parquet \
    --report reports/Q7_md5_minhash.json --cache /tmp/q7.npz

python scripts/Q8_eda_report.py      --dir final --reports reports \
    --out EDA_QWEN_REPORT.html
```

Q5 and Q7 exit non-zero on failure, so the chain can gate a CI job.

---

## What each step does, and the one decision inside it

**Q1 quality gate.** Schema, answer-in-options, answer leakage, hidden-context
phrasing, degenerate options, language-label sanity, and corpus-level answer
*position* bias. `--fix-position` shuffles options to flatten it — without that, a
model can score well by always answering A and learn nothing.

Two checks needed care. Multi-select `answer_text` is a join of several options,
so option-membership is the wrong test there — the answer *keys* are checked
instead. And true/false items legitimately contain "true" and "false" in the
stem, so the leak check skips closed-vocabulary option sets. Both were caught in
the dry run misfiring on 2,350 good rows.

**Q2 dedup.** Exact stem → full item → near-duplicate cosine ≥ 0.97, cheapest
first, compared only inside blocking buckets.

**Q3 AyurParam match.** Hashed char 3–4 gram cosine against all 14,963 benchmark
questions, plus exact Levenshtein on the top-20 cosine candidates. Annotates
every row; filters nothing.

**Q4 splits.** *Test mirrors the benchmark's composition* — domain × type ×
language — rather than being selected by per-question similarity. See below.
Validation lands on exactly 1,000 by choosing a final fact of precisely the
right size. Splits are at `fact_id` granularity throughout.

**Q5 leakage.** Five checks across all three split pairs. `--repair-side train`
drops from train so validation stays at exactly 1,000 and test stays whole.

**Q6 partition.** By question type, by language, and optionally the cross. Every
partition asserted lossless.

**Q7 MD5 + MinHash.** Both methods, run within the corpus and across the
benchmark boundary.

**Q8 EDA.** One HTML report reading the per-step JSON. A missing report renders
as missing rather than as a fabricated number.

---

## Two things you asked for that the data would not support

### The test set cannot be "only questions similar to AyurParam"

Across three independent measures — MD5, MinHash and cosine — nothing generated
from these eight treatises resembles the benchmark. On the v2 corpus the maximum
cosine was 0.7401 against a 0.80 threshold, and MD5 and MinHash both returned
exactly zero. The benchmark is drawn from Indian exam papers; the corpus is
classical treatises. They have no common ancestor.

Enforcing that rule literally gives a test set of **0 rows**.

So test is built to mirror the benchmark's *composition* instead — its
`subject_domain`, `question_type` and `language` mix. A test score on that split
predicts an AyurParam score far better than a random split does, which is the
actual objective. The similarity rule is still enforced on top: anything flagged
`bba_similar` goes to test unconditionally, so the guarantee regenerates if
BhashaBench ever publishes overlapping questions.

### The mirror has a ceiling, and it is fact-level splitting

Facts move whole, and one fact's questions span several formats. Selecting a fact
because it is mostly MCQ drags its cloze and assertion siblings along. The
benchmark is 98.4% MCQ; the dry run reached 82.3%.

Raising `TYPE_MIX["MCQ"]` in the notebook lifts the ceiling. Going to row-level
selection would hit 98.4% exactly and reintroduce the leak that fact-level
splitting exists to prevent — a bad trade. The report prints the achieved fit per
dimension with the delta, so the gap is visible rather than assumed away.

---

## Dry-run results (8,000 real rows, in `dryrun/`)

| Step | Result |
|---|---|
| Q1 quality | 7,612 passed / 388 rejected (95.2%) |
| Q2 dedup | 120 near-duplicates removed → 7,492 |
| Q3 AyurParam | **0** flagged, max cosine 0.7401 |
| Q4 splits | train 5,893 / val **1,000 exact** / test 599 |
| Q5 leakage | 50 found → repaired on train side → **CLEAN** |
| Q6 partition | lossless, 7,359 rows across all views |
| Q7 MD5+MinHash | 0 duplicates, 0 cross-boundary matches → **CLEAN** |
| Q8 EDA | 7 sections, 17 tables, 0 missing |

Q7 caught 27 cross-split near-duplicate pairs that Q5's cosine check missed —
different measures, different blind spots, which is the argument for running
both. None shared a gold answer, so they are template overlap rather than
leakage: the model saw the question shape, not the answer. Q7 reports both counts
and only fails on the second.

---

## Notes for the run

- `HINDI_SHARE = 0.375` in the notebook matches the benchmark's 5,615 of 14,963.
  The language partition in Q6 depends on the label being right, and Q1
  normalises it to `en`/`hi` and infers it from script where it is missing.
- Distractors are drawn from sibling chunks of the same treatise. A distractor
  from another domain makes the item solvable by elimination with no Ayurvedic
  knowledge at all.
- Seed is 20260730 throughout. Generation is sampled at temperature 0.7, so it is
  reproducible only per-seed with vLLM; the pipeline downstream is fully
  deterministic.
