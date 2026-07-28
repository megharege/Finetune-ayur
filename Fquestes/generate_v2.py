#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AyurShloka-QA v2 — 80,000 questions, fact-centric
=================================================

Difference from v1: questions are no longer built format-by-format. Each chunk is
first reduced to a set of discrete **facts**, each with a stable ``fact_id``; every
fact is then rendered into as many of the six formats as it supports.

That is what lets the same answer legitimately appear as an MCQ, an assertion-reason
item, a cloze, a match-the-column row and a multiple-selection item without any two
question *stems* being duplicates.

Formats
    MCQ · Fill in the blanks · Multiple selection · Assertion or Reasoning ·
    Match the column · Assorted

Every row carries:
    fact_id          which underlying fact it tests (group by this to de-duplicate
                     semantically, or to keep a fact's variants inside one split)
    source_richness  characters of source material behind the fact
    format_variant   which rendering of that fact this row is

All text-quality machinery (OCR filtering, Devanagari validation, leakage guards,
distractor isolation) is reused from generate_questions.py unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict

import generate_questions as G

SEED = 20260729
IN_DIR = G.IN_DIR
OUT_DIR = "/sessions/loving-trusting-wright/mnt/outputs/ayur_qa_v2"
BOOK_DIR = os.path.join(OUT_DIR, "by_book")
TARGET_TOTAL = 80_000

BOOKS = G.BOOKS
LETTERS5 = ["A", "B", "C", "D", "E"]

TYPE_MCQ = "MCQ"
TYPE_FIB = "Fill in the blanks"
TYPE_MS = "Multiple selection"
TYPE_AR = "Assertion or Reasoning"
TYPE_MTC = "Match the column"
TYPE_ASR = "Assorted"

SHORT = {TYPE_MCQ: "MCQ", TYPE_FIB: "FIB", TYPE_MS: "MS",
         TYPE_AR: "AR", TYPE_MTC: "MTC", TYPE_ASR: "ASR"}

# desired share of the 80k set, per format
MS_SEP = " || "           # option text may itself contain ";"
MTC_CAP = 3200            # match-the-column items per book
MTC_ATTEMPT_CAP = 9000   # overridden per book in build_book    # bounded work: group search is combinatorial

TARGET_MIX = {TYPE_MCQ: 0.34, TYPE_FIB: 0.18, TYPE_ASR: 0.18,
              TYPE_MS: 0.12, TYPE_AR: 0.10, TYPE_MTC: 0.08}


# ==========================================================================
# Enumeration extraction (feeds multiple-selection)
# ==========================================================================
TERM = r"[A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’\-]{3,26}"

ENUM_TAIL = re.compile(
    r"(?P<items>(?:%s\s*,\s*){2,}(?:and\s+|or\s+)?%s)\s+"
    r"(?:are|is)\s+(?:the\s+|said\s+to\s+be\s+the\s+|known\s+as\s+the\s+|called\s+the\s+)?"
    r"(?P<label>[^.;:]{4,70})" % (TERM, TERM))

ENUM_HEAD = re.compile(
    r"(?P<label>[^.;:]{4,70}?)\s+(?:are|include|comprise|consist\s+of)\s*[:\-]?\s*"
    r"(?P<items>(?:%s\s*,\s*){2,}(?:and\s+|or\s+)?%s)" % (TERM, TERM))

BAD_ITEM = set("""the a an and or of in on at to for with by from is are was were be been
being this that these those which who what when where how why not no all any some such
it its his her their there here also only just very more most many few both each other
same than then so if but as at we you they he she i""".split())


def _clean_items(raw):
    out = []
    for p in re.split(r"\s*,\s*|\s+and\s+|\s+or\s+", raw or ""):
        p = G.norm_ws(p).strip(" .;:()[]'\"’‘")
        if not p or " " in p:
            continue
        if len(p) < 3 or len(p) > 26:
            continue
        if p.lower() in BAD_ITEM or G.DEVA.search(p):
            continue
        if not re.fullmatch(TERM, p):
            continue
        out.append(p)
    # de-dup, preserve order
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


def extract_enumerations(text):
    """Lists of named items with the category they belong to."""
    found = []
    for rx in (ENUM_TAIL, ENUM_HEAD):
        for m in rx.finditer(text or ""):
            items = _clean_items(m.group("items"))
            label = G.norm_ws(m.group("label")).strip(" .;:-")
            label = re.sub(r"^(the|these|those|following|above|said)\s+", "", label, flags=re.I)
            if len(items) >= 3 and 4 <= len(label) <= 70 and not G.DEVA.search(label):
                if len(label.split()) <= 10:
                    found.append((label, items))
    # keep the longest list per label
    best = {}
    for label, items in found:
        k = label.lower()
        if k not in best or len(items) > len(best[k][1]):
            best[k] = (label, items)
    return list(best.values())


# ==========================================================================
# Fact extraction
# ==========================================================================
class Fact(dict):
    pass


LEAD_CONNECTOR = re.compile(
    r"^(It|They|This|These|Those|He|She|Such|Thus|Hence|Therefore|Then|Here|There|But|And|"
    r"Or|Also|However|Moreover|Besides|Now|Again|Further|Likewise|Similarly|Otherwise|Instead|So)\b")


def soft_sentence(s, lo=38, hi=400):
    """Usable as quoted evidence (cloze, true/false, reason) but not as a free-standing
    'which statement is correct' option, because it may open with a dangling pronoun."""
    s = G.norm_ws(s)
    if not (lo <= len(s) <= hi):
        return False
    if G.DEVA.search(s) or len(s.split()) < 6:
        return False
    if sum(c.isalpha() for c in s) < 0.55 * len(s):
        return False
    if len(G.OCR_NOISE.findall(s)) >= 2 or G.RUNNING_HEAD.search(s):
        return False
    toks = s.split()
    if sum(1 for t in toks if len(t.strip(".,;:")) == 1
           and t.strip(".,;:").lower() not in "ai") >= 2:
        return False
    return not G.ocr_garbled(s)


def make_facts(r, rng):
    """Reduce one chunk to discrete, separately-testable facts."""
    facts = []
    cid = r["chunk_id"]
    n = 0

    def fid():
        nonlocal n
        n += 1
        return "%s::%s::F%02d" % (r["code"], cid, n)

    heading = G.clean_heading(r["topic_heading"])
    good_head = G.good_heading(heading)
    raw = G.split_sentences(r["commentary"])
    sents = [s for s in raw if G.good_sentence(s)]          # strict: standalone options
    soft = [s for s in raw if soft_sentence(s)]             # loose: quotable evidence
    richness = len(r["sanskrit"]) + len(r["commentary"])

    # --- 1. what the verse is about -------------------------------------
    if r["sanskrit"] and len(r["sanskrit"]) >= 20 and good_head \
            and not G.devanagari_garbled(r["sanskrit"]):
        facts.append(Fact(fact_id=fid(), kind="verse_subject", subject=heading,
                          answer=heading, evidence=r["sanskrit"], richness=richness))

    # --- 2. each substantive commentary statement -----------------------
    for s in sents[:11]:
        facts.append(Fact(fact_id=fid(), kind="statement",
                          subject=heading if good_head else (r["chapter_title"] or r["sthana"]),
                          answer=G.shorten(s, 200), evidence=s, richness=richness))

    strict = {G.norm_ws(x) for x in sents}
    for s in soft[:11]:
        if G.norm_ws(s) not in strict:
            facts.append(Fact(fact_id=fid(), kind="evidence", subject=heading if good_head else "",
                              answer=G.shorten(s, 200), evidence=s, richness=richness))

    tset = [t for t in G.extract_terms(blob0) if len(t) >= 5] if (blob0 := heading + " " + r["commentary"]) else []
    tset = list(dict.fromkeys(tset))
    if len(tset) >= 2:
        facts.append(Fact(fact_id=fid(), kind="term_set",
                          subject=heading if good_head else (r["chapter_title"] or r["sthana"]),
                          answer=tset[:8], evidence=r["commentary"][:300], richness=richness))

    # a whole-chunk multi-select over its own statements
    if len(sents) >= 2:
        facts.append(Fact(fact_id=fid(), kind="statement_set",
                          subject=heading if good_head else (r["chapter_title"] or r["sthana"]),
                          answer=[G.shorten(x, 150) for x in sents[:5]],
                          evidence=r["commentary"][:400], richness=richness))

    # --- 3. the technical term the passage turns on ---------------------
    blob = heading + " " + r["commentary"]
    terms = [t for t in G.extract_terms(blob) if len(t) >= 5]
    ranked = sorted(terms, key=lambda t: -blob.count(t))
    for t in ranked[:5]:
        if blob.count(t) >= 1:
            host = next((s for s in soft if re.search(r"\b%s\b" % re.escape(t), s)), "")
            if host:
                facts.append(Fact(fact_id=fid(), kind="term", subject=heading, answer=t,
                                  evidence=host, richness=richness))

    # --- 4. an explicit count -------------------------------------------
    m = G.COUNT_RE.search(r["commentary"])
    if m:
        val = G.NUM_WORDS.get(m.group(1).lower())
        if val is None and m.group(1).isdigit():
            val = int(m.group(1))
        subj = G.norm_ws(m.group(3))
        if val and 2 <= val <= 100 and len(subj) >= 3:
            facts.append(Fact(fact_id=fid(), kind="count", subject="%s of %s" % (m.group(2).lower(), subj),
                              answer=str(val), evidence=m.group(0), richness=richness))

    # --- 5. synonym set (paryāya) ---------------------------------------
    syns = G.extract_synonyms(r)
    if len(syns) >= 3:
        subj = re.sub(r"\s*\(.*?\)\s*", " ", heading)
        subj = re.sub(G.SYN_CUE, "", subj).strip(" :–-") or r["chapter_title"]
        if subj and len(subj) >= 3:
            facts.append(Fact(fact_id=fid(), kind="synonym_set", subject=subj,
                              answer=syns, evidence=r["commentary"][:300], richness=richness))

    # --- 6. enumerations -------------------------------------------------
    for label, items in extract_enumerations(r["commentary"])[:2]:
        facts.append(Fact(fact_id=fid(), kind="enumeration", subject=label,
                          answer=items, evidence=r["commentary"][:300], richness=richness))

    if r["translit"] and len(r["translit"]) >= 25 and r["sanskrit"]:
        facts.append(Fact(fact_id=fid(), kind="translit", subject=heading,
                          answer=G.shorten(r["translit"], 200), evidence=r["sanskrit"],
                          richness=richness))

    # --- 7. where the teaching sits --------------------------------------
    if good_head and r["sthana"]:
        facts.append(Fact(fact_id=fid(), kind="location", subject=heading,
                          answer=r["sthana"], evidence=G.verse_ref(r), richness=richness))

    if not facts:
        body = r["commentary"] or r["translit"] or r["sanskrit"]
        if body and len(body) >= 20:
            facts.append(Fact(fact_id=fid(), kind="raw", subject=heading or r["chapter_title"],
                              answer=body, evidence=r["sanskrit"] or body, richness=richness))
    for f in facts:
        f["chunk"] = r
    return facts


# ==========================================================================
# Emitter
# ==========================================================================
class Emitter:
    def __init__(self):
        self.rows = []
        self.seen = set()
        self.n = Counter()

    def add(self, fact, qtype, variant, question, options, answer_letters,
            answer_text, difficulty, explanation, grounding, context=""):
        r = fact["chunk"]
        stem_key = hashlib.md5(G.norm_ws(question).lower().encode("utf-8")).hexdigest()
        if stem_key in self.seen:
            return False
        if options:
            if len({G.norm_ws(o).lower() for o in options}) != len(options):
                return False
            # leakage guard: the key must not sit in the stem outside the option block
            body = G.norm_ws(question).lower()
            for o in options:
                body = body.replace(G.norm_ws(o).lower(), " ")
            al = G.norm_ws(answer_text).lower()
            if qtype in (TYPE_MCQ, TYPE_FIB, TYPE_MS) and len(al) >= 5 and al in body:
                return False
        if options and context and len(G.norm_ws(answer_text)) >= 4 \
                and G.norm_ws(answer_text).lower() in G.norm_ws(context).lower():
            context = ""
        if qtype == TYPE_AR:
            context = ""
        if not options:
            at = G.norm_ws(answer_text)
            if len(at) < 25 or sum(c.isalpha() for c in at) < 0.5 * len(at):
                return False
        self.seen.add(stem_key)
        self.n[r["code"]] += 1
        row = {
            "question_id": "%s-%s-%06d" % (r["code"], SHORT[qtype], self.n[r["code"]]),
            "fact_id": fact["fact_id"],
            "format_variant": variant,
            "question": question,
            "correct_answer": ",".join(answer_letters),
            "answer_text": answer_text,
            "question_type": qtype,
            "grounding": grounding,
            "difficulty": difficulty,
            "n_options": len(options),
            "n_correct": len(answer_letters),
            "subject_domain": G.pick_domain(r["book"], r["sthana"], r["categories"],
                                            r["primary_category"]),
            "language": "English",
            "source_book": r["book"],
            "sthana": r["sthana"],
            "chapter_number": r["chapter_number"],
            "chapter_title": r["chapter_title"],
            "verse_id": r["verse_id"],
            "chunk_id": r["chunk_id"],
            "primary_category": r["primary_category"],
            "citation": G.citation(r),
            "source_richness": fact["richness"],
            "fact_kind": fact["kind"],
            "explanation": G.norm_ws(explanation),
            "context": G.norm_ws(context),
        }
        for i, o in enumerate(options):
            row["option_%s" % LETTERS5[i].lower()] = o
        for i in range(len(options), 5):
            row["option_%s" % LETTERS5[i].lower()] = ""
        self.rows.append(row)
        return True


def shuffled(correct_list, distractors, rng, n_total):
    """Return (options, letters-of-correct). correct_list may hold 1..n items."""
    opts = list(correct_list) + list(distractors)
    opts = opts[:n_total]
    if len(opts) < n_total:
        return None, None
    seen, uniq = set(), []
    for o in opts:
        k = G.norm_ws(o).lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(G.norm_ws(o))
    if len(uniq) < n_total:
        return None, None
    rng.shuffle(uniq)
    corr = {G.norm_ws(c).lower() for c in correct_list}
    letters = [LETTERS5[i] for i, o in enumerate(uniq) if o.lower() in corr]
    if len(letters) != len(correct_list):
        return None, None
    return uniq, letters


# ==========================================================================
# Renderers — one fact, many formats
# ==========================================================================
AR_OPTIONS = G.AR_OPTIONS
EXPLANATORY = G.EXPLANATORY


TF_OPTIONS = ["True", "False", "Partially true", "Cannot be determined"]


def _tf(rng, verdict):
    """Shuffled true/false options + key, so the verdict is not tied to a fixed letter."""
    o = list(TF_OPTIONS)
    rng.shuffle(o)
    return o, [LETTERS5[o.index(verdict)]], verdict


def _ref(r):
    v = G.verse_ref(r)
    return " (%s)" % v if v else ""


def _dash(r):
    v = G.verse_ref(r)
    return " — %s" % v if v else ""


# ---------- verse_subject -------------------------------------------------
def rend_verse_subject(f, ctx, em, rng):
    r, made = f["chunk"], 0
    dis = ctx["other_headings"](f["answer"], 3, r["sthana"])
    if dis:
        opts, L = shuffled([f["answer"]], dis, rng, 4)
        if opts:
            made += em.add(f, TYPE_MCQ, "verse_to_subject",
                "Read the following verse from %s%s:\n\n%s\n\nWhich subject does this verse deal with?"
                % (r["book"], _ref(r), r["sanskrit"]), opts, L, f["answer"], "Medium",
                "The verse %s concerns: %s." % (G.verse_ref(r) or "cited above", f["answer"]),
                "shloka_to_meaning", context=r["sanskrit"])
    # cloze on the verse itself
    toks = [t.strip("।॥|().,;:'\"") for t in r["sanskrit"].split()]
    toks = [t for t in toks if 4 <= len(t) <= 16 and G.DEVA.match(t)
            and not re.search(r"[^ऀ-ॿ‌‍]", t)]
    if len(toks) >= 4:
        tgt = rng.choice(toks)
        pool = [t for t in ctx["deva_pool"] if t != tgt and abs(len(t) - len(tgt)) <= 4]
        if len(pool) >= 3:
            opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
            if opts:
                made += em.add(f, TYPE_FIB, "verse_cloze",
                    "Fill in the blank in this verse from %s%s:\n\n%s"
                    % (r["book"], _ref(r), re.sub(re.escape(tgt), "________", r["sanskrit"], count=1)),
                    opts, L, tgt, "Medium", "The complete verse reads: %s" % r["sanskrit"],
                    "shloka_to_meaning", context="")
    made += rend_verse_book(f, ctx, em, rng)
    # open-ended exposition
    if r["commentary"]:
        made += em.add(f, TYPE_ASR, "verse_exposition",
            "Explain the meaning of the following verse from %s%s:\n\n%s" % (r["book"], _ref(r), r["sanskrit"]),
            [], [], r["commentary"],
            "Hard" if len(r["commentary"]) > 800 else "Medium",
            "Answer as given by the commentary on %s." % (G.verse_ref(r) or r["chunk_id"]),
            "shloka_to_meaning", context=r["sanskrit"])
    return made


# ---------- statement -----------------------------------------------------
def rend_statement(f, ctx, em, rng):
    r, made = f["chunk"], 0
    stmt = f["answer"]
    dis = [G.shorten(s, 200) for s in ctx["other_sentences"](r["chunk_id"], 3,
                                                             r["primary_category"],
                                                             (r["sthana"], r["chapter_number"]))]
    if len(dis) >= 3:
        opts, L = shuffled([stmt], dis, rng, 4)
        if opts:
            subj = f["subject"] if f["subject"] and G._shares_content_word(f["subject"], stmt) else ""
            stem = ("According to %s%s, which of the following statements regarding \"%s\" is correct?"
                    % (r["book"], _ref(r), subj)) if subj else \
                   ("Which of the following statements is in accordance with %s%s?" % (r["book"], _ref(r)))
            made += em.add(f, TYPE_MCQ, "statement_correct", stem, opts, L, stmt,
                           "Hard" if len(r["commentary"]) > 900 else "Medium",
                           "The commentary on %s states: %s" % (G.verse_ref(r) or r["chunk_id"], stmt),
                           "commentary_clinical", context=r["sanskrit"])
    # cloze on a technical term inside the statement
    ev = f["evidence"]
    cand = [t for t in G.extract_terms(ev) if len(t) >= 5 and t in ctx["term_set"]]
    if cand:
        tgt = rng.choice(cand)
        pool = [t for t in ctx["term_list"] if t != tgt and abs(len(t) - len(tgt)) <= 6]
        if len(pool) >= 3:
            opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
            if opts:
                made += em.add(f, TYPE_FIB, "statement_cloze",
                    "Fill in the blank (from %s%s):\n\n%s" % (r["book"], _dash(r),
                        re.sub(r"\b%s\b" % re.escape(tgt), "________", ev, count=1)),
                    opts, L, tgt, "Easy", "The original statement is: %s" % ev,
                    "term_recall", context="")
    if len(cand) >= 2:
        t2 = [t for t in cand if t != cand[0]]
        if t2:
            tgt2 = rng.choice(t2)
            pool2 = [t for t in ctx["term_list"] if t != tgt2 and abs(len(t) - len(tgt2)) <= 6]
            if len(pool2) >= 3:
                o2, L2 = shuffled([tgt2], rng.sample(pool2, 3), rng, 4)
                if o2:
                    made += em.add(f, TYPE_FIB, "statement_cloze_2",
                        "Complete the following statement from %s%s:\n\n%s"
                        % (r["book"], _dash(r),
                           re.sub(r"\b%s\b" % re.escape(tgt2), "________", ev, count=1)),
                        o2, L2, tgt2, "Easy", "The original statement is: %s" % ev,
                        "term_recall", context="")

    # true / false
    if rng.random() < 0.5:
        made += em.add(f, TYPE_ASR, "true_false",
            "State whether the following statement based on %s%s is TRUE or FALSE.\n\n%s"
            % (r["book"], _dash(r), ev),
*_tf(rng, "True"),
            "Medium", "This is faithful to the commentary on %s." % (G.verse_ref(r) or r["chunk_id"]),
            "commentary_clinical", context="")
    else:
        bad, why = G.falsify(ev, ctx["term_set"], rng)
        if bad and G.norm_ws(bad) != G.norm_ws(ev):
            made += em.add(f, TYPE_ASR, "true_false",
                "State whether the following statement based on %s%s is TRUE or FALSE.\n\n%s"
                % (r["book"], _dash(r), bad),
    *_tf(rng, "False"),
                "Medium", "The original text states: \"%s\" (%s)." % (ev, why),
                "commentary_clinical", context="")
    return made


# ---------- term ----------------------------------------------------------
def rend_term(f, ctx, em, rng):
    r, made = f["chunk"], 0
    tgt = f["answer"]
    tl = tgt.lower()
    pool = [t for t, low in ctx["term_lower"] if t != tgt and tl not in low and low not in tl]
    if len(pool) < 3:
        return 0
    body = re.sub(r"\b%s\b" % re.escape(tgt), "[X]", G.shorten(r["commentary"], 320))
    if "[X]" in body:
        opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
        if opts:
            made += em.add(f, TYPE_MCQ, "masked_term",
                "In the following passage from %s%s, the term [X] has been masked. Which term is it?\n\n%s"
                % (r["book"], _dash(r), body), opts, L, tgt, "Medium",
                "The masked term is %s." % tgt, "term_recall", context="")
    ev = f["evidence"]
    if ev and re.search(r"\b%s\b" % re.escape(tgt), ev):
        opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
        if opts:
            made += em.add(f, TYPE_FIB, "term_cloze",
                "Fill in the blank (from %s%s):\n\n%s" % (r["book"], _dash(r),
                    re.sub(r"\b%s\b" % re.escape(tgt), "________", ev, count=1)),
                opts, L, tgt, "Easy", "The original statement is: %s" % ev,
                "term_recall", context="")
    return made


# ---------- count ---------------------------------------------------------
def rend_count(f, ctx, em, rng):
    r, made = f["chunk"], 0
    val = int(f["answer"])
    cands = [c for c in sorted({val + d for d in (-3, -2, -1, 1, 2, 3, 4, 5)} - {val}) if c >= 1]
    if len(cands) < 3:
        return 0
    opts, L = shuffled([str(val)], [str(c) for c in rng.sample(cands, 3)], rng, 4)
    if opts:
        made += em.add(f, TYPE_MCQ, "enumeration_count",
            "According to %s%s, how many %s are described?" % (r["book"], _dash(r), f["subject"]),
            opts, L, str(val), "Medium", "The text states: \"%s ...\"" % G.shorten(f["evidence"], 160),
            "commentary_clinical", context="")
    made += em.add(f, TYPE_FIB, "count_cloze",
        "Fill in the blank (from %s%s):\n\nThe number of %s described is ________."
        % (r["book"], _dash(r), f["subject"]),
        opts or [], L or [], str(val), "Easy",
        "The text states: \"%s ...\"" % G.shorten(f["evidence"], 160),
        "commentary_clinical", context="") if opts else 0
    return made


# ---------- synonym_set / enumeration  -> multiple selection --------------
def _multi(f, ctx, em, rng, stem, variant, grounding, expl, difficulty):
    """2-3 correct of 5."""
    items = f["answer"]
    own = {t.lower() for t in items}
    pool = [t for t in ctx["item_pool"] if t.lower() not in own]
    if len(pool) < 3 or len(items) < 2:
        return 0
    k = min(3, max(2, min(len(items), rng.choice([2, 3]))))
    correct = rng.sample(items, k)
    dis = rng.sample(pool, 5 - k)
    opts, L = shuffled(correct, dis, rng, 5)
    if not opts:
        return 0
    return em.add(f, TYPE_MS, variant, stem, opts, L, MS_SEP.join(correct),
                  difficulty, expl, grounding, context="")


def rend_synonym_set(f, ctx, em, rng):
    r, made = f["chunk"], 0
    items = f["answer"]
    made += _multi(f, ctx, em, rng,
        "According to the %s, which of the following are synonyms (paryāya) of %s?\n"
        "Select ALL that apply." % (r["book"], f["subject"]),
        "synonyms_multi", "term_recall",
        "Synonyms listed in the text: %s." % ", ".join(items), "Medium")
    # single-answer variant of the same fact
    own = {t.lower() for t in items}
    pool = [t for t in ctx["item_pool"] if t.lower() not in own]
    if len(pool) >= 3:
        opts, L = shuffled([rng.choice(items)], rng.sample(pool, 3), rng, 4)
        if opts:
            made += em.add(f, TYPE_MCQ, "synonym_single",
                "According to the %s, which of the following is a synonym (paryāya) of %s?"
                % (r["book"], f["subject"]), opts, L, opts[LETTERS5.index(L[0])], "Medium",
                "Synonyms listed in the text: %s." % ", ".join(items), "term_recall", context="")
    return made


def rend_enumeration(f, ctx, em, rng):
    r, made = f["chunk"], 0
    items = f["answer"]
    made += _multi(f, ctx, em, rng,
        "According to %s%s, which of the following are among the %s?\nSelect ALL that apply."
        % (r["book"], _dash(r), f["subject"]),
        "enumeration_multi", "commentary_clinical",
        "The text lists: %s." % ", ".join(items), "Hard")
    own = {t.lower() for t in items}
    pool = [t for t in ctx["item_pool"] if t.lower() not in own]
    if len(pool) >= 3:
        opts, L = shuffled([rng.choice(items)], rng.sample(pool, 3), rng, 4)
        if opts:
            made += em.add(f, TYPE_MCQ, "enumeration_single",
                "According to %s%s, which of the following is among the %s?"
                % (r["book"], _dash(r), f["subject"]), opts, L,
                opts[LETTERS5.index(L[0])], "Medium",
                "The text lists: %s." % ", ".join(items), "commentary_clinical", context="")
    return made


# ---------- location ------------------------------------------------------
def rend_location(f, ctx, em, rng):
    r, made = f["chunk"], 0
    if len(ctx["sthanas"]) >= 4:
        dis = [s for s in ctx["sthanas"] if s != r["sthana"]]
        if len(dis) >= 3:
            opts, L = shuffled([r["sthana"]], rng.sample(dis, 3), rng, 4)
            if opts:
                made += em.add(f, TYPE_MCQ, "locate_sthana",
                    "In which sthana (section) of the %s is \"%s\" described?" % (r["book"], f["subject"]),
                    opts, L, r["sthana"], "Easy",
                    "%s is dealt with in the %s." % (f["subject"], r["sthana"]),
                    "concept_to_source", context="")
    same = [c for c in ctx["chapters"] if c[0] == r["sthana"] and c[2] and c[1] != r["chapter_number"]]
    if len(same) >= 3 and r["chapter_title"]:
        opts, L = shuffled([r["chapter_title"]], [c[2] for c in rng.sample(same, 3)], rng, 4)
        if opts:
            made += em.add(f, TYPE_MCQ, "locate_chapter",
                "\"%s\" is expounded in which chapter of the %s (%s)?"
                % (f["subject"], r["book"], r["sthana"]), opts, L, r["chapter_title"], "Medium",
                "It appears in %s." % r["chapter_title"], "concept_to_source", context="")
    same = ctx["headings_by_sthana"].get(r["sthana"], [])
    other = ctx["headings_other_sthana"].get(r["sthana"], [])
    if len(same) >= 3 and len(other) >= 3:
        k = rng.choice([2, 3])
        pool_same = [h for h in same if h != f["subject"]]
        if len(pool_same) >= k - 1 and len(other) >= 5 - k:
            correct = [f["subject"]] + rng.sample(pool_same, k - 1)
            opts, L = shuffled(correct, rng.sample(other, 5 - k), rng, 5)
            if opts:
                made += em.add(f, TYPE_MS, "topics_in_sthana",
                    "Which of the following topics are treated in the %s of the %s?\n"
                    "Select ALL that apply." % (r["sthana"], r["book"]),
                    opts, L, MS_SEP.join(correct), "Hard",
                    "These topics belong to the %s." % r["sthana"],
                    "concept_to_source", context="")

    made += em.add(f, TYPE_ASR, "one_line_source",
        "Name the sthana and chapter of the %s in which \"%s\" is described." % (r["book"], f["subject"]),
        [], [], "%s%s" % (r["sthana"], ", Chapter %s" % r["chapter_number"] if r["chapter_number"] else ""),
        "Easy", "Provenance of passage %s." % r["chunk_id"], "concept_to_source", context="")
    return made


def rend_evidence(f, ctx, em, rng):
    """Soft-filter sentences: cloze and true/false only, never a standalone option."""
    r, made = f["chunk"], 0
    ev = f["evidence"]
    cand = [t for t in G.extract_terms(ev) if len(t) >= 5 and t in ctx["term_set"]]
    if cand:
        tgt = rng.choice(cand)
        pool = [t for t in ctx["term_list"] if t != tgt and abs(len(t) - len(tgt)) <= 6]
        if len(pool) >= 3:
            opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
            if opts:
                made += em.add(f, TYPE_FIB, "evidence_cloze",
                    "Fill in the blank (from %s%s):\n\n%s" % (r["book"], _dash(r),
                        re.sub(r"\b%s\b" % re.escape(tgt), "________", ev, count=1)),
                    opts, L, tgt, "Easy", "The original statement is: %s" % ev,
                    "term_recall", context="")
    bad, why = G.falsify(ev, ctx["term_set"], rng)
    if bad and G.norm_ws(bad) != G.norm_ws(ev):
        made += em.add(f, TYPE_ASR, "true_false",
            "State whether the following statement based on %s%s is TRUE or FALSE.\n\n%s"
            % (r["book"], _dash(r), bad),
*_tf(rng, "False"),
            "Medium", "The original text states: \"%s\" (%s)." % (ev, why),
            "commentary_clinical", context="")
    return made


def rend_statement_set(f, ctx, em, rng):
    """Multiple selection over the chunk's own statements, plus a NOT-stated MCQ."""
    made = rend_not_stated(f, ctx, em, rng)
    r = f["chunk"]
    items = f["answer"]
    if len(items) < 2:
        return 0
    dis = [G.shorten(x, 150) for x in ctx["other_sentences"](r["chunk_id"], 3,
                                                             r["primary_category"],
                                                             (r["sthana"], r["chapter_number"]))]
    if len(dis) < 3:
        return made
    k = min(3, max(2, min(len(items), rng.choice([2, 3]))))
    correct = rng.sample(items, k)
    opts, L = shuffled(correct, dis[:5 - k], rng, 5)
    if not opts:
        return made
    subj = f["subject"] or (r["chapter_title"] or r["sthana"])
    made += _multi_negative(f, ctx, em, rng, [G.shorten(x, 150) for x in
            ctx["other_sentences"](r["chunk_id"], 4, r["primary_category"],
                                   (r["sthana"], r["chapter_number"]))],
        "Which of the following statements do NOT occur in %s%s in connection with \"%s\"?\n"
        "Select ALL that apply." % (r["book"], _dash(r), f["subject"] or r["sthana"]),
        "statements_multi_negative", "commentary_clinical",
        "The remaining options are drawn from the commentary on %s."
        % (G.verse_ref(r) or r["chunk_id"]), "Hard")
    return made + em.add(f, TYPE_MS, "statements_multi",
        "Which of the following statements occur in %s%s in connection with \"%s\"?\n"
        "Select ALL that apply." % (r["book"], _dash(r), subj),
        opts, L, MS_SEP.join(correct), "Hard",
        "These statements are drawn from the commentary on %s." % (G.verse_ref(r) or r["chunk_id"]),
        "commentary_clinical", context="")


IAST_TOK = re.compile(r"^[a-zA-ZĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’]{4,18}$")


def rend_translit(f, ctx, em, rng):
    r, made = f["chunk"], 0
    # cloze on the romanised verse - tests the same recall as the Devanagari cloze
    # but without depending on Devanagari rendering
    toks = [t.strip("|।॥.,;:()") for t in (r["translit"] or "").split()]
    toks = [t for t in toks if IAST_TOK.match(t)]
    if len(toks) >= 4:
        tgt = rng.choice(toks)
        pool = [t for t in ctx["translit_tokens"] if t != tgt and abs(len(t) - len(tgt)) <= 4]
        if len(pool) >= 3:
            opts, L = shuffled([tgt], rng.sample(pool, 3), rng, 4)
            if opts:
                made += em.add(f, TYPE_FIB, "translit_cloze",
                    "Fill in the blank in this transliterated verse from %s%s:\n\n%s"
                    % (r["book"], _ref(r),
                       re.sub(re.escape(tgt), "________", r["translit"], count=1)),
                    opts, L, tgt, "Medium",
                    "The complete transliteration reads: %s" % r["translit"],
                    "shloka_to_meaning", context="")
    pool = [x for x in ctx["translit_pool"] if x != f["answer"]]
    if len(pool) < 3:
        return made
    opts, L = shuffled([f["answer"]], rng.sample(pool, 3), rng, 4)
    if not opts:
        return made
    return made + em.add(f, TYPE_MCQ, "verse_to_translit",
        "Which of the following is the correct transliteration of this verse from %s%s?\n\n%s"
        % (r["book"], _ref(r), r["sanskrit"]), opts, L, f["answer"], "Medium",
        "Transliteration as given in the source.", "shloka_to_meaning", context="")


def rend_term_set(f, ctx, em, rng):
    r = f["chunk"]
    items = f["answer"]
    own = {t.lower() for t in items}
    pool = [t for t, low in ctx["term_lower"] if low not in own]
    if len(pool) < 3 or len(items) < 2:
        return 0
    k = min(3, max(2, rng.choice([2, 3])))
    if len(items) < k:
        return 0
    correct = rng.sample(items, k)
    opts, L = shuffled(correct, rng.sample(pool, 5 - k), rng, 5)
    if not opts:
        return 0
    subj = f["subject"] or (r["chapter_title"] or r["sthana"])
    made = _multi_negative(f, ctx, em, rng, ctx["term_list"],
        "Which of the following terms do NOT occur in the passage of %s%s dealing with \"%s\"?\n"
        "Select ALL that apply." % (r["book"], _dash(r), f["subject"] or r["sthana"]),
        "terms_multi_negative", "term_recall",
        "Terms actually present: %s." % ", ".join(items), "Hard")
    return made + em.add(f, TYPE_MS, "terms_multi",
        "Which of the following terms occur in the passage of %s%s dealing with \"%s\"?\n"
        "Select ALL that apply." % (r["book"], _dash(r), subj),
        opts, L, MS_SEP.join(correct), "Medium",
        "Terms present in the passage: %s." % ", ".join(items), "term_recall", context="")


def rend_not_stated(f, ctx, em, rng):
    """Which of these is NOT stated here - correct answer is the foreign sentence."""
    r = f["chunk"]
    own = f["answer"]
    if len(own) < 3:
        return 0
    foreign = ctx["other_sentences"](r["chunk_id"], 1, r["primary_category"],
                                     (r["sthana"], r["chapter_number"]))
    if not foreign:
        return 0
    alien = G.shorten(foreign[0], 150)
    opts, L = shuffled([alien], rng.sample(own, 3), rng, 4)
    if not opts:
        return 0
    subj = f["subject"] or (r["chapter_title"] or r["sthana"])
    return em.add(f, TYPE_MCQ, "not_stated",
        "Which of the following is NOT stated in %s%s in connection with \"%s\"?"
        % (r["book"], _dash(r), subj), opts, L, alien, "Hard",
        "The other three options are drawn from the commentary on %s; this one is not."
        % (G.verse_ref(r) or r["chunk_id"]), "commentary_clinical", context="")


def rend_verse_book(f, ctx, em, rng):
    """Which classical text does this verse belong to?"""
    r = f["chunk"]
    if not r["sanskrit"] or len(r["sanskrit"]) < 30:
        return 0
    others = [b for b in ctx["all_books"] if b != r["book"]]
    if len(others) < 3:
        return 0
    opts, L = shuffled([r["book"]], rng.sample(others, 3), rng, 4)
    if not opts:
        return 0
    return em.add(f, TYPE_MCQ, "verse_to_book",
        "The following verse is drawn from which classical text?\n\n%s" % r["sanskrit"],
        opts, L, r["book"], "Medium",
        "It appears in %s." % G.citation(r), "concept_to_source", context="")


def rend_raw(f, ctx, em, rng):
    r, made = f["chunk"], 0
    if r["sanskrit"] and len(r["sanskrit"]) >= 15:
        made += em.add(f, TYPE_ASR, "transliterate_and_explain",
            "Transliterate and give the contextual import of the following line from %s%s:\n\n%s"
            % (r["book"], _dash(r), r["sanskrit"]), [], [],
            (r["translit"] + ("  —  " if r["translit"] and r["commentary"] else "") + r["commentary"]).strip()
            or r["translit"] or r["sanskrit"],
            "Easy", "Verse and its rendering as given in the source.",
            "shloka_to_meaning", context="")
    elif r["commentary"]:
        made += em.add(f, TYPE_ASR, "direct_recall",
            "What does %s state under \"%s\"?" % (r["book"], f["subject"] or r["sthana"]),
            [], [], r["commentary"], "Easy", "Direct statement of the source text.",
            "commentary_clinical", context="")
    return made


def _multi_negative(f, ctx, em, rng, pool, stem, variant, grounding, expl, difficulty):
    """Select-all over items that do NOT belong - correct answers come from the pool."""
    items = f["answer"]
    own = {t.lower() for t in items}
    outside = [t for t in pool if t.lower() not in own]
    if len(outside) < 3 or len(items) < 2:
        return 0
    k = rng.choice([2, 3])
    if len(outside) < k or len(items) < 5 - k:
        return 0
    correct = rng.sample(outside, k)
    keep = rng.sample(items, 5 - k)
    opts, L = shuffled(correct, keep, rng, 5)
    if not opts:
        return 0
    return em.add(f, TYPE_MS, variant, stem, opts, L, MS_SEP.join(correct),
                  difficulty, expl, grounding, context="")


RENDERERS = {
    "verse_subject": rend_verse_subject,
    "raw":           rend_raw,
    "term_set":      rend_term_set,
    "evidence":      rend_evidence,
    "statement_set": rend_statement_set,
    "translit":      rend_translit,
    "statement":     rend_statement,
    "term":          rend_term,
    "count":         rend_count,
    "synonym_set":   rend_synonym_set,
    "enumeration":   rend_enumeration,
    "location":      rend_location,
}


# ==========================================================================
# Cross-fact formats: assertion-reason and match-the-column
# ==========================================================================
def rend_assertion(f, ctx, em, rng, case):
    """Pair this fact's statement with a reason. case cycles the 4 verdicts."""
    r = f["chunk"]
    a = f["evidence"]
    if not G.good_sentence(a, 50, 260):
        return 0
    sents = [s for s in G.split_sentences(r["commentary"]) if G.good_sentence(s, 50, 260)]

    def emit(A, B, key, expl, variant):
        o = list(AR_OPTIONS)
        rng.shuffle(o)
        return em.add(f, TYPE_AR, variant,
            "Given below are two statements based on %s%s.\n\nAssertion (A): %s\nReason (R): %s\n\n"
            "In the light of the above statements, choose the correct answer:"
            % (r["book"], _dash(r), G.shorten(A, 240), G.shorten(B, 240)),
            o, [LETTERS5[o.index(key)]], key, "Hard", expl, "commentary_clinical")

    for c in [case] + [x for x in (0, 2, 3, 1) if x != case]:
        if c == 0:
            nxt = next((s for i, s in enumerate(sents)
                        if i and sents[i - 1] == a and EXPLANATORY.search(s)), None)
            if nxt and emit(a, nxt, AR_OPTIONS[0],
                            "Both come from the commentary on %s and the reason accounts for the "
                            "assertion." % (G.verse_ref(r) or r["chunk_id"]), "R_explains_A"):
                return 1
        elif c == 1:
            b = None
            for _ in range(30):
                s, cat, cid, ck = ctx["sent_pool"][rng.randrange(len(ctx["sent_pool"]))]
                if cid != r["chunk_id"] and cat != r["primary_category"] and G.good_sentence(s, 50, 240):
                    b = s
                    break
            if b and emit(a, b, AR_OPTIONS[1],
                          "Both are authentic teachings of the %s, but the reason belongs to a "
                          "different topic." % r["book"], "both_true_unrelated"):
                return 1
        else:
            bad, why = G.falsify(rng.choice(sents) if sents else a, ctx["term_set"], rng)
            if bad and G.norm_ws(bad) != G.norm_ws(a):
                if c == 2 and emit(a, bad, AR_OPTIONS[2],
                                   "The assertion is authentic; the reason is distorted (%s)." % why,
                                   "A_true_R_false"):
                    return 1
                if c == 3 and emit(bad, a, AR_OPTIONS[3],
                                   "The assertion is distorted (%s); the reason is authentic." % why,
                                   "A_false_R_true"):
                    return 1
    return 0


ROMAN = ["i", "ii", "iii", "iv"]
LOW = ["a", "b", "c", "d"]


_MTC_CACHE = {}


def _mtc_parts(r, mode):
    """Cached (label, description) for a chunk - the sentence split is expensive
    and each chunk appears in many candidate groups."""
    key = (id(r), mode)
    if key in _MTC_CACHE:
        return _MTC_CACHE[key]
    h = G.clean_heading(r["topic_heading"])
    out = None
    if G.good_heading(h) and G._mtc_label_ok(h):
        if mode == "ref":
            d = G.verse_ref(r)
            out = (h, d) if (d and r["chapter_number"]) else None
        else:
            d = ""
            for s in G.split_sentences(r["commentary"]):
                if not G.good_sentence(s, 40, 240):
                    continue
                if s.lower().startswith(h.lower()[:20]) or h.lower().startswith(s.lower()[:20]):
                    continue
                d = G.shorten(s, 130)
                break
            out = (h, d) if d else None
    _MTC_CACHE[key] = out
    return out


def rend_match(group, em, rng, mode):
    """group: 4 facts. mode 'desc' pairs topic->description, 'ref' topic->location."""
    items = []
    for f in group:
        r = f["chunk"]
        parts = _mtc_parts(r, mode)
        if not parts:
            return 0
        h, d = parts
        items.append((h, d, r))
    if len({d for _, d, _ in items}) != 4 or len({h for h, _, _ in items}) != 4:
        return 0

    perm = list(range(4))
    rng.shuffle(perm)
    if perm == list(range(4)):
        perm = [1, 0, 3, 2]
    colB = [items[perm[j]][1] for j in range(4)]
    pos = {perm[j]: j for j in range(4)}
    correct = ", ".join("%s-%s" % (ROMAN[i], LOW[pos[i]]) for i in range(4))
    wrong, tries = set(), 0
    while len(wrong) < 3 and tries < 60:
        tries += 1
        alt = list(range(4))
        rng.shuffle(alt)
        cand = ", ".join("%s-%s" % (ROMAN[i], LOW[alt[i]]) for i in range(4))
        if cand != correct:
            wrong.add(cand)
    if len(wrong) < 3:
        return 0
    opts, L = shuffled([correct], sorted(wrong), rng, 4)
    if not opts:
        return 0
    r0 = group[0]["chunk"]
    head = ("Match each topic in Column A with the place in the %s where it is expounded (Column B):"
            % r0["book"]) if mode == "ref" else \
           ("Match the items in Column A with their correct descriptions in Column B (from %s%s):"
            % (r0["book"], " — " + r0["sthana"] if r0["sthana"] else ""))
    lines = [head, "", "Column A"] + ["(%s) %s" % (ROMAN[i], items[i][0]) for i in range(4)] + \
            ["", "Column B"] + ["(%s) %s" % (LOW[j], colB[j]) for j in range(4)] + \
            ["", "Select the correct match:"]
    return em.add(group[0], TYPE_MTC,
                  "topic_to_reference" if mode == "ref" else "four_pair",
                  "\n".join(lines), opts, L, correct, "Hard",
                  "Correct pairing: " + "; ".join(
                      "%s (%s) -> %s" % (ROMAN[i], items[i][0], LOW[pos[i]]) for i in range(4)),
                  "concept_to_source", context="")


# ==========================================================================
# Per-book driver
# ==========================================================================
def build_book(recs, code, rng):
    em = Emitter()

    headings = {}
    for r in recs:
        h = G.clean_heading(r["topic_heading"])
        if G.good_heading(h):
            headings.setdefault(h, r)
    heading_list = list(headings)
    by_sthana_h = defaultdict(list)
    for h in heading_list:
        by_sthana_h[headings[h]["sthana"]].append(h)

    sthanas = sorted({r["sthana"] for r in recs if r["sthana"]})
    chapters = sorted({(r["sthana"], r["chapter_number"], r["chapter_title"])
                       for r in recs if r["chapter_title"]})

    term_set = set()
    for r in recs:
        term_set |= G.extract_terms(r["commentary"]) | G.extract_terms(r["topic_heading"])
    term_set = {t for t in term_set if 4 <= len(t) <= 22}
    term_list = sorted(term_set)

    deva_pool = []
    for r in recs:
        for t in r["sanskrit"].split():
            t = re.sub(r"[०-९\d]+", "", t.strip("।॥|().,;:'\""))
            if 4 <= len(t) <= 16 and G.DEVA.match(t) and not re.search(r"[^ऀ-ॿ‌‍]", t):
                deva_pool.append(t)
    deva_pool = list(dict.fromkeys(deva_pool))

    sent_pool = []
    for r in recs:
        ck = (r["sthana"], r["chapter_number"])
        for s in G.split_sentences(r["commentary"]):
            if G.good_sentence(s):
                sent_pool.append((s, r["primary_category"], r["chunk_id"], ck))
    sent_by_cat = defaultdict(list)
    for s, c, cid, ck in sent_pool:
        sent_by_cat[c].append((s, cid, ck))
    sent_all = [(s, cid, ck) for s, c, cid, ck in sent_pool]

    def pick(pool, n, reject):
        if not pool:
            return []
        out, seen, tries = [], set(), 0
        while len(out) < n and tries < max(30, n * 8):
            tries += 1
            it = pool[rng.randrange(len(pool))]
            k = it[0] if isinstance(it, tuple) else it
            if k in seen or reject(it):
                continue
            seen.add(k)
            out.append(k)
        return out if len(out) == n else []

    def other_headings(excl, n=3, sth=None):
        p = by_sthana_h.get(sth) or heading_list
        if len(p) < n + 1:
            p = heading_list
        return pick(p, n, lambda h: h == excl) if len(p) >= n + 1 else []

    def other_sentences(excl_chunk, n=3, cat=None, excl_ch=None):
        p = sent_by_cat.get(cat) or []
        if len(p) < n + 6:
            p = sent_all
        if len(p) < n + 1:
            return []
        out = pick(p, n, lambda it: it[1] == excl_chunk or (excl_ch and it[2] == excl_ch))
        return out or pick(p, n, lambda it: it[1] == excl_chunk)

    # all facts, so multi-select distractors can be drawn book-wide
    all_facts = []
    for r in recs:
        all_facts.extend(make_facts(r, rng))
    item_pool = []
    for f in all_facts:
        if f["kind"] in ("synonym_set", "enumeration"):
            item_pool.extend(f["answer"])
    item_pool = list(dict.fromkeys(item_pool))

    translit_tokens = []
    for r in recs:
        for t in (r["translit"] or "").split():
            t = t.strip("|।॥.,;:()")
            if IAST_TOK.match(t):
                translit_tokens.append(t)
    translit_tokens = list(dict.fromkeys(translit_tokens))

    translit_pool = list(dict.fromkeys(
        G.shorten(r["translit"], 200) for r in recs
        if r["translit"] and len(r["translit"]) >= 25))

    headings_other_sthana = {sth: [h for k, hs in by_sthana_h.items() if k != sth for h in hs]
                             for sth in by_sthana_h}

    term_lower = [(t, t.lower()) for t in term_list]

    ctx = {"translit_tokens": translit_tokens, "term_lower": term_lower, "headings_by_sthana": by_sthana_h, "headings_other_sthana": headings_other_sthana,
           "all_books": [b for _, b, _ in BOOKS], "translit_pool": translit_pool, "other_headings": other_headings, "other_sentences": other_sentences,
           "term_set": term_set, "term_list": term_list, "deva_pool": deva_pool,
           "sent_pool": sent_pool, "sthanas": sthanas, "chapters": chapters,
           "item_pool": item_pool}

    for f in all_facts:
        RENDERERS[f["kind"]](f, ctx, em, rng)

    stmt_facts = [f for f in all_facts if f["kind"] in ("statement", "evidence")]
    for i, f in enumerate(stmt_facts):
        if len(f["chunk"]["commentary"]) >= 240:
            rend_assertion(f, ctx, em, rng, i % 4)

    subj_facts = [f for f in all_facts if f["kind"] in ("verse_subject", "location")]
    by_ch = defaultdict(list)
    by_sth = defaultdict(list)
    for f in subj_facts:
        by_ch[(f["chunk"]["sthana"], f["chunk"]["chapter_number"])].append(f)
        by_sth[f["chunk"]["sthana"]].append(f)
    groups = []
    for g in by_ch.values():
        for i in range(0, len(g) - 3, 4):
            groups.append(g[i:i + 4])
    for _ in range(12):
        for g in by_sth.values():
            g = list(g)
            rng.shuffle(g)
            for i in range(0, len(g) - 3, 4):
                groups.append(g[i:i + 4])
    rng.shuffle(groups)
    cap_attempts = 2500 if len(recs) > 1000 else MTC_ATTEMPT_CAP
    made_mtc, attempts = 0, 0
    for g in groups:
        if made_mtc >= MTC_CAP or attempts >= cap_attempts:
            break
        attempts += 1
        if rend_match(g, em, rng, "desc"):
            made_mtc += 1
        elif rend_match(g, em, rng, "ref"):
            made_mtc += 1

    return em.rows, len(all_facts)


# ==========================================================================
# Selection to exactly TARGET_TOTAL + IO
# ==========================================================================
def select(rows, target, seed=SEED):
    """Trim to `target` rows: guarantee one per chunk, then fill toward TARGET_MIX,
    preferring richer source material."""
    rng = random.Random(seed)
    if len(rows) <= target:
        return rows, "kept all (%d available)" % len(rows)

    by_chunk = defaultdict(list)
    for r in rows:
        by_chunk[(r["source_book"], r["chunk_id"])].append(r)

    kept, kept_ids = [], set()
    for k in sorted(by_chunk):
        best = max(by_chunk[k], key=lambda r: (r["question_type"] == TYPE_MCQ, r["source_richness"]))
        kept.append(best)
        kept_ids.add(best["question_id"] + "|" + best["source_book"])

    rest = [r for r in rows if (r["question_id"] + "|" + r["source_book"]) not in kept_ids]
    quota = {t: int(TARGET_MIX[t] * target) for t in TARGET_MIX}
    have = Counter(r["question_type"] for r in kept)

    pools = defaultdict(list)
    for r in rest:
        pools[r["question_type"]].append(r)
    for t in pools:
        rng.shuffle(pools[t])
        pools[t].sort(key=lambda r: -r["source_richness"])

    for t in sorted(quota, key=lambda t: -quota[t]):
        need = max(0, quota[t] - have.get(t, 0))
        take = pools[t][:need]
        kept.extend(take)
        pools[t] = pools[t][need:]

    if len(kept) < target:
        left = [r for t in pools for r in pools[t]]
        rng.shuffle(left)
        left.sort(key=lambda r: -r["source_richness"])
        kept.extend(left[:target - len(kept)])
    if len(kept) > target:
        prot = {id(r) for r in kept[:len(by_chunk)]}
        extra = [r for r in kept if id(r) not in prot]
        rng.shuffle(extra)
        drop = {id(r) for r in extra[:len(kept) - target]}
        kept = [r for r in kept if id(r) not in drop]

    rng.shuffle(kept)
    return kept, "selected %d of %d generated" % (len(kept), len(rows))


def outfile(book):
    return os.path.join(BOOK_DIR, "%s_v2.jsonl" % re.sub(r"[^A-Za-z0-9]+", "_", book).strip("_"))


def run_book(code_filter=None):
    os.makedirs(BOOK_DIR, exist_ok=True)
    for fname, book, code in BOOKS:
        if code_filter and code != code_filter:
            continue
        recs = G.load_book(os.path.join(IN_DIR, fname), book, code)
        rng = random.Random(SEED + sum(ord(c) for c in code))
        rows, nfacts = build_book(recs, code, rng)
        with open(outfile(book), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("%-30s chunks=%5d facts=%6d generated=%7d  (%.1f q/chunk)"
              % (book, len(recs), nfacts, len(rows), len(rows) / max(len(recs), 1)))


def combine():
    allrows, seen = [], set()
    for fname, book, code in BOOKS:
        p = outfile(book)
        if not os.path.exists(p):
            print("NOT BUILT:", book)
            continue
        for l in open(p, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            k = hashlib.md5(G.norm_ws(r["question"]).lower().encode("utf-8")).hexdigest()
            if k in seen:
                continue
            seen.add(k)
            allrows.append(r)
    print("generated pool: %d unique stems" % len(allrows))
    kept, note = select(allrows, TARGET_TOTAL)
    print(note)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "ayur_qa_v2_80k.jsonl"), "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # split by fact_id so a fact's variants never straddle train/val
    facts = sorted({r["fact_id"] for r in kept})
    random.Random(SEED).shuffle(facts)
    val_facts = set(facts[:max(1, int(len(facts) * 0.10))])
    train = [r for r in kept if r["fact_id"] not in val_facts]
    val = [r for r in kept if r["fact_id"] in val_facts]
    for name, rr in (("train.jsonl", train), ("validation.jsonl", val)):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            for r in rr:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("train=%d  validation=%d  (split on fact_id, no fact straddles)" % (len(train), len(val)))

    stats = {
        "total": len(kept),
        "by_type": dict(Counter(r["question_type"] for r in kept)),
        "by_variant": dict(Counter(r["format_variant"] for r in kept).most_common()),
        "by_book": dict(Counter(r["source_book"] for r in kept)),
        "by_difficulty": dict(Counter(r["difficulty"] for r in kept)),
        "by_fact_kind": dict(Counter(r["fact_kind"] for r in kept)),
        "distinct_facts": len({r["fact_id"] for r in kept}),
        "distinct_chunks": len({(r["source_book"], r["chunk_id"]) for r in kept}),
        "train": len(train), "validation": len(val),
    }
    with open(os.path.join(OUT_DIR, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=2)
    print(json.dumps(stats["by_type"], indent=2))


if __name__ == "__main__":
    import sys
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    if a == "combine":
        combine()
    elif a == "all":
        run_book()
        combine()
    else:
        run_book(a)
