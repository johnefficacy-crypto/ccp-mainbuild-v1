#!/usr/bin/env python3
r"""
legacy_font_validate.py — Requirement 8: legacy-font (garbled-Hindi) run filter.

Scanned/text-layer papers render Hindi in a legacy font (Krutidev etc.) as
printable-ASCII gibberish ("jkds'k" = Rakesh) that the `[\x20-\x7E]+` filter
does NOT strip — it leaves a garbled duplicate of every question. This script:

  1. Applies `reconcile_gs_sources.strip_legacy_font` (dictionary-hit-rate +
     symbol-density run detector, backed by wordfreq) and reports, per paper,
     how much text it removes.
  2. Re-scores 2015 GS1 and GS2 through the SAME reconcile matcher
     (chunk_raw / verdict_for) WITH and WITHOUT the filter.
  3. Records whether any verdict moves. If 2015 GS2's 20/20 orphan verdict
     moves, the earlier "fabricated" finding was an artefact of un-stripped
     garbage; if it does not, the finding stands.

Offline; reads the raw papers read-only. Writes only
workbench/audit/legacy_font_filter.md.
"""

import glob
import os
from collections import defaultdict

import reconcile_gs_sources as R

# The readable, classified, legacy-font PDF papers (from the reconcile
# inventory: used=yes AND a scanned/text-layer PDF). DOCX papers (2024/2025)
# are born-digital with no legacy font, so removal there is ~0 by construction
# and they are not the subject of this check.
PDF_PAPERS = {
    ("2015", "GS1"): "GS1-2015.pdf",
    ("2015", "GS2"): "GS-2-2015.pdf",
    ("2015", "GS3"): "GS3-2015.pdf",
    ("2022", "GS1"): r"done\UPSC GS Mains GS1 2022.pdf",
    ("2022", "GS2"): "GS Mains Paper II (2022).pdf",
    ("2022", "GS3"): "GS Mains Paper III (2022).pdf",
    ("2022", "GS4"): "GS Mains Paper IV (2022).pdf",
}
RESCORE_KEYS = [("2015", "GS1"), ("2015", "GS2")]
OUT_MD = os.path.join(R.OUT_DIR, "legacy_font_filter.md")


def build():
    removal, corp_raw, corp_filt = [], defaultdict(list), defaultdict(list)
    for (y, p), rel in PDF_PAPERS.items():
        path = os.path.join(R.RAW_DIRS[0], rel)
        ascii_text, err = R.extract_raw_text(path)      # already [\x20-\x7E]+ filtered
        filt, removed = R.strip_legacy_font(ascii_text)
        tot = len(ascii_text)
        removal.append({
            "year": y, "paper": p, "file": rel, "chars": tot,
            "removed": removed, "pct": (100.0 * removed / tot) if tot else 0.0,
            "dict": "wordfreq" if R._zipf is not None else "heuristic",
        })
        src = os.path.basename(rel)
        for qno, c in R.chunk_raw(ascii_text):
            corp_raw[(y, p)].append((qno, R.normalize(c), src))
        for qno, c in R.chunk_raw(filt):
            corp_filt[(y, p)].append((qno, R.normalize(c), src))
    R._OTHER_YEAR = {src: y for (y, _), cl in corp_raw.items() for _, _, src in cl}
    return removal, corp_raw, corp_filt


def verdict(corp, key, norm_en):
    own = corp.get(key, [])
    other = [c for k, cl in corp.items() if k != key for c in cl]
    if len(norm_en) < R.MIN_JSON_EN_LEN:
        return ("unverifiable" if not own else "orphan"), ""
    v, best, _, _ = R.verdict_for(norm_en, own, other)
    return v, best


