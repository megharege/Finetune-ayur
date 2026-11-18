#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates the publication-ready conference LaTeX paper RP/ayurllm_paper.tex.
Matches the exact conference draft text, author block, 10 tables, mathematical
formulations, and 26 bibliographic entries.
"""

import os
import shutil

tex_code = r"""% =====================================================================
%  AyurLLM — Conference Submission Paper
% =====================================================================
\documentclass[10pt,twocolumn,letterpaper]{article}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{times}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{xcolor}
\usepackage{microtype}
\usepackage{caption}
\usepackage[colorlinks=true,linkcolor=blue!70!black,citecolor=blue!70!black,urlcolor=blue!70!black]{hyperref}

% ---------------- GEOMETRY: Standard 2-column conference block ----------------
\usepackage[letterpaper,
            top=1in, bottom=1.125in,
            left=0.84375in, right=0.84375in]{geometry}
\setlength{\columnsep}{0.3125in}
% ------------------------------------------------------------------------------

\captionsetup{font=small,labelfont=bf,skip=4pt}
\setlength{\parskip}{0pt}
\setlength{\abovedisplayskip}{4pt}
\setlength{\belowdisplayskip}{4pt}

\title{\vspace{-1.2em}\textbf{\fontsize{13.5}{15.5}\selectfont
AyurLLM: A Verified Shloka-Level Corpus, a Fact-Grounded Instruction Benchmark,
and a Tokenizer-Aware Adaptation Pipeline for Eight Classical Ayurvedic Treatises}\vspace{-0.3em}}

\author{
  \textbf{Megha Rege} (2305792) \quad \textbf{Hitanshu Choraria} (23052395) \\
  \textbf{Agnipravo Ali} (23051323) \quad \textbf{Anand Jadon} (2305005) \\[4pt]
  \small School of Computer Engineering, Kalinga Institute of Industrial Technology (KIIT), Bhubaneswar, Odisha, India
}
\date{}

\begin{document}
\maketitle

% =====================================================================
\begin{abstract}
Classical Ayurvedic knowledge is stored in printed treatises where Devanagari verse,
IAST transliteration and commentary in English or Hindi share a page. The material
cannot be searched by symptom and cannot be used directly as supervised training data.
We present AyurLLM, a pipeline that converts eight treatises into a verified,
schema-normalised corpus of 5{,}838 chunks (2{,}708{,}568 Gemma-3 tokens; 51.87\%
Sanskrit) and into a fact-grounded instruction set of 80{,}000 items drawn from
35{,}016 facts in six formats. Every answer is a verbatim span of its source chunk
and carries a \texttt{(source\_book, chunk\_id)} provenance key. After exact and
near-duplicate removal and a leakage repair, the splits hold 65{,}701 / 4{,}954 / 5{,}648
items (train / validation / test) with zero fact overlap, and no item matches any
of the 14{,}963 BhashaBench-Ayur (BBA) questions at cosine 0.80 (maximum observed 0.74).
We attribute each coverage gap to a named extraction defect and show that token
fertility doubles as an OCR-quality diagnostic. A tokenizer audit of 12 candidates
leads us to sarvam-1, trimmed from a 68{,}096 to a 23{,}946-token vocabulary. A
paired study of four zero-shot baselines on 100 held-out items shows that the
strongest (Qwen2.5-3B-Instruct, 51\%) is indistinguishable from chance on
assertion--reasoning and answers at most 21\% of ``locate the source of this topic''
items correctly, the failure that source-grounded retrieval is meant to address.
QLoRA fine-tuning and the comparison with AyurParam (39.97\% on BBA) are specified
with a pre-registered decision rule but have not yet been executed; we mark every
such result as pending and make no claim about it.
\end{abstract}

% =====================================================================
\section{Introduction}

Ayurveda is a codified medical tradition whose primary sources are a small,
stable set of Sanskrit treatises. A physician reasons outward from a presenting
symptom, a drug or a disease name, whereas the literature is organised by verse
number within chapter within section (\emph{sthana}). A clinician who wants to
know what the tradition says about a symptom must already know which verse to open,
which is the knowledge the lookup was meant to supply.

Making these texts searchable is mostly a data-integrity problem rather than a
modelling one. Devanagari is an abugida in which stacked conjunct consonants
(\emph{samyuktakshara}), dependent vowel signs (\emph{matra}) placed above, below
or beside the base glyph, and a connecting headline (\emph{shirorekha}) defeat
recognisers that crop horizontal text lines~\cite{devaocr,devavlm}. A printed page
may carry verse, its romanisation and a commentary in a third language, and editions
disagree on all of it. The unit of retrieval is equally consequential: a verse
without its gloss is often uninterpretable, and a gloss without its verse cannot
be cited. We therefore treat the verse together with its gloss and position as the
atomic record.

A second problem appears once a corpus exists. Instruction tuning needs
question--answer pairs that primary sources do not contain, and the usual remedy
is to have a large model write them. AyurParam~\cite{ayurparam}, the closest prior
system, followed that route with Qwen-3 235B to produce about 4.75M examples, then
applied overlap filters, LLM adjudication and expert audits. In a medical domain a
fabricated detail in a teacher's output becomes confident ground truth for the
student. We take a more conservative route: every answer in our benchmark is lifted
verbatim from a chunk, so that any item can be audited against the printed page.

Our contributions are as follows:
\begin{itemize}\itemsep1.5pt
\item \textbf{A verified shloka-level corpus} under one chunk schema: 5{,}838
chunks and 2{,}708{,}568 tokens from eight volumes, with a composite key that
resolves a 102-identifier cross-volume collision (Sec.~\ref{sec:corpus}).
\item \textbf{A per-volume failure taxonomy} that ties each coverage gap to a named
defect, and token fertility as a label-free diagnostic for recognition quality
(Sec.~\ref{sec:char}--\ref{sec:failure}).
\item \textbf{A fact-grounded instruction benchmark} of 80{,}000 items from 35{,}016
facts, with deduplication, a contamination audit against all 14{,}963 BBA
questions, and fact-level splits (Sec.~\ref{sec:benchmark}).
\item \textbf{A paired baseline study} with statistics showing which formats
current 2--4B models cannot solve and where they guess by option position
(Sec.~\ref{sec:baselines}), plus a tokenizer audit and trimming step behind the
choice of sarvam-1 (Sec.~\ref{sec:tokenizer}).
\item \textbf{A pre-specified protocol} for QLoRA adaptation, grounded retrieval
and comparison with AyurParam on BBA, with a decision rule fixed before any run
(Sec.~\ref{sec:finetune}--\ref{sec:ayurparam}).
\end{itemize}

% =====================================================================
\section{Related Work}
\label{sec:related}

\subsection{Document conversion and Devanagari OCR}

