#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BhashaBench-Ayur Evaluation Harness for AyurLLM vs. AyurParam
=============================================================
Evaluates language models on BhashaBench-Ayur (BBA) across four ablation conditions:
  1. Base model alone (e.g. sarvamai/sarvam-1)
  2. Base + QLoRA adapter (e.g. nishm27/sarvam-1-TRIM or local checkpoint)
  3. Base + GraphRAG / Hybrid Retrieval (retrieved classical shloka context)
  4. Base + QLoRA + GraphRAG / Hybrid Retrieval (full proposed pipeline)

Metrics & Splits:
  - English vs. Hindi accuracy
  - Per-category accuracy across BBA subdisciplines (Kayachikitsa, Dravyaguna, Shalya Tantra, etc.)
  - Difficulty breakdown (Easy, Medium, Hard)
  - Comparison against AyurParam (arXiv:2511.02374: English 41.12%, Hindi 38.04%, Overall 39.97%)

Usage:
  # 1. Base model
  python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --mode base --output_dir eval/results_base

  # 2. QLoRA adapter
  python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --adapter nishm27/sarvam-1-TRIM --mode qlora --output_dir eval/results_qlora

  # 3. GraphRAG only
  python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --mode graphrag --corpus_path "verified data/tokenized/tokenized_corpus_all_books.jsonl" --output_dir eval/results_graphrag

  # 4. QLoRA + GraphRAG
  python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --adapter nishm27/sarvam-1-TRIM --mode both --corpus_path "verified data/tokenized/tokenized_corpus_all_books.jsonl" --output_dir eval/results_both
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("BBA-Eval")

