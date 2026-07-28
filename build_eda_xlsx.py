#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the EDA workbook from eda_out/eda.json."""
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SRC = "/sessions/loving-trusting-wright/mnt/outputs/eda_out/eda.json"
OUT = "/sessions/loving-trusting-wright/mnt/outputs/AyurShloka_QA_EDA.xlsx"

R = json.load(open(SRC, encoding="utf-8"))
TOTAL_Q = sum(b["questions"] for b in R["per_book"])
TOTAL_C = sum(b["chunks"] for b in R["per_book"])

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
TITLE_FONT = Font(name=FONT, bold=True, size=13, color="1F3864")
NOTE_FONT = Font(name=FONT, italic=True, size=9, color="595959")
BODY = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
TOTAL_FILL = PatternFill("solid", fgColor="D9E2F3")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(bottom=THIN)

wb = Workbook()
wb.remove(wb.active)


def sheet(name, title, note, header, rows, widths, formats=None, total_row=None):
    ws = wb.create_sheet(name)
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A2"] = note
    ws["A2"].font = NOTE_FONT
    r0 = 4
    for j, h in enumerate(header, 1):
        c = ws.cell(r0, j, h)
        c.font = HDR_FONT
        c.fill = HDR_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, row in enumerate(rows):
        for j, v in enumerate(row, 1):
            c = ws.cell(r0 + 1 + i, j, v)
            c.font = BODY
            c.border = BORDER
            if formats and j in formats:
                c.number_format = formats[j]
            if j == 1:
                c.alignment = Alignment(horizontal="left")
    if total_row:
        rr = r0 + 1 + len(rows)
        for j, v in enumerate(total_row, 1):
            c = ws.cell(rr, j, v)
            c.font = BOLD
            c.fill = TOTAL_FILL
            if formats and j in formats:
                c.number_format = formats[j]
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


# ---------------------------------------------------------------- 1. summary
ws = wb.create_sheet("Summary")
ws["A1"] = "AyurShloka-QA — dataset EDA"
ws["A1"].font = Font(name=FONT, bold=True, size=16, color="1F3864")
ws["A2"] = "Questions generated from 8 classical Ayurvedic texts, joined back to their source chunks."
ws["A2"].font = NOTE_FONT
s = R["chunk_yield_summary"]
sm = R["source_material_total"]
facts = [
    ("Source texts", 8, ""),
    ("Source chunks", TOTAL_C, "one shloka + commentary unit"),
    ("Chunks yielding >=1 question", s["chunks_used"], ""),
    ("Chunks yielding none", s["chunks_unused"], "see 'Unused Chunks' sheet"),
    ("Chunk coverage", s["chunks_used"] / TOTAL_C, ""),
    ("", "", ""),
    ("Questions generated", TOTAL_Q, ""),
    ("Mean questions per chunk", s["mean"], ""),
    ("Median questions per chunk", s["median"], ""),
    ("Max from a single chunk", s["max"], ""),
    ("", "", ""),
    ("Grounded in shloka only", sm.get("shloka", 0), "verse quoted; answer is verse or its subject"),
    ("Grounded in shloka + commentary", sm.get("both", 0), "verse in stem, commentary supplies answer"),
    ("Grounded in commentary only", sm.get("commentary", 0), "fact drawn from prose commentary"),
    ("Grounded in provenance", sm.get("provenance", 0), "locate the sthana / chapter / verse"),
    ("", "", ""),
    ("Shloka involved in some form", sm.get("shloka", 0) + sm.get("both", 0), ""),
    ("Commentary involved in some form", sm.get("commentary", 0) + sm.get("both", 0), ""),
]
r = 4
ws.cell(r, 1, "Metric").font = HDR_FONT
ws.cell(r, 1).fill = HDR_FILL
ws.cell(r, 2, "Value").font = HDR_FONT
ws.cell(r, 2).fill = HDR_FILL
ws.cell(r, 3, "Note").font = HDR_FONT
ws.cell(r, 3).fill = HDR_FILL
for i, (k, v, n) in enumerate(facts):
    ws.cell(r + 1 + i, 1, k).font = BOLD if k and not n else BODY
    c = ws.cell(r + 1 + i, 2, v)
    c.font = BODY
    if isinstance(v, float) and v < 1:
        c.number_format = "0.0%"
    elif isinstance(v, (int, float)):
        c.number_format = "#,##0.00" if isinstance(v, float) else "#,##0"
    ws.cell(r + 1 + i, 3, n).font = NOTE_FONT
ws.column_dimensions["A"].width = 36
ws.column_dimensions["B"].width = 14
ws.column_dimensions["C"].width = 52