Cascaded systems such as PP-OCR~\cite{ppocr} and PP-OCRv2~\cite{ppocrv2} detect
text lines, then recognise them, and are tuned for small deployment footprints.
Their segmentation assumes glyphs that do not stack vertically.
Docling~\cite{docling,doclingtr} parses documents with layout and table-structure
models on commodity hardware. Surya~\cite{surya} combines layout analysis,
reading order and recognition for 90+ languages, and Marker~\cite{marker} builds
whole-document conversion on top of it. Vision--language models are also run in
quantised form for small accelerators~\cite{lfm2vl}. Surveys and stress tests
agree that conjuncts, dependent vowel signs and the headline remain the dominant
failure points for Devanagari~\cite{devaocr,devavlm,sanskritdl}. Our findings in
Sec.~\ref{sec:failure} are consistent: the worst volume fails exactly by dropping
conjuncts and detaching matras.

\subsection{Language models for Ayurveda}

\paragraph{AyurParam.}
AyurParam-2.9B~\cite{ayurparam} fine-tunes Param-1-2.9B~\cite{param1} on about
4.75M examples synthesised from roughly 150{,}000 pages (about 54.5M words) of
digitised books, using Qwen-3 235B under evidence-anchoring constraints, with
expert review of ten books. Training ran for 3 epochs at a global batch of 1{,}024
on an H100 cluster, roughly two days on a single H100 node. On
BBA~\cite{bhashabench,bhashabenchdata}, which has 14{,}963 exam-style questions
(9{,}348 English, 5{,}615 Hindi), it reaches 39.97\% overall, 41.12\% English and
38.04\% Hindi, ahead of Llama-3.2-3B-Instruct (33.20\%) and Qwen2.5-3B-Instruct
(32.68\%). Its authors list the limits we build on: a Hindi gap, evaluation
restricted to exam-style questions, no explicit safety mechanism, no
patient-specific reasoning, and training text digitised mostly before 2024.

\paragraph{AyurGPT / IRGPT.}
Trigent's talk at NLP Summit 2024~\cite{ayurnlp} describes AyurGPT as a fine-tune
of BioGPT-Large-PubMedQA that supports English, Kannada, Tamil and Malayalam. A
companion write-up~\cite{ayurgpt} reports a GPT-2 Medium (347M) fine-tune after
the team narrowed the scope to English, because multilingual data validation
proved impractical: about one million rows shrank to roughly 113{,}000 validated
samples, translations lost the meaning of Ayurvedic terms, and Ayurveda books
($\sim$2\,GB) were reserved for a retrieval component. Two lessons transfer
directly to our design: data quality dominates volume, and scope should be staged.

\subsection{Synthetic instruction data}

Attributed grounding~\cite{attrground} anchors generated instructions to retrieved
passages to limit fabrication, answer-consistency filtering~\cite{cotself} keeps
generations on which independent reasoning paths agree, and seed-free
generation~\cite{seedfree} handles languages with no instruction seed set. All three
still let a model write the answer. We do not: the generative step is replaced by
rendering each extracted fact into an examination format, and the answer is always
a span of the source. The price is reduced linguistic variety (Sec.~\ref{sec:limitations}).

% =====================================================================
\section{Corpus Construction}
\label{sec:corpus}

\subsection{Source material}

Eight printed volumes were selected in consultation with practising physicians:
the Brihattrayi (Charaka Samhita, Sushruta Samhita, Ashtanga Hridaya), the
Laghutrayi (Sharangadhara Samhita, Madhava Nidana, Bhavaprakasha Nighantu), and a
two-volume Madhava Nidanam carrying the Madhukosa commentary. The volumes differ in
script mix, in whether transliteration is printed, in the language of the
commentary, in scan quality, and in whether verse and commentary occupy separate
columns. No single extraction setting works for all eight.

\subsection{Extraction-engine selection}

Extraction was treated as a per-volume engineering problem with six strategies.
The deciding criterion was fidelity on Devanagari verse (intact conjuncts,
correctly attached vowel signs), not page-level character accuracy: a page can
score well on characters while every verse on it is unusable, because commentary
is long and verse is short. Table~\ref{tab:ocr-decision} gives the role or rejection
reason of each strategy.

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}llc@{}}
\toprule
\textbf{Engine} & \textbf{Role / failure mode} & \textbf{Decision} \\
\midrule
LiFT (GGUF)   & Final extractor, all volumes; quantised to $\sim$6\,GB & Accepted \\
Surya~\cite{surya}   & Verse-dominant pages; keeps reading order & Accepted \\
Marker~\cite{marker} & Stable heading hierarchy (chapter/section) & Accepted \\
Docling~\cite{docling} & Verse and commentary in separate regions & Accepted \\
Bounding box  & Fallback where converters merged columns & Accepted \\
PP-OCR~\cite{ppocr}  & Line-crop cascade severs stacked conjuncts & Rejected \\
Markitdown    & Format converter; needs text layer, absent in scans & Rejected \\
\bottomrule
\end{tabular}
\caption{Extraction strategies and the decision for each.}
\label{tab:ocr-decision}
\end{table}

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lcccc@{}}
\toprule
\textbf{Engine} & \textbf{CER} & \textbf{WER} & \textbf{Conj.\ err.} & \textbf{pages/min} \\
\midrule
LiFT (GGUF)   & [pending] & [pending] & [pending] & [pending] \\
Surya         & [pending] & [pending] & [pending] & [pending] \\
Marker, Docling, bbox & [pending] & [pending] & [pending] & [pending] \\
PP-OCR, Markitdown    & [pending] & [pending] & [pending] & [pending] \\
\bottomrule
\end{tabular}
\caption{Measured extraction quality on a manually transcribed page sample (CER, WER,
conjunct error rate, throughput). Not yet measured; until filled,
Table~\ref{tab:ocr-decision} rests on qualitative failure modes.}
\label{tab:ocr-pending}
\end{table}

Extraction was made resumable: process isolation and per-page checkpointing meant
a crash partway through a volume did not discard completed pages, which under a
6\,GB budget is routine rather than exceptional.

\subsection{The chunk schema}

Every book-specific converter targets one record type, so that irregularity of
the printed page is absorbed at extraction time. The base fields are
\texttt{chunk\_id}; \texttt{sthana}, \texttt{chapter\_number},
\texttt{chapter\_title}; \texttt{verse\_id} as printed; \texttt{topic\_heading};
\texttt{sanskrit\_text}; \texttt{transliteration} (IAST, where printed);
\texttt{commentary} (verbatim); and \texttt{categories\_found} with
\texttt{primary\_category}. Three volumes needed named extensions instead of being
flattened: Sharangadhara Samhita adds \texttt{commentary\_english}, because its
printed gloss is Hindi; Madhava Nidana (Laghutrayi) adds
\texttt{sanskrit\_commentary}, \texttt{source\_citation} and \texttt{record\_type},
because the Madhukosa apparatus quotes other treatises by name; Charaka Samhita adds
\texttt{pada} for the quarter-divisions of the Chikitsasthana. Keeping these fields
explicit is what makes the failure analysis of Sec.~\ref{sec:failure} possible.

