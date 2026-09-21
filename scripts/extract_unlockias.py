#!/usr/bin/env python3
"""
extract_unlockias.py — parse the UnlockIAS UPSC CSE Mains GS compilations
(2013-2026) into structured JSON.

Input : upsc-mains-<year>.pdf  (clean text layer, no OCR)
Output: one JSON per year + a combined file + a counts summary

Parsing contract
----------------
Each question is preceded by a header line of the form
    <year>  GS-<roman>  <marks>M · <words>W
and the body runs from "QN." up to the next header.

GS-IV numbering repeats across the paper's two sections (Section A
theory and Section B case studies both start at Q1), so section is
derived from marks: <=15M -> A, >15M -> B. This is the documented
UPSC structure, not a guess about content.

Global question_number follows the DB offset convention: sequential
within a year, GS1 -> GS2 -> GS3 -> GS4, starting at 1. Because the
per-paper counts vary by year (25 per paper in 2013-14, 20 from 2015),
the offsets are computed from observed counts, NOT hard-coded.
VERIFY these against the live pyq_questions rows before any update —
the DB's existing numbering is authoritative for alignment.
"""
import json
import re
import sys
from pathlib import Path

import pdfplumber

SECTION_IDS = {
    "GS1": "daca2e9f-012e-46fc-8b10-b6df340b4200",
    "GS2": "d332fcad-6750-4542-af0a-3f203f819096",
    "GS3": "b5cbb735-b687-4de5-90cb-3978f48a71a1",
    "GS4": "dee30326-920a-40cf-bee0-a5b4c76760f7",
}
ROMAN = {"I": "GS1", "II": "GS2", "III": "GS3", "IV": "GS4"}
PAPER_ORDER = ["GS1", "GS2", "GS3", "GS4"]

HEADER = re.compile(
    r"^\s*(20\d\d)\s+GS-(I{1,3}|IV)\s+([\d.]+)M\s*[·.]\s*(\d+)W\s*$"
)
QSTART = re.compile(r"^\s*Q(\d+)\.\s*(.*)$")
FOOTER = re.compile(r"UnlockIAS\s*\|", re.I)
BANNER = re.compile(r"(UPSC Mains 20\d\d: All GS Questions"
                    r"|Questions across GS Paper"
                    r"|UnlockIAS — www)", re.I)
BARE_SECTION = re.compile(r"^\s*GS-(I{1,3}|IV)\s*$")


