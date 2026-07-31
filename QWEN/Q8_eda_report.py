#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q8 --- One EDA report covering every pipeline stage.
====================================================

Reads the per-step JSON reports written by Q1-Q7 plus the delivered splits, and
emits a single self-contained HTML page. Nothing is hard-coded: if a step's
report is missing its section says so rather than inventing numbers.

Sections
    1  Headline --- row counts, guarantees, verdicts
    2  Quality gate --- what the LLM got wrong and how often
    3  Deduplication --- what each pass removed
    4  AyurParam --- similarity distribution and the threshold sweep
    5  Splits --- composition, and how closely test mirrors the benchmark
    6  Leakage --- before and after repair
    7  MD5 / MinHash --- final duplicate verdict
    8  By type and by language --- the partition tables

Usage
    python Q8_eda_report.py --dir final --reports reports --out EDA_QWEN_REPORT.html
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

CSS = """
:root{--ink:#16130f;--mute:#6b6259;--line:#e2ddd4;--bg:#faf8f4;--card:#fff;
      --good:#1a7f52;--bad:#b3341f;--accent:#3d5a80}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:44px 26px 76px}
h1{font-size:29px;margin:0 0 4px;letter-spacing:-.02em}
.sub{color:var(--mute);margin:0 0 30px;font-size:14px}
h2{font-size:20px;margin:46px 0 6px;padding-top:18px;border-top:2px solid var(--ink)}
h2 .n{color:var(--mute);font-weight:400;font-size:15px}
h3{font-size:13.5px;margin:22px 0 8px;text-transform:uppercase;
   letter-spacing:.07em;color:var(--mute)}
table{border-collapse:collapse;width:100%;margin:12px 0;background:var(--card);
      font-size:14px;border:1px solid var(--line)}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line)}
th{background:#f2eee7;font-weight:600;font-size:11.5px;text-transform:uppercase;
   letter-spacing:.05em;color:var(--mute)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
tr.tot td{font-weight:700;background:#f7f4ee}
code{background:#efeae2;padding:1px 5px;border-radius:3px;font-size:12.5px;
     font-family:ui-monospace,Menlo,monospace}
.g{color:var(--good);font-weight:600}.r{color:var(--bad);font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
       gap:11px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:13px 15px}
.card .v{font-size:24px;font-weight:700;letter-spacing:-.02em;line-height:1.1}
.card .l{font-size:11px;color:var(--mute);text-transform:uppercase;
         letter-spacing:.06em;margin-top:4px}
.note{background:#fff;border-left:3px solid var(--accent);padding:11px 15px;
      margin:14px 0;font-size:14px}
.note.bad{border-left-color:var(--bad);background:#fdf5f3}
.note.ok{border-left-color:var(--good);background:#f2f9f5}
.miss{color:var(--mute);font-style:italic}
.bar{height:8px;background:#e8e3da;border-radius:4px;overflow:hidden;display:flex;min-width:90px}
.bar i{display:block;height:100%}
small{color:var(--mute)}
"""


