# Ayurveda benchmark kit

Drop-in replacement for the Cardiac-LLM runner, pointed at the AyurShloka-QA question set.

## Contents

| File | What it is |
|---|---|
| `ayur_assertion_25.jsonl` | 25 assertion-reasoning items |
| `ayur_mcq_25.jsonl` | 25 MCQ items |
| `ayur_fill_blanks_25.jsonl` | 25 fill-in-the-blanks items |
| `ayur_match_column_25.jsonl` | 25 match-the-column items |
| `ayur_benchmark.py` | The scoring engine — import this |
| `test_ayur_benchmark.py` | Offline self-test (no GPU, no model download) |
| `manifest.json` | Provenance and answer-key balance for each set |

All 100 items are sampled from `validation.jsonl`, so they stay **disjoint from
`train.jsonl`** — you can score a base model here and then fine-tune on the other
~21k questions without leakage.

Each set is balanced round-robin across all 8 source texts and every question subtype.

## Setup on Kaggle

1. Create a Kaggle **Dataset** containing all files in this folder (including `ayur_benchmark.py`).
2. Attach it to the notebook.
3. Settings → Accelerator → **GPU T4 x2**, Settings → Internet → **On**.
4. Open `ayur_model_testing.ipynb`, set `MODEL_NAME` in **Cell 4**, Run All.

Paths auto-detect via `Path("/kaggle/input").rglob(...)`, so you should not need to
edit them.

## Row schema

```json
{
  "id": "CS-MCQ-00412",
  "type": "mcq",
  "instruction": "Read the following verse from Charaka Samhita ...",
  "input": "{\"A\": \"...\", \"B\": \"...\", \"C\": \"...\", \"D\": \"...\"}",
  "output": "B",
  "output_text": "the full text of the correct option",
  "context": "source passage — NOT fed to the model unless use_context=True",
  "source": "Charaka Samhita — Chikitsasthana, Chapter 2, verse 44-45",
  "source_book": "Charaka Samhita",
  "language": "en",
  "difficulty": "Medium",
  "subject_domain": "Kayachikitsa (General Medicine & Internal Medicine)",
  "question_subtype": "verse_translation",
  "chunk_id": "CS318"
}
```

`input` is a JSON **string** (same convention as the cardiac dataset), so
`json.loads(row["input"])` gives you the option dict.

## Using the engine directly

```python
import ayur_benchmark as ab

ab.validate_data("path/to/data")
ab.run_benchmark("Qwen/Qwen2.5-3B-Instruct",
                 data_dir="path/to/data", results_dir="results")
ab.leaderboard("results")
ab.recommend("results")
```

Importing the module is free — it downloads nothing, loads no model and fetches no
NLTK corpora until you actually call something.

Run the self-test any time with `python test_ayur_benchmark.py` (needs only
`rouge-score`, `nltk`, `scikit-learn`, `pandas` — no torch).

## What changed vs. the cardiac runner

**Fixed — these were producing wrong numbers**

- **Right-padding on a decoder-only model.** The original called
  `tokenizer(..., padding=True)` without setting `padding_side`. HuggingFace defaults
  to right-padding, so in a batch every sequence shorter than the longest one had its
  continuation generated *after* a run of pad tokens. The engine now forces
  `tokenizer.padding_side = "left"`. This alone explains a large share of the 0.0 rows
  in your old `leaderboard.csv`.
- **Answer extraction.** `extract_mcq_letter` used `re.search(r"\b([A-E])\b")` and then
  fell back to `text[:1].upper()`. Against gold values that were answer *text*, this
  turned "Aortic dissection" into `A` and "Insert two large-bore..." into `I` — which is
  why your confusion matrix had labels `I, L, P, T`. Replaced with `resolve_letter()`,
  which tries stated answers ("The answer is C"), leading/bold/bare letters, verbatim
  option text, match-the-column permutations, then fuzzy token overlap. Critically it
  accepts `"A\n\nExplanation: ..."` — the shape Phi-3 was actually emitting, and which
  the old regex scored as a miss.
- **No chat template.** Instruct models were fed a raw `"{instruction}\n\nAnswer:"`
  string. The engine now applies `tokenizer.apply_chat_template` when the model has one
  (toggle with `use_chat_template`).
- **`max_new_tokens=128` on letter-answer tasks.** Wasted ~5x the generation time and
  gave the model room to ramble past its answer. Default is now 24.
- **Leaderboard duplication.** Re-running a model appended a second set of rows.
  Rows for a model are now replaced.

**Added**

- `format_compliance` — the fraction of items where the model emitted a parseable
  answer. Distinguishes "wrong" from "did not follow instructions"; a near-zero score
  with low compliance is a prompting problem, not a knowledge problem.
- `random_baseline: 0.25` on every row, and `lift_over_random` in `recommend()` — with
  4 options, 25% is chance, so raw accuracy alone is misleading.
- `NONE` as an explicit confusion-matrix label for unparseable responses.
- Both metric families on **all four types** (the original only did classification for
  MCQ and generation metrics for the free-text types).
- `load_in_4bit` so 7–9B models fit on a single T4.
- `compare_models()`, `recommend()`, and per-book / per-subtype / per-difficulty error
  analysis.
- Import-safety: no NLTK downloads or heavy imports at module import time.

## Reading the output

Start with **`format_compliance`**. If it is below ~0.9, the model is not answering in
the requested format and every other number is noise — set `use_chat_template=False`
(for base models) or raise `max_new_tokens`, and re-run.

Then read **`lift_over_random`** in `recommend()`. 0.25 accuracy is a coin flip across
four options. A model sitting at chance has no usable prior on these texts.

`match_column` is the hardest type by construction (a 4-way permutation match), and
`fill_blanks` on `sanskrit_pada` items requires reading Devanagari — expect most
general-purpose models to be at or near chance on both. That is the gap fine-tuning is
meant to close.