\subsection{Identifier integrity}

\texttt{chunk\_id} is unique within a volume but not across the corpus. Madhava
Nidanam Parts 1 and 2 were converted independently and both number records
\texttt{MN1}, \texttt{MN2}, \dots; 102 identifiers collide. A join on
\texttt{chunk\_id} alone silently double-counts. All analyses and indexes therefore
use the composite key \texttt{(source\_book, chunk\_id)}. The collision is
invisible to per-file validation, since each file is internally consistent, and
appears only when the corpus is treated as a whole.

% =====================================================================
\section{Corpus Characterisation}
\label{sec:char}

\subsection{Tokenisation}

Statistics use the \texttt{google/gemma-3-4b-it} tokenizer, chosen because it
belongs to the deployment size class; token counts under a different tokenizer
would misstate every context and cost estimate. The corpus holds 2{,}708{,}568
tokens: 1{,}404{,}844 Sanskrit (51.87\%), 1{,}236{,}881 English (45.67\%) and
66{,}843 Hindi (2.47\%). Devanagari verse is present in 5{,}439 chunks (801{,}705
tokens) and IAST transliteration in 2{,}950 chunks (572{,}022 tokens), so only
about half of the corpus carries printed romanisation. The mean chunk length is
463.9 tokens ($2{,}708{,}568 / 5{,}838$).

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lrrr@{}}
\toprule
\textbf{Volume} & \textbf{Chunks} & \textbf{Skt tokens} & \textbf{Fertility} \\
\midrule
Charaka Samhita          & 1{,}497 & 379{,}568 & 3.41 \\
Bhavaprakasha Nighantu   & 1{,}052 & 81{,}372  & 3.69 \\
Ashtanga Hridaya         & 913     & 38{,}899  & 1.85 \\
Madhava Nidanam P1       & 728     & 223{,}062 & 4.24 \\
Sharangadhara Samhita    & 593     & 61{,}766  & 4.43 \\
Sushruta Samhita         & 418     & 58{,}848  & 4.70 \\
Madhava Nidana (Laghu.)  & 403     & 259{,}833 & 4.09 \\
Madhava Nidanam P2       & 234     & 301{,}496 & 4.65 \\
\midrule
\textbf{Total / overall} & \textbf{5{,}838} & \textbf{1{,}404{,}844} & \textbf{3.61} \\
\bottomrule
\end{tabular}
\caption{Per-volume chunks, Sanskrit tokens and Sanskrit token fertility (Gemma-3
tokenizer). The low Ashtanga value is a recognition artefact.}
\label{tab:corpus}
\end{table}

\subsection{Token fertility as a quality diagnostic}

Fertility is tokens emitted per whitespace-delimited word, $F = N_{\text{tok}} /
N_{\text{words}}$. It is 3.61 for Sanskrit and 1.69 for English, a ratio of 2.14:
a Sanskrit word costs more than twice as much context as an English one. Across
volumes it ranges from 1.85 (Ashtanga Hridaya) to 4.70 (Sushruta Samhita). The
low Ashtanga value does not indicate simpler Sanskrit. Lost conjuncts and
detached vowel signs fragment words into short, tokenizer-friendly pieces, so
degraded recognition lowers fertility. An anomalously low value is therefore a
label-free signal to inspect a volume, available without any transcription.

\subsection{Chunk length and script balance}

Chunk length is heavily skewed: 21.62\% of chunks (1{,}262) exceed 512 tokens,
8.56\% (500) exceed 1{,}024, 2.93\% (171) exceed 2{,}048, 0.87\% (51) exceed 4{,}096
and 0.15\% (9) exceed 8{,}192. Part 2 of Madhava Nidanam averages 1{,}288 Sanskrit
tokens per chunk against 43 for Ashtanga Hridaya, a thirtyfold gap caused by
editorial convention (one chunk per commentary block versus one per verse).
Chunks above an embedding model's window must be sub-chunked before indexing or
their tails are truncated; we treat the 512-token threshold as binding since it
affects about one chunk in five. The English-to-Sanskrit token ratio per chunk
separates the corpus into prose-heavy and verse-heavy classes: 3.85 in Bhavaprakasha
Nighantu (a materia medica where verse is an index) against 0.48 in Sushruta
Samhita and 0.46 in Madhava Nidanam Part 2. Any sampling that treats chunks as
interchangeable will over-represent pharmacological prose.

% =====================================================================
\section{Per-Volume Failure Analysis}
\label{sec:failure}

Aggregate quality hides the fact that every volume fails differently. In each
case below the defect is an extraction or editorial artefact rather than missing
source content, which we confirmed against the printed page.

\paragraph{Sharangadhara Samhita: Hindi-only commentary.}
350 of 593 chunks (59.0\%) carry no English commentary. The printed gloss is
Hindi, which shares the Devanagari script with the verse, so script-based
language identification cannot separate them and a meaning-level pass is needed.
The whole Hindi mass of the corpus (560 chunks, 66{,}843 tokens) comes from this
volume. It contributes 202 of the 355 chunks that yield no question.

\paragraph{Ashtanga Hridaya: degraded Devanagari.}
The corpus minimum on Sanskrit fertility (1.85) and mean Sanskrit chunk length
(43.51 tokens). Affected chunks have lost conjuncts and have vowel signs detached
from their base glyphs. The text passes a non-empty check but cannot be read as
verse; this defect class is invisible to field-coverage metrics and motivated the
Devanagari well-formedness test of Sec.~\ref{sec:benchmark}. It accounts for 92
unused chunks.

\paragraph{Bhavaprakasha Nighantu: absent verse field.}
370 of 1{,}052 chunks have no Sanskrit text; they are drug monographs with prose
only, including the shortest chunks of the corpus (3--4 tokens). They are valid
content but cannot support verse-grounded tasks.

\paragraph{Charaka Samhita: one catastrophic chunk.}
Chunk \texttt{CS1543} holds 116{,}187 combined tokens, about nine times the next
largest and roughly 4\% of the corpus. It is the volume's back matter, rendered
as a long run of fragmentary glyphs and page numbers. It raises this volume's
English standard deviation to 2{,}558 tokens against a median of 110.

\paragraph{Madhava Nidanam P1/P2: identifier collision.}
The 102 shared identifiers of Sec.~\ref{sec:corpus}; Part 1 also has 130 of 728
chunks without English commentary.

