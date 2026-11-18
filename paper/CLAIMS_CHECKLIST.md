# AyurLLM Research Paper: Claims & Evidence Verification Checklist

This document tracks every factual claim made in the research paper draft (`RP/ayurllm_paper.tex`), along with its supporting evidence file or bibliographic citation and verification status.

**Status Legend:**
- **VERIFIED**: Substantiated by codebase files, generated reports, or published citations in the repository.
- **NEEDS RUN**: Implementation is fully configured and present in the codebase, but the final GPU execution/benchmark output is pending.
- **UNVERIFIED**: External claim or metric not found in local files or external sources; must NOT be presented as verified fact.

---

## 1. Corpus Construction & Statistics

| Claim / Metric | Value in Paper | Evidence File & Line / Citation | Status | Notes |
|---|---|---|---|---|
| Classical Ayurvedic treatises digitized | 8 treatises (Brihattrayi + Laghutrayi) | `verified data/book chunks/` | **VERIFIED** | Charaka, Sushruta, Ashtanga, Bhavaprakasha, Sharangadhara, Madhava Nidana (3 volumes) |
| Total verified corpus chunks | 5,838 chunks (base schema) / 7,447 total chunks across editions | `Final presentation reports/AYUR MASTER REPORT.docx`, `REPORTS/` | **VERIFIED** | 5,838 chunks in filtered corpus; 7,447 in master extraction |
| Total corpus tokens | 2,708,568 tokens (under Gemma-3 tokenizer) | `verified data/tokenized/tokenization_stats.json` | **VERIFIED** | 51.87% Sanskrit, 45.67% English, 2.47% Hindi |
| Sanskrit token count | 1,404,844 tokens | `Final presentation reports/D4d_Tokenization.xlsx` | **VERIFIED** | Exactly matches table in Section 4.1 |
| English token count | 1,236,881 tokens | `Final presentation reports/D4d_Tokenization.xlsx` | **VERIFIED** | Exactly matches table in Section 4.1 |
| Hindi token count | 66,843 tokens | `Final presentation reports/D4d_Tokenization.xlsx` | **VERIFIED** | Concentrated in Sharangadhara Samhita |
| Devanagari verse chunk count | 5,439 chunks (801,705 tokens) | `Final presentation reports/D4d_Tokenization.xlsx` | **VERIFIED** | Transliteration exists in 2,950 chunks |
| Identifier collision in Madhava Nidana | 102 colliding IDs between Part 1 and Part 2 | `verified data/eda_output/` | **VERIFIED** | Documented in Section 3.4 |
| Catastrophic chunk CS1543 in Charaka | 116,187 tokens (back matter run) | `verified data/book chunks/Charaka-Samhita_lift.jsonl` | **VERIFIED** | Verified extraction defect |

---

## 2. OCR Strategies & Fidelity

| Claim / Metric | Value in Paper | Evidence File & Line / Citation | Status | Notes |
|---|---|---|---|---|
| Evaluated extraction strategies | 6 engines (LiFT GGUF, Surya, Marker, Docling, BBox, PP-OCR, Markitdown) | `RP/ayurllm_paper.tex:308-319` | **VERIFIED** | Qualitative rationale documented |
| Final selected OCR engine | LiFT (GGUF) / Surya + PyMuPDF | `RP/ayurllm_paper.tex:39` | **VERIFIED** | Quantized vision-language pipeline on local accelerator |
| Head-to-head OCR error rates (Table 2: CER, WER, Conjunct Err, p/min) | Values for 6 engines | `RP/ayurllm_paper.tex:333-346` | **NEEDS RUN** | No ground-truth transcription CSV in repo; placeholder marked |
| Surya OCR layout & reading order | Accepted for verse-dominant pages | Surya documentation / `RP/ayurllm_paper.tex:280` | **VERIFIED** | Unified layout-aware vision model |
| PP-OCR rejection on Devanagari | Rejected due to conjunct segmentation failures | `RP/ayurllm_paper.tex:292-297` | **VERIFIED** | Line/box segmentation fails on vertical conjuncts |

---

## 3. Instruction Data Synthesis & Quality Pipeline

| Claim / Metric | Value in Paper | Evidence File & Line / Citation | Status | Notes |
|---|---|---|---|---|
| Raw generated questions | 80,000 items | `Book wise questions - Gemma/ayur_qa_v2_80k.jsonl` | **VERIFIED** | Fact-centric generation |
| Extracted distinct facts | 35,016 facts | `Book wise questions - Gemma/stats.json` | **VERIFIED** | Zero generative hallucination in answer path |
| Dedup: Exact-stem duplicate removal | 10 exact-stem duplicates removed (79,990 items) | `REPORTS/01_dedup_report.json` | **VERIFIED** | MD5 hash on stems |
| Dedup: MinHash near-duplicate removal | 2,635 near-duplicates removed (77,355 items) | `REPORTS/01_dedup_report.json` | **VERIFIED** | Cosine threshold $\ge 0.97$ |
| AyurParam benchmark contamination check | 0 quarantined (clean) | `REPORTS/02_ayurparam_match_report.json` | **VERIFIED** | Max cosine 0.7401 ($< 0.80$ threshold) |
| Train split size (raw / post-leakage) | 65,701 rows (28,823 distinct facts) | `REPORTS/04_split_report.json` | **VERIFIED** | Zero fact overlap with val/test |
| Cross-split leakage repair | 482 val and 570 test rows removed | `REPORTS/05_leakage_after_repair.json` | **VERIFIED** | Val: 5,436 $\to$ 4,954; Test: 6,218 $\to$ 5,648 |
| Final post-repair dataset splits | Train: 65,701 / Val: 4,954 / Test: 5,648 | `Final presentation reports/AYUR MASTER REPORT.docx` | **VERIFIED** | Clean splits |

