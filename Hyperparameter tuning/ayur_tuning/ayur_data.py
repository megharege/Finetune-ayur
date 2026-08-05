#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data layer for AyurLLM fine-tuning --- schema, prompts, formatting, auditing.
=============================================================================

Kept separate from the trainer so it can be imported and tested without a GPU,
a model download, or CUDA. ``test_ayur_data.py`` exercises everything here
against the real split files.

THE SCHEMA
----------
One JSON array per split, 41 fields per row. The ones that matter for training:

    question         the stem
    option_a..e      option text; e is empty except on multiple-selection items
    correct_answer   "A", or "A,C" for multiple-selection
    answer_text      the correct option's text
    question_type    one of six formats
    language         "en" | "hi"
    subject_domain   used only for reporting

WHY THE PROMPT LOOKS LIKE THIS
------------------------------
*Instruction matches the item's language.* A Hindi question with an English
instruction teaches the model that answer language is unrelated to question
language, which is exactly wrong for a bilingual benchmark.

*The instruction states how many answers to give.* Multiple-selection items want
two or three letters; every other format wants one. Without that, the model
learns to hedge and emits several letters on single-answer items.

*Completion is the letter, optionally followed by the answer text.* BhashaBench
is scored on the letter, so letter-only keeps training and evaluation in the same
units. ``--completion_style letter_text`` adds the text for models that benefit
from generating the content, at the cost of a longer completion span.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional

LETTERS = ["a", "b", "c", "d", "e"]
DEVA = re.compile(r"[ऀ-ॿ]")

# The six formats, with the instruction that tells the model what shape of answer
# is wanted. Two languages each, because an English instruction on a Hindi item
# is a training signal in the wrong direction.
INSTRUCTION = {
    "en": {
        "Multiple selection": "Select ALL correct options. Answer with the option "
                              "letters separated by commas, for example: A,C",
        "Match the column": "Choose the option with the correct pairing. Answer "
                            "with one option letter only.",
        "Assertion or Reasoning": "Evaluate the Assertion and the Reason. Answer "
                                  "with one option letter only.",
        "Fill in the blanks": "Choose the term that fills [X]. Answer with one "
                              "option letter only.",
        "Assorted": "Answer with one option letter only.",
        "MCQ": "Answer with one option letter only.",
    },
    "hi": {
        "Multiple selection": "सभी सही विकल्प चुनें। उत्तर केवल विकल्प अक्षरों में दें, "
                              "अल्पविराम से अलग करके, जैसे: A,C",
        "Match the column": "सही जोड़ी वाला विकल्प चुनें। उत्तर केवल एक विकल्प अक्षर में दें।",
        "Assertion or Reasoning": "अभिकथन और कारण का मूल्यांकन करें। उत्तर केवल एक "
                                  "विकल्प अक्षर में दें।",
        "Fill in the blanks": "[X] के स्थान पर सही शब्द चुनें। उत्तर केवल एक विकल्प अक्षर में दें।",
        "Assorted": "उत्तर केवल एक विकल्प अक्षर में दें।",
        "MCQ": "उत्तर केवल एक विकल्प अक्षर में दें।",
    },
}

SYSTEM = {
    "en": "You are an expert in Ayurveda, trained on the classical Sanskrit "
          "treatises. Answer examination questions accurately and concisely.",
    "hi": "आप आयुर्वेद के विशेषज्ञ हैं, जो शास्त्रीय संस्कृत ग्रंथों में प्रशिक्षित हैं। "
          "परीक्षा प्रश्नों का सटीक और संक्षिप्त उत्तर दें।",
}


