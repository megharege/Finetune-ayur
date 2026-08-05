# Hyperparameter tuning — `nishm27/sarvam-1-TRIM` on the Ayurveda hybrid split

Every hyperparameter is searchable, and **no trial is allowed to sit with a loss
that does not move**: five flat logged losses and the trial is killed, its
diagnosis recorded, and the sampler told it learned nothing rather than told the
region is bad.

```
search_space.json    what to search and what to freeze   (edit this)
tune_ayur.py         the tuner: samples, launches, watches, kills, ranks
fake_trainer.py      a GPU-free stand-in so you can test the tuner in seconds
test_tune.py         70 checks, no GPU, no model, no data — run this first
finetune_ayur.py     the trainer the tuner drives (unchanged interface)
```

---

## Run it

### 0. Install

```bash
pip install -q -U transformers trl peft bitsandbytes datasets accelerate optuna
```

`optuna` is the only new dependency. Stages `baseline` and `random` do not need
it; `bayes` does.

### 1. Pre-flight — 20 seconds, no GPU

```bash
python test_tune.py
```

Expect `70 passed, 0 failed`. This runs a complete search — sampling, launching,
stall detection, Optuna, SQLite resume — against `fake_trainer.py`, which has a
synthetic loss curve instead of a model. If something in the plumbing is broken
you find out here rather than four GPU-hours in.

### 2. Baseline — one run, known-good settings

```bash
python tune_ayur.py --stage baseline \
    --model nishm27/sarvam-1-TRIM \
    --data_dir "/kaggle/input/ayursplit" \
    --train_file "train - Hybrid.jsonl" \
    --eval_file  "validation - Hybrid.jsonl" \
    --outdir /kaggle/working/ayur_tune
```

Quote the filenames. Yours contain spaces, and an unquoted `$TRAIN_FILE` splits
into three argv elements — that is exactly the `Some specified arguments are not
used by the HfArgumentParser` error from the earlier run.

**Do not skip this.** It costs one trial and answers the only question that
matters before searching: does this model train on this data at all? Read the
eval loss it prints. If the baseline is broken, a search over it finds the least
broken corner of a broken space and reports it as a win.

### 3. Random search — 15 trials, broad

```bash
python tune_ayur.py --stage random --trials 15 \
    --model nishm27/sarvam-1-TRIM \
    --data_dir "/kaggle/input/ayursplit" \
    --train_file "train - Hybrid.jsonl" \
    --eval_file  "validation - Hybrid.jsonl" \
    --outdir /kaggle/working/ayur_tune
```

Random first, Bayesian second. TPE builds a density model of good and bad
regions, and with three or four points that model is mostly prior — it wastes
its early trials confirming the obvious. Fifteen random points map the space
cheaply, and the Bayesian stage starts with something to fit.

Read `results.json` and the printed top-5 before moving on. Look at *which*
parameter separates the good trials from the bad. If it is only ever the
learning rate, freeze the rest and search a narrower band.

### 4. Bayesian — 25 trials, focused

```bash
python tune_ayur.py --stage bayes --trials 25 \
    --model nishm27/sarvam-1-TRIM \
    --data_dir "/kaggle/input/ayursplit" \
    --train_file "train - Hybrid.jsonl" \
    --eval_file  "validation - Hybrid.jsonl" \
    --outdir /kaggle/working/ayur_tune \
    --pruner median --n-startup 5
```

State lives in `/kaggle/working/ayur_tune/study.db`. Kaggle kills the session
at 9 or 12 hours; rerun the identical command with `--resume` and it picks up
the same study rather than starting over. **Save the notebook output** — a
Kaggle session that ends without a commit takes `study.db` with it.

The run ends with a parameter-importance table. Anything near zero was not worth
a search dimension: freeze it with `{"fixed": ...}` and spend those trials on
what actually moved.

### 5. Retrain the winner

The summary prints the exact command, and `best_config.json` stores it under
`retrain_command`. Trials ran capped at 400 steps on 8,000 samples — that ranks
configs, it does not train a model. The retrain command uses the full split and
2 epochs.

---

## The stall detector

Your requirement was that a trial must not go five iterations without the loss
changing. Three things get caught, all of them common and all of them silent if
you only look at the final number:

| Verdict | Trigger | What it usually means |
|---|---|---|
| `flat` | last 5 logged losses span < `--stall-eps` (1e-3) | LR far too low, adapter attached to nothing, or nothing trainable |
| `diverged` | loss is NaN, inf, or > `--max-loss` (20) | LR too high — fires immediately, no window needed |
| `no_progress` | loss wobbles but never beats its prior best by `--min-delta` | stuck rather than merely noisy |

Defaults: 5 logs × `--logging-steps 10` = **a 50-step window**. Raise
`--stall-window` if your logging is dense, lower `--logging-steps` if you want a
faster verdict.

Two details that stop it misfiring:

**It needs a full window before it can call something flat.** The first few
steps of a perfectly healthy run are noisy and sometimes briefly flat; a
detector that fires on step 20 kills good trials.

**Progress is measured against the best loss seen before the window, not
against the window's own first value.** Without that, a run that improved
steadily and then settled at a good loss reads as "no progress", when what it
actually did was converge — the exact opposite verdict.

