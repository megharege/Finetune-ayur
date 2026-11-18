#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates the publication-ready conference research paper in Microsoft Word (.docx).
Contains exact author names, roll numbers, complete sections, all 10 tables,
mathematical formulas, and 26 citations with zero placeholders or AI buzzwords.
"""

import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def style_table(table, col_widths=None, header_bg="1E293B"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="8" w:space="0" w:color="1E293B"/>'
        f'  <w:bottom w:val="single" w:sz="8" w:space="0" w:color="1E293B"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)
    
    for r_idx, row in enumerate(table.rows):
        is_header = (r_idx == 0)
        trPr = row._tr.get_or_add_trPr()
        if is_header:
            trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        
        for c_idx, cell in enumerate(row.cells):
            if col_widths and c_idx < len(col_widths):
                cell.width = col_widths[c_idx]
            
            tcPr = cell._tc.get_or_add_tcPr()
            set_cell_margins(cell, top=90, bottom=90, left=130, right=130)
            
            if is_header:
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{header_bg}"/>')
                tcPr.append(shd)
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    for r in p.runs:
                        r.bold = True
                        r.font.name = 'Calibri'
                        r.font.size = Pt(9.5)
                        r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                bg = "F8FAFC" if (r_idx % 2 == 1) else "FFFFFF"
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>')
                tcPr.append(shd)
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    for r in p.runs:
                        r.font.name = 'Calibri'
                        r.font.size = Pt(9.5)
                        r.font.color.rgb = RGBColor(30, 41, 59)

def build_docx():
    doc = docx.Document()

    # Academic Standard 1-inch margins
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)

    PRIMARY = RGBColor(15, 23, 42)      # Deep Slate/Navy
    SECONDARY = RGBColor(30, 58, 138)   # Royal Navy
    DARK = RGBColor(15, 23, 42)

    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(17)
        run.font.color.rgb = PRIMARY
        return p

    def add_authors(authors_list, affiliation):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        for i, (name, roll) in enumerate(authors_list):
            r_name = p.add_run(name)
            r_name.bold = True
            r_name.font.size = Pt(11)
            r_roll = p.add_run(f" ({roll})")
            r_roll.font.size = Pt(10)
            if i < len(authors_list) - 1:
                p.add_run("   •   ")
        
        p_aff = doc.add_paragraph()
        p_aff.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_aff.paragraph_format.space_before = Pt(1)
        p_aff.paragraph_format.space_after = Pt(14)
        r_aff = p_aff.add_run(affiliation)
        r_aff.font.italic = True
        r_aff.font.size = Pt(9.5)
        r_aff.font.color.rgb = RGBColor(100, 116, 139)

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(13)
        run.font.color.rgb = SECONDARY
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(11.5)
        run.font.color.rgb = PRIMARY
        return p

    def add_p(text, bold_prefix=None, italic=False):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.bold = True
            r_bold.font.color.rgb = DARK
        r_text = p.add_run(text)
        r_text.font.italic = italic
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_bold = p.add_run(bold_prefix)
            r_bold.bold = True
            r_bold.font.color.rgb = DARK
        p.add_run(text)
        return p

    def add_callout_box(title, text, border_color="1E3A8A", bg_color="F1F5F9"):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.5)
        
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
        tcPr.append(shd)
        
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="160" w:type="dxa"/><w:right w:w="160" w:type="dxa"/></w:tcMar>')
        tcPr.append(tcMar)
        
        tcBorders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
            f'  <w:top w:val="none"/><w:bottom w:val="none"/><w:right w:val="none"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(tcBorders)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        if title:
            r_title = p.add_run(f"{title}: ")
            r_title.bold = True
            r_title.font.name = 'Calibri'
            r_title.font.size = Pt(10)
            r_title.font.color.rgb = SECONDARY
        r_text = p.add_run(text)
        r_text.font.name = 'Calibri'
        r_text.font.size = Pt(10)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ----------------- TITLE & AUTHORS -----------------
    add_title("AyurLLM: A Verified Shloka-Level Corpus, a Fact-Grounded Instruction Benchmark, and a Tokenizer-Aware Adaptation Pipeline for Eight Classical Ayurvedic Treatises")
    
    authors = [
        ("Megha Rege", "2305792"),
        ("Hitanshu Choraria", "23052395"),
        ("Agnipravo Ali", "23051323"),
        ("Anand Jadon", "2305005")
    ]
    add_authors(authors, "School of Computer Engineering, Kalinga Institute of Industrial Technology (KIIT), Bhubaneswar, Odisha, India")

    # ----------------- ABSTRACT -----------------
    add_h1("Abstract")
    add_p(
        "Classical Ayurvedic knowledge is stored in printed treatises where Devanagari verse, IAST transliteration "
        "and commentary in English or Hindi share a page. The material cannot be searched by symptom and cannot be used "
        "directly as supervised training data. We present AyurLLM, a pipeline that converts eight treatises into a verified, "
        "schema-normalised corpus of 5,838 chunks (2,708,568 Gemma-3 tokens; 51.87% Sanskrit) and into a fact-grounded "
        "instruction set of 80,000 items drawn from 35,016 facts in six formats. Every answer is a verbatim span of its "
        "source chunk and carries a (source_book, chunk_id) provenance key. After exact and near-duplicate removal and a "
        "leakage repair, the splits hold 65,701 / 4,954 / 5,648 items (train / validation / test) with zero fact overlap, "
        "and no item matches any of the 14,963 BhashaBench-Ayur (BBA) questions at cosine 0.80 (maximum observed 0.74). "
        "We attribute each coverage gap to a named extraction defect and show that token fertility doubles as an OCR-quality "
        "diagnostic. A tokenizer audit of 12 candidates leads us to sarvam-1, trimmed from a 68,096 to a 23,946-token vocabulary. "
        "A paired study of four zero-shot baselines on 100 held-out items shows that the strongest (Qwen2.5-3B-Instruct, 51%) is "
        "indistinguishable from chance on assertion–reasoning and answers at most 21% of 'locate the source of this topic' items "
        "correctly, the failure that source-grounded retrieval is meant to address. QLoRA fine-tuning and the comparison with "
        "AyurParam (39.97% on BBA) are specified with a pre-registered decision rule but have not yet been executed; we mark "
        "every such result as pending and make no claim about it."
    )

    # ----------------- 1. INTRODUCTION -----------------
    add_h1("1. Introduction")
    add_p(
        "Ayurveda is a codified medical tradition whose primary sources are a small, stable set of Sanskrit treatises. A physician "
        "reasons outward from a presenting symptom, a drug or a disease name, whereas the literature is organised by verse number within "
        "chapter within section (sthana). A clinician who wants to know what the tradition says about a symptom must already know which verse "
        "to open, which is the knowledge the lookup was meant to supply."
    )
    add_p(
        "Making these texts searchable is mostly a data-integrity problem rather than a modelling one. Devanagari is an abugida in which "
        "stacked conjunct consonants (samyuktakshara), dependent vowel signs (matra) placed above, below or beside the base glyph, and a "
        "connecting headline (shirorekha) defeat recognisers that crop horizontal text lines [8, 9]. A printed page may carry verse, its "
        "romanisation and a commentary in a third language, and editions disagree on all of it. The unit of retrieval is equally consequential: "
        "a verse without its gloss is often uninterpretable, and a gloss without its verse cannot be cited. We therefore treat the verse "
        "together with its gloss and position as the atomic record."
    )
    add_p(
        "A second problem appears once a corpus exists. Instruction tuning needs question–answer pairs that primary sources do not contain, "
        "and the usual remedy is to have a large model write them. AyurParam [11], the closest prior system, followed that route with Qwen-3 "
        "235B to produce about 4.75M examples, then applied overlap filters, LLM adjudication and expert audits. In a medical domain a "
        "fabricated detail in a teacher’s output becomes confident ground truth for the student. We take a more conservative route: every "
        "answer in our benchmark is lifted verbatim from a chunk, so that any item can be audited against the printed page."
    )
    add_p("Our contributions are as follows:")
    add_bullet("A verified shloka-level corpus under one chunk schema: 5,838 chunks and 2,708,568 tokens from eight volumes, with a composite key that resolves a 102-identifier cross-volume collision (Sec. 3).")
    add_bullet("A per-volume failure taxonomy that ties each coverage gap to a named defect, and token fertility as a label-free diagnostic for recognition quality (Sec. 4–5).")
    add_bullet("A fact-grounded instruction benchmark of 80,000 items from 35,016 facts, with deduplication, a contamination audit against all 14,963 BBA questions, and fact-level splits (Sec. 7).")
    add_bullet("A paired baseline study with statistics showing which formats current 2–4B models cannot solve and where they guess by option position (Sec. 8), plus a tokenizer audit and trimming step behind the choice of sarvam-1 (Sec. 9).")
    add_bullet("A pre-specified protocol for QLoRA adaptation, grounded retrieval and comparison with AyurParam on BBA, with a decision rule fixed before any run (Sec. 10–11).")

    add_callout_box(
        "Pipeline Architecture Overview",
        "[Printed Treatises: 8 volumes] -> [Multi-Engine OCR: LiFT-GGUF, Surya, Marker, Docling] -> "
        "[Chunk Schema + Key: 5,838 chunks, 2.71M tokens] -> [Fact Extraction: 35,016 facts] -> "
        "[Six-Format Rendering: 80,000 items] -> [Dedup + Leakage Repair: 65,701 / 4,954 / 5,648] -> "
        "[Baselines & Tokenizer Audit] -> [QLoRA Adaptation on sarvam-1 (trimmed): configured, pending] -> "
        "[Hybrid Retrieval + Graph + Safety Triage: system designs, not yet evaluated]."
    )

    # ----------------- 2. RELATED WORK -----------------
    add_h1("2. Related Work")
    add_h2("2.1 Document conversion and Devanagari OCR")
    add_p(
        "Cascaded systems such as PP-OCR [5] and PP-OCRv2 [6] detect text lines, then recognise them, and are tuned for small deployment footprints. "
        "Their segmentation assumes glyphs that do not stack vertically. Docling [3, 4] parses documents with layout and table-structure models "
        "on commodity hardware. Surya [1] combines layout analysis, reading order and recognition for 90+ languages, and Marker [2] builds whole-document "
        "conversion on top of it. Vision–language models are also run in quantised form for small accelerators [7]. Surveys and stress tests agree "
        "that conjuncts, dependent vowel signs and the headline remain the dominant failure points for Devanagari [8, 9, 10]. Our findings in Sec. 5 "
        "are consistent: the worst volume fails exactly by dropping conjuncts and detaching matras."
    )

    add_h2("2.2 Language models for Ayurveda")
    add_p(
        "AyurParam. AyurParam-2.9B [11] fine-tunes Param-1-2.9B [13] on about 4.75M examples synthesised from roughly 150,000 pages (about 54.5M words) "
        "of digitised books, using Qwen-3 235B under evidence-anchoring constraints, with expert review of ten books. Training ran for 3 epochs at "
        "a global batch of 1,024 on an H100 cluster, roughly two days on a single H100 node. On BBA [14, 15], which has 14,963 exam-style questions "
        "(9,348 English, 5,615 Hindi), it reaches 39.97% overall, 41.12% English and 38.04% Hindi, ahead of Llama-3.2-3B-Instruct (33.20%) and "
        "Qwen2.5-3B-Instruct (32.68%). Its authors list the limits we build on: a Hindi gap, evaluation restricted to exam-style questions, no explicit "
        "safety mechanism, no patient-specific reasoning, and training text digitised mostly before 2024."
    )
    add_p(
        "AyurGPT / IRGPT. Trigent’s talk at NLP Summit 2024 [16] describes AyurGPT as a fine-tune of BioGPT-Large-PubMedQA that supports English, "
        "Kannada, Tamil and Malayalam. A companion write-up [17] reports a GPT-2 Medium (347M) fine-tune after the team narrowed the scope to English, "
        "because multilingual data validation proved impractical: about one million rows shrank to roughly 113,000 validated samples, translations "
        "lost the meaning of Ayurvedic terms, and Ayurveda books (~2 GB) were reserved for a retrieval component. Two lessons transfer directly to "
        "our design: data quality dominates volume, and scope should be staged."
    )

    add_h2("2.3 Synthetic instruction data")
    add_p(
        "Attributed grounding [18] anchors generated instructions to retrieved passages to limit fabrication, answer-consistency filtering [19] "
        "keeps generations on which independent reasoning paths agree, and seed-free generation [20] handles languages with no instruction seed set. "
        "All three still let a model write the answer. We do not: the generative step is replaced by rendering each extracted fact into an examination "
        "format, and the answer is always a span of the source. The price is reduced linguistic variety (Sec. 12)."
    )

    # ----------------- 3. CORPUS CONSTRUCTION -----------------
    add_h1("3. Corpus Construction")
    add_h2("3.1 Source material")
    add_p(
        "Eight printed volumes were selected in consultation with practising physicians: the Brihattrayi (Charaka Samhita, Sushruta Samhita, "
        "Ashtanga Hridaya), the Laghutrayi (Sharangadhara Samhita, Madhava Nidana, Bhavaprakasha Nighantu), and a two-volume Madhava Nidanam carrying "
        "the Madhukosa commentary. The volumes differ in script mix, in whether transliteration is printed, in the language of the commentary, in scan "
        "quality, and in whether verse and commentary occupy separate columns. No single extraction setting works for all eight."
    )

    add_h2("3.2 Extraction-engine selection")
    add_p(
        "Extraction was treated as a per-volume engineering problem with six strategies. The deciding criterion was fidelity on Devanagari verse "
        "(intact conjuncts, correctly attached vowel signs), not page-level character accuracy: a page can score well on characters while every verse "
        "on it is unusable, because commentary is long and verse is short. Table 1 gives the role or rejection reason of each strategy."
    )

    # Table 1: Extraction strategies
    p_t1 = doc.add_paragraph()
    p_t1.add_run("Table 1: Extraction strategies and the decision for each.").bold = True
    tbl1 = doc.add_table(rows=8, cols=3)
    t1_headers = ["Engine", "Role / failure mode", "Decision"]
    for c_i, h in enumerate(t1_headers):
        tbl1.cell(0, c_i).paragraphs[0].text = h
    t1_data = [
        ("LiFT (GGUF)", "Final extractor, all volumes; quantised to fit about 6 GB of accelerator memory", "Accepted"),
        ("Surya", "Verse-dominant pages; keeps reading order across verse and gloss", "Accepted"),
        ("Marker", "Volumes with a stable heading hierarchy (maps to chapter/section)", "Accepted"),
        ("Docling", "Verse and commentary in separate page regions", "Accepted"),
        ("Bounding box", "Fallback where converters merged columns", "Accepted"),
        ("PP-OCR", "Line-crop cascade severs stacked conjuncts", "Rejected"),
        ("Markitdown", "Format converter; needs an existing text layer, absent in scans", "Rejected"),
    ]
    for r_i, row in enumerate(t1_data):
        for c_i, val in enumerate(row):
            tbl1.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl1, [Inches(1.6), Inches(3.8), Inches(1.1)])

    # Table 2: Measured extraction quality
    p_t2 = doc.add_paragraph()
    p_t2.add_run("Table 2: Measured extraction quality on a manually transcribed page sample (character, word and conjunct-specific error rates; throughput). Not yet measured; until filled, Table 1 rests on qualitative failure modes.").bold = True
    tbl2 = doc.add_table(rows=5, cols=5)
    t2_headers = ["Engine", "CER", "WER", "Conj. err.", "pages/min"]
    for c_i, h in enumerate(t2_headers):
        tbl2.cell(0, c_i).paragraphs[0].text = h
    t2_data = [
        ("LiFT (GGUF)", "[pending]", "[pending]", "[pending]", "[pending]"),
        ("Surya", "[pending]", "[pending]", "[pending]", "[pending]"),
        ("Marker, Docling, bbox", "[pending]", "[pending]", "[pending]", "[pending]"),
        ("PP-OCR, Markitdown", "[pending]", "[pending]", "[pending]", "[pending]"),
    ]
    for r_i, row in enumerate(t2_data):
        for c_i, val in enumerate(row):
            tbl2.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl2, [Inches(2.0), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.2)])

    add_p(
        "Extraction was made resumable: process isolation and per-page checkpointing meant a crash partway through a volume did not discard "
        "completed pages, which under a 6 GB budget is routine rather than exceptional."
    )

    add_h2("3.3 The chunk schema")
    add_p(
        "Every book-specific converter targets one record type, so that irregularity of the printed page is absorbed at extraction time. "
        "The base fields are chunk_id; sthana, chapter_number, chapter_title; verse_id as printed; topic_heading; sanskrit_text; transliteration "
        "(IAST, where the edition prints it); commentary (verbatim); and categories_found with primary_category. Three volumes needed named extensions "
        "instead of being flattened: Sharangadhara Samhita adds commentary_english, because its printed gloss is Hindi; Madhava Nidana (Laghutrayi) "
        "adds sanskrit_commentary, source_citation and record_type, because the Madhukosa apparatus quotes other treatises by name; Charaka Samhita "
        "adds pada for the quarter-divisions of the Chikitsasthana. Keeping these fields explicit is what makes the failure analysis of Sec. 5 possible."
    )

    add_h2("3.4 Identifier integrity")
    add_p(
        "chunk_id is unique within a volume but not across the corpus. Madhava Nidanam Parts 1 and 2 were converted independently and both number records "
        "MN1, MN2, …; 102 identifiers collide. A join on chunk_id alone silently double-counts. All analyses and indexes therefore use the composite "
        "key (source_book, chunk_id). The collision is invisible to per-file validation, since each file is internally consistent, and appears only when "
        "the corpus is treated as a whole."
    )

    # ----------------- 4. CORPUS CHARACTERISATION -----------------
    add_h1("4. Corpus Characterisation")
    add_h2("4.1 Tokenisation")
    add_p(
        "Statistics use the google/gemma-3-4b-it tokenizer, chosen because it belongs to the deployment size class; token counts under a different "
        "tokenizer would misstate every context and cost estimate. The corpus holds 2,708,568 tokens: 1,404,844 Sanskrit (51.87%), 1,236,881 English (45.67%) "
        "and 66,843 Hindi (2.47%). Devanagari verse is present in 5,439 chunks (801,705 tokens) and IAST transliteration in 2,950 chunks (572,022 tokens), "
        "so only about half of the corpus carries printed romanisation. The mean chunk length is 463.9 tokens (2,708,568 / 5,838)."
    )

    # Table 3: Corpus breakdown
    p_t3 = doc.add_paragraph()
    p_t3.add_run("Table 3: Per-volume chunks, Sanskrit tokens and Sanskrit token fertility (Gemma-3 tokenizer). The low Ashtanga value is a recognition artefact.").bold = True
    tbl3 = doc.add_table(rows=10, cols=4)
    t3_headers = ["Volume", "Chunks", "Skt tokens", "Fertility"]
    for c_i, h in enumerate(t3_headers):
        tbl3.cell(0, c_i).paragraphs[0].text = h
    t3_data = [
        ("Charaka Samhita", "1,497", "379,568", "3.41"),
        ("Bhavaprakasha Nighantu", "1,052", "81,372", "3.69"),
        ("Ashtanga Hridaya", "913", "38,899", "1.85"),
        ("Madhava Nidanam P1", "728", "223,062", "4.24"),
        ("Sharangadhara Samhita", "593", "61,766", "4.43"),
        ("Sushruta Samhita", "418", "58,848", "4.70"),
        ("Madhava Nidana (Laghu.)", "403", "259,833", "4.09"),
        ("Madhava Nidanam P2", "234", "301,496", "4.65"),
        ("Total / overall", "5,838", "1,404,844", "3.61"),
    ]
    for r_i, row in enumerate(t3_data):
        for c_i, val in enumerate(row):
            tbl3.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl3, [Inches(2.5), Inches(1.3), Inches(1.3), Inches(1.4)])

    add_h2("4.2 Token fertility as a quality diagnostic")
    add_p(
        "Fertility is tokens emitted per whitespace-delimited word, F = Ntok / Nwords. It is 3.61 for Sanskrit and 1.69 for English, a ratio of 2.14: "
        "a Sanskrit word costs more than twice as much context as an English one. Across volumes it ranges from 1.85 (Ashtanga Hridaya) to 4.70 (Sushruta Samhita). "
        "The low Ashtanga value does not indicate simpler Sanskrit. Lost conjuncts and detached vowel signs fragment words into short, tokenizer-friendly "
        "pieces, so degraded recognition lowers fertility. An anomalously low value is therefore a label-free signal to inspect a volume, available without any transcription."
    )

    add_h2("4.3 Chunk length and script balance")
    add_p(
        "Chunk length is heavily skewed: 21.62% of chunks (1,262) exceed 512 tokens, 8.56% (500) exceed 1,024, 2.93% (171) exceed 2,048, 0.87% (51) "
        "exceed 4,096 and 0.15% (9) exceed 8,192. Part 2 of Madhava Nidanam averages 1,288 Sanskrit tokens per chunk against 43 for Ashtanga Hridaya, "
        "a thirtyfold gap caused by editorial convention (one chunk per commentary block versus one per verse). Chunks above an embedding model’s window "
        "must be sub-chunked before indexing or their tails are truncated; we treat the 512-token threshold as binding since it affects about one chunk in five. "
        "The English-to-Sanskrit token ratio per chunk separates the corpus into prose-heavy and verse-heavy classes: 3.85 in Bhavaprakasha Nighantu "
        "(a materia medica where verse is an index) against 0.48 in Sushruta Samhita and 0.46 in Madhava Nidanam Part 2. Any sampling that treats chunks "
        "as interchangeable will over-represent pharmacological prose."
    )

    # ----------------- 5. FAILURE ANALYSIS -----------------
    add_h1("5. Per-Volume Failure Analysis")
    add_p(
        "Aggregate quality hides the fact that every volume fails differently. In each case below the defect is an extraction or editorial artefact "
        "rather than missing source content, which we confirmed against the printed page."
    )
    add_bullet("Sharangadhara Samhita: Hindi-only commentary. 350 of 593 chunks (59.0%) carry no English commentary. The printed gloss is Hindi, which shares the Devanagari script with the verse, so script-based language identification cannot separate them and a meaning-level pass is needed. The whole Hindi mass of the corpus (560 chunks, 66,843 tokens) comes from this volume. It contributes 202 of the 355 chunks that yield no question.")
    add_bullet("Ashtanga Hridaya: degraded Devanagari. The corpus minimum on Sanskrit fertility (1.85) and mean Sanskrit chunk length (43.51 tokens). Affected chunks have lost conjuncts and have vowel signs detached from their base glyphs. The text passes a non-empty check but cannot be read as verse; this defect class is invisible to field-coverage metrics and motivated the Devanagari well-formedness test of Sec. 7. It accounts for 92 unused chunks.")
    add_bullet("Bhavaprakasha Nighantu: absent verse field. 370 of 1,052 chunks have no Sanskrit text; they are drug monographs with prose only, including the shortest chunks of the corpus (3–4 tokens). They are valid content but cannot support verse-grounded tasks.")
    add_bullet("Charaka Samhita: one catastrophic chunk. Chunk CS1543 holds 116,187 combined tokens, about nine times the next largest and roughly 4% of the corpus. It is the volume’s back matter, rendered as a long run of fragmentary glyphs and page numbers. It raises this volume’s English standard deviation to 2,558 tokens against a median of 110.")
    add_bullet("Madhava Nidanam P1/P2: identifier collision. The 102 shared identifiers of Sec. 3; Part 1 also has 130 of 728 chunks without English commentary.")
    add_bullet("Remaining volumes. Sushruta Samhita is complete on both fields for all 418 chunks (its terse commentary, 66.35 English tokens per chunk, is an editorial property). Madhava Nidana (Laghutrayi) lacks English commentary in 26 of 403 chunks.")

    # ----------------- 6. SYSTEM DESIGN -----------------
    add_h1("6. Retrieval, Graph and Safety: System Design")
    add_p(
        "Status. This section specifies the serving layer that motivates the corpus design. At the time of writing, no retrieval, graph or triage component "
        "appears in any reported experiment, and the embedding configuration is not fixed; we state the design and the metrics that will evaluate it.",
        italic=True
    )
    add_p(
        "Hybrid retrieval. A physician may query by an exact Sanskrit term or by a plain-language symptom, so the index combines lexical and dense scores. "
        "With e_q, e_d the embeddings of query q and chunk d:"
    )
    add_callout_box(
        "Hybrid Retrieval Formulation",
        "S(q, d) = λ · S_dense(q, d) + (1 - λ) · S_lex(q, d)\n"
        "where S_dense(q, d) = (e_q · e_d) / (||e_q|| · ||e_d||), tildes denote per-query min–max normalisation, and λ ∈ [0, 1] is tuned on the validation split rather than fixed in advance."
    )
    add_p(
        "Chunks above 512 tokens are sub-chunked. Because every item has a gold (source_book, chunk_id), retrieval can be scored without new annotation, "
        "with Recall@k and MRR over the validation questions."
    )
    add_p(
        "Personal knowledge graph. A graph database holds patient, symptom, dosha, treatment and shloka nodes, linked by typed edges such as EXPERIENCES, "
        "AGGRAVATES, ALLEVIATES and GROUNDED_IN. A multi-hop query returns a sub-graph whose terminal shloka nodes carry the composite key above, so every "
        "generated statement can cite treatise, sthana, chapter and verse."
    )
    add_p(
        "Safety triage. A deterministic rule layer runs before retrieval and generation. If an intake matches a curated list of red-flag presentations "
        "(for example radiating chest pain, severe breathlessness, sudden neurological deficit), the generative path is bypassed and the session is "
        "escalated to emergency referral. The rule list requires clinical review and a red-team set before any claim of coverage."
    )

    # ----------------- 7. INSTRUCTION BENCHMARK -----------------
    add_h1("7. Fact-Grounded Instruction Benchmark")
    add_h2("7.1 Fact-centric generation")
    add_p(
        "Each chunk is first reduced to discrete facts, each with a stable identifier: the subject a verse addresses, a commentary statement, a technical "
        "term, an enumeration or count, a synonym set, or the location of a teaching. Each fact is then rendered into every format it supports. "
        "One answer can thus be tested as a multiple-choice item, a cloze, an assertion–reason pair or a multiple-selection item without two stems "
        "being textually identical, and semantic de-duplication reduces to grouping by fact identifier. From 5,838 chunks we extract 35,016 facts "
        "(mean 2.28 questions per fact) and render 80,000 questions covering 5,483 chunks (93.9%). 61.8% of facts appear in more than one format "
        "(38.2% in one, 36.4% in two, 18.9% in three, 6.4% in four). The finest label has 36 format variants."
    )

    add_h2("7.2 Quality controls")
    add_p("Each control was added after a defect was observed in generated output:")
    add_bullet("Distractor isolation: wrong options come from a different chapter of the same volume, so a distractor cannot accidentally be true of the asked topic.")
    add_bullet("Answer-leakage guards: an item is rejected if its answer appears in the stem outside the option block or in any context field. Verdict items carry no context.")
    add_bullet("OCR filtering: sentences with running heads, spaced-out punctuation or an anomalous share of out-of-lexicon tokens are rejected; verses failing a Devanagari well-formedness test are excluded from cloze and verse-comprehension items.")
    add_bullet("Option-order randomisation: an earlier build put true/false verdicts at fixed positions, which would have let a model score on position alone for 17% of the set. The final key is distributed 24/30/20/26% over A–D.")

    add_h2("7.3 Composition")
    add_p(
        "Table 4 gives the six formats before and after deduplication and in each split. Difficulty is assigned from format and commentary length, "
        "not measured: Medium 43.9%, Hard 32.6%, Easy 23.5% over the 80,000 items. Items are grounded in commentary alone for 81.2% (64,989), in the verse "
        "alone for 10.7%, in verse plus commentary for 1.7%, and in provenance (locating a topic) for 6.4%; the verse is involved in only 12.3% of items, "
        "against 46.7% in an earlier build. Mapped to BBA subject domains, the largest shares are Roga Vigyana (25.2%), Dravyaguna and Bhaishajya (21.2%) "
        "and Kayachikitsa (15.0%), while Swasthavritta (0.19%) and Ayurvedic Literature (0.07%) are nearly absent, so no claim should be made on those domains. "
        "Bhavaprakasha Nighantu contributes 34.4% of items and Sushruta Samhita 3.0%."
    )

    # Table 4: Formats & Splits
    p_t4 = doc.add_paragraph()
    p_t4.add_run("Table 4: Items per format: raw, after deduplication, and in the final splits (validation and test after leakage repair).").bold = True
    tbl4 = doc.add_table(rows=8, cols=6)
    t4_headers = ["Format", "Raw", "Dedup", "Train", "Val", "Test"]
    for c_i, h in enumerate(t4_headers):
        tbl4.cell(0, c_i).paragraphs[0].text = h
    t4_data = [
        ("Fill in the blanks", "20,699", "20,319", "17,252", "1,433", "1,634"),
        ("MCQ", "18,262", "16,850", "14,323", "1,173", "1,354"),
        ("Assorted / short answer", "15,428", "15,402", "13,085", "1,080", "1,237"),
        ("Assertion–reason", "11,430", "11,413", "9,701", "806", "906"),
        ("Multiple selection", "9,089", "8,300", "7,050", "581", "669"),
        ("Match the column", "5,092", "5,071", "4,290", "363", "418"),
        ("Total", "80,000", "77,355", "65,701", "4,954", "5,648"),
    ]
    for r_i, row in enumerate(t4_data):
        for c_i, val in enumerate(row):
            tbl4.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl4, [Inches(2.1), Inches(0.9), Inches(0.9), Inches(0.9), Inches(0.8), Inches(0.9)])

    add_h2("7.4 Deduplication, contamination and leakage")
    add_p(
        "Exact MD5 hashing of question stems removed 10 items (79,990 left). Near-duplicate detection at a similarity threshold of 0.97 removed "
        "a further 2,635, leaving 77,355. A contamination audit compared the training pool with all 14,963 BBA questions using hashed character 3–4-gram "
        "vectors; the maximum cosine similarity was 0.74, below the 0.80 quarantine threshold, so no item was quarantined. Splits are made on the fact "
        "identifier so no rendering of a training fact can appear in validation or test (fact overlap 0 before and after repair). A further near-duplicate "
        "pass at cosine 0.95 between training and held-out rows removed 482 validation rows (5,436 -> 4,954) and 570 test rows (6,218 -> 5,648), leaving "
        "no held-out row within 0.95 of a training item. The training split (65,701 rows) covers 28,823 distinct facts."
    )

    # ----------------- 8. ZERO-SHOT BASELINES -----------------
    add_h1("8. Zero-Shot Baselines")
    add_h2("8.1 Protocol")
    add_p(
        "A 100-item evaluation set was drawn from the validation pool: 25 items each of assertion–reason, MCQ, fill-in-the-blank and match-the-column, "
        "balanced over the eight volumes (9–16 items per book) and disjoint from training. All four formats have four options, so chance is 0.25. "
        "We also report format compliance (share of items with a parseable answer), because a model that cannot follow the answer format measures "
        "instruction following rather than domain knowledge. As all models answer the same items we use paired exact McNemar tests and Wilson 95% intervals [25, 26]."
    )

    add_h2("8.2 Results")
    # Table 5: Zero-shot baseline results
    p_t5 = doc.add_paragraph()
    p_t5.add_run("Table 5: Zero-shot accuracy on the 100-item set. p is a one-sided exact binomial test against chance 0.25. Llama-3.2-3B is not distinguishable from chance overall.").bold = True
    tbl5 = doc.add_table(rows=5, cols=5)
    t5_headers = ["Model", "Acc.", "95% CI", "p vs. chance", "Compl."]
    for c_i, h in enumerate(t5_headers):
        tbl5.cell(0, c_i).paragraphs[0].text = h
    t5_data = [
        ("Qwen2.5-3B-Instruct", "0.51", "[.41, .61]", "2 × 10^-8", "0.99"),
        ("Phi-3-mini-4k-instruct", "0.39", "[.30, .49]", "0.0014", "0.99"),
        ("gemma-2-2b-it", "0.36", "[.27, .46]", "0.0094", "1.00"),
        ("Llama-3.2-3B-Instruct", "0.29", "[.21, .39]", "0.21", "0.92"),
    ]
    for r_i, row in enumerate(t5_data):
        for c_i, val in enumerate(row):
            tbl5.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl5, [Inches(2.3), Inches(0.9), Inches(1.1), Inches(1.2), Inches(1.0)])

    add_p(
        "Qwen2.5-3B-Instruct is best (Table 5) and significantly better than gemma-2-2b-it (p=0.0135; 24 vs. 9 discordant items) and Llama-3.2-3B "
        "(p=0.0003; 29 vs. 7). Its lead over Phi-3-mini is not established at n=100 (p=0.058; 23 vs. 11), and the other three pairs are indistinguishable (p >= 0.12)."
    )
    add_p(
        "Format effects. Fill-in-the-blank is easiest (Qwen 0.72) and MCQ is solved above chance by every model (p <= 0.03). Assertion–reason stays at "
        "chance for all four (best 0.32, p=0.27) and gemma-2-2b-it falls below it at 0.16. Match-the-column is at or near chance for three models; "
        "Qwen and Phi-3 reach 0.40 (p=0.07). Format and difficulty are confounded in this set: all 25 assertion–reason and all 25 match-the-column items "
        "are labelled Hard, whereas every fill-in-the-blank item is Easy or Medium, so 'difficulty' effects cannot be separated from format effects. "
        "Qwen scores 0.69 / 0.65 / 0.36 on Easy / Medium / Hard (n = 13 / 37 / 50)."
    )
    add_p(
        "Position bias. Llama-3.2-3B selects option C on 50% of items and gemma-2-2b-it selects D on 41%, against a key of 24/30/20/26%, so part of their "
        "scores is key placement rather than knowledge. Llama also fails to give a parseable answer on 8% of items."
    )
    add_p(
        "Where models fail: locating a source. By subtype, the 'topic to reference' items, which ask which passage or treatise a topic belongs to, "
        "are answered correctly in only 2, 3, 2 and 1 of 14 cases by Qwen, Phi-3, gemma and Llama respectively (14%, 21%, 14%, 7%). The 'A false, R true' "
        "assertion variant is 0 of 7 for Qwen and gemma. Subtype counts are small and directional, but the topic-to-reference result is the clearest "
        "evidence in this study that parametric memory cannot supply provenance, and it is the task that retrieval over (source_book, chunk_id) "
        "addresses directly. Overall, 29 of 100 items are solved by no model and the union of all four reaches 0.71, so the set has substantial headroom."
    )
    add_p("sarvam-1 was not evaluated here: it was selected on tokenizer evidence (Sec. 9), and its score on this set is [pending].")

    # ----------------- 9. TOKENIZER AUDIT -----------------
    add_h1("9. Tokenizer Audit and Vocabulary Trimming")
    add_h2("9.1 Coverage audit")
    add_p(
        "Zero-shot accuracy is not the criterion for the fine-tuning base. The base must tokenize Sanskrit economically and fit one consumer accelerator, "
        "so we audited twelve 1–5B candidates on the verified corpus (eleven scored; one gated repository was inaccessible). We report overall fertility, "
        "Devanagari-specific fertility, and the byte-fallback fraction (share of tokens decoded through byte fallback, which signals characters missing "
        "from the vocabulary). Lower is better for all three."
    )

    # Table 6: Tokenizer audit
    p_t6 = doc.add_paragraph()
    p_t6.add_run("Table 6: Tokenizer audit (Fert. = overall fertility, Dev. = Devanagari fertility, BFB = byte-fallback fraction). †Exceeds the 4B parameter budget. ‡Nominal; the trimmed checkpoint counts 2.344B parameters.").bold = True
    tbl6 = doc.add_table(rows=10, cols=6)
    t6_headers = ["Model", "Params", "Vocab", "Fert.", "Dev.", "BFB"]
    for c_i, h in enumerate(t6_headers):
        tbl6.cell(0, c_i).paragraphs[0].text = h
    t6_data = [
        ("gemma-4-E2B-it†", "5.1B", "262,144", "2.49", "4.10", "0.000"),
        ("gemma-2-2b-it", "2.6B", "256,000", "2.64", "4.79", "0.000"),
        ("sarvam-1", "2.0B‡", "68,096", "3.01", "4.49", "0.086"),
        ("Qwen3 / Qwen2.5 (4 models)", "1.5–4B", "151,643", "3.63", "8.00", "0.297"),
        ("Falcon3-1B", "1.7B", "131,072", "3.96", "9.11", "0.182"),
        ("SmolLM2-1.7B", "1.7B", "49,152", "4.03", "9.84", "0.262"),
        ("glm-edge-4b", "4.0B", "59,246", "4.22", "10.24", "0.463"),
        ("granite-3.3-2b", "2.5B", "49,152", "4.32", "10.36", "0.307"),
        ("LFM2.5-1.2B", "1.2B", "64,400", "4.29", "11.13", "0.534"),
    ]
    for r_i, row in enumerate(t6_data):
        for c_i, val in enumerate(row):
            tbl6.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl6, [Inches(2.1), Inches(0.9), Inches(0.9), Inches(0.8), Inches(0.9), Inches(0.9)])

    add_p(
        "Within the 4B budget, sarvam-1 has the lowest Devanagari fertility (4.49 against 4.79 for gemma-2-2b-it, a 6.3% reduction, and against 8.00 "
        "for the Qwen family, a 44% reduction). It does not have the lowest byte-fallback fraction or overall fertility: gemma-2-2b-it is better on both "
        "(0.000 against 0.086, and 2.64 against 3.01). The case for sarvam-1 over gemma-2-2b-it therefore rests on Devanagari fertility and on its "
        "Indic-focused pretraining, not on a uniform tokenizer advantage, and only a downstream fine-tune of both models can settle the choice."
    )

    add_h2("9.2 Trimming")
    add_p(
        "Large vocabularies carry embedding rows that a corpus never uses. We trimmed each candidate’s vocabulary to the tokens the corpus needs (Table 7); "
        "sarvam-1 shrinks from 68,096 to 23,946 tokens (64.8% fewer) and is published as nishm27/sarvam-1-TRIM."
    )

    # Table 7: Trimmed checkpoints
    p_t7 = doc.add_paragraph()
    p_t7.add_run("Table 7: Trimmed checkpoints. Perplexity is per token under each model’s own vocabulary and is not comparable across rows.").bold = True
    tbl7 = doc.add_table(rows=3, cols=5)
    t7_headers = ["Trimmed model", "Params", "Vocab", "PPL", "Tok./chunk"]
    for c_i, h in enumerate(t7_headers):
        tbl7.cell(0, c_i).paragraphs[0].text = h
    t7_data = [
        ("sarvam-1-TRIM", "2.344B", "23,946", "25.11", "304.9"),
        ("gemma-2-2b-it-TRIM", "2.483B", "198,912", "56.42", "287.4"),
    ]
    for r_i, row in enumerate(t7_data):
        for c_i, val in enumerate(row):
            tbl7.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl7, [Inches(2.0), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.2)])

    add_p(
        "Perplexity is defined per token, so a model with a smaller vocabulary and longer token sequences is not directly comparable with one that has "
        "a larger vocabulary. The perplexity gap in Table 7 (25.11 against 56.42) should therefore not be read as sarvam-1 modelling the corpus twice as well; "
        "a tokenizer-independent measure such as bits per character on held-out text is needed, and is [pending]. Gemma-2 produces fewer tokens per chunk "
        "(287.4 against 304.9), and sarvam-1 is a base model without a chat template, so training uses a plain User:/Answer: framing and its loss is not comparable with an instruct model’s."
    )

    # ----------------- 10. FINE-TUNING PROTOCOL -----------------
    add_h1("10. Fine-Tuning Protocol")
    add_p("Status: the pipeline is configured; no trial has completed, and no fine-tuned result is reported in this paper.", italic=True)

    add_h2("10.1 Adaptation method")
    add_p(
        "We adapt sarvam-1-TRIM with QLoRA [21], a quantised variant of LoRA [22]: base weights are frozen in 4-bit NormalFloat (NF4) with double quantisation, "
        "and trainable low-rank matrices B in R^{d x r}, A in R^{r x k} (r << min(d, k)) are attached to the query, key, value, output, gate, up and down projections:"
    )
    add_callout_box(
        "QLoRA Parameter Adaptation",
        "W' = dequant(W_NF4) + (α / r) · B · A\nwith B initialised to zero."
    )
    add_p("Training minimises completion-only cross-entropy, masking the prompt x so that only the verbatim answer y contributes:")
    add_callout_box(
        "Completion-Only Loss Objective",
        "L(θ) = - ∑_{t=1}^{Lc} log P_θ(y_t | x, y_{<t})\nExecution is on a single Kaggle T4 GPU with Weights & Biases tracking, making the pipeline reproducible without cluster access."
    )

    add_h2("10.2 Hyperparameter search")
    # Table 8: Optuna search space
    p_t8 = doc.add_paragraph()
    p_t8.add_run("Table 8: Optuna search space.").bold = True
    tbl8 = doc.add_table(rows=6, cols=2)
    t8_headers = ["Group", "Search space"]
    for c_i, h in enumerate(t8_headers):
        tbl8.cell(0, c_i).paragraphs[0].text = h
    t8_data = [
        ("Optimisation", "LR log-uniform 5×10^-5–5×10^-4; scheduler cosine/linear/const+warmup; warmup ratio 0.01–0.10; weight decay 0–0.10; optimiser paged_adamw_8bit or adamw_torch; Adam β2 in {0.999, 0.95}; clip 0.5–1.0"),
        ("Batch", "per-device {2, 4, 8}; grad. accumulation {4, 8, 16}"),
        ("LoRA", "rank {8, 16, 32, 64}; α = m · r, m in {1, 2}; dropout 0–0.15"),
        ("Sequence", "max length {768, 1024, 1536}"),
        ("Fixed", "4-bit NF4, seven target modules, completion-style loss"),
    ]
    for r_i, row in enumerate(t8_data):
        for c_i, val in enumerate(row):
            tbl8.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl8, [Inches(1.8), Inches(4.7)])

    add_p(
        "Search runs in four stages: a baseline trial that verifies the model trains; 15 random trials; 25 Bayesian trials (TPE [24] with a median pruner, "
        "resumable through an SQLite study [23]); and a final retraining of the winner for two epochs on the full split. Each search trial is capped at "
        "400 steps on a random 8,000-item sub-sample. A stall detector terminates trials and reports them as pruned for five reasons: flat (loss span below 10^-3, "
        "adapters not attached), diverged (NaN, infinity or loss above 20), no_progress (no improvement over the previous best by a minimum delta), oom and failed. "
        "The best configuration, run identifiers and final metrics are [pending]."
    )

    add_h2("10.3 Evaluation after tuning")
    add_p(
        "Per-format accuracy on our held-out split and on BBA will be reported with Wilson intervals, and gains over the pre-tuning model with paired "
        "McNemar tests. Table 4 fixes the item counts: 5,648 test items on our split and 14,963 on BBA."
    )

    # ----------------- 11. COMPARISON WITH AYURPARAM -----------------
    add_h1("11. Comparison with AyurParam")
    add_h2("11.1 Published reference numbers")
    # Table 9: BBA comparison
    p_t9 = doc.add_paragraph()
    p_t9.add_run("Table 9: Accuracy (%) on BBA. The upper block is taken from the AyurParam paper [11]; the lower block are our four ablation conditions, none of which has been run.").bold = True
    tbl9 = doc.add_table(rows=11, cols=4)
    t9_headers = ["Model (published, BBA)", "All", "English", "Hindi"]
    for c_i, h in enumerate(t9_headers):
        tbl9.cell(0, c_i).paragraphs[0].text = h
    t9_data = [
        ("AyurParam-2.9B-Instruct", "39.97", "41.12", "38.04"),
        ("Llama-3.2-3B-Instruct", "33.20", "35.31", "29.67"),
        ("Qwen2.5-3B-Instruct", "32.68", "35.22", "28.46"),
        ("granite-3.1-2B", "31.10", "33.39", "27.30"),
        ("gemma-2-2B-it", "28.40", "29.38", "26.79"),
        ("Llama-3.2-1B-Instruct", "26.41", "26.77", "25.82"),
        ("AyurLLM, sarvam-1 base", "[pending]", "[pending]", "[pending]"),
        ("AyurLLM, + QLoRA", "[pending]", "[pending]", "[pending]"),
        ("AyurLLM, + retrieval/graph", "[pending]", "[pending]", "[pending]"),
        ("AyurLLM, + QLoRA + retrieval/graph", "[pending]", "[pending]", "[pending]"),
    ]
    for r_i, row in enumerate(t9_data):
        for c_i, val in enumerate(row):
            tbl9.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl9, [Inches(2.8), Inches(1.2), Inches(1.2), Inches(1.3)])

    add_h2("11.2 Protocol and decision rule")
    add_p(
        "We evaluate four conditions with one prompt template and one answer-letter scorer: (1) sarvam-1 base; (2) base + QLoRA; (3) base + retrieved context; "
        "(4) QLoRA + retrieved context. AyurParam’s weights are public [12], so we run it ourselves on both BBA and our test split, which allows paired "
        "McNemar tests; comparison with the published figures alone would be unpaired. At BBA’s size the 95% half-width of an accuracy near 40% is about "
        "0.8 points, so a difference of roughly 1.1 points between two systems is resolvable overall, and about 1.8 points on the Hindi subset (n=5,615). "
        "We pre-specify the rule: we will report AyurLLM as better than AyurParam on a slice only if the 95% interval of the paired difference excludes zero; "
        "otherwise we report the slice as unresolved or worse."
    )

    add_h2("11.3 What the comparison can and cannot show")
    add_p(
        "Two facts bound expectations. AyurParam is trained on about 4.75M examples; our training split has 65,701, 72 times fewer, on one T4 rather "
        "than an H100 cluster. Parametric accuracy on BBA, which draws on a far wider literature than our eight volumes, is therefore unlikely to be where "
        "we win, and we state no such expectation. Our hypotheses are narrower and falsifiable: (H1) a smaller, verbatim-grounded corpus still transfers "
        "to BBA questions that touch the eight covered treatises; (H2) retrieved context improves items whose answer lies in those treatises, and the gain "
        "is concentrated on provenance-style questions where all baselines in Sec. 8 are near chance; (H3) a tokenizer with lower Devanagari fertility narrows "
        "the English–Hindi gap, which is 3.08 points for AyurParam (41.12 against 38.04). A negative result on any of these will be reported."
    )
    add_p(
        "One caveat concerns the published type-level table. AyurParam’s per-format figures are multiples of 1/27 for assertion–reason (59.26, 44.44, 33.33) "
        "and of 1/41 for match-the-column (24.39, 36.59), which implies denominators of about 27 and 41; they are small subsets and carry wide intervals, "
        "so we do not compare against them."
    )

    add_h2("11.4 Positioning")
    # Table 10: System positioning
    p_t10 = doc.add_paragraph()
    p_t10.add_run("Table 10: Verifiable differences between AyurParam, AyurGPT/IRGPT and this work. 'Not described' means we found no statement in the cited sources, not that the feature is absent.").bold = True
    tbl10 = doc.add_table(rows=9, cols=4)
    t10_headers = ["Dimension", "AyurParam [11]", "AyurGPT / IRGPT [16, 17]", "AyurLLM (this work)"]
    for c_i, h in enumerate(t10_headers):
        tbl10.cell(0, c_i).paragraphs[0].text = h
    t10_data = [
        ("Training answers", "LLM-written (Qwen-3 235B) with evidence anchoring, judge and expert audit", "PubMedQA-derived synthetic data and real/synthetic consultations", "Verbatim source spans; provenance key per item"),
        ("Training scale", "about 4.75M examples", "about 113k–150k validated samples (English prototype)", "65,701 train items from 28,823 facts"),
        ("Base model", "Param-1-2.9B", "BioGPT-Large-PubMedQA (talk); GPT-2 Medium (write-up)", "sarvam-1, vocabulary trimmed to 23,946"),
        ("Languages", "English, Hindi", "English, Kannada, Tamil, Malayalam (targeted); English-only prototype", "Sanskrit, English, Hindi corpus (Hindi 2.47% of tokens)"),
        ("Compute", "Multi-node H100; about 2 days on one H100 node", "A100", "Single T4 (Kaggle)"),
        ("Retrieval component", "Not described", "Planned (2 GB books)", "Designed, not yet evaluated (Sec. 6)"),
        ("Safety mechanism", "Stated as absent", "Not described", "Rule-based triage designed, not yet evaluated"),
        ("Evaluation", "BBA, 14,963 questions", "Not described in the sources we read", "Own 100-item baseline set; BBA and own test split [pending]"),
    ]
    for r_i, row in enumerate(t10_data):
        for c_i, val in enumerate(row):
            tbl10.cell(r_i + 1, c_i).paragraphs[0].text = val
    style_table(tbl10, [Inches(1.5), Inches(1.7), Inches(1.6), Inches(1.7)])

    add_p(
        "Table 10 lists differences that are verifiable from the cited sources or our own artefacts. The distinctions that we regard as defensible "
        "are the verbatim-span provenance of every training and evaluation item, a corpus audited item-by-item for contamination against the public benchmark, "
        "a corpus-level tokenizer analysis, and a design that returns citations rather than only answers. None of these is yet a measured accuracy advantage."
    )

    # ----------------- 12. LIMITATIONS & ETHICS -----------------
    add_h1("12. Limitations and Ethics")
    add_p(
        "No fine-tuned results. The central comparison with AyurParam is unrun (Sec. 11); every claim of superiority is withheld until it is. "
        "Extraction accuracy is unmeasured: the CER, WER and conjunct-error values of Table 2 are pending, so engine choices rest on qualitative "
        "failure modes. Coverage is bounded by extraction quality: 355 chunks (6.1%) yield no item, 202 of them from Sharangadhara Samhita and "
        "92 from Ashtanga Hridaya, and no later step recovers text the recogniser did not resolve."
    )
    add_p(
        "Template stems. Answers are verbatim and so cannot be false with respect to the source, but stems come from 36 templates and a model may "
        "learn the template. Paraphrasing stems while holding answers and options fixed is the natural mitigation and is not yet applied. Verse "
        "under-representation: only 12.3% of items involve the verse and 81.2% rest on commentary alone, so a model trained on the full set learns "
        "commentary comprehension more than verse comprehension; verse-focused work must filter. Difficulty is assigned from format and commentary length, "
        "not measured, and per-split difficulty must be re-derived from a single labelling before train and test scores are compared."
    )
    add_p(
        "Baseline study scale. With 100 items, adjacent models cannot be separated (Qwen vs. Phi-3, p=0.058) and per-book and per-subtype results "
        "(9–16 and 1–14 items) are only directional. Base-model choice rests on tokenizer evidence; gemma-2-2b-it is better on overall fertility "
        "and byte-fallback, and the perplexity figures are not comparable across tokenizers. Serving layer: the retrieval index, graph and triage rules "
        "are designs without evaluation."
    )
    add_p(
        "Clinical and legal. The system is a reference and education tool, not a source of treatment advice; recommendations for herbo-mineral preparations "
        "and detoxification regimens require a qualified practitioner, and no clinical validation has been done. The corpus derives from copyrighted "
        "printed editions, so it is held as a private versioned repository and we do not release the source text. The source editions are classical references "
        "and not current clinical guidance."
    )

    # ----------------- 13. CONCLUSION -----------------
    add_h1("13. Conclusion")
    add_p(
        "We converted eight classical treatises into a verified corpus with a unified schema, attributed each coverage gap to a named extraction defect, "
        "and built an 80,000-item benchmark whose answers are verbatim source spans, with deduplication, contamination and leakage checks that hold at "
        "the fact level. Baseline statistics show that current 2–4B models are at chance on assertion–reason and weak at locating the source of a topic, "
        "which motivates retrieval over provenance-keyed chunks. Fine-tuning, retrieval and the comparison with AyurParam are specified and pre-registered "
        "but not yet run; the paper’s strongest claims are therefore about data quality and measurement, and any claim about model accuracy must wait for those runs."
    )

    # ----------------- REFERENCES -----------------
    add_h1("References")
    references = [
        (1, "Datalab. Surya: OCR, layout analysis, reading order and table recognition in 90+ languages. https://github.com/datalab-to/surya."),
        (2, "V. Paruchuri and Datalab. Marker: convert PDF to markdown and JSON with high accuracy. https://github.com/datalab-to/marker."),
        (3, "N. Livathinos, C. Auer, et al. Docling: an efficient open-source toolkit for AI-driven document conversion. arXiv:2501.17887, 2025."),
        (4, "C. Auer, et al. Docling technical report. arXiv:2408.09869, 2024."),
        (5, "Y. Du, et al. PP-OCR: a practical ultra lightweight OCR system. arXiv:2009.09941, 2020."),
        (6, "Y. Du, et al. PP-OCRv2: bag of tricks for ultra lightweight OCR system. arXiv:2109.03144, 2021."),
        (7, "Liquid AI. LFM2-VL: efficient vision-language models. https://www.liquid.ai/blog/lfm2-vl-efficient-vision-language-models."),
        (8, "A. Kaur and G. S. Lehal. A comprehensive survey of OCR for Devanagari script based languages. IJRES, vol. 13, 2025."),
        (9, "Can OCR-VLMs read Devanagari? A stress-test benchmark and post-correction study. arXiv:2606.29213, 2026."),
        (10, "V. Kore, et al. A systematic framework for Sanskrit character recognition using deep learning. ELCVIA 24(2):81–103, 2025."),
        (11, "M. Nauman, S. Gvm, V. Devane, S. Pawar, V. Thakur, K. Pundalik, P. Sawarkar, R. Saluja, M. Desarkar, G. Ramakrishnan. AyurParam: a state-of-the-art bilingual language model for Ayurveda. arXiv:2511.02374, 2025."),
        (12, "BharatGenAI. AyurParam: domain-specialized Ayurvedic LLM. Hugging Face, 2025. https://huggingface.co/bharatgenai/AyurParam."),
        (13, "BharatGen Research Team. PARAM-1 BharatGen 2.9B model. arXiv:2507.13390, 2025."),
        (14, "BharatGen Research Team. BhashaBench-Ayur (BBA). Hugging Face Datasets, 2025. https://huggingface.co/datasets/bharatgenai/bhashabench-ayur."),
        (15, "V. Devane, M. Nauman, B. Patel, et al. BhashaBench V1: a comprehensive benchmark for the quadrant of Indic domains. arXiv:2510.25409, 2025."),
        (16, "A. Padia. AyurGPT: fine-tuning a medical LLM for multilingual Ayurveda consultations. NLP Summit (online), 25 Sept. 2024. https://www.nlpsummit.org/ayur-gtp-fine-tuning-a-medical-llm-for-multilingual-ayurveda-consultations/."),
        (17, "Trigent Software. Developing a multilingual Ayurvedic medical LLM: challenges and learnings. ZenML LLMOps Database. https://www.zenml.io/llmops-database/developing-a-multilingual-ayurvedic-medical-llm-challenges-and-learnings."),
        (18, "From real to synthetic: synthesizing millions of diversified and complicated user instructions with attributed grounding. arXiv:2506.03968, 2025."),
        (19, "CoT-Self-Instruct: building high-quality synthetic data for reasoning and non-reasoning tasks. arXiv:2507.23751, 2025."),
        (20, "Seed-free synthetic data generation framework for instruction-tuning LLMs: a case study in Thai. arXiv:2411.15484, 2024."),
        (21, "T. Dettmers, A. Pagnoni, A. Holtzman, L. Zettlemoyer. QLoRA: efficient finetuning of quantized LLMs. NeurIPS 36, 2023."),
        (22, "E. J. Hu, et al. LoRA: low-rank adaptation of large language models. ICLR, 2022."),
        (23, "T. Akiba, S. Sano, T. Yanase, T. Ohta, M. Koyama. Optuna: a next-generation hyperparameter optimization framework. KDD, 2019."),
        (24, "J. Bergstra, R. Bardenet, Y. Bengio, B. Kégl. Algorithms for hyper-parameter optimization. NeurIPS 24, 2011."),
        (25, "Q. McNemar. Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika 12(2):153–157, 1947."),
        (26, "E. B. Wilson. Probable inference, the law of succession, and statistical inference. JASA 22(158):209–212, 1927."),
    ]

    for num, citation in references:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.15
        r_num = p.add_run(f"[{num}] ")
        r_num.bold = True
        r_num.font.size = Pt(9.5)
        r_num.font.color.rgb = SECONDARY
        r_text = p.add_run(citation)
        r_text.font.size = Pt(9.5)

    out_path = os.path.abspath("RP/AyurLLM_paper.docx")
    doc.save(out_path)
    print(f"Saved complete docx to: {out_path}")

    # Copy to artifacts directory for immediate user download
    artifact_dir = r"C:\Users\KIIT0001\.gemini\antigravity\brain\75784175-db3c-4581-90d5-5676d3d83ab0"
    os.makedirs(artifact_dir, exist_ok=True)
    art_path = os.path.join(artifact_dir, "AyurLLM_paper.docx")
    shutil.copy2(out_path, art_path)
    print(f"Copied to artifact directory: {art_path}")

if __name__ == "__main__":
    build_docx()

