#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ayurveda Shloka Benchmark — scoring engine
==========================================

Adapted from the Cardiac-LLM Indic benchmark for the AyurShloka-QA question set.

Task types: ``assertion``, ``mcq``, ``fill_blanks``, ``match_column``.
All four are 4-option items, so every type gets BOTH:

  * classification metrics — accuracy, precision/recall/F1 (micro / macro /
    weighted) and a confusion matrix over the predicted option letter;
  * generation metrics — exact match, token P/R/F1, ROUGE-1/2/L, BLEU, METEOR
    and BERTScore against the full text of the correct option;

plus latency and tokens/sec.

Import-safe: ``import ayur_benchmark`` performs no downloads, no NLTK fetches and
no model loading. Heavy dependencies are imported lazily on first use.

Typical use::

    import ayur_benchmark as ab
    ab.run_benchmark("Qwen/Qwen2.5-3B-Instruct", data_dir="data", results_dir="results")
    ab.leaderboard("results")
"""
from __future__ import annotations

import csv
import json
import os
import re
import string
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

__all__ = [
    "TASK_TYPES", "FILENAME_MAP", "run_benchmark", "compare_models",
    "validate_data", "leaderboard", "pivot_view", "recommend",
    "load_jsonl", "score_records", "resolve_letter",
]

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
TASK_TYPES: List[str] = ["assertion", "mcq", "fill_blanks", "match_column"]

#: task type -> expected file name inside ``data_dir``
FILENAME_MAP: Dict[str, str] = {
    "assertion":    "ayur_assertion_25.jsonl",
    "mcq":          "ayur_mcq_25.jsonl",
    "fill_blanks":  "ayur_fill_blanks_25.jsonl",
    "match_column": "ayur_match_column_25.jsonl",
}

MAX_PARAMS_DEFAULT = 8_000_000_000          # hard cap: 8B params
BERTSCORE_MODEL = "bert-base-multilingual-cased"   # multilingual: handles Devanagari
CHOICE_LETTERS = ["A", "B", "C", "D"]
NO_ANSWER = "NONE"                          # model produced no parseable choice

#: per-type instruction appended to the prompt so the model knows the answer format
ANSWER_DIRECTIVE: Dict[str, str] = {
    "assertion": ("You are an expert in classical Ayurveda. Choose the single correct "
                  "option. Reply with ONLY the option letter (A, B, C or D)."),
    "mcq": ("You are an expert in classical Ayurveda. Choose the single correct option. "
            "Reply with ONLY the option letter (A, B, C or D)."),
    "fill_blanks": ("You are an expert in classical Ayurveda. Choose the option that "
                    "correctly fills the blank. Reply with ONLY the option letter "
                    "(A, B, C or D)."),
    "match_column": ("You are an expert in classical Ayurveda. Choose the option giving "
                     "the correct set of matches. Reply with ONLY the option letter "
                     "(A, B, C or D)."),
}

_DEPS: dict = {}


# --------------------------------------------------------------------------
# Lazy dependency loading (keeps `import ayur_benchmark` instant + side-effect free)
# --------------------------------------------------------------------------
def _ensure_scoring_deps():
    """Import + prepare the metric libraries. Safe to call repeatedly."""
    if _DEPS.get("scoring"):
        return _DEPS

    from rouge_score import rouge_scorer
    import nltk
    from nltk.translate.bleu_score import SmoothingFunction
    from sklearn.metrics import (
        f1_score, precision_score, recall_score, accuracy_score, confusion_matrix,
    )

    for pkg, path in [("punkt", "tokenizers/punkt"), ("punkt_tab", "tokenizers/punkt_tab"),
                      ("wordnet", "corpora/wordnet"), ("omw-1.4", "corpora/omw-1.4")]:
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass

    _DEPS.update(
        scoring=True,
        rouge=rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True),
        smoothing=SmoothingFunction().method1,
        nltk=nltk,
        f1_score=f1_score, precision_score=precision_score, recall_score=recall_score,
        accuracy_score=accuracy_score, confusion_matrix=confusion_matrix,
    )
    return _DEPS


def _ensure_torch():
    if "torch" not in _DEPS:
        import torch
        _DEPS["torch"] = torch
    return _DEPS["torch"]


# --------------------------------------------------------------------------
# Text utilities
# --------------------------------------------------------------------------
def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def exact_match(pred: str, gold: str) -> int:
    return int(normalize_text(pred) == normalize_text(gold))


def token_prf(pred: str, gold: str):
    """SQuAD-style token overlap -> precision, recall, f1, tp, fp, fn."""
    p_toks, g_toks = normalize_text(pred).split(), normalize_text(gold).split()
    common = Counter(p_toks) & Counter(g_toks)
    tp = sum(common.values())
    fp, fn = len(p_toks) - tp, len(g_toks) - tp
    if tp == 0:
        return 0.0, 0.0, 0.0, tp, fp, fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1, tp, fp, fn


def _token_f1(a: str, b: str) -> float:
    return token_prf(a, b)[2]


# ---- answer extraction ----------------------------------------------------
# A leading option letter must be followed by a delimiter, a line break, or the end of
# the string. Notably this accepts "A\n\nExplanation: ..." - the single most common
# instruct-model response shape - while still refusing "A patient presents with ...",
# where "A" is the English article.
_LEADING_LETTER = re.compile(
    r"^\s*[\*_`\"'(\[]*\s*([A-D])\s*(?:[\)\].:,\-—*_`]|\r?\n|$)")
_LEADING_LETTER_VERB = re.compile(
    r"^\s*\(?([A-D])\)?\s+(?=is\b|would\b|seems\b|appears\b|correct\b|option\b)",
    re.IGNORECASE)
_BARE_LETTER = re.compile(r"^\s*[\*_`\"'(\[]*\s*([A-D])\s*[\)\]\*_`\"'.]*\s*$")
_STATED_ANSWER = re.compile(
    r"(?:final\s+)?(?:answer|option|choice|correct(?:\s+option)?)\s*(?:is|:|-|=)?\s*"
    r"[\*_`(\[]*\s*([A-D])\b", re.IGNORECASE)
_BOLD_LETTER = re.compile(r"\*\*\s*\(?([A-D])\)?\s*\*\*")
_MATCH_KEY = re.compile(r"\b(i{1,3}|iv)\s*[-–—:]\s*([abcd])\b", re.IGNORECASE)


def _match_permutation(text: str) -> Optional[str]:
    """Pull an 'i-c, ii-a, iii-b, iv-d' style mapping out of free text."""
    pairs = _MATCH_KEY.findall(text or "")
    seen = {}
    for roman, letter in pairs:
        roman = roman.lower()
        if roman in ("i", "ii", "iii", "iv") and roman not in seen:
            seen[roman] = letter.lower()
    if len(seen) == 4:
        return ", ".join("%s-%s" % (r, seen[r]) for r in ("i", "ii", "iii", "iv"))
    return None


def resolve_letter(pred: str, options: Optional[Dict[str, str]] = None) -> str:
    """Map a raw generation onto an option letter.

    Tries, in order: an explicit stated answer, a leading/bare/bold letter, a
    verbatim match against an option's text, a match-the-column permutation, and
    finally best token-overlap against the option texts. Returns ``NONE`` when the
    model produced nothing usable — which is itself worth seeing in the confusion
    matrix, since it separates "wrong" from "did not follow the format".
    """
    text = (pred or "").strip()
    if not text:
        return NO_ANSWER

    for rx in (_STATED_ANSWER, _BOLD_LETTER, _BARE_LETTER,
               _LEADING_LETTER, _LEADING_LETTER_VERB):
        m = rx.match(text) if rx in (_BARE_LETTER, _LEADING_LETTER,
                                     _LEADING_LETTER_VERB) else rx.search(text)
        if m:
            return m.group(1).upper()

    if options:
        norm_pred = normalize_text(text)
        # verbatim containment — longest option first to avoid substring collisions
        for letter, opt in sorted(options.items(), key=lambda kv: -len(kv[1] or "")):
            n_opt = normalize_text(opt)
            if len(n_opt) >= 8 and n_opt in norm_pred:
                return letter.upper()
        # match-the-column permutation stated in prose
        perm = _match_permutation(text)
        if perm:
            for letter, opt in options.items():
                if _match_permutation(opt) == perm:
                    return letter.upper()
        # fuzzy fallback
        scored = [(_token_f1(text, opt or ""), letter) for letter, opt in options.items()]
        best_score, best_letter = max(scored)
        runner_up = sorted((s for s, _ in scored), reverse=True)[1] if len(scored) > 1 else 0.0
        if best_score >= 0.55 and best_score - runner_up >= 0.10:
            return best_letter.upper()

    return NO_ANSWER


# ---- generation metrics ---------------------------------------------------
def rouge_scores(pred: str, gold: str):
    d = _ensure_scoring_deps()
    s = d["rouge"].score(gold, pred)
    return s["rouge1"].fmeasure, s["rouge2"].fmeasure, s["rougeL"].fmeasure


def bleu_score(pred: str, gold: str) -> float:
    d = _ensure_scoring_deps()
    from nltk.translate.bleu_score import sentence_bleu
    ref, hyp = normalize_text(gold).split(), normalize_text(pred).split()
    if not hyp or not ref:
        return 0.0
    try:
        return sentence_bleu([ref], hyp, smoothing_function=d["smoothing"])
    except Exception:
        return 0.0


def meteor(pred: str, gold: str) -> float:
    _ensure_scoring_deps()
    from nltk.translate.meteor_score import meteor_score
    ref, hyp = normalize_text(gold).split(), normalize_text(pred).split()
    if not hyp or not ref:
        return 0.0
    try:
        return meteor_score([ref], hyp)
    except Exception as e:
        # Silent zeros here would look like a model failure rather than a missing
        # corpus, so say it once, loudly.
        if not _DEPS.get("meteor_warned"):
            _DEPS["meteor_warned"] = True
            print("  [WARN] METEOR unavailable (%s: %s) — the nltk 'wordnet' corpus is "
                  "missing, so METEOR will report 0.0 for every row. Fix with "
                  "`import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')` "
                  "(needs Internet ON). All other metrics are unaffected."
                  % (type(e).__name__, e))
        return 0.0


def bertscore_batch(preds: Sequence[str], golds: Sequence[str], device: str):
    """Batched BERTScore across a whole task type — far faster than per-example."""
    from bert_score import score as bertscore_score
    safe = [(p if (p or "").strip() else " ", g if (g or "").strip() else " ")
            for p, g in zip(preds, golds)]
    P, R, F1 = bertscore_score(
        [p for p, _ in safe], [g for _, g in safe],
        model_type=BERTSCORE_MODEL, lang=None, rescale_with_baseline=False,
        device=device if "cuda" in str(device) else "cpu", verbose=False,
    )
    return P.tolist(), R.tolist(), F1.tolist()


# --------------------------------------------------------------------------
# Data loading / validation
# --------------------------------------------------------------------------
def load_jsonl(path) -> List[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _parse_options(row: dict) -> Dict[str, str]:
    raw = row.get("input") or ""
    if isinstance(raw, dict):
        return {k.upper(): v for k, v in raw.items()}
    if not str(raw).strip():
        return {}
    try:
        return {k.upper(): v for k, v in json.loads(raw).items()}
    except Exception:
        return {}


def validate_data(data_dir="data", types: Optional[Sequence[str]] = None) -> bool:
    """Print a validation report for the eval files. Returns True if all clean."""
    data_dir = Path(data_dir)
    types = list(types or TASK_TYPES)
    print("=" * 72)
    print("AYURVEDA BENCHMARK — DATASET VALIDATION")
    print("=" * 72)
    ok = True
    for dtype in types:
        path = data_dir / FILENAME_MAP[dtype]
        print("\n--- %s ---" % dtype.upper())
        if not path.exists():
            print("  FILE NOT FOUND: %s" % path)
            ok = False
            continue
        rows = load_jsonl(path)
        bad_opts = sum(1 for r in rows if len(_parse_options(r)) != 4)
        bad_key = sum(1 for r in rows
                      if str(r.get("output", "")).strip().upper() not in CHOICE_LETTERS)
        mismatched = 0
        for r in rows:
            opts = _parse_options(r)
            key = str(r.get("output", "")).strip().upper()
            if opts and key in opts and r.get("output_text"):
                if normalize_text(opts[key]) != normalize_text(r["output_text"]):
                    mismatched += 1
        empty_instr = sum(1 for r in rows if not str(r.get("instruction", "")).strip())
        books = Counter(r.get("source_book", "?") for r in rows)
        subs = Counter(r.get("question_subtype", "?") for r in rows)
        letters = Counter(str(r.get("output", "")).upper() for r in rows)

        print("  Rows                : %d" % len(rows))
        print("  Empty instruction   : %d" % empty_instr)
        print("  Rows without 4 opts : %d" % bad_opts)
        print("  Bad answer key      : %d" % bad_key)
        print("  Key/text mismatch   : %d" % mismatched)
        print("  Answer letters      : %s" % dict(sorted(letters.items())))
        print("  Books               : %d  %s" % (len(books), dict(books.most_common())))
        print("  Subtypes            : %s" % dict(subs.most_common()))
        if empty_instr or bad_opts or bad_key or mismatched:
            ok = False
            print("  WARNING: issues above will distort scores")

    print("\n%s" % ("DATASET LOOKS CLEAN." if ok else "DATASET HAS ISSUES — fix before trusting scores."))
    return ok


# --------------------------------------------------------------------------
# Model loading + generation
# --------------------------------------------------------------------------
def load_model(model_name: str, device: str = "cuda", force_size: bool = False,
               load_in_4bit: bool = False, max_params: int = MAX_PARAMS_DEFAULT):
    torch = _ensure_torch()
    from transformers import AutoTokenizer, AutoModelForCausalLM

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    # decoder-only models MUST be left-padded for batched generation, otherwise the
    # generated continuation starts after the pad run and comes back empty/garbage
    tokenizer.padding_side = "left"

    dtype = torch.float16 if "cuda" in device else torch.float32
    kwargs = dict(trust_remote_code=True,
                  device_map={"": 0} if "cuda" in device else None)

    if load_in_4bit:
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
    else:
        kwargs["dtype"] = dtype

    def _load(**extra):
        try:                                  # transformers >= 4.56 uses `dtype`
            return AutoModelForCausalLM.from_pretrained(model_name, **kwargs, **extra)
        except TypeError:                     # older versions want `torch_dtype`
            k = dict(kwargs)
            if "dtype" in k:
                k["torch_dtype"] = k.pop("dtype")
            return AutoModelForCausalLM.from_pretrained(model_name, **k, **extra)

    try:
        model = _load()
    except OSError:
        model = _load(use_safetensors=False)

    n_params = sum(p.numel() for p in model.parameters())
    print("Model params: %.2fB" % (n_params / 1e9))
    if n_params > max_params and not force_size:
        raise RuntimeError(
            "REJECTED: %s has %.2fB params — cap is %.1fB. "
            "Pass force_size=True to override." % (model_name, n_params / 1e9, max_params / 1e9)
        )
    model.eval()
    return tokenizer, model


def build_prompt(row: dict, dtype: str, tokenizer=None, use_chat_template: bool = True,
                 use_context: bool = False) -> str:
    """Assemble the prompt. Applies the model's chat template when it has one."""
    parts = []
    if use_context and str(row.get("context", "")).strip():
        parts.append("Context:\n%s" % row["context"])
    parts.append(row.get("instruction", ""))

    opts = _parse_options(row)
    if opts:
        parts.append("\n".join("(%s) %s" % (L, opts[L]) for L in CHOICE_LETTERS if L in opts))

    body = "\n\n".join(p for p in parts if p)
    directive = ANSWER_DIRECTIVE.get(dtype, "Reply with ONLY the option letter.")

    if use_chat_template and tokenizer is not None and getattr(tokenizer, "chat_template", None):
        messages = [{"role": "user", "content": "%s\n\n%s" % (directive, body)}]
        try:
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            pass
    return "%s\n\n%s\n\nAnswer:" % (directive, body)


