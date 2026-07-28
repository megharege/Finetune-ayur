#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit ayur_model_testing.ipynb (self-contained: the engine is embedded)."""
import json

import base64
import gzip
import os
import textwrap

BASE = "/sessions/loving-trusting-wright/mnt/outputs"

ENGINE_SRC = open(os.path.join(BASE, "ayur_benchmark.py"), encoding="utf-8").read().rstrip("\n")

# --- embed the 100 eval questions so the notebook needs no attached dataset ---
EVAL_FILES = ["ayur_assertion_25.jsonl", "ayur_mcq_25.jsonl",
              "ayur_fill_blanks_25.jsonl", "ayur_match_column_25.jsonl"]
_bundle = {name: open(os.path.join(BASE, "ayur_eval_sets", name), encoding="utf-8").read()
           for name in EVAL_FILES}
_raw = json.dumps(_bundle, ensure_ascii=False).encode("utf-8")
_b64 = base64.b64encode(gzip.compress(_raw, 9)).decode("ascii")
DATA_B64 = "\n".join('"%s"' % chunk for chunk in textwrap.wrap(_b64, 100))
print("embedded data: %d KB raw -> %d KB base64" % (len(_raw) / 1024, len(_b64) / 1024))

cells = []


def _next_id():
    # nbformat >= 4.5 requires a unique `id` on every cell; strict importers reject
    # notebooks without them.
    return "cell-%03d" % len(cells)


def md(src):
    cells.append({"id": _next_id(), "cell_type": "markdown", "metadata": {},
                  "source": src.split("\n")})


def code(src):
    cells.append({"id": _next_id(), "cell_type": "code", "execution_count": None,
                  "metadata": {}, "outputs": [], "source": src.split("\n")})


md("""# Ayurveda Shloka Benchmark — model selection runner

Scores a candidate base model on **100 questions** drawn from the AyurShloka-QA set
(25 each: assertion-reasoning, MCQ, fill-in-the-blanks, match-the-column), so you can
pick which model to trim and fine-tune on the remaining ~21k questions.

All four task types are 4-option items, so each one reports **both**:

* **classification** — accuracy, precision/recall/F1 (micro / macro / weighted), confusion matrix
* **generation** — exact match, token P/R/F1, ROUGE-1/2/L, BLEU, METEOR, BERTScore

plus latency, tokens/sec and **format compliance** (how often the model emitted a
parseable answer at all — a low value means the score reflects instruction-following,
not Ayurvedic knowledge).

---

## 🔧 Cells you need to edit

| Cell | What to change |
|---|---|
| **Section 6 — CONFIG** | `MODEL_NAME` — the only required edit |
| **Section 11 — Full run** | `BATCH_SIZE`, `LOAD_IN_4BIT`, `USE_CHAT_TEMPLATE` per model |
| **Section 15 — Recommend** | `WEIGHTS`, if some task types matter more than others |

**Nothing to attach.** The scoring engine (Section 4) and all 100 questions
(Section 5) are embedded in this notebook. Import it, set `MODEL_NAME`, Run All.

Everything else runs as-is.

**Before running:** Settings → Accelerator → **GPU T4 x2**, and Settings → Internet → **On**
(needed for model downloads, BERTScore and the NLTK corpora).""")

md("## 1. Install dependencies")
code("""!pip install -q transformers torch rouge-score nltk python-dotenv tqdm sacremoses \\
    scikit-learn bitsandbytes accelerate bert-score
!pip install -q -U transformers

# METEOR needs the wordnet corpus; without it METEOR silently reports 0.0 for every row.
import nltk
for pkg in ["punkt", "punkt_tab", "wordnet", "omw-1.4"]:
    nltk.download(pkg, quiet=True)
print("deps + nltk corpora ready")""")

md("## 2. Check GPU")
code("""import torch
print("CUDA available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only")
if torch.cuda.is_available():
    print("VRAM: %.1f GB" % (torch.cuda.get_device_properties(0).total_memory / 1e9))""")

