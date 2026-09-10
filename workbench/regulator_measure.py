"""Measure the two defect classes on IFSCA, PFRDA and SEBI.

1. Missing direction-block context: a printed question that sits inside a
   `Directions (a-b):` range whose loaded stem does not carry the block body.
2. Option continuations: a printed option whose second and later lines were
   dropped, leaving the loaded option text a strict prefix of the printed one.
   Reconstruction follows migration 286 - walk the printed block, open an
   option at its marker, append until the next marker.

Absent vs lost: a loaded question with no printed counterpart in the book is
`absent` - the recall compiler never captured it, and no migration recovers it.
Only `lost` (printed in the book, missing from the row) is repairable.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "workbench")
from regulator_source_index import (  # noqa: E402
    RE_DIRECTIONS, SourceQuestion, ascii_digits, load_all, squash,
)

TEXTDIR = ("/tmp/claude-0/-home-user-ccp-mainbuild-v1/"
           "d442057c-9243-523f-b533-4d39a3e783a8/scratchpad/reg")
LIVE = "verified"

# What a loader welds onto the tail of a paper's last option: the book's
# running header, a page number, or the subject heading printed as a footer.
SUBJECT_WORDS = (
    r"Quantitative\s+Aptitude|Reasoning\s*(?:Ability|Onoing|oning)?|REASONOING|"
    r"English\s+Language|General\s+Awareness|Commerce\s*&?\s*Account\w*|Costing|"
    r"Economic[s]?(?:\s*&\s*Social\s+Development)?|Finance|Management|"
    r"Companies\s+Act|Pension\s+Sector|Insurance\s*&\s*Pension|"
    r"IFSCA\s*&\s*GIFT\s*CITY|Union\s+Budget\s*&\s*Economic\s+Survey|"
    r"Banking[,]?\s*Capital\s+Market\w*\s*&\s*Bullion"
)
RE_TAIL_FURNITURE = re.compile(
    r"^\W*(?:\d{1,3}\s*)?(?:"
    r"(?:IFSCA|PFRDA|FRDA|CA)\s+Grade\s+A\b.*"
    r"|(?:" + SUBJECT_WORDS + r")\b\W*(?:\d{1,3})?\W*"
    r"(?:(?:IFSCA|PFRDA|FRDA|CA)\s+Grade\s+A\b.*)?"
    r")\W*$",
    re.I | re.S,
)


def load_db(slug: str):
    base = f"review_out_{slug}"
    q = json.load(open(f"{base}/questions_export.json", encoding="utf-8"))
    o = json.load(open(f"{base}/options_export.json", encoding="utf-8"))
    papers = {p["paper_id"]: p
              for p in json.load(open(f"mojibake_scan_{slug}.json",
                                      encoding="utf-8"))["papers"]}
    st = json.load(open(f"{base}/stimuli_export.json", encoding="utf-8"))
    # a set's context legitimately lives in pyq_stimuli rather than in the stem;
    # a question is only missing context when neither carries it
    stim_by_q = defaultdict(list)
    for row in st:
        qids = row.get("question_ids") or []
        if isinstance(qids, str):
            qids = ast.literal_eval(qids)
        for qid in qids:
            stim_by_q[qid].append(row)
    by_q = defaultdict(list)
    for row in o:
        by_q[row["question_id"]].append(row)
    for rows in by_q.values():
        rows.sort(key=lambda r: r.get("display_order") or 0)
    for row in q:
        row["paper_code"] = papers.get(row["paper_id"], {}).get("paper_code", "?")
        row["options"] = by_q.get(row["id"], [])
        row["stimuli"] = stim_by_q.get(row["id"], [])
    return q, st


# The books open most direction blocks with a lead-in that addresses the
# candidate rather than stating the setup.  A loader that stores only the
# substance is right to drop it, so it must not count as missing context.
RE_LEADIN = re.compile(
    r"^\s*(?:read|study|answer|refer\s+to|go\s+through|consider)\b[^.:?]{0,120}"
    r"(?:below|following|passage|information|questions?|carefully|data|table|"
    r"paragraph|graph|chart)\b[^.:?]{0,60}[.:]?\s*",
    re.I,
)


def strip_leadin(body: str) -> str:
    return RE_LEADIN.sub("", body, count=1).strip()


def contains(hay: str, needle: str, anchor: int = 40) -> bool:
    """Does `hay` carry `needle`?

    Squash both to lowercase alphanumerics, then probe with sliding anchors
    rather than only the head: the head is exactly what a loader legitimately
    trims (a lead-in sentence), and the tail is what a truncating loader drops.
    A hit anywhere means the substance is carried.
    """
    h, _ = squash(ascii_digits(hay))
    n, _ = squash(ascii_digits(strip_leadin(needle) or needle))
    if not n:
        return True
    if len(n) <= anchor:
        return n in h
    step = max(1, anchor // 2)
    return any(n[i:i + anchor] in h for i in range(0, len(n) - anchor + 1, step))


def _stem_hit(a: str, b: str, anchor: int = 40) -> bool:
    """Do two squashed stems share a head anchor in either direction?"""
    if not a or not b:
        return False
    pa = a[:anchor] if len(a) > anchor else a
    pb = b[:anchor] if len(b) > anchor else b
    return pb in a or pa in b


def match_paper(db_rows: list[dict], printed: dict[int, SourceQuestion]):
    """Pair loaded rows to printed questions within one paper.

    question_number is not a safe key: where a printed question was never
    loaded the loader recompacted the numbering, so whole papers sit at a
    constant offset from the book.  Stem text alone is not safe either - a
    reasoning paper repeats "Which of the following statements is correct?"
    verbatim across unrelated sets, and a greedy matcher hands the second
    occurrence to the first set.

    Both sequences run in printed order, so alignment must preserve it.  This
    is a Needleman-Wunsch pass over (loaded order, printed order) scoring a
    stem anchor as a match; order-preserving alignment resolves the duplicates
    and absorbs a constant offset in one step.
    """
    db = sorted(db_rows, key=lambda r: r["question_number"])
    nums = sorted(printed)
    A = [squash(ascii_digits(r["question_text"]))[0] for r in db]
    B = [squash(ascii_digits(printed[n].stem))[0] for n in nums]
    n, m = len(A), len(B)
    GAP = -1
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        score[i][0] = i * GAP
    for j in range(1, m + 1):
        score[0][j] = j * GAP
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            hit = 3 if _stem_hit(A[i - 1], B[j - 1]) else -2
            score[i][j] = max(score[i - 1][j - 1] + hit,
                              score[i - 1][j] + GAP,
                              score[i][j - 1] + GAP)
    pairs = {}
    i, j = n, m
    while i > 0 and j > 0:
        hit = 3 if _stem_hit(A[i - 1], B[j - 1]) else -2
        if score[i][j] == score[i - 1][j - 1] + hit:
            if hit > 0:
                pairs[db[i - 1]["id"]] = nums[j - 1]
            i, j = i - 1, j - 1
        elif score[i][j] == score[i - 1][j] + GAP:
            i -= 1
        else:
            j -= 1
    return pairs


def measure(slug: str, src: dict[str, dict[int, SourceQuestion]]):
    rows, _ = load_db(slug)
    out = {
        "exam": slug,
        "loaded": len(rows),
        "live": sum(1 for r in rows if r["reviewer_status"] == LIVE),
        "matched": 0,
        "unmatched_paper": Counter(),
        "ctx_lost": [],
        "ctx_ok": 0,
        "ctx_absent": [],
        "ctx_mismatch": [],
        "ctx_via_stimulus": 0,
        "opt_lost": [],
        "opt_bleed": [],
        "opt_divergent": [],
        "opt_absent_q": 0,
        "opt_checked": 0,
        "not_in_book": 0,
    }
    by_paper = defaultdict(list)
    for r in rows:
        by_paper[r["paper_code"]].append(r)
    pairs = {}
    for code, db_rows in by_paper.items():
        if code in src:
            pairs.update(match_paper(db_rows, src[code]))

    for r in rows:
        code = r["paper_code"]
        num = pairs.get(r["id"])
        sq = src.get(code, {}).get(num) if num is not None else None
        if sq is None:
            if code in src:
                out["not_in_book"] += 1
            else:
                out["unmatched_paper"][code] += 1
            continue
        out["matched"] += 1

        # --- measurement 1: direction-block context ---------------------
        if sq.direction_body:
            substance = strip_leadin(sq.direction_body)
            # observed gap in these books: task instructions top out at 463
            # chars, the shortest real scenario runs 554.  Cut at 500.
            kind = "setup" if len(substance) >= 500 else "instruction"
            carriers = [r["question_text"]] + [
                s.get("content_text") or "" for s in r["stimuli"]
            ]
            if any(contains(c, sq.direction_body) for c in carriers):
                out["ctx_ok"] += 1
            else:
                out["ctx_lost"].append({
                    "id": r["id"], "paper_code": code, "q": num,
                    "status": r["reviewer_status"],
                    "range": sq.direction_range,
                    "kind": kind,
                    "has_stimulus": bool(r["stimuli"]),
                    "body_len": len(sq.direction_body),
                    "body": sq.direction_body,
                    "stem": r["question_text"],
                })

        # --- measurement 2: option continuations ------------------------
        db_opts = r["options"]
        if not db_opts or not sq.options:
            if db_opts and not sq.options:
                out["opt_absent_q"] += 1
            continue
        for i, opt in enumerate(db_opts):
            label = (opt.get("option_label") or "").strip().lower()
            printed = sq.options.get(label)
            if printed is None and i < len(sq.options):
                printed = list(sq.options.values())[i]
            if not printed:
                continue
            out["opt_checked"] += 1
            db_sq, _ = squash(ascii_digits(opt["option_text"]))
            pr_sq, pr_idx = squash(ascii_digits(printed))
            if db_sq == pr_sq or not db_sq:
                continue
            rec = {
                "option_id": opt["id"], "question_id": r["id"],
                "paper_code": code, "src_q": num, "label": label,
                "is_correct": bool(opt.get("is_correct")),
                "status": r["reviewer_status"],
                "loaded": opt["option_text"], "printed": printed,
            }
            if pr_sq.startswith(db_sq) and len(pr_sq) - len(db_sq) >= 3:
                # loaded text stops short of the printed option
                out["opt_lost"].append(rec)
            elif db_sq.startswith(pr_sq) and len(db_sq) - len(pr_sq) >= 3:
                # loaded text runs past the printed option; what it swallowed
                # decides whether this is page furniture or real text
                tail = opt["option_text"]
                head_len = len(printed.rstrip())
                idx = opt["option_text"].lower().find(printed.strip()[:20].lower())
                if idx >= 0:
                    tail = opt["option_text"][idx + head_len:]
                rec["tail"] = tail.strip()
                rec["tail_kind"] = ("furniture"
                                    if RE_TAIL_FURNITURE.match(tail.strip())
                                    else "text")
                out["opt_bleed"].append(rec)
            else:
                out["opt_divergent"].append(rec)
    return out


def main():
    src = load_all(TEXTDIR)
    results = {}
    for slug in ("ifsca", "pfrda"):
        results[slug] = measure(slug, src)
    json.dump(results, open(f"{TEXTDIR}/measure.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    for slug, r in results.items():
        print(f"=== {slug.upper()}  loaded={r['loaded']} live={r['live']} "
              f"matched={r['matched']}")
        lost = r["ctx_lost"]
        setup = [c for c in lost if c["kind"] == "setup"]
        instr = [c for c in lost if c["kind"] == "instruction"]
        print(f"    ctx: in a printed block={r['ctx_ok'] + len(lost)}  "
              f"carried={r['ctx_ok']}  lost={len(lost)}")
        print(f"         setup lost={len(setup)} (live "
              f"{sum(1 for c in setup if c['status'] == LIVE)})  "
              f"instruction lost={len(instr)} (live "
              f"{sum(1 for c in instr if c['status'] == LIVE)})")
        bleed_f = [o for o in r["opt_bleed"] if o["tail_kind"] == "furniture"]
        bleed_t = [o for o in r["opt_bleed"] if o["tail_kind"] == "text"]
        print(f"    opt: checked={r['opt_checked']}  "
              f"tail-lost={len(r['opt_lost'])}  "
              f"furniture-bleed={len(bleed_f)} (keyed "
              f"{sum(1 for o in bleed_f if o['is_correct'])}, live "
              f"{sum(1 for o in bleed_f if o['status'] == LIVE)})  "
              f"text-bleed={len(bleed_t)}  divergent={len(r['opt_divergent'])}")
        print(f"    rows loaded but not printed in the book={r['not_in_book']}")
        print(f"    unmatched rows={sum(r['unmatched_paper'].values())}")
        for code, n in r["unmatched_paper"].most_common(12):
            print(f"        {code:32s} {n}")


if __name__ == "__main__":
    main()