def clean(text: str) -> str:
    text = FOOTER.sub(" ", text)
    text = re.sub(r"www\.unlockias\.in\S*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse(path: Path):
    lines = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            lines.extend((page.extract_text(layout=True) or "").split("\n"))

    rows, cur, buf = [], None, []

    def flush():
        if cur and buf:
            body = clean(" ".join(buf))
            m = QSTART.match(body)
            if m:
                cur["q_label"] = f"Q{m.group(1)}"
                cur["question_text"] = m.group(2).strip()
                if cur["question_text"]:
                    rows.append(cur)

    for line in lines:
        if BANNER.search(line) or BARE_SECTION.match(line):
            continue
        h = HEADER.match(line)
        if h:
            flush()
            cur = {
                "year": int(h.group(1)),
                "paper": ROMAN[h.group(2)],
                "marks": float(h.group(3)),
                "word_limit": int(h.group(4)),
            }
            buf = []
        elif cur is not None:
            buf.append(line)
    flush()
    return rows


def gs4_section(items, idx):
    """GS-IV has Section A (theory) and Section B (case studies).

    Two numbering styles appear in the corpus:
      * repeating  — A and B both restart at Q1 (2014 onward). The
        second occurrence of a label is Section B.
      * continuous — Q1..Q14 straight through (2013). Section B is the
        trailing block of case studies; UPSC set 6 of them, and they
        are the last 6 questions on the paper.
    Neither rule uses marks: 2013 Section A carries 10/20/25/30M
    questions, so a marks threshold misclassifies them.
    """
    labels = [x["q_label"] for x in items]
    if len(set(labels)) < len(labels):
        return "B" if labels.index(items[idx]["q_label"]) != idx else "A"
    return "B" if idx >= len(items) - 6 else "A"


def enrich(rows):
    """Add GS4 section A/B, paper-local numbering, refs, global numbers."""
    by_paper = {p: [r for r in rows if r["paper"] == p] for p in PAPER_ORDER}
    out = []
    for paper in PAPER_ORDER:
        items = by_paper[paper]
        for i, r in enumerate(items, start=1):
            r["paper_local_number"] = i
            if paper == "GS4":
                r["paper_section"] = gs4_section(items, i - 1)
                r["source_question_ref"] = (
                    f"GS4-{r['paper_section']}-{r['q_label']}"
                )
            else:
                r["paper_section"] = None
                r["source_question_ref"] = f"{paper}-{r['q_label']}"
            r["section_id"] = SECTION_IDS[paper]
            r["question_type"] = "descriptive"
            r["source"] = "unlockias"
            out.append(r)
    for n, r in enumerate(out, start=1):
        r["question_number"] = n
        r["display_order"] = n
    return out


def main(src_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    combined, summary = [], []

    skipped = []
    for pdf in sorted(src_dir.glob("upsc-mains-*.pdf")):
        # Contract is upsc-mains-<year>.pdf. Skip anything else the glob catches
        # (e.g. per-paper compilations upsc-mains-gs-paper-*.pdf, or duplicate
        # copies like "upsc-mains-2021 (1).pdf") rather than crashing / double-
        # counting a year.
        m = re.fullmatch(r"upsc-mains-(20\d\d)\.pdf", pdf.name)
        if not m:
            skipped.append(pdf.name)
            continue
        year = int(m.group(1))
        rows = enrich(parse(pdf))
        for r in rows:
            r["year"] = year

        counts = {p: sum(1 for r in rows if r["paper"] == p)
                  for p in PAPER_ORDER}
        gs4a = sum(1 for r in rows
                   if r["paper"] == "GS4" and r["paper_section"] == "A")
        gs4b = sum(1 for r in rows
                   if r["paper"] == "GS4" and r["paper_section"] == "B")

        # defects
        dupes, gaps = {}, {}
        for p in PAPER_ORDER:
            texts = [r["question_text"] for r in rows if r["paper"] == p]
            seen, dup = set(), []
            for t in texts:
                key = re.sub(r"[^a-z0-9 ]", "", t.lower())[:90]
                if key in seen:
                    dup.append(t[:70])
                seen.add(key)
            if dup:
                dupes[p] = dup
            labels = sorted(
                int(r["q_label"][1:]) for r in rows if r["paper"] == p
            )
            if labels:
                missing = [n for n in range(1, max(labels) + 1)
                           if n not in labels]
                if missing:
                    gaps[p] = missing

        (out_dir / f"upsc-mains-{year}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        combined.extend(rows)
        summary.append({
            "year": year,
            "total": len(rows),
            **counts,
            "GS4_sectionA": gs4a,
            "GS4_sectionB": gs4b,
            "duplicate_texts": dupes,
            "numbering_gaps": gaps,
        })
        print(f"{year}  total={len(rows):>3}  "
              f"GS1={counts['GS1']:>2} GS2={counts['GS2']:>2} "
              f"GS3={counts['GS3']:>2} GS4={counts['GS4']:>2} "
              f"(A={gs4a} B={gs4b})"
              + (f"  DUPES={list(dupes)}" if dupes else "")
              + (f"  GAPS={gaps}" if gaps else ""))

    (out_dir / "upsc-mains-all-years.json").write_text(
        json.dumps(combined, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (out_dir / "extraction-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\ncombined rows: {len(combined)}")
    if skipped:
        print(f"skipped {len(skipped)} non-year file(s): {skipped}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