def generate_batch(tokenizer, model, device, prompts, max_new_tokens=24):
    torch = _ensure_torch()
    enc = tokenizer(prompts, return_tensors="pt", padding=True,
                    truncation=True, max_length=2048).to(device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tokenizer.pad_token_id)
    texts = []
    for i in range(out.shape[0]):
        gen_ids = out[i][enc["input_ids"].shape[1]:]
        texts.append(tokenizer.decode(gen_ids, skip_special_tokens=True).strip())
    return texts


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def score_records(records: List[dict], device: str = "cpu", skip_bertscore: bool = False):
    """Score one task type. Returns (metrics dict, confusion dict)."""
    if not records:
        return {}, None
    d = _ensure_scoring_deps()
    n = len(records)

    # ---------- classification over the option letter ----------
    y_true = [r["gold_letter"] for r in records]
    y_pred = [r["pred_letter"] for r in records]
    labels = sorted(set(y_true) | set(y_pred))

    metrics = {
        "n": n,
        "accuracy": round(d["accuracy_score"](y_true, y_pred), 4),
        "f1_micro": round(d["f1_score"](y_true, y_pred, labels=labels, average="micro", zero_division=0), 4),
        "f1_macro": round(d["f1_score"](y_true, y_pred, labels=labels, average="macro", zero_division=0), 4),
        "f1_weighted": round(d["f1_score"](y_true, y_pred, labels=labels, average="weighted", zero_division=0), 4),
        "precision_micro": round(d["precision_score"](y_true, y_pred, labels=labels, average="micro", zero_division=0), 4),
        "precision_macro": round(d["precision_score"](y_true, y_pred, labels=labels, average="macro", zero_division=0), 4),
        "recall_micro": round(d["recall_score"](y_true, y_pred, labels=labels, average="micro", zero_division=0), 4),
        "recall_macro": round(d["recall_score"](y_true, y_pred, labels=labels, average="macro", zero_division=0), 4),
        "format_compliance": round(sum(1 for p in y_pred if p != NO_ANSWER) / n, 4),
        "random_baseline": 0.25,
    }
    cm = d["confusion_matrix"](y_true, y_pred, labels=labels)
    confusion = {"labels": labels, "matrix": cm.tolist()}

    # ---------- generation metrics against the correct option's text ----------
    preds = [r["pred"] for r in records]
    golds = [r["gold_text"] for r in records]

    ems, f1s, precs, recs, r1s, r2s, rLs, bl, mt = ([] for _ in range(9))
    tp_sum = fp_sum = fn_sum = 0
    for pred, gold in zip(preds, golds):
        ems.append(exact_match(pred, gold))
        p, rc, f1, tp, fp, fn = token_prf(pred, gold)
        precs.append(p); recs.append(rc); f1s.append(f1)
        tp_sum += tp; fp_sum += fp; fn_sum += fn
        a, b, c = rouge_scores(pred, gold)
        r1s.append(a); r2s.append(b); rLs.append(c)
        bl.append(bleu_score(pred, gold))
        mt.append(meteor(pred, gold))

    micro_p = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) else 0.0
    micro_r = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

    metrics.update({
        "exact_match": round(sum(ems) / n, 4),
        "token_precision_macro": round(sum(precs) / n, 4),
        "token_recall_macro": round(sum(recs) / n, 4),
        "token_f1_macro": round(sum(f1s) / n, 4),
        "token_precision_micro": round(micro_p, 4),
        "token_recall_micro": round(micro_r, 4),
        "token_f1_micro": round(micro_f1, 4),
        "rouge1": round(sum(r1s) / n, 4),
        "rouge2": round(sum(r2s) / n, 4),
        "rougeL": round(sum(rLs) / n, 4),
        "bleu": round(sum(bl) / n, 4),
        "meteor": round(sum(mt) / n, 4),
    })

    if skip_bertscore:
        metrics.update(bertscore_precision=None, bertscore_recall=None, bertscore_f1=None)
    else:
        try:
            bp, br, bf = bertscore_batch(preds, golds, device)
            metrics.update(
                bertscore_precision=round(sum(bp) / n, 4),
                bertscore_recall=round(sum(br) / n, 4),
                bertscore_f1=round(sum(bf) / n, 4),
            )
        except Exception as e:
            print("  BERTScore failed (%s) — reporting 0.0" % e)
            metrics.update(bertscore_precision=0.0, bertscore_recall=0.0, bertscore_f1=0.0)

    return metrics, confusion