A stalled trial is reported to Optuna as **pruned, not as a bad score**. A
completed trial with a terrible value teaches TPE "this region is bad". A trial
that went flat because the sampled LR was 1e-9 says something about the LR and
nothing about the rest of the region, and scoring it steers the sampler away
from neighbourhoods that were fine.

The same reasoning applies to crashes. An OOM is labelled `oom` and a traceback
`failed`, and neither is scored — otherwise the sampler learns that `lora_r=64`
is bad when what happened is that `lora_r=64` did not fit in memory.

---

## `search_space.json`

Five kinds of entry:

```jsonc
{"fixed": 0.05}                    // never searched, passed through
{"loguniform": [5e-5, 5e-4]}       // continuous, log scale — use for LR
{"uniform": [0.0, 0.15]}           // continuous, linear
{"categorical": [8, 16, 32, 64]}   // discrete
{"int": [1, 4, 1]}                 // [lo, hi, step]
```

The tuner prints `SEARCHED` and `FROZEN` lists before the first trial, so a
parameter you meant to search but froze by accident is visible in the first ten
lines rather than after forty trials.

Two choices in the shipped space worth knowing about:

**`lora_alpha_mult`, not `lora_alpha`.** Alpha is sampled as a multiplier on
rank (1 or 2), because searching alpha directly spends trials on combinations
that violate the α ≈ r or 2r convention and are simply badly scaled adapters.

**Batch size and accumulation are searched separately but only the product
matters.** The tuner logs the effective batch for every trial so you can read
the results in those terms. If VRAM is the binding constraint, freeze
`per_device_train_batch_size` at what fits and search accumulation alone.

---

## Notes specific to this model and this data

**sarvam-1 is a base model, not an instruct model.** It has no chat template.
`ayur_data.format_example` detects that and falls back to a plain
`User: … / Answer:` framing, so nothing to configure — but it does mean you
cannot compare its loss against an instruct model's and read the difference as
quality.

**Set `max_seq_length` from the audit, not from intuition.** The trainer writes
`preflight_report.json` with the token-length percentiles for your actual
tokenizer. Devanagari costs several tokens per character on tokenizers built for
English; if `max_seq_length` is set for the English rows it truncates the
completion off the Hindi ones and you train on loss over nothing. Run the
baseline, read `pct_over_max_seq_length`, then narrow the `max_seq_length`
choices in the search space to the two values that bracket p99.

**Budget from the baseline, not from a guess.** The baseline prints its wall
time for 400 steps. Multiply by your trial count, add ~30% for the pruner not
firing as often as you hope, and compare against the session limit. If it does
not fit, cut `--max_train_samples` before you cut trials — trial count buys
coverage, sample count mostly buys a slightly less noisy ranking.

---

## Useful flags

| Flag | Default | Why you would change it |
|---|---|---|
| `--max-steps-per-trial` | 400 | Lower for a first sweep; too low and the ranking is noise |
| `--max_train_samples` | 8000 | Per trial, not total |
| `--trial-timeout` | 0 (off) | Set it on a shared box so one slow trial cannot eat the session |
| `--stall-window` | 5 | Your "5 iterations" |
| `--poll-seconds` | 10 | How often the metrics file is checked |
| `--pruner` | median | `hyperband` prunes harder; use it when trials are expensive |
| `--keep-checkpoints` | off | Adapters are deleted after each trial; 25 rank-64 adapters fill `/kaggle/working` |
| `--resume` | off | Continue an interrupted study |
| `--trainer` | `finetune_ayur.py` | Point at `fake_trainer.py` to rehearse without a GPU |

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| every trial `failed`, 0 steps | Read `trial_*/trial.log`. The first traceback is the whole story — usually a bad path or a missing HF token |
| `Some specified arguments are not used by the HfArgumentParser` | An unquoted filename with spaces |
| every trial `stalled/flat` at step 50 | LR range too low, or the adapter is not attached — check `trainable params` in the log |
| every trial `stalled/diverged` | LR range too high; lower the top of the `loguniform` band |
| all `oom` above some rank | Freeze `per_device_train_batch_size` at 2 and let accumulation carry the effective batch |
| `study.db` gone after a Kaggle restart | The session ended without a commit; save the notebook version |

---

## One change to `finetune_ayur.py`

`parse_arguments()` now drops any of its own dataclass fields whose flag
`SFTConfig` already owns, then copies the parsed value back. `HfArgumentParser`
adds one argparse option per field across every dataclass it is handed and
argparse raises on a duplicate — and which names collide moves between versions.
`SFTConfig` carried `max_seq_length` until TRL 0.20; `TrainingArguments` carried
`group_by_length` until transformers v5. On today's `pip install -U` there is no
collision and the code path is identical to before. On a pinned older stack it
would previously have raised at parser construction — inside a trial subprocess,
where it surfaces only as "every trial failed".

---

## Your HF token

The token pasted earlier in our conversation is in plaintext chat history and
should be revoked at <https://huggingface.co/settings/tokens>. Read it from
Kaggle Secrets instead:

```python
from kaggle_secrets import UserSecretsClient
os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
```