# Published reference scores from AyurParam (arXiv:2511.02374v1)
AYURPARAM_SCORES = {
    "overall": 0.3997,
    "english": 0.4112,
    "hindi": 0.3804,
    "source": "https://arxiv.org/html/2511.02374v1",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate on BhashaBench-Ayur benchmark.")
    parser.add_argument("--model", type=str, default="sarvamai/sarvam-1",
                        help="HuggingFace model ID or local path to base model.")
    parser.add_argument("--adapter", type=str, default=None,
                        help="HuggingFace model ID or local path to PEFT LoRA adapter.")
    parser.add_argument("--mode", type=str, default="base",
                        choices=["base", "qlora", "graphrag", "both"],
                        help="Ablation condition to run.")
    parser.add_argument("--dataset_name", type=str, default="bharatgenai/BhashaBench-Ayur",
                        help="HuggingFace dataset repository name or local path to parquet/jsonl.")
    parser.add_argument("--local_bba_file", type=str, default=None,
                        help="Path to local BBA parquet/json file if running offline.")
    parser.add_argument("--corpus_path", type=str, default="verified data/tokenized/tokenized_corpus_all_books.jsonl",
                        help="Path to verified chunk corpus for GraphRAG/hybrid retrieval.")
    parser.add_argument("--top_k", type=int, default=3,
                        help="Number of chunks to retrieve in GraphRAG mode.")
    parser.add_argument("--output_dir", type=str, default="eval/results",
                        help="Directory to store evaluation logs and metric tables.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Optional limit on number of items per split (for testing/quick audits).")
    parser.add_argument("--batch_size", type=int, default=8,
                        help="Batch size for model inference.")
    parser.add_argument("--device", type=str, default="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") != "" else "cpu",
                        help="Device to run inference on.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Simple BM25 / Cosine hybrid retriever for offline GraphRAG simulation
# ---------------------------------------------------------------------------
class SimpleHybridRetriever:
    """Retrieves top-k classical shloka chunks matching the query.
    Used when connecting to live Neo4j/Meilisearch is unavailable or during local eval."""
    def __init__(self, corpus_path: str):
        self.chunks = []
        self._load_corpus(corpus_path)

    def _load_corpus(self, path: str):
        if not os.path.exists(path):
            logger.warning(f"Corpus path {path} not found. GraphRAG retrieval will return empty context.")
            return
        logger.info(f"Loading retrieval corpus from {path}...")
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.chunks.append(json.loads(line))
            logger.info(f"Loaded {len(self.chunks)} verified corpus chunks for GraphRAG.")
        except Exception as e:
            logger.warning(f"Failed to load corpus: {e}")

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []
        q_words = set(re.findall(r"\w+", query.lower()))
        scores = []
        for i, c in enumerate(self.chunks):
            text = (c.get("sanskrit_text", "") + " " +
                    c.get("commentary", "") + " " +
                    c.get("topic_heading", "")).lower()
            overlap = sum(1 for w in q_words if w in text)
            if overlap > 0:
                scores.append((overlap, i))
        scores.sort(reverse=True)
        return [self.chunks[idx] for _, idx in scores[:top_k]]


def format_bba_prompt(question: str, options: Dict[str, str], context: Optional[str] = None, language: str = "en") -> str:
    """Builds standard evaluation prompt for 4-option multiple-choice items."""
    prompt = ""
    if context:
        prompt += f"Context from Classical Ayurvedic Treatises:\n{context}\n\n"
    
    prompt += f"Question: {question}\n\nOptions:\n"
    for opt_key in ["A", "B", "C", "D"]:
        if opt_key in options and options[opt_key]:
            prompt += f"{opt_key}. {options[opt_key]}\n"
    
    prompt += "\nAnswer with only the correct option letter (A, B, C, or D).\nAnswer:"
    return prompt


def extract_prediction(raw_output: str) -> Optional[str]:
    """Robust extraction of option letter from model generation."""
    s = raw_output.strip()
    # Match leading letter like "A", "A)", "Option A", "(A)"
    m = re.search(r"^(?:option\s+)?[\(\[]?([A-D])[\)\]\.\:]?", s, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Fallback: search for first standalone A, B, C, or D
    m = re.search(r"\b([A-D])\b", s, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def evaluate_dataset(args):
    os.makedirs(args.output_dir, exist_ok=True)
    logger.info(f"=== Starting BhashaBench-Ayur Evaluation ===")
    logger.info(f"Model: {args.model} | Adapter: {args.adapter} | Mode: {args.mode}")

    # Load dataset
    items = []
    if args.local_bba_file and os.path.exists(args.local_bba_file):
        logger.info(f"Loading local BBA file from {args.local_bba_file}")
        if args.local_bba_file.endswith(".parquet"):
            import pandas as pd
            df = pd.read_parquet(args.local_bba_file)
            items = df.to_dict(orient="records")
        else:
            with open(args.local_bba_file, "r", encoding="utf-8") as f:
                items = [json.loads(l) for l in f if l.strip()]
    else:
        logger.info(f"Loading dataset from HuggingFace Hub: {args.dataset_name}")
        try:
            from datasets import load_dataset
            ds = load_dataset(args.dataset_name)
            # Combine test or validation splits
            split_key = "test" if "test" in ds else list(ds.keys())[0]
            items = list(ds[split_key])
            logger.info(f"Successfully loaded {len(items)} samples from split '{split_key}'")
        except Exception as e:
            logger.error(f"Could not load HuggingFace dataset {args.dataset_name}: {e}")
            logger.warning("Falling back to local Parquet/REPORTS data if present...")
            parquet_fallback = "Parqet/test.parquet"
            if os.path.exists(parquet_fallback):
                import pandas as pd
                df = pd.read_parquet(parquet_fallback)
                items = df.to_dict(orient="records")
                logger.info(f"Loaded {len(items)} items from fallback {parquet_fallback}")
            else:
                raise RuntimeError("No evaluation dataset available. Provide --local_bba_file or internet access.")

    if args.limit:
        logger.info(f"Limiting evaluation to {args.limit} samples.")
        items = items[:args.limit]

    # Initialize GraphRAG retriever if needed
    retriever = None
    if args.mode in ["graphrag", "both"]:
        logger.info(f"Initializing GraphRAG Hybrid Retriever with {args.corpus_path}")
        retriever = SimpleHybridRetriever(args.corpus_path)

    # Check for PyTorch & Transformers
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        logger.error("torch, transformers, and peft are required to run inference.")
        logger.info("Writing placeholder template for execution on compute node.")
        _write_stub_results(args)
        return

    logger.info(f"Loading tokenizer for {args.model}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    logger.info(f"Loading model weights for {args.model}...")
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch_dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )

    if args.adapter and args.mode in ["qlora", "both"]:
        logger.info(f"Attaching LoRA adapter from {args.adapter}...")
        model = PeftModel.from_pretrained(model, args.adapter)

    model.eval()

    # Evaluation loop
    results = []
    category_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    lang_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    diff_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    overall_correct = 0
    total_valid = 0

    logger.info(f"Starting inference across {len(items)} items...")
    start_time = time.time()

    for idx, item in enumerate(items):
        q_text = item.get("question", "")
        options = {
            "A": str(item.get("option_a", "")),
            "B": str(item.get("option_b", "")),
            "C": str(item.get("option_c", "")),
            "D": str(item.get("option_d", "")),
        }
        gold = str(item.get("correct_answer", "")).strip().upper()
        # Normalize gold answer (e.g. 'option_a' -> 'A', '1' -> 'A')
        if gold.startswith("OPTION_"):
            gold = gold.replace("OPTION_", "")
        if gold in ["1", "2", "3", "4"]:
            gold = {"1": "A", "2": "B", "3": "C", "4": "D"}[gold]

        category = item.get("subject_domain") or item.get("primary_category") or "General"
        language = item.get("language") or ("hi" if re.search(r"[\u0900-\u097F]", q_text) else "en")
        difficulty = item.get("difficulty") or item.get("difficulty_bba") or "Medium"

        context = None
        if retriever is not None:
            retrieved_chunks = retriever.retrieve(q_text, top_k=args.top_k)
            if retrieved_chunks:
                context_parts = []
                for c in retrieved_chunks:
                    c_txt = c.get("sanskrit_text", "") + "\n" + c.get("commentary", "")
                    context_parts.append(f"[{c.get('source_book', '')} {c.get('verse_id', '')}]: {c_txt.strip()}")
                context = "\n---\n".join(context_parts)

        prompt = format_bba_prompt(q_text, options, context=context, language=language)

        # Tokenize and generate
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1536)
        if torch.cuda.is_available():
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=8,
                temperature=0.0,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )

        gen_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        raw_pred = tokenizer.decode(gen_tokens, skip_special_tokens=True)
        pred_letter = extract_prediction(raw_pred)

        is_correct = (pred_letter == gold)
        if is_correct:
            overall_correct += 1
        total_valid += 1

        category_stats[category]["total"] += 1
        lang_stats[language]["total"] += 1
        diff_stats[difficulty]["total"] += 1
        if is_correct:
            category_stats[category]["correct"] += 1
            lang_stats[language]["correct"] += 1
            diff_stats[difficulty]["correct"] += 1

        results.append({
            "idx": idx,
            "question": q_text[:100],
            "gold": gold,
            "pred": pred_letter,
            "raw_output": raw_pred.strip(),
            "is_correct": is_correct,
            "category": category,
            "language": language,
            "difficulty": difficulty,
        })

        if (idx + 1) % 50 == 0 or (idx + 1) == len(items):
            current_acc = overall_correct / total_valid if total_valid else 0.0
            logger.info(f"Processed {idx + 1}/{len(items)} | Current Acc: {current_acc:.4f}")

    elapsed = time.time() - start_time
    overall_acc = overall_correct / total_valid if total_valid else 0.0

    summary = {
        "model": args.model,
        "adapter": args.adapter,
        "mode": args.mode,
        "total_evaluated": total_valid,
        "overall_accuracy": round(overall_acc, 4),
        "ayurparam_comparison": {
            "our_score": round(overall_acc, 4),
            "ayurparam_reported": AYURPARAM_SCORES["overall"],
            "delta": round(overall_acc - AYURPARAM_SCORES["overall"], 4),
        },
        "by_language": {
            lang: {
                "accuracy": round(d["correct"] / d["total"], 4) if d["total"] else 0.0,
                "count": d["total"],
                "ayurparam_ref": AYURPARAM_SCORES.get(lang.lower(), None)
            } for lang, d in lang_stats.items()
        },
        "by_difficulty": {
            diff: {
                "accuracy": round(d["correct"] / d["total"], 4) if d["total"] else 0.0,
                "count": d["total"]
            } for diff, d in diff_stats.items()
        },
        "by_category": {
            cat: {
                "accuracy": round(d["correct"] / d["total"], 4) if d["total"] else 0.0,
                "count": d["total"]
            } for cat, d in sorted(category_stats.items(), key=lambda x: -x[1]["total"])
        },
        "elapsed_sec": round(elapsed, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    report_path = os.path.join(args.output_dir, f"bba_report_{args.mode}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Evaluation complete in {elapsed:.1f}s!")
    logger.info(f"Overall Accuracy: {overall_acc:.4f} (AyurParam: {AYURPARAM_SCORES['overall']})")
    logger.info(f"Saved full report to {report_path}")
    print("\n" + "="*60)
    print(f"BhashaBench-Ayur Evaluation Results [{args.mode.upper()}]")
    print(f"Overall Accuracy : {overall_acc*100:.2f}% (vs. AyurParam {AYURPARAM_SCORES['overall']*100:.2f}%)")
    for lang, d in summary["by_language"].items():
        print(f"  - {lang.upper():8s}: {d['accuracy']*100:.2f}% (N={d['count']})")
    print("="*60 + "\n")


def _write_stub_results(args):
    """Writes empty result template when running on non-GPU environment."""
    os.makedirs(args.output_dir, exist_ok=True)
    stub = {
        "status": "pending_gpu_execution",
        "model": args.model,
        "adapter": args.adapter,
        "mode": args.mode,
        "note": "Execute this script inside a GPU environment (e.g. Kaggle T4) to populate final scores.",
        "ayurparam_baseline": AYURPARAM_SCORES,
    }
    with open(os.path.join(args.output_dir, f"bba_report_{args.mode}_stub.json"), "w", encoding="utf-8") as f:
        json.dump(stub, f, indent=2)


if __name__ == "__main__":
    evaluate_dataset(parse_args())