\paragraph{Remaining volumes.}
Sushruta Samhita is complete on both fields for all 418 chunks (its terse
commentary, 66.35 English tokens per chunk, is an editorial property). Madhava
Nidana (Laghutrayi) lacks English commentary in 26 of 403 chunks.

% =====================================================================
\section{Retrieval, Graph and Safety: System Design}
\label{sec:system}

\noindent\textit{Status.} This section specifies the serving layer that
motivates the corpus design. At the time of writing, no retrieval, graph or
triage component appears in any reported experiment, and the embedding
configuration is not fixed; we state the design and the metrics that will
evaluate it.

\paragraph{Hybrid retrieval.}
A physician may query by an exact Sanskrit term or by a plain-language symptom,
so the index combines lexical and dense scores. With $\mathbf{e}_q, \mathbf{e}_d$
the embeddings of query $q$ and chunk $d$:
\begin{equation}
S(q, d) = \lambda \widetilde{S}_{\text{dense}}(q, d) + (1 - \lambda) \widetilde{S}_{\text{lex}}(q, d),
\end{equation}
where $S_{\text{dense}}(q, d) = \frac{\mathbf{e}_q^\top \mathbf{e}_d}{\|\mathbf{e}_q\| \|\mathbf{e}_d\|}$,
tildes denote per-query min--max normalisation and $\lambda \in [0, 1]$ is tuned on
the validation split rather than fixed in advance. Chunks above 512 tokens are
sub-chunked. Because every item has a gold \texttt{(source\_book, chunk\_id)},
retrieval can be scored without new annotation, with Recall@$k$ and MRR over the
validation questions.

\paragraph{Personal knowledge graph.}
A graph database holds patient, symptom, dosha, treatment and shloka nodes,
linked by typed edges such as \texttt{EXPERIENCES}, \texttt{AGGRAVATES},
\texttt{ALLEVIATES} and \texttt{GROUNDED\_IN}. A multi-hop query returns a
sub-graph whose terminal shloka nodes carry the composite key above, so every
generated statement can cite treatise, sthana, chapter and verse.

\paragraph{Safety triage.}
A deterministic rule layer runs before retrieval and generation. If an intake
matches a curated list of red-flag presentations (for example radiating chest
pain, severe breathlessness, sudden neurological deficit), the generative path
is bypassed and the session is escalated to emergency referral. The rule list
requires clinical review and a red-team set before any claim of coverage.

% =====================================================================
\section{Fact-Grounded Instruction Benchmark}
\label{sec:benchmark}

\subsection{Fact-centric generation}

Each chunk is first reduced to discrete facts, each with a stable identifier:
the subject a verse addresses, a commentary statement, a technical term, an
enumeration or count, a synonym set, or the location of a teaching. Each fact
is then rendered into every format it supports. One answer can thus be tested
as a multiple-choice item, a cloze, an assertion--reason pair or a
multiple-selection item without two stems being textually identical, and
semantic de-duplication reduces to grouping by fact identifier. From 5{,}838
chunks we extract 35{,}016 facts (mean 2.28 questions per fact) and render
80{,}000 questions covering 5{,}483 chunks (93.9\%). 61.8\% of facts appear in
more than one format (38.2\% in one, 36.4\% in two, 18.9\% in three, 6.4\% in
four). The finest label has 36 format variants.

\subsection{Quality controls}

Each control was added after a defect was observed in generated output:
\begin{itemize}\itemsep1.5pt
\item \textbf{Distractor isolation:} wrong options come from a different chapter
of the same volume, so a distractor cannot accidentally be true of the asked topic.
\item \textbf{Answer-leakage guards:} an item is rejected if its answer appears
in the stem outside the option block or in any context field. Verdict items carry
no context.
\item \textbf{OCR filtering:} sentences with running heads, spaced-out
punctuation or an anomalous share of out-of-lexicon tokens are rejected; verses
failing a Devanagari well-formedness test are excluded from cloze and
verse-comprehension items.
\item \textbf{Option-order randomisation:} an earlier build put true/false
verdicts at fixed positions, which would have let a model score on position alone
for 17\% of the set. The final key is distributed 24/30/20/26\% over A--D.
\end{itemize}

\subsection{Composition}

Table~\ref{tab:formats} gives the six formats before and after deduplication
and in each split. Difficulty is assigned from format and commentary length,
not measured: Medium 43.9\%, Hard 32.6\%, Easy 23.5\% over the 80{,}000 items.
Items are grounded in commentary alone for 81.2\% (64{,}989), in the verse alone
for 10.7\%, in verse plus commentary for 1.7\%, and in provenance (locating a
topic) for 6.4\%; the verse is involved in only 12.3\% of items, against 46.7\%
in an earlier build. Mapped to BBA subject domains, the largest shares are
Roga Vigyana (25.2\%), Dravyaguna and Bhaishajya (21.2\%) and Kayachikitsa
(15.0\%), while Swasthavritta (0.19\%) and Ayurvedic Literature (0.07\%) are
nearly absent, so no claim should be made on those domains. Bhavaprakasha
Nighantu contributes 34.4\% of items and Sushruta Samhita 3.0\%.

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
\textbf{Format} & \textbf{Raw} & \textbf{Dedup} & \textbf{Train} & \textbf{Val} & \textbf{Test} \\
\midrule
Fill in the blanks       & 20{,}699 & 20{,}319 & 17{,}252 & 1{,}433 & 1{,}634 \\
MCQ                      & 18{,}262 & 16{,}850 & 14{,}323 & 1{,}173 & 1{,}354 \\
Assorted / short answer  & 15{,}428 & 15{,}402 & 13{,}085 & 1{,}080 & 1{,}237 \\
Assertion--reason        & 11{,}430 & 11{,}413 &  9{,}701 &   806   &   906   \\
Multiple selection       &  9{,}089 &  8{,}300 &  7{,}050 &   581   &   669   \\
Match the column         &  5{,}092 &  5{,}071 &  4{,}290 &   363   &   418   \\
\midrule
\textbf{Total}           & \textbf{80{,}000} & \textbf{77{,}355} & \textbf{65{,}701} & \textbf{4{,}954} & \textbf{5{,}648} \\
\bottomrule
\end{tabular}
\caption{Items per format: raw, after deduplication, and in the final splits
(validation and test after leakage repair).}
\label{tab:formats}
\end{table}

\subsection{Deduplication, contamination and leakage}