note = R["data_notes"]
rr = r + len(facts) + 3
ws.cell(rr, 1, "Data notes").font = TITLE_FONT
ws.cell(rr + 1, 1, "chunk_id is unique WITHIN a book, not across books: %d ids collide between "
                   "Madhava Nidanam Part 1 and Part 2." % note["chunk_id_collisions_across_books"]).font = BODY
ws.cell(rr + 2, 1, "Join on (source_book, chunk_id), never chunk_id alone.").font = BODY
ws.cell(rr + 3, 1, "Orphan questions (chunk_id not found in any source file): %d"
        % note["orphan_questions"]).font = BODY

# ---------------------------------------------------------------- 2. by book
rows = []
for b in R["per_book"]:
    rows.append([b["book"], b["chunks"], b["chunks_used"], b["chunks_used"] / b["chunks"],
                 b["questions"], b["questions"] / b["chunks"], b["questions"] / TOTAL_Q])
sheet("By Book", "Questions and chunk coverage per source text",
      "Coverage = chunks that produced at least one question. q/chunk is over all chunks, not just used ones.",
      ["Book", "Chunks", "Chunks used", "Coverage", "Questions", "Q per chunk", "Share of set"],
      rows, [30, 10, 12, 11, 11, 12, 12],
      {4: "0.0%", 2: "#,##0", 3: "#,##0", 5: "#,##0", 6: "0.00", 7: "0.0%"},
      ["TOTAL", TOTAL_C, R["chunk_yield_summary"]["chunks_used"],
       R["chunk_yield_summary"]["chunks_used"] / TOTAL_C, TOTAL_Q, TOTAL_Q / TOTAL_C, 1.0])

# ---------------------------------------------------------------- 3. raw material
rows = [[m["book"], m["chunks"], m["both_pct"] / 100, m["shloka_only_pct"] / 100,
         m["commentary_only_pct"] / 100, m["neither_pct"] / 100,
         m["median_shloka_chars"], m["median_commentary_chars"], m["hindi_only_commentary"]]
        for m in R["raw_material"]]
sheet("Raw Material", "What each chunk actually contains",
      "The generator can only build a verse question where a shloka exists, and a commentary "
      "question where English commentary exists. 'Neither' chunks are headings and front matter.",
      ["Book", "Chunks", "Shloka + commentary", "Shloka only", "Commentary only", "Neither",
       "Median shloka chars", "Median commentary chars", "Hindi-only commentary"],
      rows, [30, 10, 18, 13, 15, 11, 16, 18, 18],
      {2: "#,##0", 3: "0.0%", 4: "0.0%", 5: "0.0%", 6: "0.0%", 7: "#,##0", 8: "#,##0", 9: "#,##0"})

# ---------------------------------------------------------------- 4. source material
order = ["shloka", "both", "commentary", "provenance"]
rows = []
for b in R["per_book"]:
    d = R["source_material_by_book"][b["book"]]
    rows.append([b["book"]] + [d.get(k, 0) for k in order] + [b["questions"]])
