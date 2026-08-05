#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AyurBench-Shloka question-set generator
=======================================
Builds a BhashaBench-Ayur (BBA) style question set from classical Ayurvedic
shloka + commentary chunk datasets.

Question types produced (matching BBA taxonomy):
  * MCQ
  * Fill in the blanks
  * Match the column
  * Assertion or Reasoning
  * Assorted            (short-answer / descriptive / true-false / one-word)

Grounding strategies (all four requested):
  * shloka_to_meaning     - give the Sanskrit verse, ask what it teaches
  * concept_to_source     - given a teaching, identify text / sthana / chapter
  * commentary_clinical   - lakshana, nidana, chikitsa, dravya facts from commentary
  * term_recall           - paryaya, technical terms, counts, classifications

Only `sanskrit_text`, `transliteration` and `commentary` are used as knowledge
sources. Everything else (chunk_id, sthana, chapter, verse_id, categories) is
carried through as provenance metadata columns.
"""

import json
import os
import re
import random
import hashlib
import unicodedata
from collections import defaultdict, Counter

SEED = 20260728
random.seed(SEED)

IN_DIR = "/sessions/loving-trusting-wright/mnt/uploads"
OUT_DIR = "/sessions/loving-trusting-wright/mnt/outputs/ayur_question_set"
BOOK_DIR = os.path.join(OUT_DIR, "by_book")

# --------------------------------------------------------------------------
# Book registry
# --------------------------------------------------------------------------
BOOKS = [
    # (filename, pretty book name, short code)
    ("FINAL_Charaka_Samhita.jsonl",            "Charaka Samhita",                       "CS"),
    ("FINAL_Sushruta_Samhita.jsonl",           "Sushruta Samhita",                      "SU"),
    ("FINAL_Ashtanga_Hridaya.jsonl",           "Ashtanga Hridaya",                      "AH"),
    ("FINAL_Sharangadhara_Samhita.jsonl",      "Sharangadhara Samhita",                 "SG"),
    ("FINAL_B01_Bhavaprakasha_Nighantu.jsonl", "Bhavaprakasha Nighantu",                "BPN"),
    ("FINAL_B02_Madhavanidanam_Part1.jsonl",   "Madhava Nidanam (Part 1)",              "MN1"),
    ("FINAL_B03_Madhavanidanam_Part2.jsonl",   "Madhava Nidanam (Part 2)",              "MN2"),
    ("FINAL_Madhava_Nidana_LaghuTrayi.jsonl",  "Madhava Nidana (Laghutrayi)",           "MNL"),
]

# --------------------------------------------------------------------------
# Subject-domain mapping (BBA domain labels)
# --------------------------------------------------------------------------
D_KAYA   = "Kayachikitsa (General Medicine & Internal Medicine)"
D_DRAVYA = "Dravyaguna & Bhaishajya (Pharmacology & Therapeutics)"
D_SAMHIT = "Samhita & Siddhanta (Fundamental Principles)"
D_SHARIR = "Sharir (Anatomy & Physiology)"
D_PANCHA = "Panchakarma & Rasayana (Detoxification & Rejuvenation)"
D_STRI   = "Stri Roga & Prasuti Tantra (Gynecology & Obstetrics)"
D_SHALAK = "Shalakya Tantra (ENT, Ophthalmology & Dentistry)"
D_KAUMAR = "Kaumarbhritya & Pediatrics (Child Health)"
D_AGAD   = "Agad Tantra & Forensic Medicine (Toxicology)"
D_SHALYA = "Shalya Tantra (Surgery)"
D_SWASTH = "Swasthavritta & Public Health (Preventive Medicine)"
D_ROGA   = "Roga Vigyana (Diagnostics & Pathology)"
D_LIT    = "Ayurvedic Literature & History"

BOOK_DEFAULT_DOMAIN = {
    "Charaka Samhita":                D_KAYA,
    "Sushruta Samhita":               D_SHALYA,
    "Ashtanga Hridaya":               D_SAMHIT,
    "Sharangadhara Samhita":          D_DRAVYA,
    "Bhavaprakasha Nighantu":         D_DRAVYA,
    "Madhava Nidanam (Part 1)":       D_ROGA,
    "Madhava Nidanam (Part 2)":       D_ROGA,
    "Madhava Nidana (Laghutrayi)":    D_ROGA,
}

STHANA_DOMAIN = [
    (("sutra",),                    D_SAMHIT),
    (("sharir", "sarir", "śārīra", "shaarir"), D_SHARIR),
    (("nidan", "nidān"),            D_ROGA),
    (("chikitsa", "cikitsā", "cikitsa"), D_KAYA),
    (("kalpa", "siddhi"),           D_PANCHA),
    (("uttara",),                   D_SHALAK),
    (("shalya", "śalya"),           D_SHALYA),
    (("varga", "nighantu", "khanda", "khaṇḍa"), D_DRAVYA),
]

CATEGORY_DOMAIN = [
    (("rasayana", "vajikarana", "panchakarma", "vamana", "virechana", "basti",
      "nasya", "raktamokshana", "snehana", "swedana"), D_PANCHA),
    (("dravya", "aushadha", "oushadha", "haritaki", "kalpana", "churna",
      "kwatha", "asava", "arishta", "taila", "ghrita", "rasa_shastra",
      "bhaishajya", "synonym", "guna"), D_DRAVYA),
    (("garbha", "stri", "yoni", "prasuti", "artava", "rajas"), D_STRI),
    (("bala", "kaumar", "shishu", "stanya"), D_KAUMAR),
    (("visha", "vish", "agad", "toxic", "poison", "damsha", "sarpa"), D_AGAD),
    (("netra", "karna", "nasa", "mukha", "danta", "shiro", "shalakya"), D_SHALAK),
    (("vrana", "shastra", "surgery", "bhagna", "arsha", "bhagandara",
      "ashmari", "granthi", "arbuda"), D_SHALYA),
    (("dinacharya", "ritucharya", "sadvritta", "swasthavritta", "ahara",
      "vihara", "pathya", "regimen", "hygiene"), D_SWASTH),
    (("srotas", "dhatu", "marma", "kostha", "anatomy", "physiology",
      "ojas", "agni_sharir"), D_SHARIR),
    (("nidana", "purvarupa", "rupa", "samprapti", "lakshana", "upashaya",
      "arishta", "prognosis", "diagnosis", "roga_pariksha"), D_ROGA),
    (("invocation", "prayer", "purpose", "compilation", "treatise",
      "history", "author", "colophon"), D_LIT),
    (("jvara", "atisara", "grahani", "pandu", "kasa", "shwasa", "prameha",
      "kushtha", "vatavyadhi", "amavata", "gulma", "udara", "shotha",
      "treatment", "disease_treatment", "chikitsa"), D_KAYA),
    (("ayurveda_fundamentals", "dosha", "tridosha", "siddhanta", "general"), D_SAMHIT),
]


def pick_domain(book, sthana, categories, primary):
    blob = " ".join([primary or ""] + list(categories or [])).lower()
    for keys, dom in CATEGORY_DOMAIN:
        if any(k in blob for k in keys):
            return dom
    s = (sthana or "").lower()
    for keys, dom in STHANA_DOMAIN:
        if any(k in s for k in keys):
            return dom
    return BOOK_DEFAULT_DOMAIN.get(book, D_SAMHIT)


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------
DEVA = re.compile(r"[ऀ-ॿ]")
DIACRITIC_CHARS = "āīūṛṝḷḹṅñṭḍṇśṣṃḥṁĀĪŪṚṜḶṄÑṬḌṆŚṢṀḤ"

STOP_CAPS = {
    "The", "This", "That", "These", "Those", "There", "Then", "Thus", "Therefore",
    "Hence", "However", "Here", "It", "Its", "In", "On", "At", "By", "For", "From",
    "With", "Without", "And", "But", "Or", "Also", "So", "Such", "Some", "Both",
    "All", "Any", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "When", "While", "Where", "Which", "Who", "What", "Why", "How",
    "If", "Since", "Because", "According", "As", "After", "Before", "During",
    "Now", "Again", "Further", "Note", "See", "Salutation", "Salutations",
    "Chapter", "Verse", "Section", "Lord", "God", "Sri", "Shri", "First",
    "Second", "Third", "Fourth", "Being", "Having", "They", "He", "She", "We",
    "You", "Their", "His", "Her", "Our", "Thereafter", "Thereby", "Above",
    "Below", "Only", "Even", "Like", "Similarly", "Likewise", "Moreover",
    "Besides", "Otherwise", "Instead", "Meaning", "Means", "Remark", "Text",
    "Translation", "Commentary", "English", "Sanskrit", "Ayurveda", "Ayurvedic",
    "Modern", "Indian", "India", "Latin", "Hindi", "Note:", "Fig", "Table",
}

_ABBR = re.compile(r"\b(?:Ca|Ci|Su|Sū|Ni|Sa|Śa|Ka|Si|Ut|Vi|A|Ch|Adhy|Sth|e\.g|i\.e|Dr|Mr|No|Vol|p|pp|cf|etc|viz)\.$")


def norm_ws(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


# Running heads / page furniture injected by OCR of the printed editions
RUNNING_HEAD = re.compile(
    r"(CARAKA[- ]?SAMHIT[ĀÃĂA][^\s]*|BH[ĀA]VAPRAK[ĀA][ŚS]A\s+NIGHANTU|"
    r"SU[ŚS]RUTA[- ]?SAMHIT[ĀÃĂA][^\s]*|A[ŚS]T[ĀA][NṄ]GA\s+H[ṚR]DAYA[^\s]*|"
    r"[ŚS][ĀA]RA[NṄ]GADHARA[- ]?SAMHIT[ĀÃĂA][^\s]*|M[ĀA]DHAVA\s+NID[ĀA]NA[^\s]*|"
    r"CHAPTER\s+[IVXLC\d]+|SECTION\s+[IVXLC\d]+)",
    re.I)


def clean_commentary(s):
    """Strip OCR page furniture from a commentary string."""
    s = norm_ws(s)
    if not s:
        return ""
    s = RUNNING_HEAD.sub(" ", s)
    s = re.sub(r"\[\s*\d+[^\]]{0,12}\]", " ", s)        # "[ 28 ]", "[1]"
    s = re.sub(r"\(\s*\d{1,3}\s*\)", " ", s)             # "( 5 )"
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)               # " ,"  ->  ","
    s = re.sub(r"([,;:])(?=\S)", r"\1 ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:-—|")


OCR_NOISE = re.compile(r"(\s[,;:]\s|\b[a-z]{1,2}\s[,;]|[A-ZĀĪŪ]{8,})")

# Word inside a word ("TOne", "tookMuch") and long vowel-less runs are OCR tells
CAMEL_GARBLE = re.compile(r"\b\w*[a-z][A-Z]\w*\b|\b[A-Z][a-z]+[A-Z]\w*\b")
NO_VOWEL = re.compile(r"\b[bcdfghjklmnpqrstvwxz]{6,}\b", re.I)


def _load_wordlist():
    words = set()
    for p in ("/usr/share/hunspell/en_US.dic", "/usr/share/dict/words"):
        try:
            with open(p, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    w = line.split("/")[0].strip().lower()
                    if w.isalpha():
                        words.add(w)
        except OSError:
            continue
    return words


ENGLISH_WORDS = _load_wordlist()


def ocr_garbled(s, max_unknown=0.34):
    """Fraction of lowercase alphabetic tokens absent from the English lexicon.

    Sanskrit technical terms are almost always capitalised or diacritic-marked, so a
    high proportion of unknown *lowercase* tokens is a reliable OCR-damage signal.
    """
    if CAMEL_GARBLE.search(s) or NO_VOWEL.search(s):
        return True
    if not ENGLISH_WORDS:
        return False
    toks = [t.strip(".,;:!?()[]'\"’‘-") for t in s.split()]
    cand = [t for t in toks
            if len(t) >= 3 and t.isalpha() and t.islower()
            and not any(c in DIACRITIC_CHARS for c in t)]
    if len(cand) < 6:
        return False
    unknown = sum(1 for t in cand if t not in ENGLISH_WORDS)
    return unknown / len(cand) > max_unknown


def devanagari_garbled(s):
    """Detect broken Devanagari (lost conjuncts / detached vowel signs)."""
    all_toks = s.split()
    toks = [t for t in all_toks if DEVA.search(t)]
    if len(toks) < 5:
        return False
    tiny = sum(1 for t in toks if len(t.strip("।॥|()")) <= 2)
    if tiny / len(toks) > 0.30:
        return True
    # stray latin letters / symbols dropped in by OCR
    junk = sum(1 for t in all_toks if re.fullmatch(r"[/><\\_^~`*=+@#$%&a-zA-Z]{1,3}", t))
    return junk >= 2


def split_sentences(text):
    """Conservative sentence splitter tolerant of IAST + citation abbreviations."""
    text = norm_ws(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;])\s+(?=[A-ZĀĪŪṚṜḶṄÑṬḌṆŚṢṀḤ0-9(])", text)
    out, buf = [], ""
    for p in parts:
        cand = (buf + " " + p).strip() if buf else p
        if _ABBR.search(p.strip()):
            buf = cand
            continue
        buf = ""
        out.append(cand)
    if buf:
        out.append(buf)
    return [norm_ws(s) for s in out if norm_ws(s)]


def good_sentence(s, lo=45, hi=340):
    """Is this sentence usable as a standalone factual statement?"""
    if not (lo <= len(s) <= hi):
        return False
    if DEVA.search(s):
        return False
    words = s.split()
    if len(words) < 8:
        return False
    # reject sentences that start with a dangling pronoun / connector
    if re.match(r"^(It|They|This|These|Those|He|She|Such|Thus|Hence|Therefore|Then|"
                r"Here|There|But|And|Or|Also|However|Moreover|Besides|Now|Again|"
                r"Further|Likewise|Similarly|Otherwise|Instead|So)\b", s):
        return False
    # reject pure page-furniture
    if re.search(r"(see (above|below)|as (stated|said|mentioned) (above|earlier))", s, re.I):
        return False
    letters = sum(c.isalpha() for c in s)
    if letters < 0.55 * len(s):
        return False
    # OCR-damaged text: spaced-out punctuation, stray one-letter tokens, ALLCAPS runs
    if len(OCR_NOISE.findall(s)) >= 2:
        return False
    if RUNNING_HEAD.search(s):
        return False
    toks = s.split()
    stray = sum(1 for t in toks if len(t.strip(".,;:")) == 1 and t.strip(".,;:").lower() not in "ai")
    if stray >= 2:
        return False
    if ocr_garbled(s):
        return False
    return True


def clean_heading(h):
    h = norm_ws(h)
    h = re.sub(r"\s*[:\-–—]\s*$", "", h)
    h = re.sub(r"^\d+\s*[\-–—.)]\s*", "", h)          # "3 - Origin of Ayurveda"
    h = re.sub(r"\s*\[\s*\d+[^\]]*\]\s*$", "", h)      # trailing "[1]"
    h = re.sub(r"\s*\|\|\s*\d+\s*\|\|\s*$", "", h)
    return norm_ws(h)


def good_heading(h):
    """A usable heading is a short NOUN-PHRASE label, not a sentence fragment."""
    h = clean_heading(h)
    if not (8 <= len(h) <= 110):
        return False
    # sentence-like headings make awkward, leaky stems -> reject them
    if re.match(r"^(If|When|While|The|A|An|In|On|By|For|Thus|Hence|Now|After|"
                r"Before|Since|Because|One|It|He|She|They|This|These)\b", h) and len(h.split()) > 7:
        return False
    if re.search(r"[.;]\s", h) or h.endswith((",", ";", "and", "or", "as", "of", "with", "to")):
        return False
    if len(h.split()) > 14:
        return False
    if DEVA.search(h) and len(re.sub(r"[^ऀ-ॿ]", "", h)) > len(h) * 0.6:
        return False
    if re.match(r"^(front matter|title|contents|index|preface|colophon)$", h, re.I):
        return False
    # bare locators ("Verse 14", "Chapter 3") carry no subject matter
    if re.match(r"^(verse|verses|shloka|sloka|śloka|chapter|adhyaya|adhyāya|section|"
                r"sthana|sthāna|para|paragraph|part|no\.?)\s*[\d.\-–,\s]*$", h, re.I):
        return False
    if len(h.split()) < 2:
        return False
    return True


TERM_RE = re.compile(
    r"\b([A-ZĀĪŪṚṜḶṄÑṬḌṆŚṢṀḤ][A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’́-]{2,24})\b"
)
DIA_TERM_RE = re.compile(
    r"\b([a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ][a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ'’-]{3,24})\b"
)


def extract_terms(text):
    """Sanskrit / Ayurvedic technical terms out of an English commentary."""
    terms = set()
    for m in TERM_RE.finditer(text or ""):
        t = m.group(1)
        if t in STOP_CAPS or len(t) < 4:
            continue
        # keep it if it carries diacritics OR looks Sanskritic
        if any(c in DIACRITIC_CHARS for c in t):
            terms.add(t)
        elif re.search(r"(a|i|u)$", t) and len(t) >= 5 and t.lower() not in ENGLISH_COMMON:
            terms.add(t)
    for m in DIA_TERM_RE.finditer(text or ""):
        t = m.group(1)
        if any(c in DIACRITIC_CHARS for c in t) and len(t) >= 5:
            terms.add(t)
    return terms


ENGLISH_COMMON = {
    "area", "idea", "data", "extra", "formula", "media", "india", "aroma", "coma",
    "drama", "era", "alpha", "beta", "gamma", "delta", "sigma", "china", "asia",
    "africa", "america", "europe", "anaemia", "anemia", "nausea", "diarrhoea",
    "diarrhea", "oedema", "edema", "trauma", "plasma", "stigma", "schema",
    "criteria", "bacteria", "genera", "flora", "fauna", "aura", "saliva", "vagina",
    "retina", "trachea", "urethra", "vertebra", "pelvis", "thesis", "basis",
    "series", "species", "process", "disease", "tissue", "muscle", "female",
    "male", "human", "animal", "water", "milk", "honey", "blood", "urine",
}

NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "eighteen": 18, "twenty": 20,
}
NUM_WORDS_INV = {v: k for k, v in NUM_WORDS.items()}


_FALSIFY_IDX = {}


def _len_buckets(book_terms):
    key = id(book_terms)
    hit = _FALSIFY_IDX.get(key)
    if hit is None or hit[0] != len(book_terms):
        idx = defaultdict(list)
        for t in book_terms:
            idx[len(t)].append(t)
        hit = (len(book_terms), idx)
        _FALSIFY_IDX[key] = hit
    return hit[1]


def falsify(sentence, book_terms, rng):
    """Return a plausibly-worded but factually FALSE variant of a true sentence."""
    # Strategy 1: number swap
    m = list(re.finditer(r"\b(" + "|".join(NUM_WORDS) + r")\b", sentence, re.I))
    if m:
        pick = rng.choice(m)
        orig = pick.group(1)
        val = NUM_WORDS[orig.lower()]
        choices = [v for v in NUM_WORDS_INV if v != val and abs(v - val) <= 8 and v > 1]
        if choices:
            newv = NUM_WORDS_INV[rng.choice(choices)]
            if orig[0].isupper():
                newv = newv.capitalize()
            return sentence[:pick.start(1)] + newv + sentence[pick.end(1):], f"number changed from '{orig}' to '{newv}'"
    m = list(re.finditer(r"\b(\d{1,3})\b", sentence))
    if m:
        pick = rng.choice(m)
        val = int(pick.group(1))
        newv = str(val + rng.choice([1, 2, 3, -1, -2]) or val + 4)
        if newv != pick.group(1) and int(newv) > 0:
            return sentence[:pick.start(1)] + newv + sentence[pick.end(1):], f"numeral changed from '{pick.group(1)}' to '{newv}'"
    # Strategy 2: technical-term swap
    present = [t for t in extract_terms(sentence) if t in book_terms]
    if present:
        old = rng.choice(present)
        idx = _len_buckets(book_terms)
        pool = [t for L in range(len(old) - 6, len(old) + 7) for t in idx.get(L, ()) if t != old]
        if pool:
            new = rng.choice(pool)
            return re.sub(r"\b" + re.escape(old) + r"\b", new, sentence, count=1), f"term '{old}' replaced by unrelated term '{new}'"
    # Strategy 3: dosha / rasa swap
    SWAPS = [("Vāta", "Kapha"), ("Pitta", "Vāta"), ("Kapha", "Pitta"),
             ("vata", "kapha"), ("pitta", "vata"), ("kapha", "pitta"),
             ("hot", "cold"), ("cold", "hot"), ("increases", "decreases"),
             ("decreases", "increases"), ("aggravates", "pacifies"),
             ("pacifies", "aggravates"), ("sweet", "pungent"), ("bitter", "sweet")]
    for a, b in SWAPS:
        if re.search(r"\b" + re.escape(a) + r"\b", sentence):
            return re.sub(r"\b" + re.escape(a) + r"\b", b, sentence, count=1), f"'{a}' replaced by '{b}'"
    return None, None


def shorten(s, n=190):
    s = norm_ws(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,;:.") + " ..."


def verse_ref(rec):
    bits = []
    if rec["sthana"]:
        bits.append(rec["sthana"])
    if rec["chapter_number"]:
        bits.append("Chapter %s" % rec["chapter_number"])
    if rec["verse_id"] and re.match(r"^[\d.\-]+$", str(rec["verse_id"])):
        bits.append("verse %s" % rec["verse_id"])
    return ", ".join(bits)


def citation(rec):
    c = verse_ref(rec)
    return "%s — %s" % (rec["book"], c) if c else rec["book"]


# --------------------------------------------------------------------------
# Load + normalise records
# --------------------------------------------------------------------------
def load_book(path, book, code):
    recs = []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Sharangadhara commentary is Hindi -> prefer the English rendering
            comm = d.get("commentary_english") or d.get("commentary") or ""
            if DEVA.search(comm) and d.get("commentary_english"):
                comm = d["commentary_english"]
            if DEVA.search(comm) and not d.get("commentary_english"):
                # Hindi-only commentary: unusable for English questions
                comm_en = ""
            else:
                comm_en = comm
            recs.append({
                "book": book,
                "code": code,
                "chunk_id": d.get("chunk_id", "%s_L%d" % (code, ln)),
                "sthana": norm_ws(d.get("sthana", "")),
                "chapter_number": d.get("chapter_number", 0) or 0,
                "chapter_title": norm_ws(d.get("chapter_title", "")),
                "verse_id": norm_ws(str(d.get("verse_id", ""))),
                "topic_heading": norm_ws(d.get("topic_heading", "")),
                "sanskrit": norm_ws(d.get("sanskrit_text", "")),
                "translit": norm_ws(d.get("transliteration", "")),
                "commentary": clean_commentary(comm_en),
                "categories": d.get("categories_found") or [],
                "primary_category": norm_ws(d.get("primary_category", "")),
                "source_citation": norm_ws(d.get("source_citation", "")),
                "record_type": norm_ws(d.get("record_type", "")),
            })
    return recs


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------
LETTERS = ["A", "B", "C", "D"]


class Emitter:
    def __init__(self):
        self.rows = []
        self.seen = set()
        self.counter = Counter()

    def add(self, rec, qtype, grounding, question, options, answer_text,
            difficulty, explanation, context="", subtype=""):
        """options: list of 4 strings (or [] for open-ended Assorted)."""
        key = hashlib.md5(norm_ws(question).lower().encode("utf-8")).hexdigest()
        if key in self.seen:
            return False
        if options:
            if len(set(norm_ws(o).lower() for o in options)) != 4:
                return False
            if answer_text not in options:
                return False
            # ---- leakage guard: the stem must not already contain the key ----
            ql = norm_ws(question).lower()
            al = norm_ws(answer_text).lower()
            if qtype in ("MCQ", "Fill in the blanks") and len(al) >= 4:
                stem_only = ql.split("\n\n")[0] if "\n\n" in ql else ql
                body = ql
                for o in options:
                    body = body.replace(norm_ws(o).lower(), " ")
                if al in body:
                    return False
        # ---- leakage guard: context must not hand over the answer ----
        if options and context and len(norm_ws(answer_text)) >= 4:
            if norm_ws(answer_text).lower() in norm_ws(context).lower():
                context = ""
        # Verdict questions (true/false, assertion-reasoning) are decided by comparing the
        # statement against the source text - so no source text may be supplied.
        if qtype == "Assertion or Reasoning" or subtype.startswith("true_false"):
            context = ""
        self.seen.add(key)
        self.counter[rec["code"]] += 1
        qid = "%s-%s-%05d" % (rec["code"], SHORT[qtype], self.counter[rec["code"]])
        row = {
            "question_id": qid,
            "question": question,
            "option_a": options[0] if options else "",
            "option_b": options[1] if options else "",
            "option_c": options[2] if options else "",
            "option_d": options[3] if options else "",
            "correct_answer": LETTERS[options.index(answer_text)] if options else "",
            "answer_text": answer_text,
            "question_type": qtype,
            "question_subtype": subtype,
            "grounding": grounding,
            "difficulty": difficulty,
            "subject_domain": pick_domain(rec["book"], rec["sthana"],
                                          rec["categories"], rec["primary_category"]),
            "language": "English",
            "source_book": rec["book"],
            "sthana": rec["sthana"],
            "chapter_number": rec["chapter_number"],
            "chapter_title": rec["chapter_title"],
            "verse_id": rec["verse_id"],
            "chunk_id": rec["chunk_id"],
            "primary_category": rec["primary_category"],
            "citation": citation(rec),
            "explanation": norm_ws(explanation),
            "context": norm_ws(context),
        }
        self.rows.append(row)
        return True


SHORT = {
    "MCQ": "MCQ",
    "Fill in the blanks": "FIB",
    "Match the column": "MTC",
    "Assertion or Reasoning": "AR",
    "Assorted": "ASR",
}


def shuffled_options(correct, distractors, rng):
    opts = [correct] + list(distractors)[:3]
    if len(opts) < 4:
        return None
    seen, uniq = set(), []
    for o in opts:
        k = norm_ws(o).lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(norm_ws(o))
    if len(uniq) < 4:
        return None
    uniq = uniq[:4]
    rng.shuffle(uniq)
    return uniq


# --------------------------------------------------------------------------
# Question builders
# --------------------------------------------------------------------------
def build_for_book(recs, book, code, em, rng):
    # ---------- pools ----------
    headings = {}
    for r in recs:
        h = clean_heading(r["topic_heading"])
        if good_heading(h):
            headings.setdefault(h, r)
    heading_list = list(headings.keys())

    sthanas = sorted({r["sthana"] for r in recs if r["sthana"]})
    chapters = sorted({(r["sthana"], r["chapter_number"], r["chapter_title"])
                       for r in recs if r["chapter_title"]})

    book_terms = set()
    for r in recs:
        book_terms |= extract_terms(r["commentary"])
        book_terms |= extract_terms(r["topic_heading"])
    book_terms = {t for t in book_terms if 4 <= len(t) <= 22}
    book_term_list = sorted(book_terms)

    # Devanagari token pool for Sanskrit fill-in-the-blank
    deva_tokens = defaultdict(list)   # length-bucket -> tokens
    for r in recs:
        for tok in r["sanskrit"].split():
            tok = tok.strip("।॥|॥().,;:'\"")
            tok = re.sub(r"[०-९\d]+", "", tok)
            if 4 <= len(tok) <= 16 and DEVA.match(tok) and not re.search(r"[^ऀ-ॿ‌‍]", tok):
                deva_tokens[min(len(tok) // 3, 5)].append(tok)
    for k in deva_tokens:
        deva_tokens[k] = list(dict.fromkeys(deva_tokens[k]))

    # sentence pool (for distractors and for "which statement is correct")
    sent_pool = []          # (sentence, category, chunk_id, chapter_key)
    for r in recs:
        ck = (r["sthana"], r["chapter_number"])
        for s in split_sentences(r["commentary"]):
            if good_sentence(s):
                sent_pool.append((s, r["primary_category"], r["chunk_id"], ck))

    by_cat = defaultdict(list)
    for r in recs:
        by_cat[r["primary_category"] or "general"].append(r)
    by_chapter = defaultdict(list)
    for r in recs:
        by_chapter[(r["sthana"], r["chapter_number"])].append(r)

    # --- precomputed index pools (avoid O(N) rebuilds inside the per-chunk loop)
    headings_by_sthana = defaultdict(list)
    for h in heading_list:
        headings_by_sthana[headings[h]["sthana"]].append(h)

    sent_by_cat = defaultdict(list)
    for (s, c, cid, ck) in sent_pool:
        sent_by_cat[c].append((s, cid, ck))
    sent_all = [(s, cid, ck) for (s, c, cid, ck) in sent_pool]

    def _sample_reject(pool, n, reject, tries_mult=8):
        """Randomly draw n distinct items from pool skipping those failing `reject`."""
        if not pool:
            return []
        out, seen, tries = [], set(), 0
        limit = max(30, n * tries_mult)
        while len(out) < n and tries < limit:
            tries += 1
            item = pool[rng.randrange(len(pool))]
            key = item[0] if isinstance(item, tuple) else item
            if key in seen or reject(item):
                continue
            seen.add(key)
            out.append(key)
        return out if len(out) == n else []

    def other_headings(exclude, n=3, same_ctx=None):
        pool = headings_by_sthana.get(same_ctx) or heading_list
        if len(pool) < n + 1:
            pool = heading_list
        if len(pool) < n + 1:
            return []
        return _sample_reject(pool, n, lambda h: h == exclude)

    def other_sentences(exclude_chunk, n=3, cat=None, exclude_chapter=None):
        """Distractor sentences: same book, but never the same chunk and never the
        same chapter (so a distractor cannot accidentally be true of the topic)."""
        pool = sent_by_cat.get(cat) or []
        if len(pool) < n + 6:
            pool = sent_all
        if len(pool) < n + 1:
            return []
        out = _sample_reject(
            pool, n,
            lambda it: it[1] == exclude_chunk or (exclude_chapter and it[2] == exclude_chapter))
        if not out:      # relax the chapter constraint rather than lose the item
            out = _sample_reject(pool, n, lambda it: it[1] == exclude_chunk)
        return out

    usable = [r for r in recs
              if (len(r["sanskrit"]) >= 15 or len(r["commentary"]) >= 60)]

    # ---- synonym pool (paryaya lists) for Nighantu-style texts ----
    syn_pool = []
    for r in recs:
        for t in extract_synonyms(r):
            syn_pool.append(t)
    syn_pool = list(dict.fromkeys(syn_pool))

    # ======================================================================
    # PRIMARY PASS
    # MCQ is the backbone (as in BhashaBench-Ayur); every usable chunk is
    # guaranteed at least one question, richer chunks yield several.
    # ======================================================================
    fib_toggle = 0
    ar_case = 0
    for idx, r in enumerate(usable):
        made_any = False

        # ---- MCQ family (attempt all applicable) ----
        made_any |= bool(q_shloka_meaning(r, em, rng, other_headings))
        made_any |= bool(q_verse_translation(r, em, rng, other_sentences))
        made_any |= bool(q_commentary_stmt(r, em, rng, other_sentences))
        if idx % 2 == 0:
            made_any |= bool(q_concept_source(r, em, rng, sthanas, chapters, recs))
        if idx % 2 == 1:
            made_any |= bool(q_term_recall(r, em, rng, book_term_list))
        made_any |= bool(q_count(r, em, rng))
        made_any |= bool(q_synonym(r, em, rng, syn_pool))

        # ---- Fill in the blanks (one per chunk, alternating flavour) ----
        fib_order = [q_fib_sanskrit, q_fib_term] if fib_toggle % 2 == 0 else [q_fib_term, q_fib_sanskrit]
        for fn in fib_order:
            ok = fn(r, em, rng, deva_tokens) if fn is q_fib_sanskrit else fn(r, em, rng, book_term_list)
            if ok:
                made_any = True
                fib_toggle += 1
                break

        # ---- Assorted (descriptive) ----
        made_any |= bool(q_assorted(r, em, rng, book_terms))
        if idx % 5 == 0:
            q_descriptive(r, em, rng)
        if idx % 4 == 0:
            q_truefalse(r, em, rng, book_terms)

        # ---- Assertion / Reasoning (content-rich chunks only) ----
        if len(r["commentary"]) >= 240 and idx % 3 == 0:
            if q_assertion(r, em, rng, sent_pool, book_terms, ar_case % 4):
                ar_case += 1
                made_any = True

        # ---- guarantee: fall back to a plain exposition item ----
        if not made_any:
            q_fallback(r, em, rng)

    # ======================================================================
    # MATCH THE COLUMN - grouped by chapter, then by category
    # ======================================================================
    groups = []
    for key, grp in by_chapter.items():
        cands = [r for r in grp if good_heading(r["topic_heading"]) and
                 (len(r["commentary"]) >= 60 or len(r["sanskrit"]) >= 20)]
        for i in range(0, len(cands) - 3, 4):
            groups.append(cands[i:i + 4])
    for key, grp in by_cat.items():
        cands = [r for r in grp if good_heading(r["topic_heading"]) and len(r["commentary"]) >= 70]
        rng.shuffle(cands)
        for i in range(0, len(cands) - 3, 4):
            groups.append(cands[i:i + 4])
    # third pass: group across chapters within the same sthana (two reshuffles)
    by_sthana = defaultdict(list)
    for r in recs:
        if good_heading(r["topic_heading"]) and len(r["commentary"]) >= 70:
            by_sthana[r["sthana"]].append(r)
    for _pass in range(6):
        for key, cands in by_sthana.items():
            cands = list(cands)
            rng.shuffle(cands)
            for i in range(0, len(cands) - 3, 4):
                groups.append(cands[i:i + 4])
    rng.shuffle(groups)
    for grp in groups:
        if not q_match_column(grp, em, rng):
            q_match_reference(grp, em, rng)


# ---------------- individual builders ----------------

def q_shloka_meaning(r, em, rng, other_headings):
    if len(r["sanskrit"]) < 20 or devanagari_garbled(r["sanskrit"]):
        return False
    h = clean_heading(r["topic_heading"])
    if not good_heading(h):
        return False
    dis = other_headings(h, 3, same_ctx=r["sthana"])
    if not dis:
        return False
    opts = shuffled_options(h, dis, rng)
    if not opts:
        return False
    stem = ("Read the following verse from %s%s:\n\n%s\n\n"
            "Which subject does this verse deal with?") % (
        r["book"], (" (" + verse_ref(r) + ")") if verse_ref(r) else "", r["sanskrit"])
    expl = "The verse %s is concerned with: %s.%s" % (
        verse_ref(r) or "cited above", h,
        (" Commentary: " + shorten(r["commentary"], 260)) if r["commentary"] else "")
    return em.add(r, "MCQ", "shloka_to_meaning", stem, opts, h,
                  "Medium", expl, context=r["sanskrit"], subtype="verse_subject")


GENERIC_WORDS = set("""the a an of and or in on at to for with by from as is are was were be
been being this that these those which who whom whose what when where how why all any some
such other others its it his her their there here also not no nor but if then than so very
more most much many few less least own same too only just even ever never always according
said states stated described mention mentioned given give gives text verse chapter section
commentary book part type types kind kinds""".split())


def _content_words(s):
    return {w for w in re.findall(r"[A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ]{4,}", s.lower())
            if w not in GENERIC_WORDS}


def _shares_content_word(a, b):
    wa, wb = _content_words(a), _content_words(b)
    if not wa:
        return False
    if wa & wb:
        return True
    # tolerate inflection / transliteration variance on the stem
    for x in wa:
        for y in wb:
            if len(x) >= 5 and len(y) >= 5 and (x[:5] == y[:5]):
                return True
    return False


def q_commentary_stmt(r, em, rng, other_sentences):
    sents = [s for s in split_sentences(r["commentary"]) if good_sentence(s)]
    if not sents:
        return False
    # prefer a sentence that is on-topic for the chunk's heading
    topic = clean_heading(r["topic_heading"])
    on_topic = [s for s in sents if _shares_content_word(topic, s)] if good_heading(topic) else []
    correct = shorten(rng.choice(on_topic or sents), 200)
    dis = [shorten(s, 200) for s in other_sentences(r["chunk_id"], 3, r["primary_category"],
                                            (r["sthana"], r["chapter_number"]))]
    if len(dis) < 3:
        return False
    opts = shuffled_options(correct, dis, rng)
    if not opts:
        return False
    topic = clean_heading(r["topic_heading"])
    subj = topic if good_heading(topic) else ""
    # the subject must not restate the keyed option (that would give the answer away)
    if subj and correct.lower().startswith(subj.lower()[:30]):
        subj = ""
    # ...and the keyed sentence must actually be *about* the named subject,
    # otherwise the "regarding X" framing makes the key indefensible
    if subj and not _shares_content_word(subj, correct):
        subj = ""
    if subj:
        stem = ("According to %s%s, which of the following statements regarding "
                "\"%s\" is correct?") % (
            r["book"], (" (" + verse_ref(r) + ")") if verse_ref(r) else "", subj)
    else:
        stem = ("Which of the following statements is in accordance with %s%s?") % (
            r["book"], (" (" + verse_ref(r) + ")") if verse_ref(r) else "")
    diff = "Hard" if len(r["commentary"]) > 900 else "Medium"
    expl = "The commentary on %s states: %s" % (verse_ref(r) or r["chunk_id"], correct)
    return em.add(r, "MCQ", "commentary_clinical", stem, opts, correct, diff, expl,
                  context=shorten(r["commentary"], 400), subtype="correct_statement")


def q_verse_translation(r, em, rng, other_sentences):
    """Give the verse, ask which option correctly renders its import."""
    if len(r["sanskrit"]) < 25 or devanagari_garbled(r["sanskrit"]):
        return False
    sents = [s for s in split_sentences(r["commentary"]) if good_sentence(s, 50, 300)]
    if not sents:
        return False
    correct = shorten(sents[0], 210)
    dis = [shorten(s, 210) for s in other_sentences(r["chunk_id"], 3, r["primary_category"],
                                            (r["sthana"], r["chapter_number"]))]
    if len(dis) < 3:
        return False
    opts = shuffled_options(correct, dis, rng)
    if not opts:
        return False
    stem = ("Identify the correct import of the following verse of the %s%s:\n\n%s") % (
        r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", r["sanskrit"])
    expl = "The commentary renders this verse as: %s" % correct
    return em.add(r, "MCQ", "shloka_to_meaning", stem, opts, correct,
                  "Medium", expl, context=r["sanskrit"], subtype="verse_translation")


COUNT_RE = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    r"fourteen|fifteen|sixteen|eighteen|twenty|\d{1,3})\s+"
    r"(?:main\s+|principal\s+|chief\s+|different\s+|distinct\s+)?"
    r"(types?|kinds?|varieties|classes|divisions|sub-?types?|bhedas?|"
    r"forms?|groups?|categories|stages?|factors?|causes?|qualities|gunas?|"
    r"doshas?|dhatus?|malas?|srotas|sthanas?|members?|constituents?)\s+of\s+"
    r"([A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’-]"
    r"[A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’ -]{2,38}?)"
    r"(?=[,.;:)]|\s+(?:are|is|which|that|has|have|and|according|described|mentioned)\b)",
    re.I)


def q_count(r, em, rng):
    """'How many X of Y are described?' - numeric-fact MCQ tied to an explicit subject."""
    text = r["commentary"]
    m = COUNT_RE.search(text)
    if not m:
        return False
    num_raw, noun, subject = m.group(1), m.group(2), norm_ws(m.group(3))
    val = NUM_WORDS.get(num_raw.lower())
    if val is None:
        try:
            val = int(num_raw)
        except ValueError:
            return False
    if not (2 <= val <= 100):
        return False
    if len(subject) < 3 or subject.lower() in ("them", "these", "those", "it", "this",
                                               "which", "the", "a", "an", "such"):
        return False
    # the same count phrase must not recur with a different number in the passage
    others = {NUM_WORDS.get(x[0].lower(), None) or (int(x[0]) if x[0].isdigit() else None)
              for x in COUNT_RE.findall(text)
              if norm_ws(x[2]).lower() == subject.lower()}
    others.discard(None)
    if len(others) > 1:
        return False
    # build numeric distractors near the true value
    cands = sorted({val + d for d in (-3, -2, -1, 1, 2, 3, 4, 5)} - {val})
    cands = [c for c in cands if c >= 1]
    if len(cands) < 3:
        return False
    dis = [str(c) for c in rng.sample(cands, 3)]
    opts = shuffled_options(str(val), dis, rng)
    if not opts:
        return False
    stem = ("According to %s%s, how many %s of %s are described?") % (
        r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", noun.lower(), subject)
    expl = "The text states: \"%s ...\"" % shorten(m.group(0), 160)
    return em.add(r, "MCQ", "commentary_clinical", stem, opts, str(val),
                  "Medium", expl, context=shorten(text, 320), subtype="enumeration_count")


SYN_CUE = re.compile(r"(synonym|paryāya|paryaya|also (called|known as)|other names)", re.I)


def extract_synonyms(r):
    """Pull the paryāya (synonym) list out of a Nighantu-style commentary."""
    blob = (r["topic_heading"] or "") + " " + (r["commentary"] or "")
    if not SYN_CUE.search(blob):
        return []
    seg = r["commentary"]
    m = SYN_CUE.search(seg)
    if m:
        seg = seg[m.end():]
    seg = seg.split(".")[0]
    parts = re.split(r"\s*[,;]\s*|\s+and\s+", seg)
    terms = []
    for p in parts:
        p = norm_ws(p).strip(" .:;()")
        if 3 <= len(p) <= 22 and " " not in p and not DEVA.search(p) \
                and re.match(r"^[A-Za-zĀĪŪṚṜḶḹṄÑṬḌṆŚṢṀḤāīūṛṝḷṅñṭḍṇśṣṃḥ'’-]+$", p) \
                and p not in STOP_CAPS:
            terms.append(p)
    return terms[:14]


def q_synonym(r, em, rng, syn_pool):
    terms = extract_synonyms(r)
    if len(terms) < 2 or len(syn_pool) < 12:
        return False
    subject = clean_heading(r["topic_heading"])
    subject = re.sub(r"\s*\(.*?\)\s*", " ", subject)
    subject = re.sub(SYN_CUE, "", subject).strip(" :–-")
    if not subject:
        subject = r["chapter_title"]
    if not subject or len(subject) < 3:
        return False
    correct = rng.choice(terms)
    own = set(t.lower() for t in terms)
    pool = [t for t in syn_pool if t.lower() not in own]
    if len(pool) < 3:
        return False
    dis = rng.sample(pool, 3)
    opts = shuffled_options(correct, dis, rng)
    if not opts:
        return False
    stem = ("According to the %s, which of the following is a synonym (paryāya) of %s?") % (
        r["book"], subject)
    expl = "Synonyms listed in the text: %s." % ", ".join(terms)
    return em.add(r, "MCQ", "term_recall", stem, opts, correct, "Medium", expl,
                  context=shorten(r["commentary"], 320), subtype="paryaya")


def q_fallback(r, em, rng):
    """Last-resort item so no usable chunk is skipped entirely."""
    if r["sanskrit"] and len(r["sanskrit"]) >= 15:
        stem = ("Transliterate and give the contextual import of the following line "
                "from %s%s:\n\n%s") % (
            r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", r["sanskrit"])
        ans = (r["translit"] + ("  —  " if r["translit"] and r["commentary"] else "")
               + r["commentary"]).strip() or r["translit"] or r["sanskrit"]
        return em.add(r, "Assorted", "shloka_to_meaning", stem, [], ans, "Easy",
                      "Verse and its rendering as given in the source.",
                      context=r["sanskrit"], subtype="transliterate_and_explain")
    if r["commentary"]:
        topic = clean_heading(r["topic_heading"]) or r["chapter_title"] or r["sthana"]
        stem = "What does %s state under \"%s\"?" % (r["book"], topic)
        return em.add(r, "Assorted", "commentary_clinical", stem, [], r["commentary"],
                      "Easy", "Direct statement of the source text.",
                      context="", subtype="direct_recall")
    return False


def q_fib_sanskrit(r, em, rng, deva_tokens):
    if devanagari_garbled(r["sanskrit"]):
        return False
    toks = [t.strip("।॥|().,;:'\"") for t in r["sanskrit"].split()]
    toks = [t for t in toks if 4 <= len(t) <= 16 and DEVA.match(t)
            and not re.search(r"[^ऀ-ॿ‌‍]", t)]
    if len(toks) < 4:
        return False
    target = rng.choice(toks)
    bucket = min(len(target) // 3, 5)
    pool = [t for t in deva_tokens.get(bucket, []) if t != target]
    if len(pool) < 3:
        pool = [t for b in deva_tokens.values() for t in b if t != target]
    if len(pool) < 3:
        return False
    dis = rng.sample(pool, 3)
    opts = shuffled_options(target, dis, rng)
    if not opts:
        return False
    blanked = re.sub(re.escape(target), "________", r["sanskrit"], count=1)
    stem = ("Fill in the blank in this verse from %s%s:\n\n%s") % (
        r["book"], (" (" + verse_ref(r) + ")") if verse_ref(r) else "", blanked)
    expl = "The complete verse reads: %s%s" % (
        r["sanskrit"], ("  Meaning: " + shorten(r["commentary"], 200)) if r["commentary"] else "")
    return em.add(r, "Fill in the blanks", "shloka_to_meaning", stem, opts, target,
                  "Medium", expl, context=r["sanskrit"], subtype="sanskrit_pada")


def q_fib_term(r, em, rng, book_term_list):
    sents = [s for s in split_sentences(r["commentary"]) if good_sentence(s, 55, 260)]
    rng.shuffle(sents)
    for s in sents:
        terms = [t for t in extract_terms(s) if t in set(book_term_list)]
        terms = [t for t in terms if len(t) >= 5]
        if not terms:
            continue
        target = rng.choice(terms)
        pool = [t for t in book_term_list
                if t != target and abs(len(t) - len(target)) <= 6
                and t.lower() != target.lower()]
        if len(pool) < 3:
            continue
        dis = rng.sample(pool, 3)
        opts = shuffled_options(target, dis, rng)
        if not opts:
            continue
        blanked = re.sub(r"\b" + re.escape(target) + r"\b", "________", s, count=1)
        stem = ("Fill in the blank (from %s%s):\n\n%s") % (
            r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", blanked)
        expl = "The original statement is: %s" % s
        return em.add(r, "Fill in the blanks", "term_recall", stem, opts, target,
                      "Easy", expl, context=shorten(r["commentary"], 320),
                      subtype="technical_term")
    return False


def q_concept_source(r, em, rng, sthanas, chapters, recs):
    h = clean_heading(r["topic_heading"])
    if not good_heading(h) or not r["sthana"]:
        return False
    if len(sthanas) >= 4:
        dis = [s for s in sthanas if s != r["sthana"]]
        if len(dis) < 3:
            return False
        dis = rng.sample(dis, 3)
        opts = shuffled_options(r["sthana"], dis, rng)
        if not opts:
            return False
        stem = ("In which sthana (section) of the %s is \"%s\" described?" % (r["book"], h))
        expl = "%s is dealt with in the %s of the %s%s." % (
            h, r["sthana"], r["book"],
            (", " + ("Chapter %s" % r["chapter_number"]) if r["chapter_number"] else ""))
        return em.add(r, "MCQ", "concept_to_source", stem, opts, r["sthana"],
                      "Easy", expl, context=shorten(r["commentary"], 260),
                      subtype="locate_sthana")
    # fall back to chapter identification within the sthana
    same = [c for c in chapters if c[0] == r["sthana"] and c[2] and c[1] != r["chapter_number"]]
    if len(same) < 3 or not r["chapter_title"]:
        return False
    dis = [c[2] for c in rng.sample(same, 3)]
    opts = shuffled_options(r["chapter_title"], dis, rng)
    if not opts:
        return False
    stem = ("\"%s\" is expounded in which chapter of the %s (%s)?" % (h, r["book"], r["sthana"]))
    expl = "It appears in %s, %s of the %s." % (
        r["chapter_title"], r["sthana"], r["book"])
    return em.add(r, "MCQ", "concept_to_source", stem, opts, r["chapter_title"],
                  "Medium", expl, context=shorten(r["commentary"], 260),
                  subtype="locate_chapter")


def q_term_recall(r, em, rng, book_term_list):
    """Which Sanskrit term is discussed in this passage?"""
    terms = [t for t in extract_terms(r["topic_heading"] + " " + r["commentary"]) if len(t) >= 5]
    if not terms:
        return False
    target = max(terms, key=lambda t: (r["commentary"] + r["topic_heading"]).count(t))
    if (r["commentary"] + r["topic_heading"]).count(target) < 2:
        return False
    pool = [t for t in book_term_list if t != target and target.lower() not in t.lower()
            and t.lower() not in target.lower()]
    if len(pool) < 3:
        return False
    dis = rng.sample(pool, 3)
    opts = shuffled_options(target, dis, rng)
    if not opts:
        return False
    body = re.sub(r"\b" + re.escape(target) + r"\b", "[X]",
                  shorten(r["commentary"], 320))
    if "[X]" not in body:
        return False
    stem = ("In the following passage from %s%s, the term [X] has been masked. "
            "Which term is it?\n\n%s") % (
        r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", body)
    expl = "The masked term is %s. Full passage: %s" % (target, shorten(r["commentary"], 300))
    return em.add(r, "MCQ", "term_recall", stem, opts, target, "Medium", expl,
                  context=shorten(r["commentary"], 400), subtype="masked_term")


def _mtc_label_ok(h):
    """Column-A entries must be compact labels, not truncated clauses."""
    if len(h.split()) > 9:
        return False
    if re.search(r"\b(who|which|that|the|a|an|in|on|by|for|is|are|of|and|or|to|with)$",
                 h, re.I):
        return False
    return True


def q_match_column(grp, em, rng):
    items = []
    for r in grp:
        h = clean_heading(r["topic_heading"])
        if not good_heading(h) or not _mtc_label_ok(h):
            return False
        # the description must NOT simply restate the Column-A label
        desc = ""
        for s in split_sentences(r["commentary"]):
            if not good_sentence(s, 40, 240):
                continue
            if s.lower().startswith(h.lower()[:20]) or h.lower().startswith(s.lower()[:20]):
                continue
            desc = shorten(s, 130)
            break
        if not desc:
            return False
        items.append((h, desc, r))
    if len({d for _, d, _ in items}) != 4 or len({h for h, _, _ in items}) != 4:
        return False
    r0 = grp[0]
    return _mtc_emit(grp, items, em, rng, "four_pair",
                     "Match the items in Column A with their correct descriptions in "
                     "Column B (from %s%s):" % (
                         r0["book"], (" — " + r0["sthana"]) if r0["sthana"] else ""),
                     "Column B")


def _mtc_emit(grp, items, em, rng, subtype, header, colb_title):
    roman = ["i", "ii", "iii", "iv"]
    letters = ["a", "b", "c", "d"]
    perm = list(range(4))
    rng.shuffle(perm)
    if perm == list(range(4)):
        perm = [1, 0, 3, 2]
    colB = [items[perm[j]][1] for j in range(4)]
    pos = {perm[j]: j for j in range(4)}
    correct = ", ".join("%s-%s" % (roman[i], letters[pos[i]]) for i in range(4))

    wrongs, tries = set(), 0
    while len(wrongs) < 3 and tries < 60:
        tries += 1
        alt = list(range(4))
        rng.shuffle(alt)
        cand = ", ".join("%s-%s" % (roman[i], letters[alt[i]]) for i in range(4))
        if cand != correct:
            wrongs.add(cand)
    if len(wrongs) < 3:
        return False
    opts = shuffled_options(correct, sorted(wrongs), rng)
    if not opts:
        return False

    r0 = grp[0]
    lines = [header, "", "Column A"]
    lines += ["(%s) %s" % (roman[i], items[i][0]) for i in range(4)]
    lines += ["", colb_title]
    lines += ["(%s) %s" % (letters[j], colB[j]) for j in range(4)]
    lines += ["", "Select the correct match:"]
    expl = "Correct pairing: " + "; ".join(
        "%s (%s) → %s (%s)" % (roman[i], items[i][0], letters[pos[i]], shorten(items[i][1], 80))
        for i in range(4))
    return em.add(r0, "Match the column", "concept_to_source", "\n".join(lines), opts,
                  correct, "Hard", expl,
                  context="; ".join(r["chunk_id"] for r in grp), subtype=subtype)


def q_match_reference(grp, em, rng):
    """Match each topic to the chapter / verse in which it occurs."""
    items = []
    for r in grp:
        h = clean_heading(r["topic_heading"])
        if not good_heading(h) or not _mtc_label_ok(h):
            return False
        ref = verse_ref(r)
        if not ref or not r["chapter_number"]:
            return False
        items.append((h, ref, r))
    if len({d for _, d, _ in items}) != 4 or len({h for h, _, _ in items}) != 4:
        return False
    r0 = grp[0]
    return _mtc_emit(grp, items, em, rng, "topic_to_reference",
                     "Match each topic in Column A with the place in the %s where it is "
                     "expounded (Column B):" % r0["book"],
                     "Column B")


AR_OPTIONS = [
    "Both (A) and (R) are true, and (R) is the correct explanation of (A)",
    "Both (A) and (R) are true, but (R) is NOT the correct explanation of (A)",
    "(A) is true, but (R) is false",
    "(A) is false, but (R) is true",
]

EXPLANATORY = re.compile(
    r"\b(because|since|as it|hence|therefore|thus|so that|due to|owing to|"
    r"for this reason|that is why|consequently|this is why|by reason of|in order to)\b", re.I)


def q_assertion(r, em, rng, sent_pool, book_terms, want_case=0):
    """want_case cycles 0..3 so the four answer keys stay balanced."""
    sents = [s for s in split_sentences(r["commentary"]) if good_sentence(s, 50, 260)]
    if not sents:
        return False

    # fall back toward the falsification cases (2, 3) before the "unrelated"
    # case (1), which is otherwise over-produced and skews the answer key
    order = [want_case] + [c for c in (0, 2, 3, 1) if c != want_case]

    for case in order:
        # --- Case 0 : R genuinely explains A
        if case == 0:
            for i in range(len(sents) - 1):
                a, b = sents[i], sents[i + 1]
                if EXPLANATORY.search(b):
                    if em.add(r, "Assertion or Reasoning", "commentary_clinical",
                              _ar_stem(r, a, b), _ar_opts(rng), AR_OPTIONS[0], "Hard",
                              "Both statements come from the commentary on %s, and the reason "
                              "sentence directly accounts for the assertion."
                              % (verse_ref(r) or r["chunk_id"]),
                              context=shorten(r["commentary"], 400), subtype="R_explains_A"):
                        return True
            continue

        # --- Case 1 : both true, but unrelated
        if case == 1:
            a = rng.choice(sents)
            b = None
            for _ in range(40):
                s, c, cid, ck = sent_pool[rng.randrange(len(sent_pool))]
                if cid != r["chunk_id"] and c != r["primary_category"] and good_sentence(s, 50, 240):
                    b = s
                    break
            if b and em.add(r, "Assertion or Reasoning", "commentary_clinical",
                            _ar_stem(r, a, b), _ar_opts(rng), AR_OPTIONS[1], "Hard",
                            "Both statements are authentic teachings of the %s, but the reason "
                            "belongs to a different topic and does not explain the assertion." % r["book"],
                            context=shorten(r["commentary"], 350), subtype="both_true_unrelated"):
                return True
            continue

        # --- Case 2 / 3 : one statement falsified
        a = rng.choice(sents)
        false_s, why = falsify(rng.choice(sents), book_terms, rng)
        if not false_s or norm_ws(false_s) == norm_ws(a):
            continue
        if case == 2:
            ok = em.add(r, "Assertion or Reasoning", "commentary_clinical",
                        _ar_stem(r, a, false_s), _ar_opts(rng), AR_OPTIONS[2], "Hard",
                        "The assertion is authentic; the reason is a distorted version of the "
                        "text (%s)." % why,
                        context=shorten(r["commentary"], 350), subtype="A_true_R_false")
        else:
            ok = em.add(r, "Assertion or Reasoning", "commentary_clinical",
                        _ar_stem(r, false_s, a), _ar_opts(rng), AR_OPTIONS[3], "Hard",
                        "The assertion is a distorted version of the text (%s); the reason is "
                        "authentic." % why,
                        context=shorten(r["commentary"], 350), subtype="A_false_R_true")
        if ok:
            return True
    return False


def _ar_opts(rng):
    o = list(AR_OPTIONS)
    rng.shuffle(o)
    return o


def _ar_stem(r, a, b):
    return ("Given below are two statements based on %s%s.\n\n"
            "Assertion (A): %s\n"
            "Reason (R): %s\n\n"
            "In the light of the above statements, choose the correct answer:") % (
        r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "",
        shorten(a, 240), shorten(b, 240))


ASSORTED_STEMS = [
    "Explain the meaning of the following verse from {book}{ref}:\n\n{sanskrit}",
    "State and explain what {book}{ref} teaches regarding {topic}.",
    "Write a short note on \"{topic}\" as described in {book}{ref}.",
]


def q_assorted(r, em, rng, book_terms):
    if not r["commentary"] or len(r["commentary"]) < 70:
        return False
    ref = (" (" + verse_ref(r) + ")") if verse_ref(r) else ""
    topic = clean_heading(r["topic_heading"])
    if r["sanskrit"] and len(r["sanskrit"]) >= 20:
        stem = ASSORTED_STEMS[0].format(book=r["book"], ref=ref, sanskrit=r["sanskrit"])
        sub = "verse_exposition"
    elif good_heading(topic):
        stem = ASSORTED_STEMS[rng.choice([1, 2])].format(book=r["book"], ref=ref, topic=topic)
        sub = "short_note"
    else:
        return False
    ans = r["commentary"]
    diff = "Hard" if len(ans) > 800 else ("Medium" if len(ans) > 260 else "Easy")
    return em.add(r, "Assorted", "shloka_to_meaning" if sub == "verse_exposition" else "commentary_clinical",
                  stem, [], ans, diff,
                  "Answer as given by the commentary on %s." % (verse_ref(r) or r["chunk_id"]),
                  context=r["sanskrit"], subtype=sub)


def q_descriptive(r, em, rng):
    """One-word / one-line factual Assorted question."""
    topic = clean_heading(r["topic_heading"])
    if not good_heading(topic) or not r["sthana"]:
        return False
    stem = "Name the sthana and chapter of the %s in which \"%s\" is described." % (r["book"], topic)
    ans = "%s%s%s" % (r["sthana"],
                      ", Chapter %s" % r["chapter_number"] if r["chapter_number"] else "",
                      " (%s)" % r["chapter_title"] if r["chapter_title"] else "")
    return em.add(r, "Assorted", "concept_to_source", stem, [], ans, "Easy",
                  "Provenance of the passage %s." % r["chunk_id"],
                  context=shorten(r["commentary"], 200), subtype="one_line_source")


def q_truefalse(r, em, rng, book_terms):
    sents = [s for s in split_sentences(r["commentary"]) if good_sentence(s, 60, 240)]
    if not sents:
        return False
    s = rng.choice(sents)
    if rng.random() < 0.5:
        stmt, ans, expl = s, "True", "This statement is faithful to the commentary on %s." % (
            verse_ref(r) or r["chunk_id"])
        sub = "true_false_true"
    else:
        false_s, why = falsify(s, book_terms, rng)
        if not false_s:
            return False
        stmt, ans = false_s, "False"
        expl = "The original text states: \"%s\" (%s)." % (s, why)
        sub = "true_false_false"
    stem = ("State whether the following statement based on %s%s is TRUE or FALSE.\n\n%s") % (
        r["book"], (" — " + verse_ref(r)) if verse_ref(r) else "", stmt)
    return em.add(r, "Assorted", "commentary_clinical", stem,
                  ["True", "False", "Partially true", "Cannot be determined"], ans,
                  "Medium", expl, context=shorten(r["commentary"], 300), subtype=sub)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def book_outfile(book):
    return os.path.join(BOOK_DIR, "%s_questions.jsonl"
                        % re.sub(r"[^A-Za-z0-9]+", "_", book).strip("_"))


def run_book(code_filter=None):
    os.makedirs(BOOK_DIR, exist_ok=True)
    for fname, book, code in BOOKS:
        if code_filter and code != code_filter:
            continue
        path = os.path.join(IN_DIR, fname)
        if not os.path.exists(path):
            print("MISSING:", path)
            continue
        recs = load_book(path, book, code)
        em = Emitter()
        rng = random.Random(SEED + sum(ord(c) for c in code))
        build_for_book(recs, book, code, em, rng)
        rows = em.rows
        rng.shuffle(rows)
        with open(book_outfile(book), "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print("%-32s chunks=%5d  questions=%6d" % (book, len(recs), len(rows)))


MASTER = "ayurbench_shloka_all_books.jsonl"


def _read_all():
    rows = []
    for fname, book, code in BOOKS:
        out = book_outfile(book)
        if not os.path.exists(out):
            print("NOT BUILT:", book)
            continue
        with open(out, encoding="utf-8") as fh:
            rows.extend(json.loads(l) for l in fh if l.strip())
    return rows


def combine_master():
    """Merge per-book files into the shuffled master set (global de-duplication)."""
    rows, seen = [], set()
    dropped = 0
    for row in _read_all():
        k = hashlib.md5(norm_ws(row["question"]).lower().encode("utf-8")).hexdigest()
        if k in seen:
            dropped += 1
            continue
        seen.add(k)
        rows.append(row)
    random.Random(SEED).shuffle(rows)
    with open(os.path.join(OUT_DIR, MASTER), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("master rows: %d  (cross-book duplicates dropped: %d)" % (len(rows), dropped))


def combine_splits():
    """90/10 train-validation split stratified by (book, question_type)."""
    rows = [json.loads(l) for l in open(os.path.join(OUT_DIR, MASTER), encoding="utf-8") if l.strip()]
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row["source_book"], row["question_type"])].append(row)
    train, val = [], []
    for k in sorted(buckets):
        rr = list(buckets[k])
        random.Random(SEED).shuffle(rr)
        n_val = max(1, int(round(len(rr) * 0.1)))
        val.extend(rr[:n_val])
        train.extend(rr[n_val:])
    random.Random(SEED).shuffle(train)
    random.Random(SEED).shuffle(val)
    for name, rr in (("train.jsonl", train), ("validation.jsonl", val)):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            for row in rr:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("train: %d   validation: %d" % (len(train), len(val)))


def combine_stats():
    rows = [json.loads(l) for l in open(os.path.join(OUT_DIR, MASTER), encoding="utf-8") if l.strip()]
    stats = {}
    for fname, book, code in BOOKS:
        br = [r for r in rows if r["source_book"] == book]
        if not br:
            continue
        n_chunks = sum(1 for l in open(os.path.join(IN_DIR, fname), encoding="utf-8") if l.strip())
        stats[book] = {
            "chunks": n_chunks,
            "chunks_covered": len({r["chunk_id"] for r in br}),
            "questions": len(br),
            "questions_per_chunk": round(len(br) / max(n_chunks, 1), 2),
            "by_type": dict(Counter(r["question_type"] for r in br)),
            "by_difficulty": dict(Counter(r["difficulty"] for r in br)),
            "by_grounding": dict(Counter(r["grounding"] for r in br)),
            "by_domain": dict(Counter(r["subject_domain"] for r in br)),
            "file": "by_book/" + os.path.basename(book_outfile(book)),
        }
    summary = {
        "dataset_name": "AyurShloka-QA",
        "built_from": "8 classical Ayurvedic shloka + commentary chunk files",
        "schema": "BhashaBench-Ayur (BBA) compatible",
        "total_questions": len(rows),
        "by_type": dict(Counter(r["question_type"] for r in rows)),
        "by_subtype": dict(Counter(r["question_subtype"] for r in rows)),
        "by_difficulty": dict(Counter(r["difficulty"] for r in rows)),
        "by_grounding": dict(Counter(r["grounding"] for r in rows)),
        "by_domain": dict(Counter(r["subject_domain"] for r in rows)),
        "answer_letter_distribution": dict(Counter(r["correct_answer"] for r in rows if r["correct_answer"])),
        "per_book": stats,
    }
    with open(os.path.join(OUT_DIR, "dataset_stats.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("TOTAL:", len(rows))
    print(json.dumps(summary["by_type"], indent=2))


def combine():
    combine_master()
    combine_splits()
    combine_stats()


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arg == "combine":
        combine()
    elif arg == "master":
        combine_master()
    elif arg == "splits":
        combine_splits()
    elif arg == "stats":
        combine_stats()
    elif arg == "all":
        run_book()
        combine()
    else:
        run_book(arg)