def rd(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def load_split(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def tbl(headers, rows, aligns=None):
    a = aligns or [""] * len(headers)
    h = "".join('<th class="%s">%s</th>' % ("n" if x == "r" else "", c)
                for c, x in zip(headers, a))
    body = []
    for r in rows:
        cls = ' class="tot"' if r and str(r[0]).lower() in ("total", "grand total") else ""
        body.append("<tr%s>%s</tr>" % (cls, "".join(
            '<td class="%s">%s</td>' % ("n" if x == "r" else "", c)
            for c, x in zip(r, a))))
    return "<table><tr>%s</tr>%s</table>" % (h, "".join(body))


def missing(what):
    return '<p class="miss">%s not found — run that step to populate this section.</p>' % what


def fmt(x):
    return "{:,}".format(x) if isinstance(x, int) else x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", default="EDA_QWEN_REPORT.html")
    a = ap.parse_args()

    R = a.reports
    q1 = rd(os.path.join(R, "Q1_quality.json"))
    q2 = rd(os.path.join(R, "Q2_dedup.json"))
    q3 = rd(os.path.join(R, "Q3_match.json"))
    q4 = rd(os.path.join(R, "Q4_splits.json"))
    q5b = rd(os.path.join(R, "Q5_leakage_before.json"))
    q5a = rd(os.path.join(R, "Q5_leakage_after.json"))
    q6 = rd(os.path.join(R, "Q6_partitions.json"))
    q7 = rd(os.path.join(R, "Q7_md5_minhash.json"))

    splits = {s: load_split(os.path.join(a.dir, "%s.json" % s))
              for s in ("train", "validation", "test")}
    n = {s: len(v) for s, v in splits.items()}

    H = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
         "<title>AyurShloka-QA v3 (Qwen) — pipeline EDA</title>",
         "<style>%s</style></head><body><div class='wrap'>" % CSS]

    H.append("<h1>AyurShloka-QA v3 (Qwen) — pipeline EDA</h1>")
    H.append('<p class="sub">Every stage from raw generation to the delivered '
             'splits. Numbers are read from the per-step reports, not restated '
             'from memory — a missing report is shown as missing.</p>')

    # ---- 1 headline ---------------------------------------------------
    dup_ok = q7 and q7.get("verdict") == "CLEAN"
    leak_ok = q5a and q5a.get("total_leaks", 1) == 0
    H.append('<div class="cards">')
    for label, val, cls in [
            ("train rows", fmt(n["train"]), ""),
            ("validation rows", fmt(n["validation"]), ""),
            ("test rows", fmt(n["test"]), ""),
            ("duplicates", "0" if dup_ok else "—", "g" if dup_ok else ""),
            ("cross-split leaks", "0" if leak_ok else "—", "g" if leak_ok else "")]:
        H.append('<div class="card"><div class="v %s">%s</div>'
                 '<div class="l">%s</div></div>' % (cls, val, label))
    H.append("</div>")

    # ---- 2 quality gate ------------------------------------------------
    H.append('<h2><span class="n">1 ·</span> Quality gate</h2>')
    if q1:
        H.append(tbl(["", "Rows"],
                     [["Generated", fmt(q1["input_rows"])],
                      ["Passed", fmt(q1["passed"])],
                      ["Rejected", fmt(q1["rejected"])],
                      ["Total", "%.1f%% pass rate" % (100 * q1["pass_rate"])]],
                     ["", "r"]))
        if q1.get("reject_reasons"):
            H.append("<h3>Why rows were rejected</h3>")
            H.append(tbl(["Reason", "Rows", "Share of rejects"],
                         [[k, fmt(v), "%.1f%%" % (100 * v / max(q1["rejected"], 1))]
                          for k, v in q1["reject_reasons"].items()],
                         ["", "r", "r"]))
            H.append('<div class="note">An LLM asked for JSON fails in '
                     'characteristic ways. The counts above are the honest yield; '
                     'a reject rate above roughly 15% is a prompt problem rather '
                     'than noise, and is worth fixing before committing to a long run.</div>')
        pb, pa = q1.get("answer_position_before"), q1.get("answer_position_after")
        if pb:
            tot = sum(pb.values()) or 1
            tota = sum(pa.values()) or 1
            H.append("<h3>Answer position bias</h3>")
            H.append(tbl(["Option", "Before", "%", "After", "%"],
                         [[k, fmt(pb.get(k, 0)), "%.1f" % (100 * pb.get(k, 0) / tot),
                           fmt(pa.get(k, 0)), "%.1f" % (100 * pa.get(k, 0) / tota)]
                          for k in sorted(set(pb) | set(pa))],
                         ["", "r", "r", "r", "r"]))
            H.append('<div class="note">If the correct answer sits at one letter '
                     'far more often than chance, a model can score well by always '
                     'picking it and learn nothing about Ayurveda.</div>')
    else:
        H.append(missing("<code>Q1_quality.json</code>"))

    # ---- 3 dedup -------------------------------------------------------
    H.append('<h2><span class="n">2 ·</span> Deduplication</h2>')
    if q2:
        H.append(tbl(["Pass", "Removed"],
                     [["Exact stem", fmt(q2.get("removed_exact_stem", 0))],
                      ["Full item", fmt(q2.get("removed_full_item", 0))],
                      ["Near-duplicate", fmt(q2.get("removed_near_duplicate", 0))],
                      ["Total", fmt(q2.get("total_removed", 0))]],
                     ["", "r"]))
        H.append("<p>%s rows in, %s out, %s distinct facts remaining.</p>"
                 % (fmt(q2.get("input_rows", 0)), fmt(q2.get("output_rows", 0)),
                    fmt(q2.get("distinct_facts_after", 0))))
    else:
        H.append(missing("<code>Q2_dedup.json</code>"))

    # ---- 4 ayurparam ---------------------------------------------------
    H.append('<h2><span class="n">3 ·</span> AyurParam similarity</h2>')
    if q3:
        c = q3["cosine"]
        H.append(tbl(["Measure", "Value"],
                     [["Questions scored", fmt(q3["ours"])],
                      ["Benchmark questions", fmt(q3["bba"])],
                      ["Flagged similar", fmt(q3["flagged_similar"])],
                      ["Max cosine", c["max"]],
                      ["Mean cosine", c["mean"]],
                      ["99.9th percentile", c.get("p99_9", "—")],
                      ["Max Levenshtein", q3["levenshtein"]["max"]]],
                     ["", "r"]))
        sw = q3.get("threshold_sweep", {})
        if sw:
            H.append("<h3>Threshold sweep</h3>")
            H.append(tbl(["Cosine ≥", "Questions"],
                         [[k, fmt(v)] for k, v in sw.items()], ["", "r"]))
        cls = "ok" if q3["flagged_similar"] == 0 else "bad"
        H.append('<div class="note %s"><b>%d questions resemble the benchmark.</b> '
                 'Max cosine %s against a %s threshold. Duplication inside the corpus '
                 'and resemblance to an external benchmark are unrelated properties; '
                 'a low number here is the expected result for questions generated '
                 'from classical treatises against a benchmark drawn from exam papers.'
                 '</div>' % (cls, q3["flagged_similar"], c["max"],
                             q3["thresholds"]["cosine"]))
        ex = q3.get("closest_examples") or []
        if ex:
            H.append("<h3>Closest pairs</h3>")
            H.append(tbl(["Cosine", "Ours", "Benchmark"],
                         [[e["cosine"], e["ours"], e["bba"]] for e in ex],
                         ["r", "", ""]))
    else:
        H.append(missing("<code>Q3_match.json</code>"))

    # ---- 5 splits ------------------------------------------------------
    H.append('<h2><span class="n">4 ·</span> Splits</h2>')
    if q4:
        sp = q4["splits"]
        H.append(tbl(["Split", "Rows", "Facts", "Max BBA cosine"],
                     [[k, fmt(sp[k]["rows"]), fmt(sp[k]["facts"]),
                       sp[k]["max_bba_cosine"]] for k in ("train", "validation", "test")],
                     ["", "r", "r", "r"]))
        H.append('<div class="note"><b>Test mirrors the benchmark\'s composition.</b> %s</div>'
                 % q4.get("test_strategy", ""))
        mf = q4.get("mirror_fit", {})
        for key, title in (("question_type", "Question type"),
                           ("language", "Language"),
                           ("subject_domain", "Subject domain")):
            if key in mf:
                H.append("<h3>Mirror fit — %s</h3>" % title)
                H.append(tbl([title, "Benchmark %", "Test %", "Delta"],
                             [[k, v["benchmark"], v["test"], "%+.2f" % v["delta"]]
                              for k, v in list(mf[key].items())[:16]],
                             ["", "r", "r", "r"]))
        fo = q4.get("fact_overlaps", {})
        H.append("<p>Fact overlaps — train/val %s, train/test %s, val/test %s. "
                 "All must be zero: a fact renders into several questions, and "
                 "splitting one across sides is leakage dressed as generalisation.</p>"
                 % (fo.get("train_val"), fo.get("train_test"), fo.get("val_test")))
    else:
        H.append(missing("<code>Q4_splits.json</code>"))

    # ---- 6 leakage -----------------------------------------------------
    H.append('<h2><span class="n">5 ·</span> Cross-split leakage</h2>')
    if q5b or q5a:
        rows_ = []
        for name, rep in (("Before repair", q5b), ("After repair", q5a)):
            if not rep:
                continue
            nd = rep.get("near_duplicate", {})
            rows_.append([name,
                          sum(rep.get("question_id", {}).values()),
                          sum(rep.get("exact_stem", {}).values()),
                          sum(rep.get("fact_id", {}).values()),
                          nd.get("train|validation", {}).get("above_threshold", "—"),
                          nd.get("train|test", {}).get("above_threshold", "—"),
                          rep.get("verdict", "—")])
        H.append(tbl(["State", "id", "stem", "fact", "near-dup val",
                      "near-dup test", "Verdict"], rows_,
                     ["", "r", "r", "r", "r", "r", ""]))
        if q5b and q5b.get("verdict") == "LEAKAGE DETECTED":
            H.append('<div class="note bad"><b>Splitting on fact_id is necessary '
                     'but not sufficient.</b> Exact checks can be clean while '
                     'near-duplicate stems still cross splits, because two '
                     'different facts can render through one template into nearly '
                     'the same question. Only the near-duplicate check sees it.</div>')
    else:
        H.append(missing("<code>Q5_leakage_*.json</code>"))

    # ---- 7 md5/minhash --------------------------------------------------
    H.append('<h2><span class="n">6 ·</span> MD5 and MinHash</h2>')
    if q7:
        w, m = q7.get("md5_within", {}), q7.get("minhash_within", {})
        H.append(tbl(["Check", "Result"],
                     [["MD5 duplicate rows", fmt(w.get("duplicate_rows", 0))],
                      ["MD5 groups with conflicting gold answers",
                       fmt(w.get("conflicting_answer_groups", 0))],
                      ["MinHash similar pairs", fmt(m.get("similar_pairs", 0))],
                      ["MinHash true duplicates (same answer)",
                       fmt(m.get("duplicate_pairs", 0))],
                      ["MinHash cross-split pairs", fmt(m.get("cross_split_pairs", 0))]],
                     ["", "r"]))
        H.append('<div class="note"><b>Similar is not duplicate.</b> %s</div>'
                 % m.get("note", ""))
        ab = q7.get("across_benchmark")
        if ab:
            H.append("<h3>Across the benchmark boundary</h3>")
            H.append(tbl(["Method", "Matches"],
                         [["MD5 exact", fmt(ab.get("md5_matches", 0))],
                          ["MinHash", fmt(ab.get("minhash_matches", 0))],
                          ["Max Jaccard seen", ab.get("max_jaccard_seen")],
                          ["Max stored cosine", ab.get("max_stored_cosine")]],
                         ["", "r"]))
        cls = "ok" if q7.get("verdict") == "CLEAN" else "bad"
        H.append('<div class="note %s">Verdict: <b>%s</b></div>'
                 % (cls, q7.get("verdict")))
    else:
        H.append(missing("<code>Q7_md5_minhash.json</code>"))

    # ---- 8 partitions ---------------------------------------------------
    H.append('<h2><span class="n">7 ·</span> By question type and language</h2>')
    if any(splits.values()):
        types = sorted({r.get("question_type") for v in splits.values() for r in v},
                       key=lambda t: -sum(1 for r in splits["train"]
                                          if r.get("question_type") == t))
        rows_ = []
        for t in types:
            rows_.append([t] + [fmt(sum(1 for r in splits[s]
                                        if r.get("question_type") == t))
                                for s in ("train", "validation", "test")])
        rows_.append(["Total"] + [fmt(n[s]) for s in ("train", "validation", "test")])
        H.append("<h3>Question type</h3>")
        H.append(tbl(["Type", "train", "validation", "test"], rows_,
                     ["", "r", "r", "r"]))

        langs = sorted({r.get("language") for v in splits.values() for r in v})
        rows_ = []
        for l in langs:
            rows_.append([l] + [fmt(sum(1 for r in splits[s] if r.get("language") == l))
                                for s in ("train", "validation", "test")])
        rows_.append(["Total"] + [fmt(n[s]) for s in ("train", "validation", "test")])
        H.append("<h3>Language</h3>")
        H.append(tbl(["Language", "train", "validation", "test"], rows_,
                     ["", "r", "r", "r"]))

        books = Counter(r.get("source_book") for v in splits.values() for r in v)
        rows_ = [[b] + [fmt(sum(1 for r in splits[s] if r.get("source_book") == b))
                        for s in ("train", "validation", "test")]
                 for b, _ in books.most_common()]
        rows_.append(["Total"] + [fmt(n[s]) for s in ("train", "validation", "test")])
        H.append("<h3>Source text</h3>")
        H.append(tbl(["Book", "train", "validation", "test"], rows_,
                     ["", "r", "r", "r"]))
    else:
        H.append(missing("split files"))

    H.append("</div></body></html>")
    d = os.path.dirname(a.out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    print("wrote %s" % a.out)


if __name__ == "__main__":
    main()