def clean(s: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def load_split(path: str) -> List[Dict[str, Any]]:
    """Accepts a JSON array or JSON Lines; both appear across this project."""
    with open(path, encoding="utf-8") as fh:
        head = fh.read(2048)
        fh.seek(0)
        if head.lstrip().startswith("["):
            return json.load(fh)
        return [json.loads(l) for l in fh if l.strip()]


def options_of(row: Dict[str, Any]) -> Dict[str, str]:
    """Present, non-empty options only. Rows carry five slots; most use four."""
    return {L: clean(row.get("option_%s" % L))
            for L in LETTERS if clean(row.get("option_%s" % L))}


def answer_keys(row: Dict[str, Any], opts: Dict[str, str]) -> List[str]:
    """Upper-case letters that exist as options. Handles "A" and "A,C" alike."""
    raw = str(row.get("correct_answer", ""))
    keys = [k.strip().upper() for k in raw.split(",") if k.strip()]
    return [k for k in keys if k.lower() in opts]


def infer_language(row: Dict[str, Any]) -> str:
    """Normalise the label; fall back to the script of the stem when absent."""
    raw = str(row.get("language", "")).strip().lower()
    if raw in ("hi", "hin", "hindi", "हिन्दी", "हिंदी"):
        return "hi"
    if raw in ("en", "eng", "english"):
        return "en"
    q = clean(row.get("question"))
    return "hi" if len(DEVA.findall(q)) / max(len(q), 1) > 0.30 else "en"


# Some rows are open-ended by construction --- "explain this verse", "name the
# sthana and chapter" --- so they have no options at all. They are ~2.5% of the
# corpus and every one carries an answer_text, which makes them the most
# content-rich rows available: answering them requires generating Ayurvedic
# explanation rather than picking a letter. Dropping them for lack of options
# would throw away exactly the material that teaches domain knowledge, so they
# are trained as free-text generation instead.
OPEN_INSTRUCTION = {
    "en": "Answer concisely, based on the classical text.",
    "hi": "शास्त्रीय ग्रंथ के आधार पर संक्षेप में उत्तर दें।",
}


def is_open_ended(row: Dict[str, Any]) -> bool:
    """No usable options, but a usable answer --- a free-text item."""
    opts = options_of(row)
    if len(opts) >= 2 and answer_keys(row, opts):
        return False
    return bool(clean(row.get("answer_text")))


def build_user_prompt(row: Dict[str, Any], allow_open: bool = True) -> Optional[str]:
    opts = options_of(row)
    keys = answer_keys(row, opts)
    lang = infer_language(row)

    if len(opts) < 2 or not keys:
        if allow_open and is_open_ended(row):
            return "%s\n\n%s" % (clean(row.get("question")), OPEN_INSTRUCTION[lang])
        return None

    qtype = row.get("question_type", "MCQ")
    instr = INSTRUCTION[lang].get(qtype, INSTRUCTION[lang]["MCQ"])
    option_block = "\n".join("%s. %s" % (L.upper(), opts[L])
                             for L in LETTERS if L in opts)
    return "%s\n\n%s\n\n%s" % (clean(row.get("question")), option_block, instr)


def format_example(row: Dict[str, Any], tokenizer,
                   completion_style: str = "letter",
                   use_system: bool = True,
                   allow_open: bool = True,
                   open_answer_chars: int = 600) -> Dict[str, str]:
    """Row -> {"prompt", "completion"} for TRL's native completion-only loss.

    Returns empty strings when the row cannot be rendered; the caller drops those
    rather than training on a malformed item.
    """
    user = build_user_prompt(row, allow_open=allow_open)
    if user is None:
        return {"prompt": "", "completion": ""}

    opts = options_of(row)
    keys = answer_keys(row, opts)
    lang = infer_language(row)

    if not keys:
        # Free-text item. Capping the answer keeps a handful of very long verse
        # expositions from dominating the loss and blowing past max_seq_length.
        answer = clean(row.get("answer_text"))[:open_answer_chars]
    else:
        answer = ",".join(keys)
        if completion_style == "letter_text":
            answer = "%s. %s" % (answer, " ; ".join(opts[k.lower()] for k in keys))

    eos = getattr(tokenizer, "eos_token", "") or ""
    template = getattr(tokenizer, "chat_template", None)

    if template:
        msgs = ([{"role": "system", "content": SYSTEM[lang]}] if use_system else [])
        msgs = msgs + [{"role": "user", "content": user}]
        prompt_only = tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True)
        full = tokenizer.apply_chat_template(
            msgs + [{"role": "assistant", "content": answer}], tokenize=False)
        if full.startswith(prompt_only) and len(full) > len(prompt_only):
            return {"prompt": prompt_only, "completion": full[len(prompt_only):]}
        # Some templates do not prefix-match cleanly. Falling back keeps the run
        # alive; the masking check downstream still confirms a non-empty span.
        return {"prompt": prompt_only, "completion": answer + eos}

    head = SYSTEM[lang] + "\n\n" if use_system else ""
    return {"prompt": "%sUser: %s\nAnswer:" % (head, user),
            "completion": " %s%s" % (answer, eos)}