Exact MD5 hashing of question stems removed 10 items (79{,}990 left).
Near-duplicate detection at a similarity threshold of 0.97 removed a further
2{,}635, leaving 77{,}355. A contamination audit compared the training pool with
all 14{,}963 BBA questions using hashed character 3--4-gram vectors; the maximum
cosine similarity was 0.74, below the 0.80 quarantine threshold, so no item was
quarantined. Splits are made on the fact identifier so no rendering of a training
fact can appear in validation or test (fact overlap 0 before and after repair). A
further near-duplicate pass at cosine 0.95 between training and held-out rows
removed 482 validation rows (5{,}436 $\to$ 4{,}954) and 570 test rows (6{,}218
$\to$ 5{,}648), leaving no held-out row within 0.95 of a training item. The
training split (65{,}701 rows) covers 28{,}823 distinct facts.

% =====================================================================
\section{Zero-Shot Baselines}
\label{sec:baselines}

\subsection{Protocol}

A 100-item evaluation set was drawn from the validation pool: 25 items each of
assertion--reason, MCQ, fill-in-the-blank and match-the-column, balanced over the
eight volumes (9--16 items per book) and disjoint from training. All four formats
have four options, so chance is 0.25. We also report format compliance (share of
items with a parseable answer), because a model that cannot follow the answer
format measures instruction following rather than domain knowledge. As all models
answer the same items we use paired exact McNemar tests~\cite{mcnemar} and
Wilson 95\% intervals~\cite{wilson}.

\subsection{Results}

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lcccc@{}}
\toprule
\textbf{Model} & \textbf{Acc.} & \textbf{95\% CI} & \textbf{$p$ vs.\ chance} & \textbf{Compl.} \\
\midrule
Qwen2.5-3B-Instruct     & \textbf{0.51} & [.41, .61] & $2 \times 10^{-8}$ & 0.99 \\
Phi-3-mini-4k-instruct  & 0.39 & [.30, .49] & 0.0014             & 0.99 \\
gemma-2-2b-it           & 0.36 & [.27, .46] & 0.0094             & 1.00 \\
Llama-3.2-3B-Instruct   & 0.29 & [.21, .39] & 0.21               & 0.92 \\
\bottomrule
\end{tabular}
\caption{Zero-shot accuracy on the 100-item set. $p$ is a one-sided exact binomial
test against chance 0.25. Llama-3.2-3B is not distinguishable from chance overall.}
\label{tab:baselines}
\end{table}

Qwen2.5-3B-Instruct is best (Table~\ref{tab:baselines}) and significantly better
than gemma-2-2b-it ($p=0.0135$; 24 vs.\ 9 discordant items) and Llama-3.2-3B
($p=0.0003$; 29 vs.\ 7). Its lead over Phi-3-mini is not established at $n=100$
($p=0.058$; 23 vs.\ 11), and the other three pairs are indistinguishable ($p \ge 0.12$).

\paragraph{Format effects.}
Fill-in-the-blank is easiest (Qwen 0.72) and MCQ is solved above chance by every
model ($p \le 0.03$). Assertion--reason stays at chance for all four (best 0.32,
$p=0.27$) and gemma-2-2b-it falls below it at 0.16. Match-the-column is at or
near chance for three models; Qwen and Phi-3 reach 0.40 ($p=0.07$). Format and
difficulty are confounded in this set: all 25 assertion--reason and all 25
match-the-column items are labelled Hard, whereas every fill-in-the-blank item is
Easy or Medium, so ``difficulty'' effects cannot be separated from format effects.
Qwen scores 0.69 / 0.65 / 0.36 on Easy / Medium / Hard ($n = 13 / 37 / 50$).

\paragraph{Position bias.}
Llama-3.2-3B selects option C on 50\% of items and gemma-2-2b-it selects D on
41\%, against a key of 24/30/20/26\%, so part of their scores is key placement
rather than knowledge. Llama also fails to give a parseable answer on 8\% of items.

\paragraph{Where models fail: locating a source.}
By subtype, the ``topic to reference'' items, which ask which passage or treatise
a topic belongs to, are answered correctly in only 2, 3, 2 and 1 of 14 cases by
Qwen, Phi-3, gemma and Llama respectively (14\%, 21\%, 14\%, 7\%). The ``A false,
R true'' assertion variant is 0 of 7 for Qwen and gemma. Subtype counts are small
and directional, but the topic-to-reference result is the clearest evidence in
this study that parametric memory cannot supply provenance, and it is the task
that retrieval over \texttt{(source\_book, chunk\_id)} addresses directly.
Overall, 29 of 100 items are solved by no model and the union of all four reaches
0.71, so the set has substantial headroom.

sarvam-1 was not evaluated here: it was selected on tokenizer evidence
(Sec.~\ref{sec:tokenizer}), and its score on this set is [pending].

% =====================================================================
\section{Tokenizer Audit and Vocabulary Trimming}
\label{sec:tokenizer}

\subsection{Coverage audit}

Zero-shot accuracy is not the criterion for the fine-tuning base. The base must
tokenize Sanskrit economically and fit one consumer accelerator, so we audited
twelve 1--5B candidates on the verified corpus (eleven scored; one gated
repository was inaccessible). We report overall fertility, Devanagari-specific
fertility, and the byte-fallback fraction (share of tokens decoded through byte
fallback, which signals characters missing from the vocabulary). Lower is better
for all three.

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
\textbf{Model} & \textbf{Params} & \textbf{Vocab} & \textbf{Fert.} & \textbf{Dev.} & \textbf{BFB} \\
\midrule
gemma-4-E2B-it$^\dagger$    & 5.1B  & 262{,}144 & 2.49 & 4.10 & 0.000 \\
gemma-2-2b-it               & 2.6B  & 256{,}000 & 2.64 & 4.79 & 0.000 \\
sarvam-1                    & 2.0B$^\ddagger$ &  68{,}096 & 3.01 & 4.49 & 0.086 \\
Qwen3 / Qwen2.5 (4 models)  & 1.5--4B & 151{,}643 & 3.63 & 8.00 & 0.297 \\
Falcon3-1B                  & 1.7B  & 131{,}072 & 3.96 & 9.11 & 0.182 \\
SmolLM2-1.7B                & 1.7B  &  49{,}152 & 4.03 & 9.84 & 0.262 \\
glm-edge-4b                 & 4.0B  &  59{,}246 & 4.22 & 10.24 & 0.463 \\
granite-3.3-2b              & 2.5B  &  49{,}152 & 4.32 & 10.36 & 0.307 \\
LFM2.5-1.2B                 & 1.2B  &  64{,}400 & 4.29 & 11.13 & 0.534 \\
\bottomrule
\end{tabular}
\caption{Tokenizer audit (Fert.\ = overall fertility, Dev.\ = Devanagari
fertility, BFB = byte-fallback fraction). $^\dagger$Exceeds 4B budget.
$^\ddagger$Nominal; trimmed checkpoint counts 2.344B parameters.}
\label{tab:trimming}
\end{table}

