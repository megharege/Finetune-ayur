# Hybrid from your two uploaded split sets

```
train.json       66,156
validation.json   1,000   (exact)
test.json         3,084
TOTAL            70,240
```

Deduplicated, fact-disjoint, verified CLEAN. Ready to train.

---

## The thing you need to know first

**The two sets you uploaded are not two independent corpora.** Set B is 96.2%
contained in Set A, byte-identical:

| | Rows | |
|---|---:|---|
| Set A (`train-c0343863` etc.) | 76,291 | |
| Set B (`train.json` etc.) | 7,359 | |
| Set B ids already present in Set A | **7,076** | **96.2% of Set B** |
| Set B ids that are new | **283** | |
| Union of unique ids | 76,574 | |

Set B looks like an earlier hybrid output that was itself drawn from Set A's
corpus, so merging them is Set A plus 283 rows — not a 50/50 blend of two
generators.

Two consequences for what you asked:

**"40k from each" is impossible.** Set B has 7,359 rows in total. It cannot
supply 40,000, and after deduplication it contributes 333 unique rows.

**"80k total" is impossible.** The union of unique question_ids is 76,574 before
any content deduplication. There is no arrangement of these two files that
reaches 80,000 without duplicating rows.

So I built the largest clean set the two files actually support, and hit your
split spec exactly where it was achievable: **validation is exactly 1,000, train
is ~66k, test is the AyurParam-mirrored union.**

---

## Why balance was disabled

Equal weighting caps the hybrid at 2× the smaller source. Here that ceiling is
**666 rows** — it would have thrown away 66,000 rows of Set A to match a set that
contributes 333. That is not balance, it is deletion.

I used `--no-balance`, which I added for exactly this case. The flag is
documented in the script; the default remains equal weighting, which is right
when the two sources are genuinely comparable.

Resulting composition:

| Split | Rows | Set A | Set B |
|---|---:|---:|---:|
| train | 66,156 | 66,125 | 31 |
| validation | 1,000 | 698 | 302 |
| test | 3,084 | 2,500 | 584 |

Set B is over-represented in validation and test relative to its 0.4% share of
the pool, because its test rows entered through the test union before dedup ran.

---

## What deduplication removed

| | Rows |
|---|---:|
| Exact duplicates across the two sets | 6,048 |
| Pool rows matching a test row | 2,178 |
| Rows withheld — their fact is in test | 1,620 |
| Cross-set near-duplicates (Jaccard ≥ 0.90) | 313 pairs |
| Same-set residual duplicates | 103 |
| Identical stems with conflicting answers | 0 |

The 6,048 exact duplicates are the overlap made visible: the same question
present in both files.

---

## Test

Test is the union of the two uploaded test sets — the AyurParam-mirrored ones —
capped by `--test-rows 5000` and then reduced to 3,084 by deduplication against
the pool. Nothing else was admitted.

It came out below 5,000 because 2,178 of its candidates duplicated pool rows and
were dropped. Raising the cap would not help: the union only holds 6,247 rows to
begin with, and most of Set A's 5,648 overlap Set B's 599.

---

## Verification

`Q7_md5_minhash.py`, which shares no code path with the merger:

```
MD5 duplicate rows            : 0
MinHash true duplicates       : 0
Cross-split leaking pairs     : 0
MD5 matches vs AyurParam      : 0
MinHash matches vs AyurParam  : 0
max cosine vs AyurParam       : 0.7401  (threshold 0.80)
VERDICT                       : CLEAN
```

Fact overlaps train/validation, train/test, validation/test: 0, 0, 0.

893 MinHash *similar* pairs remain and are expected — questions about verse 4 and
verse 5 of one chapter score above 0.97 while being different questions with
different answers. A pair must also share its gold answer to count as a
duplicate, and none do.

---

## A bug this run surfaced

Validation failed on the first attempt:

```
cannot hit 1000 exactly: need a fact of size 148, none left.
```

The exact-size filler required a *single* fact of precisely the remaining gap.
With a gap of 148 and facts running 1–6 rows, no such fact can exist. It now
closes the gap with several small facts instead, smallest first, which preserves
the fact-whole invariant and lands on 1,000 exactly.

---

## To actually get 80,000 with 40k from each

You need two genuinely independent corpora. The generation notebooks in
`../ayur_qwen/` produce them:

```bash
# on a GPU box
run qwen_generate_80k.ipynb    -> master_80k_qwen.jsonl
run gemma_generate_80k.ipynb   -> master_80k_gemma.jsonl

# then the per-model pipeline for each, then:
python scripts/Q9_build_hybrid.py \
    --sources qwen=out/qwen_final gemma=out/gemma_final \
    --outdir hybrid --per-model 40000 --val-rows 1000 --test-rows 5000
```

With two real 80k corpora that lands at roughly 71,000 — test 5,000, validation
1,000, train ~65,000 — with a true 50/50 split and `--no-balance` left off.
