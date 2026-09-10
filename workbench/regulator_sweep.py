"""Source-free defect sweep over SEBI, IFSCA and PFRDA.

Everything here is decidable from the loaded rows alone, so it also covers
SEBI, whose source books are not in the repo.  Findings are structural
signatures of a loader mistake, not judgements about the content.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, "workbench")
from regulator_measure import LIVE, load_db  # noqa: E402

# a stem that opens mid-sentence: lowercase or a clause connector
RE_MIDSENTENCE = re.compile(r"^\s*(?:[a-z]|and\b|or\b|but\b|which\b|that\b|of\b|"
                            r"is\s|are\s|was\s|were\s|can\s|the\s+[a-z])")
RE_PAGE_FOOTER = re.compile(r"\|\s*P\s*a\s*g\s*e|\bPage\s+\d+\s+of\s+\d+", re.I)
RE_BOOK_FURNITURE = re.compile(
    r"(?:SEBI|IFSCA|PFRDA|FRDA|RBI|NABARD)\s+Grade\s+[AB]\b|Recollected\s+Questions|"
    r"Previous\s+Year\s+Paper|Answer\s+Key\b|Phase\s*\d\s*[-–]?\s*Paper\s*\d",
    re.I,
)
RE_DIRECTIONS_IN_STEM = re.compile(
    r"(?:Directions?|Instructions?)\s*\(?\s*Q?\.?\s*\d{1,3}\s*[-–—]", re.I)
# UTF-8 bytes decoded as cp1252 - the loader's own encoding slip
RE_MOJIBAKE = re.compile(r"â€|Ã¢|Â\s|Ã©|â‚¹|ï¿½")
RE_TRAIL_ORPHAN = re.compile(r"\b(?:the|a|an|of|to|in|for|and|or|is|are|by|with)\s*$",
                             re.I)


def nonascii_digits(text: str) -> list[str]:
    return [ch for ch in text
            if not ch.isascii() and unicodedata.category(ch) == "Nd"]


def sweep(slug: str) -> dict:
    rows, _ = load_db(slug)
    f = defaultdict(list)
    for r in rows:
        st, txt = r["reviewer_status"], r["question_text"] or ""
        base = {"id": r["id"], "paper_code": r["paper_code"],
                "q": r["question_number"], "status": st}
        if RE_MIDSENTENCE.match(txt):
            f["stem_midsentence"].append({**base, "text": txt[:120]})
        if RE_PAGE_FOOTER.search(txt) or RE_BOOK_FURNITURE.search(txt):
            f["stem_furniture"].append({**base, "text": txt[:160]})
        if nonascii_digits(txt):
            f["stem_nonascii_digits"].append(
                {**base, "chars": "".join(sorted(set(nonascii_digits(txt)))),
                 "text": txt[:120]})
        if RE_DIRECTIONS_IN_STEM.search(txt):
            f["stem_carries_directions_header"].append({**base, "text": txt[:120]})
        if RE_MOJIBAKE.search(txt):
            f["stem_mojibake"].append({**base, "text": txt[:120]})

        opts = r["options"]
        texts = [(o.get("option_text") or "").strip() for o in opts]
        # normalise whitespace and a trailing full stop only: stripping every
        # non-word character would make "1:1" and "11" collide, and a ratio
        # against a bare number is exactly what these papers print
        norm = [re.sub(r"\s+", " ", t).strip().rstrip(".").lower() for t in texts]
        seen = {}
        for o, t, n in zip(opts, texts, norm):
            if not n:
                f["option_empty"].append({**base, "label": o.get("option_label")})
                continue
            if n in seen:
                f["option_duplicate"].append({
                    **base, "labels": [seen[n], o.get("option_label")],
                    "text": t[:90],
                    "keyed_is_dup": bool(o.get("is_correct")),
                })
            else:
                seen[n] = o.get("option_label")
            if RE_PAGE_FOOTER.search(t) or RE_BOOK_FURNITURE.search(t):
                f["option_furniture"].append({
                    **base, "label": o.get("option_label"),
                    "is_correct": bool(o.get("is_correct")), "text": t[:160]})
            if RE_DIRECTIONS_IN_STEM.search(t):
                f["option_carries_directions_header"].append({
                    **base, "label": o.get("option_label"), "text": t[:160]})
            if RE_MOJIBAKE.search(t):
                f["option_mojibake"].append({
                    **base, "label": o.get("option_label"),
                    "is_correct": bool(o.get("is_correct")), "text": t[:120]})
            if nonascii_digits(t):
                f["option_nonascii_digits"].append({
                    **base, "label": o.get("option_label"), "text": t[:120]})
            if RE_TRAIL_ORPHAN.search(t):
                f["option_ends_on_function_word"].append({
                    **base, "label": o.get("option_label"),
                    "is_correct": bool(o.get("is_correct")), "text": t[:120]})
        # an option that is a strict prefix of a sibling: continuation candidate
        for i, a in enumerate(norm):
            for j, b in enumerate(norm):
                if i != j and a and b and b.startswith(a) and len(b) - len(a) >= 4:
                    f["option_prefix_of_sibling"].append({
                        **base, "short": texts[i][:70], "long": texts[j][:90],
                        "short_keyed": bool(opts[i].get("is_correct"))})
                    break
        if not opts:
            f["question_without_options"].append(base)
    return f


def main():
    report = {}
    for slug in ("sebi", "ifsca", "pfrda"):
        f = sweep(slug)
        report[slug] = {k: v for k, v in f.items()}
        rows, _ = load_db(slug)
        print(f"=== {slug.upper()}  loaded={len(rows)} "
              f"live={sum(1 for r in rows if r['reviewer_status'] == LIVE)}")
        for k in sorted(f):
            live = sum(1 for x in f[k] if x["status"] == LIVE)
            print(f"    {k:38s} {len(f[k]):4d}  live={live}")
    json.dump(report, open("workbench/regulator_sweep.json", "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