Within the 4B budget, sarvam-1 has the lowest Devanagari fertility (4.49 against
4.79 for gemma-2-2b-it, a 6.3\% reduction, and against 8.00 for the Qwen family,
a 44\% reduction). It does not have the lowest byte-fallback fraction or overall
fertility: gemma-2-2b-it is better on both (0.000 against 0.086, and 2.64 against
3.01). The case for sarvam-1 over gemma-2-2b-it therefore rests on Devanagari
fertility and on its Indic-focused pretraining, not on a uniform tokenizer
advantage, and only a downstream fine-tune of both models can settle the choice.

\subsection{Trimming}

Large vocabularies carry embedding rows that a corpus never uses. We trimmed each
candidate's vocabulary to the tokens the corpus needs (Table~\ref{tab:trimmed});
sarvam-1 shrinks from 68{,}096 to 23{,}946 tokens (64.8\% fewer) and is published
as \texttt{nishm27/sarvam-1-TRIM}.

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lcccc@{}}
\toprule
\textbf{Trimmed model} & \textbf{Params} & \textbf{Vocab} & \textbf{PPL} & \textbf{Tok./chunk} \\
\midrule
sarvam-1-TRIM        & 2.344B &  23{,}946 & 25.11 & 304.9 \\
gemma-2-2b-it-TRIM   & 2.483B & 198{,}912 & 56.42 & 287.4 \\
\bottomrule
\end{tabular}
\caption{Trimmed checkpoints. Perplexity is per token under each model's own
vocabulary and is not comparable across rows.}
\label{tab:trimmed}
\end{table}

Perplexity is defined per token, so a model with a smaller vocabulary and longer
token sequences is not directly comparable with one that has a larger vocabulary.
The perplexity gap in Table~\ref{tab:trimmed} (25.11 against 56.42) should therefore
not be read as sarvam-1 modelling the corpus twice as well; a tokenizer-independent
measure such as bits per character on held-out text is needed, and is [pending].
Gemma-2 produces fewer tokens per chunk (287.4 against 304.9), and sarvam-1 is a
base model without a chat template, so training uses a plain \texttt{User:/Answer:}
framing and its loss is not comparable with an instruct model's.

% =====================================================================
\section{Fine-Tuning Protocol}
\label{sec:finetune}

\noindent\textit{Status:} the pipeline is configured; no trial has completed,
and no fine-tuned result is reported in this paper.

\subsection{Adaptation method}

We adapt sarvam-1-TRIM with QLoRA~\cite{qlora}, a quantised variant of
LoRA~\cite{lora}: base weights are frozen in 4-bit NormalFloat (NF4) with double
quantisation, and trainable low-rank matrices $B \in \mathbb{R}^{d \times r},
A \in \mathbb{R}^{r \times k}$ ($r \ll \min(d, k)$) are attached to the query,
key, value, output, gate, up and down projections:
\begin{equation}
W' = \text{dequant}(W_{\text{NF4}}) + \frac{\alpha}{r} B A,
\end{equation}
with $B$ initialised to zero. Training minimises completion-only cross-entropy,
masking the prompt $x$ so that only the verbatim answer $y$ contributes:
\begin{equation}
\mathcal{L}(\theta) = - \sum_{t=1}^{L_c} \log P_\theta(y_t \mid x, y_{<t}).
\end{equation}
Execution is on a single Kaggle T4 GPU with Weights \& Biases tracking, the setting
that makes the pipeline reproducible without cluster access.

\subsection{Hyperparameter search}

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lp{5.5cm}@{}}
\toprule
\textbf{Group} & \textbf{Search space} \\
\midrule
Optimisation & LR log-uniform $5\times 10^{-5}$--$5\times 10^{-4}$; scheduler cosine/linear/const+warmup; warmup ratio 0.01--0.10; weight decay 0--0.10; optimiser \texttt{paged\_adamw\_8bit} or \texttt{adamw\_torch}; Adam $\beta_2 \in \{0.999, 0.95\}$; clip 0.5--1.0 \\
\addlinespace[2pt]
Batch & per-device $\{2, 4, 8\}$; grad.\ accumulation $\{4, 8, 16\}$ \\
\addlinespace[2pt]
LoRA & rank $\{8, 16, 32, 64\}$; $\alpha = m \cdot r, m \in \{1, 2\}$; dropout 0--0.15 \\
\addlinespace[2pt]
Sequence & max length $\{768, 1024, 1536\}$ \\
\addlinespace[2pt]
Fixed & 4-bit NF4, seven target modules, completion-style loss \\
\bottomrule
\end{tabular}
\caption{Optuna hyperparameter search space.}
\label{tab:optuna}
\end{table}

Search runs in four stages: a baseline trial that verifies the model trains;
15 random trials; 25 Bayesian trials (TPE~\cite{tpe} with a median pruner,
resumable through an SQLite study~\cite{optuna}); and a final retraining of the
winner for two epochs on the full split. Each search trial is capped at 400
steps on a random 8{,}000-item sub-sample. A stall detector terminates trials
and reports them as pruned for five reasons: \textit{flat} (loss span below
$10^{-3}$, adapters not attached), \textit{diverged} (NaN, infinity or loss
above 20), \textit{no\_progress} (no improvement over the previous best by a
minimum delta), \textit{oom} and \textit{failed}. The best configuration, run
identifiers and final metrics are [pending].

\subsection{Evaluation after tuning}

Per-format accuracy on our held-out split and on BBA will be reported with
Wilson intervals, and gains over the pre-tuning model with paired McNemar tests.
Table~\ref{tab:formats} fixes the item counts: 5{,}648 test items on our split
and 14{,}963 on BBA.

% =====================================================================
\section{Comparison with AyurParam}
\label{sec:ayurparam}

\subsection{Published reference numbers}

\begin{table}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lccc@{}}
\toprule
\textbf{Model (published, BBA)} & \textbf{All} & \textbf{English} & \textbf{Hindi} \\
\midrule
AyurParam-2.9B-Instruct~\cite{ayurparam} & \textbf{39.97} & \textbf{41.12} & \textbf{38.04} \\
Llama-3.2-3B-Instruct                   & 33.20 & 35.31 & 29.67 \\
Qwen2.5-3B-Instruct                     & 32.68 & 35.22 & 28.46 \\
granite-3.1-2B                          & 31.10 & 33.39 & 27.30 \\
gemma-2-2B-it                           & 28.40 & 29.38 & 26.79 \\
Llama-3.2-1B-Instruct                   & 26.41 & 26.77 & 25.82 \\
\midrule
AyurLLM, sarvam-1 base                  & [pending] & [pending] & [pending] \\
AyurLLM, + QLoRA                        & [pending] & [pending] & [pending] \\
AyurLLM, + retrieval/graph              & [pending] & [pending] & [pending] \\
AyurLLM, + QLoRA + retrieval/graph      & [pending] & [pending] & [pending] \\
\bottomrule
\end{tabular}
\caption{Accuracy (\%) on BBA. Upper block from AyurParam~\cite{ayurparam}; lower
block are our four ablation conditions, none of which has been run.}
\label{tab:bba}
\end{table}