md("""## 3. HF token (only for gated/private models)

Add via **Add-ons → Secrets** in Kaggle (key: `HF_TOKEN`). Needed for Llama, Gemma, etc.""")
code("""import os
try:
    from kaggle_secrets import UserSecretsClient
    os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    print("HF_TOKEN loaded (ok)")
except Exception as e:
    print("No HF_TOKEN secret — fine for public models:", e)""")

md("""## 4. Write the benchmark engine

The full scoring engine is bundled inside this notebook. This cell writes it out as
`ayur_benchmark.py` in the working directory, and later cells import it from there — so
you can edit it in place and just re-run the import cell, no kernel restart needed.""")
code("%%writefile ayur_benchmark.py\n" + ENGINE_SRC)

md("""## 5. Write the 100 evaluation questions

The question sets are embedded in this notebook too, so **nothing needs to be attached**.
This cell unpacks them into the working directory as four `.jsonl` files.

All 100 items come from the AyurShloka-QA `validation.jsonl` split, so they are disjoint
from the ~21k `train.jsonl` questions you will fine-tune on — no leakage.""")
code('''import base64, gzip, json
from pathlib import Path

_DATA_B64 = (
%s
)

_bundle = json.loads(gzip.decompress(base64.b64decode(_DATA_B64)).decode("utf-8"))
for _name, _text in _bundle.items():
    Path(_name).write_text(_text, encoding="utf-8")
    print("wrote %%-28s %%3d questions" %% (_name, len(_text.strip().splitlines())))''' % DATA_B64)

md("""## 6. 🔧 CONFIG — **edit this cell**

`MODEL_NAME` is the only thing you must set. Everything else is already in place.

Candidates that fit a T4 (≤8B, all public):

```
Qwen/Qwen2.5-3B-Instruct          Qwen/Qwen2.5-7B-Instruct
meta-llama/Llama-3.2-3B-Instruct  microsoft/Phi-3-mini-4k-instruct
google/gemma-2-2b-it              google/gemma-2-9b-it        (needs 4-bit)
sarvamai/sarvam-1                 ai4bharat/Airavata          (Indic-tuned)
bharatgenai/Param-1-2.9B-Instruct bharatgenai/AyurParam       (the Ayurveda baseline)
```

Benchmarking **AyurParam** first gives you the number to beat.""")
code('''# ============================ EDIT ME ============================
MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"     # <-- the model you want to score
# =================================================================

import sys
from pathlib import Path

RESULTS_DIR = "results"
DATA_DIR = Path(".")             # sections 4 and 5 wrote everything here
if "." not in sys.path:
    sys.path.insert(0, ".")

print("MODEL_NAME:", MODEL_NAME)
missing = [f for f in _bundle if not (DATA_DIR / f).exists()]
print("Missing files:", missing or "none — ready to run")''')

md("""## 7. Import the engine and validate the data

`ayur_benchmark` is import-safe — importing it downloads nothing and loads no model.
`reload` means any edit you make to `ayur_benchmark.py` takes effect without restarting
the kernel.""")
code("""import importlib
import ayur_benchmark as ab
importlib.reload(ab)          # so edits to the .py take effect without restarting

print("Task types:", ab.TASK_TYPES)
ab.validate_data(DATA_DIR)""")

md("""## 8. Inspect a couple of items

Worth eyeballing once so you know what the model is actually being asked.""")
code("""import json, textwrap

for dtype in ab.TASK_TYPES:
    rows = ab.load_jsonl(DATA_DIR / ab.FILENAME_MAP[dtype])
    r = rows[0]
    print("=" * 78)
    print("%s  |  %s  |  %s" % (dtype.upper(), r["source"], r["difficulty"]))
    print("=" * 78)
    print(textwrap.fill(r["instruction"], 76)[:700])
    for L, txt in json.loads(r["input"]).items():
        print("  (%s) %s" % (L, txt[:110]))
    print("  ANSWER: %s -> %s" % (r["output"], r["output_text"][:90]))
    print()""")

