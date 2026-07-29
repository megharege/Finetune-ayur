#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured EDA over the AyurShloka-QA question set, joined back to source chunks.

Answers: how many questions came from each book and each chunk, and how much of that
was carried by the shloka (sanskrit_text) versus the commentary.
"""
import json
import os
import re
from collections import Counter, defaultdict

IN_DIR = "/sessions/loving-trusting-wright/mnt/uploads"
QSET = "/sessions/loving-trusting-wright/mnt/outputs/ayur_question_set/ayurbench_shloka_all_books.jsonl"
OUT = "/sessions/loving-trusting-wright/mnt/outputs/eda_out"

BOOKS = [
    ("FINAL_Charaka_Samhita.jsonl",            "Charaka Samhita",             "CS"),
    ("FINAL_Sushruta_Samhita.jsonl",           "Sushruta Samhita",            "SU"),
    ("FINAL_Ashtanga_Hridaya.jsonl",           "Ashtanga Hridaya",            "AH"),
    ("FINAL_Sharangadhara_Samhita.jsonl",      "Sharangadhara Samhita",       "SG"),
    ("FINAL_B01_Bhavaprakasha_Nighantu.jsonl", "Bhavaprakasha Nighantu",      "BPN"),
    ("FINAL_B02_Madhavanidanam_Part1.jsonl",   "Madhava Nidanam (Part 1)",    "MN1"),
    ("FINAL_B03_Madhavanidanam_Part2.jsonl",   "Madhava Nidanam (Part 2)",    "MN2"),
    ("FINAL_Madhava_Nidana_LaghuTrayi.jsonl",  "Madhava Nidana (Laghutrayi)", "MNL"),
]
BOOK_ORDER = [b for _, b, _ in BOOKS]

DEVA = re.compile(r"[ऀ-ॿ]")

# Which source material does each question subtype actually draw on?
#   shloka      - the Sanskrit verse is quoted in the stem or is the answer
#   commentary  - the fact comes from the prose commentary
#   both        - verse in the stem, commentary supplies the answer
#   provenance  - built from heading + sthana/chapter/verse location metadata
SOURCE_MATERIAL = {
    "verse_subject":              "shloka",
    "sanskrit_pada":              "shloka",
    "verse_translation":          "both",
    "verse_exposition":           "both",
    "transliterate_and_explain":  "both",
    "correct_statement":          "commentary",
    "masked_term":                "commentary",
    "technical_term":             "commentary",
    "enumeration_count":          "commentary",
    "paryaya":                    "commentary",
    "short_note":                 "commentary",
    "direct_recall":              "commentary",
    "true_false_true":            "commentary",
    "true_false_false":           "commentary",
    "R_explains_A":               "commentary",
    "both_true_unrelated":        "commentary",
    "A_true_R_false":             "commentary",
    "A_false_R_true":             "commentary",
    "four_pair":                  "commentary",
    "topic_to_reference":         "provenance",
    "locate_sthana":              "provenance",
    "locate_chapter":             "provenance",
    "one_line_source":            "provenance",
}


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def load_chunks():
    """Every source chunk, with flags for what raw material it carries."""
    rows = []
    for fname, book, code in BOOKS:
        path = os.path.join(IN_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                comm = d.get("commentary_english") or d.get("commentary") or ""
                if DEVA.search(comm) and not d.get("commentary_english"):
                    comm_en = ""          # Hindi-only commentary: unusable in English
                else:
                    comm_en = comm
                sans = norm(d.get("sanskrit_text", ""))
                rows.append({
                    "book": book, "code": code,
                    "chunk_id": d.get("chunk_id", ""),
                    "sthana": norm(d.get("sthana", "")),
                    "chapter_number": d.get("chapter_number", 0) or 0,
                    "chapter_title": norm(d.get("chapter_title", "")),
                    "verse_id": norm(str(d.get("verse_id", ""))),
                    "primary_category": norm(d.get("primary_category", "")),
                    "has_shloka": len(sans) >= 15,
                    "has_commentary": len(norm(comm_en)) >= 60,
                    "shloka_chars": len(sans),
                    "commentary_chars": len(norm(comm_en)),
                    "hindi_only_commentary": bool(DEVA.search(comm) and not d.get("commentary_english")),
                })
    return rows


def load_questions():
    return [json.loads(l) for l in open(QSET, encoding="utf-8") if l.strip()]


def tbl(rows, header):
    """Render a list-of-lists as an aligned text table."""
    allr = [header] + [[str(c) for c in r] for r in rows]
    w = [max(len(r[i]) for r in allr) for i in range(len(header))]
    out = ["  ".join(h.ljust(w[i]) if i == 0 else h.rjust(w[i]) for i, h in enumerate(header))]
    out.append("  ".join("-" * w[i] for i in range(len(header))))
    for r in allr[1:]:
        out.append("  ".join(c.ljust(w[i]) if i == 0 else c.rjust(w[i]) for i, c in enumerate(r)))
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    chunks = load_chunks()
    qs = load_questions()

    # chunk_id is unique *within* a book but not across books - Madhava Nidanam
    # Part 1 and Part 2 both number their chunks MN1, MN2, ... and 102 ids collide.
    # Every join below is therefore keyed on (book, chunk_id).
    for c in chunks:
        c["key"] = (c["book"], c["chunk_id"])
    for q in qs:
        q["key"] = (q["source_book"], q["chunk_id"])
        q["source_material"] = SOURCE_MATERIAL.get(q["question_subtype"], "other")

    chunk_keys = {c["key"] for c in chunks}
    orphans = [q for q in qs if q["key"] not in chunk_keys]
    global_dupes = len(chunks) - len({c["chunk_id"] for c in chunks})
    report_notes = {
        "chunk_id_collisions_across_books": global_dupes,
        "orphan_questions": len(orphans),
    }

    report = {"data_notes": report_notes}

    # ---------------- 1. per book -----------------------------------------
    per_book = []
    for book in BOOK_ORDER:
        bc = [c for c in chunks if c["book"] == book]
        bq = [q for q in qs if q["source_book"] == book]
        used = {q["key"] for q in bq}
        per_book.append({
            "book": book,
            "chunks": len(bc),
            "chunks_with_shloka": sum(c["has_shloka"] for c in bc),
            "chunks_with_commentary": sum(c["has_commentary"] for c in bc),
            "chunks_with_both": sum(c["has_shloka"] and c["has_commentary"] for c in bc),
            "chunks_used": len(used & {c["key"] for c in bc}),
            "coverage_pct": round(100 * len(used & {c["key"] for c in bc}) / max(len(bc), 1), 1),
            "questions": len(bq),
            "q_per_chunk": round(len(bq) / max(len(bc), 1), 2),
            "q_per_used_chunk": round(len(bq) / max(len(used), 1), 2),
            "share_pct": round(100 * len(bq) / len(qs), 1),
        })
    report["per_book"] = per_book

    # ---------------- 2. source material ----------------------------------
    sm_total = Counter(q["source_material"] for q in qs)
    sm_book = defaultdict(Counter)
    for q in qs:
        sm_book[q["source_book"]][q["source_material"]] += 1
    report["source_material_total"] = dict(sm_total)
    report["source_material_by_book"] = {b: dict(sm_book[b]) for b in BOOK_ORDER}

    # ---------------- 3. type / subtype -----------------------------------
    report["type_by_book"] = {
        b: dict(Counter(q["question_type"] for q in qs if q["source_book"] == b))
        for b in BOOK_ORDER}
    report["subtype_total"] = dict(Counter(q["question_subtype"] for q in qs).most_common())
    report["difficulty_by_book"] = {
        b: dict(Counter(q["difficulty"] for q in qs if q["source_book"] == b))
        for b in BOOK_ORDER}
    report["domain_total"] = dict(Counter(q["subject_domain"] for q in qs).most_common())

    # ---------------- 4. chunk-level yield --------------------------------
    per_chunk = Counter(q["key"] for q in qs)
    yields = [per_chunk.get(c["key"], 0) for c in chunks]
    hist = Counter(yields)
    report["chunk_yield_hist"] = {str(k): hist[k] for k in sorted(hist)}
    srt = sorted(yields)
    report["chunk_yield_summary"] = {
        "chunks_total": len(chunks),
        "chunks_used": sum(1 for y in yields if y > 0),
        "chunks_unused": sum(1 for y in yields if y == 0),
        "min": srt[0], "p25": srt[len(srt) // 4], "median": srt[len(srt) // 2],
        "p75": srt[3 * len(srt) // 4], "max": srt[-1],
        "mean": round(sum(yields) / len(yields), 2),
    }

    # why were chunks unused?
    unused = [c for c in chunks if per_chunk.get(c["key"], 0) == 0]
    report["unused_reasons"] = {
        "total": len(unused),
        "no_shloka_no_commentary": sum(1 for c in unused if not c["has_shloka"] and not c["has_commentary"]),
        "hindi_only_commentary": sum(1 for c in unused if c["hindi_only_commentary"]),
        "shloka_only_short": sum(1 for c in unused if c["has_shloka"] and not c["has_commentary"]),
        "commentary_only": sum(1 for c in unused if c["has_commentary"] and not c["has_shloka"]),
        "by_book": dict(Counter(c["book"] for c in unused)),
    }

    # ---------------- 5. raw material availability ------------------------
    avail = []
    for book in BOOK_ORDER:
        bc = [c for c in chunks if c["book"] == book]
        n = len(bc)
        avail.append({
            "book": book, "chunks": n,
            "both_pct": round(100 * sum(c["has_shloka"] and c["has_commentary"] for c in bc) / n, 1),
            "shloka_only_pct": round(100 * sum(c["has_shloka"] and not c["has_commentary"] for c in bc) / n, 1),
            "commentary_only_pct": round(100 * sum(c["has_commentary"] and not c["has_shloka"] for c in bc) / n, 1),
            "neither_pct": round(100 * sum(not c["has_shloka"] and not c["has_commentary"] for c in bc) / n, 1),
            "median_shloka_chars": sorted(c["shloka_chars"] for c in bc)[n // 2],
            "median_commentary_chars": sorted(c["commentary_chars"] for c in bc)[n // 2],
            "hindi_only_commentary": sum(c["hindi_only_commentary"] for c in bc),
        })
    report["raw_material"] = avail

    # ---------------- 6. sthana breakdown ---------------------------------
    sth = defaultdict(lambda: {"chunks": 0, "questions": 0})
    for c in chunks:
        sth[(c["book"], c["sthana"])]["chunks"] += 1
    for q in qs:
        sth[(q["source_book"], q["sthana"])]["questions"] += 1
    report["by_sthana"] = [
        {"book": b, "sthana": s or "(none)", "chunks": v["chunks"], "questions": v["questions"],
         "q_per_chunk": round(v["questions"] / max(v["chunks"], 1), 2)}
        for (b, s), v in sorted(sth.items(), key=lambda kv: (kv[0][0], -kv[1]["questions"]))]

    # ---------------- 7. chapter breakdown --------------------------------
    ch = defaultdict(lambda: {"chunks": 0, "questions": 0, "title": ""})
    for c in chunks:
        k = (c["book"], c["sthana"], c["chapter_number"])
        ch[k]["chunks"] += 1
        ch[k]["title"] = ch[k]["title"] or c["chapter_title"]
    for q in qs:
        ch[(q["source_book"], q["sthana"], q["chapter_number"])]["questions"] += 1
    report["by_chapter"] = [
        {"book": b, "sthana": s or "(none)", "chapter": n, "chapter_title": v["title"],
         "chunks": v["chunks"], "questions": v["questions"],
         "q_per_chunk": round(v["questions"] / max(v["chunks"], 1), 2)}
        for (b, s, n), v in sorted(ch.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))]

    with open(os.path.join(OUT, "eda.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    # ---------------- console summary -------------------------------------
    print("=" * 104)
    print("1. PER BOOK — chunk coverage and question yield")
    print("=" * 104)
    print(tbl([[r["book"], r["chunks"], r["chunks_used"], "%.1f%%" % r["coverage_pct"],
                r["questions"], r["q_per_chunk"], "%.1f%%" % r["share_pct"]] for r in per_book],
              ["book", "chunks", "used", "coverage", "questions", "q/chunk", "share"]))
    print("\nTOTAL chunks=%d  used=%d  questions=%d"
          % (len(chunks), report["chunk_yield_summary"]["chunks_used"], len(qs)))

    print("\n" + "=" * 104)
    print("2. RAW MATERIAL AVAILABLE PER CHUNK (what the generator had to work with)")
    print("=" * 104)
    print(tbl([[r["book"], r["chunks"], "%.1f%%" % r["both_pct"], "%.1f%%" % r["shloka_only_pct"],
                "%.1f%%" % r["commentary_only_pct"], "%.1f%%" % r["neither_pct"],
                r["median_shloka_chars"], r["median_commentary_chars"]] for r in avail],
              ["book", "chunks", "both", "shloka only", "comm only", "neither",
               "med shloka ch", "med comm ch"]))

    print("\n" + "=" * 104)
    print("3. SOURCE MATERIAL BEHIND EACH QUESTION")
    print("=" * 104)
    tot = len(qs)
    print(tbl([[k, v, "%.1f%%" % (100 * v / tot)] for k, v in sm_total.most_common()],
              ["source material", "questions", "share"]))
    print()
    print(tbl([[b] + [sm_book[b].get(k, 0) for k in ("shloka", "both", "commentary", "provenance")]
               for b in BOOK_ORDER],
              ["book", "shloka", "both", "commentary", "provenance"]))

    print("\n" + "=" * 104)
    print("4. QUESTIONS PER CHUNK")
    print("=" * 104)
    s = report["chunk_yield_summary"]
    print("min=%d  p25=%d  median=%d  p75=%d  max=%d  mean=%.2f"
          % (s["min"], s["p25"], s["median"], s["p75"], s["max"], s["mean"]))
    print("unused chunks: %d" % s["chunks_unused"])
    print(tbl([[k, v, "%.1f%%" % (100 * v / len(chunks))]
               for k, v in report["chunk_yield_hist"].items()],
              ["questions from chunk", "n chunks", "share"]))

    print("\n" + "=" * 104)
    print("5. UNUSED CHUNKS — why")
    print("=" * 104)
    u = report["unused_reasons"]
    for k in ("total", "no_shloka_no_commentary", "hindi_only_commentary",
              "shloka_only_short", "commentary_only"):
        print("  %-26s %d" % (k, u[k]))
    print("  by book: %s" % u["by_book"])

    print("\n" + "=" * 104)
    print("6. TYPE x BOOK")
    print("=" * 104)
    types = ["MCQ", "Assorted", "Fill in the blanks", "Match the column", "Assertion or Reasoning"]
    print(tbl([[b] + [report["type_by_book"][b].get(t, 0) for t in types] for b in BOOK_ORDER],
              ["book"] + [t[:14] for t in types]))

    print("\n" + "=" * 104)
    print("7. SUBTYPE TOTALS")
    print("=" * 104)
    print(tbl([[k, v, SOURCE_MATERIAL.get(k, "?")] for k, v in report["subtype_total"].items()],
              ["subtype", "questions", "source"]))

    print("\nWrote %s/eda.json" % OUT)


if __name__ == "__main__":
    main()