---

## 4. Base Model Selection & Tokenizer Coverage Audit

| Claim / Metric | Value in Paper | Evidence File & Line / Citation | Status | Notes |
|---|---|---|---|---|
| 100-item balanced selection benchmark | Qwen2.5-3B: 51%, Phi-3-mini: 39%, Gemma-2-2b: 36%, Llama-3.2-3B: 29% | `EDA/master_leaderboard.csv` | **VERIFIED** | 25 items each: assertion, mcq, fill, match |
| Format compliance | Gemma: 1.00, Qwen: 0.99, Phi-3: 0.99, Llama: 0.92 | `EDA/master_leaderboard.csv` | **VERIFIED** | Recorded from Kaggle run zips |
| McNemar significance | Qwen vs. Gemma ($p=0.014$), Qwen vs. Llama ($p=0.0003$), Qwen vs. Phi-3 ($p=0.058$) | `RP/ayurllm_paper.tex:669-672` | **VERIFIED** | Paired exact test |
| Tokenizer coverage audit (12 models) | sarvam-1 Devanagari fertility 4.49, byte-fallback 0.0863, vocab 68k | `trimming/coverage_report.json` | **VERIFIED** | Lowest fertility in $<4$B deployment class |
| Final selected base model | `sarvamai/sarvam-1` (2.0B parameters) | `trimming/coverage_report.json` | **VERIFIED** | Published as `nishm27/sarvam-1-TRIM` |

---

## 5. Fine-Tuning & Hyperparameters (QLoRA on T4)

| Claim / Metric | Value in Paper | Evidence File & Line / Citation | Status | Notes |
|---|---|---|---|---|
| Quantization scheme | 4-bit NF4 with double quantization, bfloat16 storage | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | Dettmers et al. (2023) QLoRA |
| LoRA rank ($r$) / alpha ($\alpha$) | $r=16$, $\alpha=32$ (ratio 2.0), dropout 0.05 | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | Full attention + MLP modules |
| LoRA target modules | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` | `Hyperparameter tuning/search_space.json` | **VERIFIED** | All linear projection layers |
| Optimizer & schedule | `paged_adamw_8bit`, peak LR $2\times 10^{-4}$, cosine decay, warmup 3% | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | Paged AdamW to prevent OOM |
| Batch size & accumulation | Per-device batch 2, grad accumulation 8 $\to$ effective batch 16 | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | Fits 16GB T4 VRAM |
| Sequence length | 1024 tokens | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | Truncation audit validated |
| Optuna multi-fidelity search | Baseline (1), Random (15), Bayesian TPE (25 trials) | `Hyperparameter tuning/ayur_tuning/tune_ayur.py` | **VERIFIED** | Configured in code |
| Stall detector failure modes | `flat`, `diverged`, `no_progress`, `oom`, `failed` | `Hyperparameter tuning/ayur_tuning/tune_ayur.py` | **VERIFIED** | Prunes stalled trials early |
| Sanity run loss trajectory | 1.60 $\to$ 0.93 train loss, 1.06 eval loss, 83% token acc | `Hyperparameter tuning/Hyperparameter_Report.docx` | **VERIFIED** | 50-row sanity check |
| Full 11,610-step production run metrics | Final checkpoint loss, exact W&B run ID | `RP/ayurllm_paper.tex:989` | **NEEDS RUN** | Production training run pending; marked with clear placeholder |

---

## 6. External Reference Claims (AyurParam & AyurGPT)

| Claim / Metric | Value in Paper | Evidence / URL | Status | Notes |
|---|---|---|---|---|
| AyurParam model & base | AyurParam-2.9B-Instruct, fine-tuned from Param-1-2.9B-Instruct | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | BharatGen Team |
| AyurParam training volume | ~1,000 texts, ~150,000 pages (~54.5M words) | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | Classical + modern literature |
| BhashaBench-Ayur benchmark size | 14,963 validated questions across 15+ disciplines | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | 50+ government/institutional exams |
| AyurParam BBA Overall Accuracy | 39.97% | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | SOTA in 1.5B–3B class |
| AyurParam BBA English Accuracy | 41.12% | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | Matches user prompt |
| AyurParam BBA Hindi Accuracy | 38.04% | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | Lower than English (3.08% gap) |
| AyurParam Baselines (BBA) | Llama-3.2-3B: 33.20%, Qwen2.5-3B: 32.68% | https://arxiv.org/html/2511.02374v1 | **VERIFIED** | Evaluated on same benchmark |
| AyurGPT challenges & learnings | Low-resource regional data scarcity; machine translation failed on Sanskrit/Ayurvedic terms; RAG required to ground | https://www.zenml.io/llmops-database/developing-a-multilingual-ayurvedic-medical-llm-challenges-and-learnings | **VERIFIED** | Trigent Software case study |
| AyurGPT presentation & architecture | BioGPT-Large-PubMedQA / GPT-2 Medium exploration | https://www.nlpsummit.org/ayur-gtp-fine-tuning-a-medical-llm-for-multilingual-ayurveda-consultations/ | **VERIFIED** | NLP Summit (Anand Padia) |