\subsection{Protocol and decision rule}

We evaluate four conditions with one prompt template and one answer-letter scorer:
(1) sarvam-1 base; (2) base + QLoRA; (3) base + retrieved context; (4) QLoRA +
retrieved context. AyurParam's weights are public~\cite{ayurparamhf}, so we run it
ourselves on both BBA and our test split, which allows paired McNemar tests;
comparison with the published figures alone would be unpaired. At BBA's size the
95\% half-width of an accuracy near 40\% is about 0.8 points, so a difference of
roughly 1.1 points between two systems is resolvable overall, and about 1.8 points
on the Hindi subset ($n=5{,}615$). We pre-specify the rule: we will report AyurLLM
as better than AyurParam on a slice only if the 95\% interval of the paired
difference excludes zero; otherwise we report the slice as unresolved or worse.

\subsection{What the comparison can and cannot show}

Two facts bound expectations. AyurParam is trained on about 4.75M examples; our
training split has 65{,}701, 72 times fewer, on one T4 rather than an H100
cluster. Parametric accuracy on BBA, which draws on a far wider literature than
our eight volumes, is therefore unlikely to be where we win, and we state no such
expectation. Our hypotheses are narrower and falsifiable: (H1) a smaller,
verbatim-grounded corpus still transfers to BBA questions that touch the eight
covered treatises; (H2) retrieved context improves items whose answer lies in
those treatises, and the gain is concentrated on provenance-style questions where
all baselines in Sec.~\ref{sec:baselines} are near chance; (H3) a tokenizer with
lower Devanagari fertility narrows the English--Hindi gap, which is 3.08 points
for AyurParam (41.12 against 38.04). A negative result on any of these will be
reported.

One caveat concerns the published type-level table. AyurParam's per-format
figures are multiples of 1/27 for assertion--reason (59.26, 44.44, 33.33) and of
1/41 for match-the-column (24.39, 36.59), which implies denominators of about 27
and 41; they are small subsets and carry wide intervals, so we do not compare
against them.

\subsection{Positioning}

\begin{table*}[t]
\centering
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}llll@{}}
\toprule
\textbf{Dimension} & \textbf{AyurParam~\cite{ayurparam}} & \textbf{AyurGPT / IRGPT~\cite{ayurgpt,ayurnlp}} & \textbf{AyurLLM (this work)} \\
\midrule
Training answers     & LLM-written (Qwen-3 235B) with audit & PubMedQA-derived / consultations & Verbatim source spans; provenance key \\
Training scale       & $\approx$4.75M examples              & $\approx$113k--150k validated samples & 65{,}701 train items from 28{,}823 facts \\
Base model           & Param-1-2.9B                         & BioGPT-Large-PubMedQA / GPT-2 & sarvam-1, trimmed to 23{,}946 vocab \\
Languages            & English, Hindi                       & English, regional (prototype English) & Sanskrit, English, Hindi corpus \\
Compute              & Multi-node H100 ($\approx$2 days)    & A100                          & Single T4 (Kaggle) \\
Retrieval component  & Not described                        & Planned (2\,GB books)         & Designed, not yet evaluated (Sec.~\ref{sec:system}) \\
Safety mechanism     & Stated as absent                     & Not described                 & Rule-based triage designed, un-evaluated \\
Evaluation           & BBA, 14{,}963 questions              & Not described in cited sources & Own 100-item baseline; BBA [pending] \\
\bottomrule
\end{tabular}
\caption{Verifiable differences between AyurParam, AyurGPT/IRGPT and this work.
``Not described'' means no statement in cited sources, not that the feature is absent.}
\label{tab:positioning}
\end{table*}

Table~\ref{tab:positioning} lists differences that are verifiable from the cited
sources or our own artefacts. The distinctions that we regard as defensible are
the verbatim-span provenance of every training and evaluation item, a corpus
audited item-by-item for contamination against the public benchmark, a
corpus-level tokenizer analysis, and a design that returns citations rather than
only answers. None of these is yet a measured accuracy advantage.

% =====================================================================
\section{Limitations and Ethics}
\label{sec:limitations}

\paragraph{No fine-tuned results.}
The central comparison with AyurParam is unrun (Sec.~\ref{sec:ayurparam}); every
claim of superiority is withheld until it is. Extraction accuracy is unmeasured:
the CER, WER and conjunct-error values of Table~\ref{tab:ocr-pending} are pending,
so engine choices rest on qualitative failure modes. Coverage is bounded by
extraction quality: 355 chunks (6.1\%) yield no item, 202 of them from
Sharangadhara Samhita and 92 from Ashtanga Hridaya, and no later step recovers
text the recogniser did not resolve.

\paragraph{Template stems.}
Answers are verbatim and so cannot be false with respect to the source, but
stems come from 36 templates and a model may learn the template. Paraphrasing
stems while holding answers and options fixed is the natural mitigation and is
not yet applied. Verse under-representation: only 12.3\% of items involve the
verse and 81.2\% rest on commentary alone, so a model trained on the full set
learns commentary comprehension more than verse comprehension; verse-focused work
must filter. Difficulty is assigned from format and commentary length, not
measured, and per-split difficulty must be re-derived from a single labelling
before train and test scores are compared.

\paragraph{Baseline study scale.}
With 100 items, adjacent models cannot be separated (Qwen vs.\ Phi-3, $p=0.058$)
and per-book and per-subtype results (9--16 and 1--14 items) are only
directional. Base-model choice rests on tokenizer evidence; gemma-2-2b-it is
better on overall fertility and byte-fallback, and the perplexity figures are not
comparable across tokenizers. Serving layer: the retrieval index, graph and
triage rules are designs without evaluation.

\paragraph{Clinical and legal.}
The system is a reference and education tool, not a source of treatment advice;
recommendations for herbo-mineral preparations and detoxification regimens require
a qualified practitioner, and no clinical validation has been done. The corpus
derives from copyrighted printed editions, so it is held as a private versioned
repository and we do not release the source text. The source editions are
classical references and not current clinical guidance.

% =====================================================================
\section{Conclusion}

We converted eight classical treatises into a verified corpus with a unified
schema, attributed each coverage gap to a named extraction defect, and built an
80{,}000-item benchmark whose answers are verbatim source spans, with
deduplication, contamination and leakage checks that hold at the fact level.
Baseline statistics show that current 2--4B models are at chance on
assertion--reason and weak at locating the source of a topic, which motivates
retrieval over provenance-keyed chunks. Fine-tuning, retrieval and the comparison
with AyurParam are specified and pre-registered but not yet run; the paper's
strongest claims are therefore about data quality and measurement, and any claim
about model accuracy must wait for those runs.