md("""## 9. Preview the exact prompt the model will receive

If a model scores near zero, look here first — it is almost always a prompt/template
problem, not a knowledge problem.""")
code("""from transformers import AutoTokenizer

_tok = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
_row = ab.load_jsonl(DATA_DIR / ab.FILENAME_MAP["mcq"])[0]

print("--- WITH chat template (use for *-Instruct / *-it models) ---")
print(ab.build_prompt(_row, "mcq", _tok, use_chat_template=True)[:900])
print("\\n--- WITHOUT chat template (use for base models) ---")
print(ab.build_prompt(_row, "mcq", _tok, use_chat_template=False)[:900])""")

md("""## 10. Sanity run (fast, writes nothing)

`limit=4` per type and `save_results=False`, so this can never pollute `leaderboard.csv`.
Confirm **format_compliance is near 1.0** before spending time on the full run.""")
code("""ab.run_benchmark(
    MODEL_NAME,
    data_dir=DATA_DIR,
    results_dir=RESULTS_DIR,
    device="cuda",
    limit=4,
    batch_size=4,
    skip_bertscore=True,     # skip the 700MB BERTScore download for a smoke test
    save_results=False,
)""")

md("""## 11. 🔧 Full run — **tune these per model**

* `BATCH_SIZE` — drop to 2 if you hit OOM; raise to 8 for small models.
* `LOAD_IN_4BIT` — set `True` for 7-9B models so they fit on one T4.
* `USE_CHAT_TEMPLATE` — `True` for instruct/chat models, `False` for base models.
* `MAX_NEW_TOKENS` — 24 is plenty; these are letter-answer tasks. Raise to 128 only
  if you want to inspect the model's reasoning in the row-level CSV.
* `USE_CONTEXT` — `False` tests recall of the classical texts (what you want when
  choosing a fine-tuning base). `True` supplies the source passage, turning the task
  into reading comprehension.""")
code("""BATCH_SIZE        = 4
LOAD_IN_4BIT      = False
USE_CHAT_TEMPLATE = True
MAX_NEW_TOKENS    = 24
USE_CONTEXT       = False
FORCE_SIZE        = False      # True to allow models above the 8B cap

metrics = ab.run_benchmark(
    MODEL_NAME,
    data_dir=DATA_DIR,
    results_dir=RESULTS_DIR,
    device="cuda",
    batch_size=BATCH_SIZE,
    max_new_tokens=MAX_NEW_TOKENS,
    load_in_4bit=LOAD_IN_4BIT,
    use_chat_template=USE_CHAT_TEMPLATE,
    use_context=USE_CONTEXT,
    force_size=FORCE_SIZE,
)""")

md("## 12. This run's report")
code('print(open(f"{RESULTS_DIR}/benchmark_report.txt").read())')

md("""## 13. Leaderboard — every model scored so far

One row per `(model, task type)`. Re-running a model **replaces** its rows rather than
appending duplicates.""")
code("""import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)

lb = ab.leaderboard(RESULTS_DIR)
lb""")

md("## 14. Pivot — one row per model")
code('ab.pivot_view(RESULTS_DIR, values=["accuracy", "f1_macro", "format_compliance", "bertscore_f1", "tokens_per_sec"])')

md("""## 15. 🔧 Recommendation — which model to fine-tune

Composite = 80% weighted accuracy + 20% format compliance. Adjust `WEIGHTS` if some
task types matter more to you.

Read `lift_over_random` first: **0.25 is chance**. A model near 0.25 knows nothing
useful about these texts yet — which is not disqualifying for a fine-tuning base, but
it means the benchmark cannot distinguish it from a coin flip.""")
code("""WEIGHTS = {"mcq": 0.35, "assertion": 0.25, "fill_blanks": 0.20, "match_column": 0.20}

ab.recommend(RESULTS_DIR, weights=WEIGHTS)""")

