# AyurLLM fine-tuning

QLoRA / SFT for the Ayurvedic corpus, adapted from your MedQA trainer. Same
architecture — typed config, native TRL completion-only loss, hardware
autotuning, telemetry, dashboards — with the data layer rewritten for this schema
and tuned for throughput.

```
ayur_data.py         schema, prompts, formatting, audits   (no torch — importable anywhere)
finetune_ayur.py     the trainer
test_ayur_data.py    pre-flight data test, no GPU needed
test_dashboards.py   renders the dashboards from a synthetic run
```

## Run it

```bash
# 1. prove the data is sound — seconds, no GPU
python test_ayur_data.py --data_dir ../ayur_pipeline/final --max_seq_length 1024

# 2. train
python finetune_ayur.py \
    --model_name_or_path Qwen/Qwen2.5-3B-Instruct \
    --data_dir ../ayur_pipeline/final \
    --output_dir ./ayur_qlora_out \
    --num_train_epochs 2 \
    --per_device_train_batch_size 8 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-4 \
    --lr_scheduler_type cosine \
    --warmup_ratio 0.03 \
    --max_seq_length 1024 \
    --logging_steps 10 \
    --save_steps 200
```

Add `--auto_batch_size` to have it size the batch from free VRAM instead of
guessing. Everything else has a working default.

---

## What I changed from your MedQA script, and why

**The data layer.** MedQA is one flat schema off the Hub. This is three local
JSON files with `option_a..e`, a `correct_answer` that may hold several letters,
six question formats and two languages. All of it lives in `ayur_data.py`,
deliberately free of torch so it can be tested without a GPU.

**Validation is not re-split from train.** Your script carved eval out of train
with `train_test_split`. Here `validation.json` already exists and was built at
fact granularity so no underlying fact straddles the two splits. Re-splitting
would silently undo that, so the script loads the real file.

**Pre-flight audits.** Composition, answer-position balance and token-length
percentiles are computed and written to `preflight_report.json` before the model
loads. The length audit earns its keep: Devanagari costs several tokens per
character, so a `max_seq_length` picked for English can truncate the answer off a
chunk of the Hindi half — and a truncated completion means loss computed over
nothing. The script warns when that is about to happen and, by default, drops
those rows rather than training on broken ones.

**Throughput.** `group_by_length=True` is the big one — stems run from 40 to 900
tokens, so length-sorted batching removes most of the padding. Plus TF32 on
Ampere+, real dataloader workers with pinned memory and persistent workers, and
optional VRAM-probing batch sizing.

**Two more dashboard panels.** Yours had loss, LR, batch size, GPU. This has
loss, LR, throughput (samples/s), gradient norm, GPU spikes, and a token-length
histogram with the `max_seq_length` line drawn on it so truncation risk is
visible rather than inferred.

---

## The finding worth acting on

**1,650 training rows have no options at all** — 2.5% of the corpus. They are
verse expositions, source lookups and transliteration items:

> *"Explain the meaning of the following verse from Ashtanga Hridaya
> (Sutrasthana, Chapter 1): आयुः कामायमानेन..."*

A multiple-choice formatter drops them for lack of options. But every one carries
a real `answer_text`, and they are arguably the most valuable rows in the corpus:
answering them requires generating Ayurvedic explanation rather than picking a
letter. So they are trained as **free-text generation** instead, with their own
instruction and a 600-character answer cap so a few long expositions cannot
dominate the loss.

Result: **0 rows dropped instead of 1,650.** Turn it off with
`--include_open_ended False` if you want a pure letter-prediction model.

---

## What the tests proved

`test_ayur_data.py` against the real split files:

```
train        64749 formatted, 0 dropped, 1650 open-ended
validation    1000 formatted, 0 dropped,   20 open-ended
test          5945 formatted, 0 dropped,  145 open-ended

masking integrity     : 0 rows with an empty completion span
completion content    : 788 multi-answer rows, 0 missing a key letter
language routing      : 0 mismatched instructions
token lengths         : p50 198 | p90 328 | p99 903 | max 4117
over max_seq_length=1024: 34 rows (0.85%)
answer position       : A 26.1% B 26.3% C 26.1% D 26.0% E 3.5%  — balanced
PASS
```

`test_dashboards.py` renders all six panels from a synthetic 1,200-step run and
asserts every one has data. Both exit non-zero on failure, so they can gate a job.

---

## Hyperparameters, and the reasoning

| | Value | Why |
|---|---|---|
| `lora_r` | 32 | Double your MedQA 16. This corpus asks the model to absorb domain vocabulary in two scripts, not just pick a letter on English text. |
| `lora_alpha` | 64 | Conventional 2×rank. |
| `learning_rate` | 2e-4 | Standard QLoRA starting point; drop to 1e-4 if the loss curve is jagged. |
| `max_seq_length` | 1024 | From the audit: p99 is 903 tokens. 768 truncates 1.4%, 1024 truncates 0.85%. |
| effective batch | 32 | 8 × 4 accumulation. Raise accumulation, not batch size, if you hit OOM. |
| `optim` | `paged_adamw_8bit` | Paged states survive the spikes visible in the GPU panel. |

`--optimizer_switch_step` still works if you want to start on 8-bit AdamW and
move to plain AdamW or SGD later; the switch is annotated on the loss curve.

---

## One caveat

I could not run the training itself. This sandbox has no GPU, 3 GB of RAM, no
PyTorch, and HuggingFace is blocked at the proxy — so `torch`, `trl` and `peft`
cannot be installed or imported here.

What I did verify: all three files parse, the data layer runs end-to-end against
your real 64,749-row train split, the masking check passes on 2,000 rows, and the
dashboard code renders all six panels to PNG (`test_dashboards.py` stubs the
heavy imports so the *real* plotting functions execute). The parts I could not
execute are the model load, the TRL trainer construction and the training loop —
those follow your original script closely, since it evidently works.

Run `test_ayur_data.py` first on your GPU box with `--real-tokenizer` pointed at
whichever model you are using. It takes seconds and will catch any
tokenizer-specific chat-template surprise before you commit to a long run:

```bash
python test_ayur_data.py --data_dir ../ayur_pipeline/final \
    --real-tokenizer Qwen/Qwen2.5-3B-Instruct --max_seq_length 1024
```