# --------------------------------------------------------------------------
# Auditing --- run before training, not after it fails
# --------------------------------------------------------------------------

def audit_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Composition, plus the two defects that silently break a run."""
    return {
        "rows": len(rows),
        "unusable_missing_options": sum(1 for r in rows if len(options_of(r)) < 2),
        "unusable_missing_answer_key": sum(
            1 for r in rows if not answer_keys(r, options_of(r))),
        "by_type": dict(Counter(r.get("question_type") for r in rows).most_common()),
        "by_language": dict(Counter(infer_language(r) for r in rows)),
        "by_book": dict(Counter(r.get("source_book") for r in rows).most_common()),
        "multi_answer_rows": sum(1 for r in rows
                                 if len(answer_keys(r, options_of(r))) > 1),
        "open_ended_rows": sum(1 for r in rows if is_open_ended(r)),
        "answer_position": dict(Counter(
            k for r in rows for k in answer_keys(r, options_of(r)))),
    }


def token_length_audit(pairs: List[Dict[str, str]], tokenizer,
                       max_seq_length: int, sample: int = 4000) -> Dict[str, Any]:
    """Percentiles of prompt+completion length, and how much would be truncated.

    Devanagari costs several tokens per character on most tokenizers, so a
    max_seq_length chosen for an English corpus can silently cut the answer off a
    large share of the Hindi half --- and a truncated completion means the loss is
    computed over nothing.
    """
    import random
    rnd = random.Random(0)
    take = pairs if len(pairs) <= sample else rnd.sample(pairs, sample)
    lens, comp_lens = [], []
    for p in take:
        pl = len(tokenizer(p["prompt"], add_special_tokens=False)["input_ids"])
        cl = len(tokenizer(p["completion"], add_special_tokens=False)["input_ids"])
        lens.append(pl + cl)
        comp_lens.append(cl)
    lens.sort()

    def pct(q):
        return lens[min(int(q * len(lens)), len(lens) - 1)] if lens else 0

    over = sum(1 for x in lens if x > max_seq_length)
    return {
        "sampled": len(lens),
        "total_tokens_p50": pct(0.50), "total_tokens_p90": pct(0.90),
        "total_tokens_p99": pct(0.99), "total_tokens_max": lens[-1] if lens else 0,
        "completion_tokens_mean": round(sum(comp_lens) / max(len(comp_lens), 1), 2),
        "completion_tokens_min": min(comp_lens) if comp_lens else 0,
        "rows_over_max_seq_length": over,
        "pct_over_max_seq_length": round(100 * over / max(len(lens), 1), 2),
        "max_seq_length": max_seq_length,
        "all_token_lengths": lens,          # for the histogram plot
    }


def prepare(rows: List[Dict[str, Any]], tokenizer, completion_style="letter",
            use_system=True, allow_open=True, open_answer_chars=600):
    """Format and drop unusable rows. Returns (pairs, dropped, n_open)."""
    out, dropped, n_open = [], 0, 0
    for r in rows:
        p = format_example(r, tokenizer, completion_style, use_system,
                           allow_open, open_answer_chars)
        if not p["prompt"] or not p["completion"].strip():
            dropped += 1
            continue
        if allow_open and is_open_ended(r):
            n_open += 1
        out.append(p)
    return out, dropped, n_open

# ==========================================================================
# Raw treatise chunks --- the other schema this corpus ships in
# ==========================================================================
# The QA splits above are one input. The other is the source corpus itself:
# one row per verse, with sanskrit_text, transliteration and commentary. Those
# rows have no question and no options, so nothing above applies to them --- but
# they are the most direct way to teach the model the texts, because the target
# is the actual translation rather than a letter.
#
# Three tasks are derived per chunk, and only when the field that would be the
# answer is actually present:
#
#   translate      Sanskrit verse -> commentary / English meaning
#   transliterate  Devanagari -> IAST
#   explain        cited topic -> what the text says about it
#
# A chunk with an empty commentary yields no translate task rather than a task
# with an empty target, which would train the model to emit nothing.

CHUNK_KEYS = {"sanskrit_text", "commentary", "chunk_id"}

CHUNK_TASKS = {
    "translate": {
        "en": "Translate this verse from {cite} into English.",
        "hi": "{cite} के इस श्लोक का हिन्दी में अनुवाद करें।",
    },
    "transliterate": {
        "en": "Transliterate this verse from {cite} into IAST.",
        "hi": "{cite} के इस श्लोक का IAST में लिप्यंतरण करें।",
    },
    "explain": {
        "en": "According to {cite}, explain: {topic}",
        "hi": "{cite} के अनुसार समझाइए: {topic}",
    },
}


def is_chunk_row(row: Dict[str, Any]) -> bool:
    """True when the row is a raw treatise chunk rather than a QA item."""
    return "question" not in row and CHUNK_KEYS.issubset(set(row))


def detect_schema(rows: List[Dict[str, Any]]) -> str:
    """'qa' | 'chunk' | 'mixed', from the first few hundred rows."""
    sample = rows[:500]
    if not sample:
        return "qa"
    chunk = sum(1 for r in sample if is_chunk_row(r))
    if chunk == 0:
        return "qa"
    if chunk == len(sample):
        return "chunk"
    return "mixed"


def chunk_citation(row: Dict[str, Any]) -> str:
    bits = [clean(row.get("book") or row.get("source_book") or "the classical text")]
    if clean(row.get("sthana")):
        bits.append(clean(row.get("sthana")))
    if row.get("chapter_number") not in (None, ""):
        bits.append("Chapter %s" % row.get("chapter_number"))
    if clean(row.get("verse_id")):
        bits.append("verse %s" % clean(row.get("verse_id")))
    return ", ".join(bits)


def chunk_examples(row: Dict[str, Any], min_target: int = 40,
                   max_target_chars: int = 1200) -> List[Dict[str, str]]:
    """Every usable (instruction, input, target) triple this chunk supports."""
    out = []
    cite = chunk_citation(row)
    sanskrit = clean(row.get("sanskrit_text"))
    translit = clean(row.get("transliteration"))
    comm = clean(row.get("commentary"))
    topic = clean(row.get("topic_heading")) or clean(row.get("chapter_title"))
    lang = "hi" if len(DEVA.findall(comm)) / max(len(comm), 1) > 0.30 else "en"

    if sanskrit and len(comm) >= min_target:
        out.append({"instruction": CHUNK_TASKS["translate"][lang].format(cite=cite),
                    "input": sanskrit, "target": comm[:max_target_chars],
                    "task": "translate", "language": lang})

    # Only when the transliteration is really IAST. Some rows carry English prose
    # in that field --- training on those teaches the model that transliteration
    # means translation.
    if sanskrit and translit and not DEVA.search(translit)             and len(translit) >= min_target             and len(re.findall(r"[āīūṛṝḷṅñṭḍṇśṣḥṁṃ]", translit)) >= 2:
        out.append({"instruction": CHUNK_TASKS["transliterate"][lang].format(cite=cite),
                    "input": sanskrit, "target": translit[:max_target_chars],
                    "task": "transliterate", "language": lang})

    if topic and len(comm) >= min_target and topic.lower() not in comm.lower()[:60]:
        out.append({"instruction": CHUNK_TASKS["explain"][lang].format(
                        cite=cite, topic=topic),
                    "input": "", "target": comm[:max_target_chars],
                    "task": "explain", "language": lang})
    return out


def format_chunk_example(ex: Dict[str, str], tokenizer,
                         use_system: bool = True) -> Dict[str, str]:
    lang = ex.get("language", "en")
    user = ex["instruction"] + (("\n\n" + ex["input"]) if ex["input"] else "")
    answer = ex["target"]
    eos = getattr(tokenizer, "eos_token", "") or ""
    template = getattr(tokenizer, "chat_template", None)
    if template:
        msgs = ([{"role": "system", "content": SYSTEM[lang]}] if use_system else [])
        msgs = msgs + [{"role": "user", "content": user}]
        prompt_only = tokenizer.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True)
        full = tokenizer.apply_chat_template(
            msgs + [{"role": "assistant", "content": answer}], tokenize=False)
        if full.startswith(prompt_only) and len(full) > len(prompt_only):
            return {"prompt": prompt_only, "completion": full[len(prompt_only):]}
        return {"prompt": prompt_only, "completion": answer + eos}
    head = SYSTEM[lang] + "\n\n" if use_system else ""
    return {"prompt": "%sUser: %s\nAssistant:" % (head, user),
            "completion": " %s%s" % (answer, eos)}


def prepare_chunks(rows: List[Dict[str, Any]], tokenizer, use_system=True,
                   max_target_chars=1200):
    """Raw chunks -> prompt/completion pairs. Returns (pairs, skipped, by_task)."""
    out, skipped = [], 0
    by_task = Counter()
    for r in rows:
        exs = chunk_examples(r, max_target_chars=max_target_chars)
        if not exs:
            skipped += 1
            continue
        for e in exs:
            p = format_chunk_example(e, tokenizer, use_system)
            if p["prompt"] and p["completion"].strip():
                out.append(p)
                by_task[e["task"]] += 1
    return out, skipped, dict(by_task)


def prepare_any(rows: List[Dict[str, Any]], tokenizer, **kw):
    """Route by detected schema. Returns (pairs, info dict)."""
    schema = detect_schema(rows)
    if schema == "chunk":
        pairs, skipped, by_task = prepare_chunks(
            rows, tokenizer, kw.get("use_system", True),
            kw.get("max_target_chars", 1200))
        return pairs, {"schema": "chunk", "input_rows": len(rows),
                       "pairs": len(pairs), "chunks_skipped": skipped,
                       "by_task": by_task}
    if schema == "qa":
        pairs, dropped, n_open = prepare(
            rows, tokenizer, kw.get("completion_style", "letter"),
            kw.get("use_system", True), kw.get("allow_open", True),
            kw.get("open_answer_chars", 600))
        return pairs, {"schema": "qa", "input_rows": len(rows),
                       "pairs": len(pairs), "dropped": dropped,
                       "open_ended": n_open}
    qa_rows = [r for r in rows if not is_chunk_row(r)]
    ch_rows = [r for r in rows if is_chunk_row(r)]
    a, ia = prepare_any(qa_rows, tokenizer, **kw)
    b, ib = prepare_any(ch_rows, tokenizer, **kw)
    return a + b, {"schema": "mixed", "qa": ia, "chunk": ib,
                   "pairs": len(a) + len(b)}
