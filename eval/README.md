# AyurLLM Evaluation Harness & Benchmark Replication Guide

This directory contains standalone, reproducible evaluation scripts to benchmark language models against the **BhashaBench-Ayur (BBA)** suite and compare head-to-head with published results from **AyurParam** (arXiv:2511.02374v1).

---

## 1. Quickstart

### Environment Setup
Install required dependencies:
```bash
pip install -q transformers peft datasets torch accelerate pandas numpy scikit-learn
```

---

## 2. Benchmark Ablation Protocol (AyurLLM vs. AyurParam)

To rigorously isolate gains from supervised domain fine-tuning (+QLoRA) and grounding (+GraphRAG), `eval/run_bhashabench_ayur.py` supports four standard ablation conditions:

| Condition | Command | Description |
|---|---|---|
| **Condition 1: Base Model** | `python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --mode base --output_dir eval/results_base` | Evaluates raw `sarvam-1` prior to domain adaptation. |
| **Condition 2: +QLoRA** | `python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --adapter nishm27/sarvam-1-TRIM --mode qlora --output_dir eval/results_qlora` | Evaluates `sarvam-1` with the trained 4-bit LoRA adapter. |
| **Condition 3: +GraphRAG** | `python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --mode graphrag --corpus_path "verified data/tokenized/tokenized_corpus_all_books.jsonl" --output_dir eval/results_graphrag` | Evaluates base `sarvam-1` augmented with retrieved classical shloka context. |
| **Condition 4: +Both (Proposed)** | `python eval/run_bhashabench_ayur.py --model sarvamai/sarvam-1 --adapter nishm27/sarvam-1-TRIM --mode both --corpus_path "verified data/tokenized/tokenized_corpus_all_books.jsonl" --output_dir eval/results_both` | Full proposed pipeline: QLoRA fine-tuned model + GraphRAG shloka retrieval. |

---

## 3. Baselines & Reference Numbers

All scores are compared against published metrics from the AyurParam paper (arXiv:2511.02374v1, Section 4 & Table 1):

| Model | Parameters | Overall BBA Acc. | English Acc. | Hindi Acc. | Source |
|---|---|---|---|---|---|
| **AyurParam-2.9B-Instruct** | 2.9B | **39.97%** | **41.12%** | **38.04%** | arXiv:2511.02374 |
| **Llama-3.2-3B-Instruct** | 3.2B | 33.20% | ~34.1% | ~31.8% | arXiv:2511.02374 |
| **Qwen2.5-3B-Instruct** | 3.1B | 32.68% | ~33.5% | ~31.2% | arXiv:2511.02374 |
| **AyurLLM (sarvam-1 base)** | 2.0B | *[To be computed]* | *[To be computed]* | *[To be computed]* | `eval/results_base/bba_report_base.json` |
| **AyurLLM (+QLoRA)** | 2.0B | *[To be computed]* | *[To be computed]* | *[To be computed]* | `eval/results_qlora/bba_report_qlora.json` |
| **AyurLLM (+GraphRAG)** | 2.0B | *[To be computed]* | *[To be computed]* | *[To be computed]* | `eval/results_graphrag/bba_report_graphrag.json` |
| **AyurLLM (+Both)** | 2.0B | *[To be computed]* | *[To be computed]* | *[To be computed]* | `eval/results_both/bba_report_both.json` |

---

## 4. Evaluation on Kaggle T4 Accelerator

To run the complete benchmark in a single command on Kaggle or a cloud T4:
```bash
python eval/run_bhashabench_ayur.py \
    --model "sarvamai/sarvam-1" \
    --adapter "nishm27/sarvam-1-TRIM" \
    --mode "both" \
    --corpus_path "verified data/tokenized/tokenized_corpus_all_books.jsonl" \
    --output_dir "/kaggle/working/eval_results" \
    --batch_size 8
```

The script outputs:
1. `bba_report_{mode}.json`: Overall accuracy, English vs. Hindi accuracy, per-difficulty accuracy (Easy, Medium, Hard), and per-category breakdown across 15+ Ayurvedic specialties (Kayachikitsa, Dravyaguna, Shalya Tantra, etc.).
2. Console summary with exact delta vs. AyurParam's published 39.97% benchmark.

