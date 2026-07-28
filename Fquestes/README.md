# AyurShloka-QA v2 — 80,000 questions

Rebuilt from all 5,838 chunks of your 8 classical texts, with a **fact-centric** design:
each chunk is first reduced to discrete facts, then each fact is rendered into every
format it supports. That is what lets the same answer appear as an MCQ, a cloze, an
assertion-reason item and a multiple-selection item **without any two question stems
being duplicates**.

| | v1 | v2 |
|---|---:|---:|
| Questions | 21,475 | **80,000** |
| Formats | 5 | **6** (adds Multiple selection) |
| Distinct facts | — | 35,016 |
| Chunks used | 5,780 | 5,483 |
| Duplicate stems | 0 | **0** |

## Files

| File | Rows |
|---|---:|
| `ayur_qa_v2_80k.jsonl` | 80,000 — master, shuffled |
| `train.jsonl` | 71,987 |
| `validation.jsonl` | 8,013 |
| `by_book/*.jsonl` | the full 83,667-row pool before selection |
| `stats.json` | full distribution breakdown |

**The split is on `fact_id`, not row.** All renderings of one fact land in the same
split, so a paraphrase of a training item can never appear in validation.

## Format mix

| Format | Count | Share |
|---|---:|---:|
| Fill in the blanks | 20,699 | 25.9% |
| MCQ | 18,262 | 22.8% |
| Assorted (descriptive / true-false / one-word) | 15,428 | 19.3% |
| Assertion or Reasoning | 11,430 | 14.3% |
| Multiple selection | 9,089 | 11.4% |
| Match the column | 5,092 | 6.4% |

**Multiple selection** is 5 options with 2–3 correct (4,694 have 2, 4,395 have 3).
`correct_answer` is comma-joined letters (`"A,C"`), `answer_text` joins the option texts
with **` || `** — not `;`, because option text can itself contain a semicolon — and
`answer_texts` carries the same thing as a list.

36 `format_variant` values sit underneath the 6 formats, including the negative
variants (`terms_multi_negative`, `statements_multi_negative`, `not_stated`) which ask
which items do *not* belong.

## New columns in v2

| Column | Use |
|---|---|
| `fact_id` | which underlying fact the item tests. **Group by this** to de-duplicate semantically |
| `format_variant` | which of the 36 renderings this row is |
| `source_richness` | characters of source material behind the fact — your density filter |
| `fact_kind` | statement, term, verse_subject, location, term_set, translit, statement_set, evidence, enumeration, count, synonym_set, raw |
| `n_options`, `n_correct` | 4 or 5 options; 1 for single-answer, 2–3 for multi-select |
| `answer_texts` | list form of the multi-select answer |

## Multi-format reuse

Of 35,016 facts, **24,917 are rendered more than once**:

| Distinct formats per fact | Facts |
|---:|---:|
| 1 | 13,381 |
| 2 | 12,755 |
| 3 | 6,628 |
| 4 | 2,252 |

Mean 2.28 questions per fact.

## Verification

`verify_v2.py` reports **zero failures** across 25 checks on all 80,000 rows:

- 0 duplicate stems (global, across all books)
- answer key always matches the keyed option(s); multi-select keys validated against
  `answer_text` and `answer_texts`
- no key leaks into the stem or the `context` field
- assertion-reason and true/false items carry **no** context (it would give the verdict away)
- every cloze contains `________`; every match item has both columns and a bijective key;
  every multi-select says "Select ALL that apply" and has 5 options with 2–3 correct
- answer letters: A 24.9% · B 25.3% · C 24.9% · D 24.9%
- train/validation `fact_id` overlap: **0**

### Two defects found and fixed during the build

1. **Multi-select answers were ambiguous.** `answer_text` joined options with `"; "`, but
   option text can contain a semicolon (`"...in the muscles and blood; therefore..."`), so
   splitting the answer back apart gave the wrong pieces. 5,984 rows affected. The keys and
   options were always correct — only the derived string was. Now joined with ` || `.
2. **True/false items had a fixed option order**, so the answer was always A or B. Across
   13,605 items that skewed the global letter balance to A 29.0% / B 30.9% and handed a
   model a shortcut worth ~17% of the set. Options are now shuffled per item. Non-true/false
   items were already balanced at 24.8/25.2/24.9/25.0.

## Coverage — read this before training

**5,483 of 5,838 chunks (93.9%)**, down from 99.0% in v1. The drop is deliberate: v2
rejects items whose answer is OCR junk, and some chunks had nothing else to offer.

| Book | Chunks | Covered | | Questions |
|---|---:|---:|---:|---:|
| Bhavaprakasha Nighantu | 1,052 | 1,043 | 99.1% | 27,534 |
| Madhava Nidanam (Part 2) | 234 | 234 | 100% | 8,376 |
| Madhava Nidana (Laghutrayi) | 403 | 403 | 100% | 9,549 |
| Sushruta Samhita | 418 | 418 | 100% | 2,414 |
| Madhava Nidanam (Part 1) | 728 | 716 | 98.4% | 12,601 |
| Charaka Samhita | 1,497 | 1,457 | 97.3% | 11,334 |
| Ashtanga Hridaya | 913 | 821 | 89.9% | 5,134 |
| Sharangadhara Samhita | 593 | 391 | 65.9% | 3,058 |

The two gaps have specific, checkable causes:

- **Sharangadhara — 202 uncovered chunks.** All 202 have a shloka; 200 have **no English
  commentary** (the source carries Hindi only, with no `commentary_english`). There is
  nothing to build an English question from beyond reciting the verse.
- **Ashtanga Hridaya — 92 uncovered chunks.** Mostly **broken Devanagari** — lost conjuncts
  and detached vowel signs, e.g. `ग ये ीरघत ृ े े ठे नि दते`. Verse questions are refused
  on purpose rather than shipping unanswerable items.

**The set is heavily skewed toward Bhavaprakasha Nighantu (34.4%)** because its drug
monographs are long, list-heavy prose — exactly what the fact extractor thrives on.
Sushruta is 3.0%. If you want balance, down-sample BPN by `fact_id` rather than by row.

## Density

`source_richness` is characters of source behind each fact. 80,000 questions across 5,483
chunks is ~14.6 per chunk, and median commentary is only ~434 characters, so the thin tail
is real. Filter on `source_richness` if items look stretched, and use `fact_id` to see how
many questions share one underlying fact.

## Regenerating

```bash
python3 generate_v2.py CS        # per book: CS SU AH SG BPN MN1 MN2 MNL
python3 rebuild_v2_master.py     # normalise, select to 80k, split, stats
python3 verify_v2.py             # 25-check audit
```

Seeded (`SEED = 20260729`) and reproducible. No LLM is involved — every answer is lifted
verbatim from your source text and traceable via `(source_book, chunk_id)`.

> Join on `(source_book, chunk_id)`, never `chunk_id` alone: 102 ids collide between
> Madhava Nidanam Part 1 and Part 2, which both number their chunks `MN1, MN2, …`.

## Adding phrasing variety

Stems are templated, so a model can learn the template rather than the content.
`ayur_gemma_paraphrase.ipynb` runs Gemma over the set and rewrites **stems only** —
options, keys and provenance are frozen and verified unchanged. It skips cloze, match and
assertion items, whose stems are structural. ~2–4 GPU hours on a T4 for all 80k.
