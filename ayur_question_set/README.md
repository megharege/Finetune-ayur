# AyurShloka-QA

A question set generated from your 8 classical Ayurvedic shloka + commentary chunk files,
in a schema compatible with **BhashaBench-Ayur (BBA)** — the benchmark AyurParam is
evaluated on.

**21,475 questions** across **5,678 source chunks** (97–100% chunk coverage per book).
Only `sanskrit_text`, `transliteration` and `commentary` were used as knowledge sources;
every other field in your data is carried through as a provenance column.

---

## Files

| File | Rows | Purpose |
|---|---:|---|
| `ayurbench_shloka_all_books.jsonl` | 21,475 | Master set, shuffled |
| `train.jsonl` | 19,327 | 90% split, stratified by (book × question type) |
| `validation.jsonl` | 2,148 | 10% split, zero stem overlap with train |
| `by_book/*.jsonl` | — | One file per source text |
| `sft/*_sft.jsonl` | — | Same splits rendered as AyurParam `<user>`/`<assistant>` strings |
| `dataset_stats.json` | — | Full distribution breakdown |

### Per book

| Book | Chunks | Questions |
|---|---:|---:|
| Bhavaprakasha Nighantu | 1,052 | 5,242 |
| Charaka Samhita | 1,497 | 4,344 |
| Madhava Nidanam (Part 1) | 728 | 3,059 |
| Ashtanga Hridaya | 913 | 2,464 |
| Madhava Nidana (Laghutrayi) | 403 | 2,250 |
| Madhava Nidanam (Part 2) | 234 | 1,492 |
| Sharangadhara Samhita | 593 | 1,346 |
| Sushruta Samhita | 418 | 1,278 |

---

## Schema

```json
{
  "question_id": "CS-MCQ-00412",
  "question": "Read the following verse from Charaka Samhita ...",
  "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...",
  "correct_answer": "B",
  "answer_text": "...",
  "question_type": "MCQ",
  "question_subtype": "verse_translation",
  "grounding": "shloka_to_meaning",
  "difficulty": "Medium",
  "subject_domain": "Kayachikitsa (General Medicine & Internal Medicine)",
  "language": "English",
  "source_book": "Charaka Samhita",
  "sthana": "Chikitsasthana",
  "chapter_number": 2,
  "chapter_title": "...",
  "verse_id": "44-45",
  "chunk_id": "CS318",
  "primary_category": "rasayana",
  "citation": "Charaka Samhita — Chikitsasthana, Chapter 2, verse 44-45",
  "explanation": "...",
  "context": "..."
}
```

**Open-ended items** (`question_type: "Assorted"`, descriptive subtypes) leave the four
option fields and `correct_answer` empty; the reference answer is in `answer_text`.

`context` is safe to feed as a `<context>` block — it never contains the keyed answer
(enforced by the generator and re-checked by `verify.py`).

---

## Question types

| Type | Count | Share |
|---|---:|---:|
| MCQ | 8,261 | 38.5% |
| Assorted (descriptive / true-false / one-word) | 6,465 | 30.1% |
| Fill in the blanks | 3,876 | 18.0% |
| Match the column | 1,909 | 8.9% |
| Assertion or Reasoning | 964 | 4.5% |

Difficulty: Medium 55.0%, Hard 25.0%, Easy 20.1%.

### Grounding strategies

| Strategy | What it tests |
|---|---|
| `shloka_to_meaning` | Verse given in Devanagari → its subject or import |
| `concept_to_source` | Teaching given → which text / sthana / chapter states it |
| `commentary_clinical` | Lakshana, nidana, chikitsa, dravya facts from the commentary |
| `term_recall` | Paryāya, technical terms, enumerations, classifications |

### Subtypes

`verse_exposition`, `verse_translation`, `verse_subject`, `correct_statement`,
`sanskrit_pada` (Devanagari cloze), `technical_term` (IAST cloze), `masked_term`,
`paryaya` (synonym recall), `enumeration_count`, `locate_sthana`, `locate_chapter`,
`four_pair` / `topic_to_reference` (matching), `R_explains_A` / `both_true_unrelated` /
`A_true_R_false` / `A_false_R_true` (assertion-reasoning), `true_false_*`,
`one_line_source`, `short_note`, `transliterate_and_explain`.

---

## Quality controls

Every item passes `verify.py` with zero failures:

- **No duplicates** — global de-duplication on the normalised stem, across all books.
- **Answer-key integrity** — the lettered option always equals `answer_text`.
- **No answer leakage** — the key never appears in the stem outside the options, nor in
  `context`. Verdict questions (true/false, assertion-reasoning) ship *no* `context` at all,
  since supplying the source passage would give the verdict away.
- **Distractor isolation** — MCQ distractors are drawn from a *different chapter* of the same
  book, so a distractor cannot accidentally also be true of the asked topic.
- **On-topic keys** — a "regarding X" stem is only used when the keyed sentence actually
  shares content with X; otherwise the stem falls back to a neutral framing.
- **OCR filtering** — sentences are rejected if they contain running heads
  (`CARAKA-SAMHITĀ`, …), spaced-out punctuation, camel-cased garble (`TOne`), vowel-less
  runs, or >34% of lowercase tokens absent from an English lexicon. Verses with broken
  Devanagari (detached vowel signs / lost conjuncts) are excluded from cloze and
  verse-comprehension items.
- **Non-trivial matching** — Column B descriptions never restate their Column A label, and
  Column A labels must be compact noun phrases (≤9 words, no dangling clause).
- **Balanced keys** — answer letters sit at roughly 25% each; assertion-reasoning cycles
  through all four verdicts.
- **Clean splits** — 0 identical stems shared between train and validation.

### Known limitations

- Hindi-only commentary in `Sharangadhara_Samhita` is used via its `commentary_english`
  field; chunks with no English rendering yield verse-only items.
- `Madhava Nidanam Part 1/2` and `Madhava Nidana (Laghutrayi)` overlap in subject matter.
  Stems are globally de-duplicated, but semantically similar items can appear across
  these three files — keep them in the same split if that matters to you.
- Assertion-reasoning "false" statements are produced by controlled corruption (number
  swap, term swap, dosha/quality inversion). The corruption is recorded in `explanation`.
- Source OCR quality varies; `Ashtanga Hridaya` has the most damaged Devanagari and so
  yields fewer cloze items than its chunk count suggests.

---

## Regenerating

```bash
python3 generate_questions.py CS        # one book (codes: CS SU AH SG BPN MN1 MN2 MNL)
python3 generate_questions.py master    # merge + de-duplicate
python3 generate_questions.py splits    # train / validation
python3 generate_questions.py stats     # dataset_stats.json
python3 verify.py                       # full integrity + quality audit
python3 to_sft.py                       # optional AyurParam <user>/<assistant> format
```

Generation is seeded (`SEED = 20260728`) and reproducible.