md("""## 16. MCQ-style confusion matrix

Rows = true option letter, columns = predicted. A column piled up on one letter means
the model has a **position bias** (it always answers "A"). A large `NONE` column means
it never emitted a parseable answer.""")
code("""import re
from pathlib import Path
try:
    from IPython.display import display
except ImportError:              # running outside a notebook kernel
    display = print

safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", MODEL_NAME)
for dtype in ab.TASK_TYPES:
    p = Path(RESULTS_DIR) / f"confusion_matrix_{dtype}_{safe}.csv"
    if p.exists():
        print(f"\\n=== {dtype} ===")
        display(pd.read_csv(p, index_col=0))
    else:
        print(f"(no confusion matrix for {dtype})")""")

md("""## 17. Error analysis — where is it losing points?

Accuracy broken down by source book, question subtype and difficulty. This is what
tells you *what* to over-sample when you build the fine-tuning mix.""")
code("""rows = pd.read_csv(f"{RESULTS_DIR}/benchmark_results_{safe}.csv")

print("--- accuracy by task type ---")
display(rows.groupby("type")["correct"].agg(["mean", "count"]).round(3))

print("--- accuracy by question subtype ---")
display(rows.groupby("question_subtype")["correct"].agg(["mean", "count"]).round(3)
            .sort_values("mean"))

print("--- accuracy by source book ---")
display(rows.groupby("source_book")["correct"].agg(["mean", "count"]).round(3)
            .sort_values("mean"))

print("--- accuracy by difficulty ---")
display(rows.groupby("difficulty")["correct"].agg(["mean", "count"]).round(3))""")

md("## 18. Row-level predictions vs. gold")
code("""cols = ["type", "id", "source", "gold_letter", "pred_letter", "correct", "pred"]
display(rows[cols].head(30))

print("\\n--- items it got WRONG (first 10) ---")
for _, r in rows[rows["correct"] == 0].head(10).iterrows():
    print("\\n[%s] %s" % (r["type"], r["source"]))
    print("  gold: %s   pred: %s" % (r["gold_letter"], r["pred_letter"]))
    print("  raw : %s" % str(r["pred"])[:200].replace("\\n", " ⏎ "))""")

md("""## 19. Compare several models in one go

Uncomment and run to queue a batch. Each model is loaded, scored and freed in turn;
a failure is recorded and does not abort the rest.""")
code('''# CANDIDATES = [
#     "Qwen/Qwen2.5-3B-Instruct",
#     "meta-llama/Llama-3.2-3B-Instruct",
#     "microsoft/Phi-3-mini-4k-instruct",
#     "google/gemma-2-2b-it",
#     "bharatgenai/AyurParam",
# ]
# ab.compare_models(
#     CANDIDATES,
#     data_dir=DATA_DIR, results_dir=RESULTS_DIR, device="cuda",
#     batch_size=4, max_new_tokens=24, use_chat_template=True,
# )
# ab.recommend(RESULTS_DIR)''')

md("""## 20. Download everything

Files land in `/kaggle/working/results/`:
`benchmark_report.txt`, `leaderboard.csv`, `benchmark_results_<model>.csv`,
`confusion_matrix_<type>_<model>.csv`.""")
code("""import shutil
shutil.make_archive("ayur_benchmark_results", "zip", RESULTS_DIR)
print("Created ayur_benchmark_results.zip — download from the Output panel.")""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {
            "name": "python",
            "version": "3.10.13",
            "mimetype": "text/x-python",
            "codemirror_mode": {"name": "ipython", "version": 3},
            "pygments_lexer": "ipython3",
            "nbconvert_exporter": "python",
            "file_extension": ".py",
        },
        "accelerator": "GPU",
        "kaggle": {"accelerator": "nvidiaTeslaT4", "dataSources": [],
                   "isGpuEnabled": True, "isInternetEnabled": True,
                   "language": "python", "sourceType": "notebook"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = "/sessions/loving-trusting-wright/mnt/outputs/ayur_model_testing.ipynb"
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote %s  (%d cells)" % (out, len(cells)))