% =====================================================================
{\small
\begin{thebibliography}{26}\itemsep2pt

\bibitem{surya}
Datalab.
\newblock Surya: OCR, layout analysis, reading order and table recognition in 90+ languages.
\newblock \url{https://github.com/datalab-to/surya}.

\bibitem{marker}
V.~Paruchuri and Datalab.
\newblock Marker: convert PDF to markdown and JSON with high accuracy.
\newblock \url{https://github.com/datalab-to/marker}.

\bibitem{docling}
N.~Livathinos, C.~Auer, et~al.
\newblock Docling: an efficient open-source toolkit for AI-driven document conversion.
\newblock {\em arXiv:2501.17887}, 2025.

\bibitem{doclingtr}
C.~Auer, et~al.
\newblock Docling technical report.
\newblock {\em arXiv:2408.09869}, 2024.

\bibitem{ppocr}
Y.~Du, et~al.
\newblock PP-OCR: a practical ultra lightweight OCR system.
\newblock {\em arXiv:2009.09941}, 2020.

\bibitem{ppocrv2}
Y.~Du, et~al.
\newblock PP-OCRv2: bag of tricks for ultra lightweight OCR system.
\newblock {\em arXiv:2109.03144}, 2021.

\bibitem{lfm2vl}
Liquid AI.
\newblock LFM2-VL: efficient vision-language models.
\newblock \url{https://www.liquid.ai/blog/lfm2-vl-efficient-vision-language-models}.

\bibitem{devaocr}
A.~Kaur and G.~S.~Lehal.
\newblock A comprehensive survey of OCR for Devanagari script based languages.
\newblock {\em IJRES}, 13, 2025.

\bibitem{devavlm}
Can OCR-VLMs read Devanagari? A stress-test benchmark and post-correction study.
\newblock {\em arXiv:2606.29213}, 2026.

\bibitem{sanskritdl}
V.~Kore, et~al.
\newblock A systematic framework for Sanskrit character recognition using deep learning.
\newblock {\em ELCVIA}, 24(2):81--103, 2025.

\bibitem{ayurparam}
M.~Nauman, S.~Gvm, V.~Devane, S.~Pawar, V.~Thakur, K.~Pundalik, P.~Sawarkar, R.~Saluja, M.~Desarkar, and G.~Ramakrishnan.
\newblock AyurParam: a state-of-the-art bilingual language model for Ayurveda.
\newblock {\em arXiv:2511.02374}, 2025.

\bibitem{ayurparamhf}
BharatGenAI.
\newblock AyurParam: domain-specialized Ayurvedic LLM.
\newblock Hugging Face, 2025.
\newblock \url{https://huggingface.co/bharatgenai/AyurParam}.

\bibitem{param1}
BharatGen Research Team.
\newblock PARAM-1 BharatGen 2.9B model.
\newblock {\em arXiv:2507.13390}, 2025.

\bibitem{bhashabenchdata}
BharatGen Research Team.
\newblock BhashaBench-Ayur (BBA).
\newblock Hugging Face Datasets, 2025.
\newblock \url{https://huggingface.co/datasets/bharatgenai/bhashabench-ayur}.

\bibitem{bhashabench}
V.~Devane, M.~Nauman, B.~Patel, et~al.
\newblock BhashaBench V1: a comprehensive benchmark for the quadrant of Indic domains.
\newblock {\em arXiv:2510.25409}, 2025.

\bibitem{ayurnlp}
A.~Padia.
\newblock AyurGPT: fine-tuning a medical LLM for multilingual Ayurveda consultations.
\newblock In {\em NLP Summit}, 25 Sept.\ 2024.
\newblock \url{https://www.nlpsummit.org/ayur-gtp-fine-tuning-a-medical-llm-for-multilingual-ayurveda-consultations/}.

\bibitem{ayurgpt}
Trigent Software.
\newblock Developing a multilingual Ayurvedic medical LLM: challenges and learnings.
\newblock {\em ZenML LLMOps Database}.
\newblock \url{https://www.zenml.io/llmops-database/developing-a-multilingual-ayurvedic-medical-llm-challenges-and-learnings}.

\bibitem{attrground}
From real to synthetic: synthesizing millions of diversified and complicated user instructions with attributed grounding.
\newblock {\em arXiv:2506.03968}, 2025.

\bibitem{cotself}
CoT-Self-Instruct: building high-quality synthetic data for reasoning and non-reasoning tasks.
\newblock {\em arXiv:2507.23751}, 2025.

\bibitem{seedfree}
Seed-free synthetic data generation framework for instruction-tuning LLMs: a case study in Thai.
\newblock {\em arXiv:2411.15484}, 2024.

\bibitem{qlora}
T.~Dettmers, A.~Pagnoni, A.~Holtzman, and L.~Zettlemoyer.
\newblock QLoRA: efficient finetuning of quantized LLMs.
\newblock In {\em NeurIPS}, 36, 2023.

\bibitem{lora}
E.~J.~Hu, et~al.
\newblock LoRA: low-rank adaptation of large language models.
\newblock In {\em ICLR}, 2022.

\bibitem{optuna}
T.~Akiba, S.~Sano, T.~Yanase, T.~Ohta, and M.~Koyama.
\newblock Optuna: a next-generation hyperparameter optimization framework.
\newblock In {\em KDD}, 2019.

\bibitem{tpe}
J.~Bergstra, R.~Bardenet, Y.~Bengio, and B.~K{\'e}gl.
\newblock Algorithms for hyper-parameter optimization.
\newblock In {\em NeurIPS}, 24, 2011.

\bibitem{mcnemar}
Q.~McNemar.
\newblock Note on the sampling error of the difference between correlated proportions or percentages.
\newblock {\em Psychometrika}, 12(2):153--157, 1947.

\bibitem{wilson}
E.~B.~Wilson.
\newblock Probable inference, the law of succession, and statistical inference.
\newblock {\em JASA}, 22(158):209--212, 1927.

\end{thebibliography}
}

\end{document}
"""

with open("RP/ayurllm_paper.tex", "w", encoding="utf-8") as f:
    f.write(tex_code)
print("Saved complete LaTeX file to: RP/ayurllm_paper.tex")

# Copy to artifacts directory
artifact_dir = r"C:\Users\KIIT0001\.gemini\antigravity\brain\75784175-db3c-4581-90d5-5676d3d83ab0"
os.makedirs(artifact_dir, exist_ok=True)
art_path = os.path.join(artifact_dir, "ayurllm_paper.tex")
shutil.copy2("RP/ayurllm_paper.tex", art_path)
print(f"Copied to artifact directory: {art_path}")