def run_type(dtype, tokenizer, model, device, data_dir, batch_size, limit,
             max_new_tokens, use_chat_template, use_context, skip_bertscore):
    path = Path(data_dir) / FILENAME_MAP[dtype]
    if not path.exists():
        print("  (skip) %s not found" % path)
        return None, [], None

    rows = load_jsonl(path)
    if limit:
        rows = rows[:limit]

    records, total_new_tokens = [], 0
    t0 = time.time()
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        prompts = [build_prompt(r, dtype, tokenizer, use_chat_template, use_context)
                   for r in chunk]
        preds = generate_batch(tokenizer, model, device, prompts, max_new_tokens)
        for r, pred in zip(chunk, preds):
            total_new_tokens += len(tokenizer.encode(pred))
            opts = _parse_options(r)
            gold_letter = str(r.get("output", "")).strip().upper()
            records.append({
                "type": dtype,
                "id": r.get("id", ""),
                "instruction": r.get("instruction", ""),
                "input": r.get("input", ""),
                "gold_letter": gold_letter,
                "gold_text": r.get("output_text", opts.get(gold_letter, "")),
                "pred": pred,
                "pred_letter": resolve_letter(pred, opts),
                "correct": "",
                "source": r.get("source", ""),
                "source_book": r.get("source_book", ""),
                "difficulty": r.get("difficulty", ""),
                "question_subtype": r.get("question_subtype", ""),
                "subject_domain": r.get("subject_domain", ""),
                "language": r.get("language", "en"),
            })
    for rec in records:
        rec["correct"] = int(rec["pred_letter"] == rec["gold_letter"])

    elapsed = time.time() - t0
    metrics, confusion = score_records(records, device, skip_bertscore)
    metrics["latency_sec"] = round(elapsed, 2)
    metrics["tokens_per_sec"] = round(total_new_tokens / elapsed if elapsed > 0 else 0.0, 2)
    return metrics, records, confusion


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def run_benchmark(model_name: str,
                  data_dir: str = "data",
                  results_dir: str = "results",
                  device: str = "cuda",
                  limit: int = 0,
                  batch_size: int = 4,
                  max_new_tokens: int = 24,
                  types: Optional[Sequence[str]] = None,
                  force_size: bool = False,
                  save_results: bool = True,
                  load_in_4bit: bool = False,
                  use_chat_template: bool = True,
                  use_context: bool = False,
                  skip_bertscore: bool = False,
                  max_params: int = MAX_PARAMS_DEFAULT) -> dict:
    """Benchmark one model over the Ayurveda question sets.

    Args:
        model_name: full HuggingFace repo id, e.g. ``"Qwen/Qwen2.5-3B-Instruct"``.
        data_dir: folder holding the four ``ayur_*_25.jsonl`` files.
        results_dir: where CSVs and the report are written.
        limit: cap rows per type (0 = all). Use with ``save_results=False`` for smoke tests.
        max_new_tokens: keep small (16-32); these are letter-answer tasks.
        load_in_4bit: quantise so 7-8B models fit on a single T4.
        use_chat_template: apply the model's chat template when it has one. Turn OFF
            for base (non-instruct) models.
        use_context: also feed the source passage. Off by default — with context the
            task becomes reading comprehension rather than recall of the texts.
        skip_bertscore: skip the BERTScore backbone download (faster smoke tests).
        save_results: False prints metrics but writes nothing, so quick runs never
            pollute leaderboard.csv.
    """
    types = list(types or TASK_TYPES)
    results_dir = Path(results_dir)

    print("\nModel      : %s" % model_name)
    print("Device     : %s" % device)
    print("Data dir   : %s" % data_dir)
    print("Types      : %s" % types)
    print("Limit      : %s" % (limit or "ALL"))
    print("4-bit      : %s" % load_in_4bit)
    print("Chat tmpl  : %s" % use_chat_template)
    print("Saving     : %s\n" % ("yes" if save_results else "no (sanity-check mode)"))

    tokenizer, model = load_model(model_name, device, force_size, load_in_4bit, max_params)

    all_metrics, all_records, confusions = {}, [], {}
    for dtype in types:
        print("\n--- Running %s ---" % dtype)
        metrics, records, confusion = run_type(
            dtype, tokenizer, model, device, data_dir, batch_size, limit,
            max_new_tokens, use_chat_template, use_context, skip_bertscore)
        if metrics:
            all_metrics[dtype] = metrics
            all_records.extend(records)
            print("  accuracy=%.4f  f1_macro=%.4f  format_compliance=%.2f  tok/s=%.1f"
                  % (metrics["accuracy"], metrics["f1_macro"],
                     metrics["format_compliance"], metrics["tokens_per_sec"]))
        if confusion:
            confusions[dtype] = confusion

    if all_metrics:
        overall = sum(m["accuracy"] * m["n"] for m in all_metrics.values()) / \
                  sum(m["n"] for m in all_metrics.values())
        print("\nOVERALL ACCURACY: %.4f  (random baseline 0.25)" % overall)

    if not save_results:
        print("\n(sanity-check mode: nothing written to %s)" % results_dir)
        return all_metrics

    results_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model_name)

    if all_records:
        with open(results_dir / ("benchmark_results_%s.csv" % safe), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(all_records[0].keys()))
            w.writeheader()
            w.writerows(all_records)

    for dtype, conf in confusions.items():
        p = results_dir / ("confusion_matrix_%s_%s.csv" % (dtype, safe))
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["true\\pred"] + conf["labels"])
            for label, row in zip(conf["labels"], conf["matrix"]):
                w.writerow([label] + row)
        print("Wrote confusion matrix: %s" % p)

    lb = results_dir / "leaderboard.csv"
    rows_out = [{"model": model_name, "type": dt, **m} for dt, m in all_metrics.items()]
    if rows_out:
        existing = []
        if lb.exists():
            with open(lb, newline="", encoding="utf-8") as f:
                existing = list(csv.DictReader(f))
        # drop previous rows for this model so re-runs replace rather than duplicate
        existing = [r for r in existing if r.get("model") != model_name]
        combined = existing + [{k: ("" if v is None else v) for k, v in r.items()}
                               for r in rows_out]
        keys = sorted({k for r in combined for k in r},
                      key=lambda k: (k != "model", k != "type", k != "n", k))
        with open(lb, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in combined:
                w.writerow({k: r.get(k, "") for k in keys})

    with open(results_dir / "benchmark_report.txt", "w", encoding="utf-8") as f:
        f.write("Ayurveda Shloka Benchmark Report\nModel: %s\n" % model_name)
        f.write("=" * 64 + "\n")
        for dtype, m in all_metrics.items():
            f.write("\n[%s] (n=%s)\n" % (dtype, m.get("n")))
            for k, v in m.items():
                if k != "n":
                    f.write("  %-24s: %s\n" % (k, v))
        if confusions:
            f.write("\n" + "=" * 64 + "\n")
            f.write("Confusion matrices: results/confusion_matrix_<type>_<model>.csv\n")

    print("\nDone. Results written to %s/" % results_dir)
    return all_metrics


def compare_models(model_names: Sequence[str], **kwargs) -> dict:
    """Run several models back to back; failures are recorded, not fatal."""
    out = {}
    for name in model_names:
        try:
            out[name] = run_benchmark(name, **kwargs)
        except Exception as e:
            print("\n!! %s FAILED: %s\n" % (name, e))
            out[name] = {"error": str(e)}
    return out


# --------------------------------------------------------------------------
# Reporting helpers
# --------------------------------------------------------------------------
def leaderboard(results_dir="results"):
    import pandas as pd
    return pd.read_csv(Path(results_dir) / "leaderboard.csv")


def pivot_view(results_dir="results", values=None):
    import pandas as pd
    df = leaderboard(results_dir)
    values = values or ["accuracy", "f1_macro", "f1_weighted", "format_compliance",
                        "bertscore_f1", "tokens_per_sec"]
    values = [v for v in values if v in df.columns]
    return df.pivot_table(index="model", columns="type", values=values, aggfunc="last")


def recommend(results_dir="results", weights=None):
    """Rank models by a composite score to shortlist a fine-tuning base.

    Default weighting favours reasoning-heavy types and rewards format compliance,
    since a model that cannot emit a clean answer letter is painful to evaluate
    even if its underlying knowledge is fine.
    """
    import pandas as pd
    df = leaderboard(results_dir)
    weights = weights or {"mcq": 0.35, "assertion": 0.25,
                          "fill_blanks": 0.20, "match_column": 0.20}

    acc = df.pivot_table(index="model", columns="type", values="accuracy", aggfunc="last")
    comp = df.pivot_table(index="model", columns="type", values="format_compliance", aggfunc="last")
    speed = df.pivot_table(index="model", columns="type", values="tokens_per_sec", aggfunc="last")

    out = pd.DataFrame(index=acc.index)
    for t in TASK_TYPES:
        out["acc_" + t] = acc[t] if t in acc.columns else float("nan")
    out["weighted_accuracy"] = sum(
        out["acc_" + t].fillna(0) * w for t, w in weights.items() if "acc_" + t in out)
    out["mean_format_compliance"] = comp.mean(axis=1) if not comp.empty else float("nan")
    out["mean_tokens_per_sec"] = speed.mean(axis=1) if not speed.empty else float("nan")
    out["lift_over_random"] = out["weighted_accuracy"] - 0.25
    out["composite"] = (0.80 * out["weighted_accuracy"]
                        + 0.20 * out["mean_format_compliance"].fillna(0))
    return out.sort_values("composite", ascending=False).round(4)


if __name__ == "__main__":
    validate_data(os.environ.get("AYUR_DATA_DIR", "data"))