tot = [sum(R["source_material_by_book"][b["book"]].get(k, 0) for b in R["per_book"]) for k in order]
sheet("Source Material", "Which source material each question draws on",
      "shloka = verse quoted, answer is the verse or its subject · both = verse in the stem, "
      "commentary supplies the answer · commentary = fact from prose · provenance = locate the "
      "sthana/chapter/verse.",
      ["Book", "Shloka", "Shloka + commentary", "Commentary", "Provenance", "Total"],
      rows, [30, 11, 18, 13, 12, 11],
      {2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0", 6: "#,##0"},
      ["TOTAL"] + tot + [TOTAL_Q])

# ---------------------------------------------------------------- 5. type x book
types = ["MCQ", "Assorted", "Fill in the blanks", "Match the column", "Assertion or Reasoning"]
rows = [[b["book"]] + [R["type_by_book"][b["book"]].get(t, 0) for t in types] + [b["questions"]]
        for b in R["per_book"]]
tot = [sum(R["type_by_book"][b["book"]].get(t, 0) for b in R["per_book"]) for t in types]
sheet("Type by Book", "Question type distribution per text",
      "Match the column needs 4 sibling chunks with compact headings, so texts with sentence-like "
      "headings (Sushruta, Sharangadhara) produce very few.",
      ["Book"] + types + ["Total"], rows, [30, 10, 10, 15, 15, 18, 10],
      {i: "#,##0" for i in range(2, 8)}, ["TOTAL"] + tot + [TOTAL_Q])

# ---------------------------------------------------------------- 6. subtype
SM = {"verse_subject": "shloka", "sanskrit_pada": "shloka", "verse_translation": "both",
      "verse_exposition": "both", "transliterate_and_explain": "both",
      "topic_to_reference": "provenance", "locate_sthana": "provenance",
      "locate_chapter": "provenance", "one_line_source": "provenance"}
rows = [[k, v, v / TOTAL_Q, SM.get(k, "commentary")] for k, v in R["subtype_total"].items()]
sheet("Subtype", "All 23 question subtypes",
      "Subtype is the finest-grained label; use it to over-sample a weak category when building "
      "the fine-tuning mix.",
      ["Subtype", "Questions", "Share", "Source material"], rows, [30, 12, 10, 16],
      {2: "#,##0", 3: "0.0%"}, ["TOTAL", TOTAL_Q, 1.0, ""])

# ---------------------------------------------------------------- 7. difficulty
diffs = ["Easy", "Medium", "Hard"]
rows = [[b["book"]] + [R["difficulty_by_book"][b["book"]].get(d, 0) for d in diffs] + [b["questions"]]
        for b in R["per_book"]]
tot = [sum(R["difficulty_by_book"][b["book"]].get(d, 0) for b in R["per_book"]) for d in diffs]
sheet("Difficulty", "Difficulty split per text",
      "Assigned from question type and commentary length, not measured against model performance.",
      ["Book"] + diffs + ["Total"], rows, [30, 11, 11, 11, 11],
      {2: "#,##0", 3: "#,##0", 4: "#,##0", 5: "#,##0"}, ["TOTAL"] + tot + [TOTAL_Q])

# ---------------------------------------------------------------- 8. domain
rows = [[k, v, v / TOTAL_Q] for k, v in R["domain_total"].items()]
sheet("Subject Domain", "BhashaBench-Ayur subject domains",
      "Mapped from each chunk's category keywords and sthana.",
      ["Subject domain", "Questions", "Share"], rows, [56, 12, 10],
      {2: "#,##0", 3: "0.0%"}, ["TOTAL", TOTAL_Q, 1.0])

# ---------------------------------------------------------------- 9. chunk yield
rows = [[int(k), v, v / TOTAL_C] for k, v in R["chunk_yield_hist"].items()]
sheet("Chunk Yield", "How many questions each chunk produced",
      "A long tail: content-rich chunks with both a verse and a substantial commentary carry "
      "the most weight.",
      ["Questions from chunk", "Number of chunks", "Share of chunks"], rows, [22, 18, 16],
      {2: "#,##0", 3: "0.0%"}, ["TOTAL", TOTAL_C, 1.0])

# ---------------------------------------------------------------- 10. unused
u = R["unused_reasons"]
rows = [["Total unused chunks", u["total"]],
        ["  no shloka and no usable commentary", u["no_shloka_no_commentary"]],
        ["  Hindi-only commentary (no English rendering)", u["hindi_only_commentary"]],
        ["  shloka present but too short / garbled", u["shloka_only_short"]],
        ["  commentary present but no shloka", u["commentary_only"]],
        ["", ""]] + [["  " + k, v] for k, v in sorted(u["by_book"].items(), key=lambda x: -x[1])]
sheet("Unused Chunks", "Chunks that produced no question, and why",
      "Mostly front matter, section headings and colophons that carry no teachable content.",
      ["Reason / book", "Chunks"], rows, [46, 10], {2: "#,##0"})

# ---------------------------------------------------------------- 11. sthana
rows = [[x["book"], x["sthana"], x["chunks"], x["questions"], x["q_per_chunk"]]
        for x in R["by_sthana"]]
sheet("By Sthana", "Chunks and questions per sthana / varga",
      "Sorted by book, then by question count.",
      ["Book", "Sthana / Varga", "Chunks", "Questions", "Q per chunk"], rows,
      [30, 34, 10, 11, 12], {3: "#,##0", 4: "#,##0", 5: "0.00"},
      ["TOTAL", "", TOTAL_C, TOTAL_Q, TOTAL_Q / TOTAL_C])

# ---------------------------------------------------------------- 12. chapter
rows = [[x["book"], x["sthana"], x["chapter"], x["chapter_title"], x["chunks"],
         x["questions"], x["q_per_chunk"]] for x in R["by_chapter"]]
sheet("By Chapter", "Chunks and questions per chapter (%d chapters)" % len(R["by_chapter"]),
      "Use this to spot chapters that are under-represented in the fine-tuning mix.",
      ["Book", "Sthana", "Ch #", "Chapter title", "Chunks", "Questions", "Q per chunk"],
      rows, [28, 26, 7, 44, 9, 11, 12],
      {3: "0", 5: "#,##0", 6: "#,##0", 7: "0.00"},
      ["TOTAL", "", "", "", TOTAL_C, TOTAL_Q, TOTAL_Q / TOTAL_C])

wb.save(OUT)
print("wrote", OUT)
print("sheets:", wb.sheetnames)