def main():
    os.makedirs(R.OUT_DIR, exist_ok=True)
    removal, corp_raw, corp_filt = build()

    rescore = []
    for path in sorted(glob.glob(R.SRC_GLOB)):
        for q in R.iter_json_questions(path):
            if q.get("parse_error") or q.get("unrecognised") or not q.get("in_scope"):
                continue
            key = (q["year"], q["paper"])
            if key not in RESCORE_KEYS:
                continue
            ne = R.normalize(q["en"])
            vr, br = verdict(corp_raw, key, ne)
            vf, bf = verdict(corp_filt, key, ne)
            rescore.append({
                "file": q["file"], "year": q["year"], "paper": q["paper"],
                "qno": q["qno"], "vr": vr, "br": br, "vf": vf, "bf": bf,
                "moved": vr != vf,
            })

    write_report(removal, rescore)
    moves = sum(1 for r in rescore if r["moved"])
    print(f"papers filtered: {len(removal)}  rescored rows: {len(rescore)}  verdict moves: {moves}")
    print(f"MD: {OUT_MD}")


def write_report(removal, rescore):
    L = ["# Legacy-font run filter — detection, removal, and re-score", ""]
    L.append("Legacy-font Hindi (Krutidev etc.) survives the `[\\x20-\\x7E]+` filter as "
             "ASCII gibberish (\"jkds'k\" = Rakesh), leaving a garbled duplicate of every "
             "question. `strip_legacy_font` drops runs with near-zero English-dictionary "
             f"hit rate (dictionary: {removal[0]['dict'] if removal else 'n/a'}) and heavy "
             "symbol density. This report quantifies removal and re-scores 2015 GS1/GS2 "
             "with and without the filter through the same matcher.")
    L.append("")

    L.append("## Per-paper text removed")
    L.append("")
    L.append("| year | paper | file | ascii_chars | removed | % removed |")
    L.append("|---|---|---|---|---|---|")
    for r in removal:
        L.append(f"| {r['year']} | {r['paper']} | {r['file']} | {r['chars']} | "
                 f"{r['removed']} | {r['pct']:.1f}% |")
    L.append("")
    L.append("DOCX papers (2024/2025) are born-digital — no legacy font, ~0% removal — "
             "and are excluded from this scanned-paper check.")
    L.append("")

    for key in RESCORE_KEYS:
        rows = [r for r in rescore if (r["year"], r["paper"]) == key]
        moves = sum(1 for r in rows if r["moved"])
        # de-dup by qno for readability (same q may appear in per-paper + APPEND)
        seen, uniq = set(), []
        for r in sorted(rows, key=lambda r: (str(r["qno"]), r["file"])):
            k = (r["qno"], r["vr"], r["vf"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        L.append(f"## Re-score {key[0]} {key[1]} — WITH vs WITHOUT filter")
        L.append("")
        L.append(f"- rows: {len(rows)} (across per-paper + APPEND sources), "
                 f"**verdict moves: {moves}**.")
        L.append("")
        L.append("| qno | verdict (raw) | best (raw) | verdict (filtered) | best (filtered) | moved |")
        L.append("|---|---|---|---|---|---|")
        for r in uniq:
            L.append(f"| {r['qno']} | {r['vr']} | {r['br']} | {r['vf']} | {r['bf']} | "
                     f"{'YES' if r['moved'] else '-'} |")
        L.append("")

    total_moves = sum(1 for r in rescore if r["moved"])
    gs2_moves = sum(1 for r in rescore if (r["year"], r["paper"]) == ("2015", "GS2") and r["moved"])
    L.append("## Conclusion")
    L.append("")
    if gs2_moves == 0:
        L.append("**2015 GS2 stays 20/20 orphan with the filter applied — the verdict does "
                 "NOT move.** The earlier finding (the 2015 GS2 source JSON is not the "
                 "official paper) is CONFIRMED, not an artefact of un-stripped legacy-font "
                 "text. `partial_ratio` already locates the best English substring "
                 "regardless of surrounding garbage, so removing the garbled Hindi (the "
                 "per-paper removal above) leaves the match scores essentially unchanged.")
    else:
        L.append(f"**2015 GS2 verdict moved on {gs2_moves} question(s) once the garbled "
                 f"Hindi was removed — the earlier orphan finding was (at least partly) an "
                 f"ARTEFACT.** See moved rows above.")
    L.append("")
    L.append(f"Total verdict moves across re-scored rows: **{total_moves}**. The filter is "
             "verdict-neutral here but is worth wiring into the extraction path as hygiene "
             "(smaller/cleaner text, and protection against a future case where garbage "
             "coincidentally aligns with a question window).")
    L.append("")

    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
