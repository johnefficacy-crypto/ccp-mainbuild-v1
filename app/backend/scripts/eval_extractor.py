"""CLI: grade extraction candidates against a fixture or smoke-check an unlabeled run.

Usage (labeled 2026 fixture):
    python -m scripts.eval_extractor \\
        --candidates /tmp/extracted_2026.json \\
        --fixture app/backend/tests/fixtures/exam_intelligence_extraction/upsc_cse_pyq_v1/questions.json

Usage (unlabeled 2025 smoke):
    python -m scripts.eval_extractor \\
        --candidates /tmp/extracted_2025.json \\
        --smoke-only

Prints a Markdown report to stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from typing import Any


# ---------------------------------------------------------------------------
# Text normalization (mirrors the acceptance gate test)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'^[qn]\.\s*', '', t)
    t = re.sub(r"[^\w\s?.']", '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _text_sim(a: str, b: str) -> float:
    try:
        from Levenshtein import ratio
    except ImportError:
        # Fallback: simple character overlap
        na, nb = _normalize(a), _normalize(b)
        if not na and not nb:
            return 1.0
        if not na or not nb:
            return 0.0
        common = sum(1 for c in set(na) if c in nb)
        return common / max(len(set(na)), len(set(nb)))
    return ratio(_normalize(a), _normalize(b))


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _iou(a: list[float], b: list[float]) -> float:
    ix_min = max(a[0], b[0])
    iy_min = max(a[1], b[1])
    ix_max = min(a[2], b[2])
    iy_max = min(a[3], b[3])
    if ix_max <= ix_min or iy_max <= iy_min:
        return 0.0
    inter = (ix_max - ix_min) * (iy_max - iy_min)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid_inside(bbox_ext: list[float], bbox_fix: list[float]) -> bool:
    cx = (bbox_ext[0] + bbox_ext[2]) / 2.0
    cy = (bbox_ext[1] + bbox_ext[3]) / 2.0
    return bbox_fix[0] <= cx <= bbox_fix[2] and bbox_fix[1] <= cy <= bbox_fix[3]


# ---------------------------------------------------------------------------
# Match logic
# ---------------------------------------------------------------------------

IOU_THRESHOLD = 0.50
TEXT_SIM_THRESHOLD = 0.95


def _is_match(ext_q: dict, fix_q: dict) -> bool:
    fix_page = fix_q["regions"][0]["page"]
    fix_bbox = fix_q["regions"][0]["bbox"]
    for region in ext_q.get("regions", []):
        if region["page"] != fix_page:
            continue
        eb = region["bbox"]
        geom_ok = _iou(eb, fix_bbox) >= IOU_THRESHOLD or _centroid_inside(eb, fix_bbox)
        text_ok = (
            _text_sim(ext_q["question_text"], fix_q["question_text"]) >= TEXT_SIM_THRESHOLD
            or ext_q["question_number"] == fix_q["question_number"]
        )
        if geom_ok and text_ok:
            return True
    return False


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _percentile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100.0 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac


# ---------------------------------------------------------------------------
# Full eval (labeled)
# ---------------------------------------------------------------------------

def run_eval(candidates: dict, fixture: dict) -> str:
    ext_qs = candidates.get("expected_questions", [])
    fix_qs = fixture.get("expected_questions", [])

    matched_fix_nums: list[int] = []
    missed_fix_nums: list[int] = []
    iou_vals: list[float] = []
    text_sim_vals: list[float] = []

    for fq in fix_qs:
        best_iou = 0.0
        best_sim = 0.0
        matched = False
        for eq in ext_qs:
            if _is_match(eq, fq):
                matched = True
                for region in eq.get("regions", []):
                    if region["page"] == fq["regions"][0]["page"]:
                        v = _iou(region["bbox"], fq["regions"][0]["bbox"])
                        best_iou = max(best_iou, v)
                best_sim = max(best_sim, _text_sim(eq["question_text"], fq["question_text"]))
                break
        if matched:
            matched_fix_nums.append(fq["question_number"])
            if best_iou > 0:
                iou_vals.append(best_iou)
            if best_sim > 0:
                text_sim_vals.append(best_sim)
        else:
            missed_fix_nums.append(fq["question_number"])

    ext_qnums = [q["question_number"] for q in ext_qs]
    qnum_counts = Counter(ext_qnums)
    invented = [n for n in ext_qnums if not (1 <= n <= 200)]
    duplicates = [n for n, c in qnum_counts.items() if c > 1]

    recall = len(matched_fix_nums) / len(fix_qs) if fix_qs else 0.0
    precision = len(matched_fix_nums) / len(ext_qs) if ext_qs else 0.0

    lines = [
        "# Extractor Evaluation Report",
        "",
        "## Match summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Fixture questions | {len(fix_qs)} |",
        f"| Extracted candidates | {len(ext_qs)} |",
        f"| Matched | {len(matched_fix_nums)} |",
        f"| Recall | **{recall:.3f}** {'✅' if recall >= 0.80 else '❌ (< 0.80 threshold)'} |",
        f"| Precision | {precision:.3f} |",
        f"| Invented Q#s | {len(invented)} {'✅' if not invented else '❌'} |",
        f"| Duplicate Q#s | {len(duplicates)} {'✅' if not duplicates else '❌'} |",
        "",
        "## IoU distribution (matched pairs)",
        f"| p50 | p90 |",
        f"|-----|-----|",
        f"| {_percentile(iou_vals, 50):.3f} | {_percentile(iou_vals, 90):.3f} |",
        "",
        "## Text similarity distribution (matched pairs)",
        f"| p50 | p90 |",
        f"|-----|-----|",
        f"| {_percentile(text_sim_vals, 50):.3f} | {_percentile(text_sim_vals, 90):.3f} |",
    ]

    if missed_fix_nums:
        lines += ["", "## Missed fixture questions", f"{sorted(missed_fix_nums)}"]
    if invented:
        lines += ["", "## Invented question numbers", f"{sorted(invented)}"]
    if duplicates:
        lines += ["", "## Duplicate question numbers", f"{sorted(duplicates)}"]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Smoke eval (unlabeled)
# ---------------------------------------------------------------------------

def run_smoke(candidates: dict) -> str:
    ext_qs = candidates.get("expected_questions", [])
    qnums = [q["question_number"] for q in ext_qs]
    qnum_counts = Counter(qnums)

    by_page: Counter = Counter()
    for q in ext_qs:
        for r in q.get("regions", []):
            by_page[r["page"]] += 1

    invalid = [n for n in qnums if not (1 <= n <= 200)]
    duplicates = [n for n, c in qnum_counts.items() if c > 1]

    bucket_1_50 = sum(1 for n in qnums if 1 <= n <= 50)
    bucket_51_100 = sum(1 for n in qnums if 51 <= n <= 100)
    bucket_over_100 = sum(1 for n in qnums if n > 100)

    pages_sorted = sorted(by_page.items())

    lines = [
        "# Extractor Smoke Report (unlabeled)",
        "",
        f"Total candidates: **{len(ext_qs)}**",
        "",
        "## Q# range buckets",
        f"| Range | Count |",
        f"|-------|-------|",
        f"| 1–50 | {bucket_1_50} |",
        f"| 51–100 | {bucket_51_100} |",
        f"| >100 | {bucket_over_100} |",
        "",
        f"Invalid Q#s (outside 1–200): {sorted(invalid) or 'none'} {'✅' if not invalid else '❌'}",
        f"Duplicate Q#s: {sorted(duplicates) or 'none'} {'✅' if not duplicates else '❌'}",
        "",
        "## Per-page candidate counts",
        "| Page | Candidates |",
        "|------|------------|",
    ] + [f"| {pg} | {cnt} |" for pg, cnt in pages_sorted]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade extraction candidates against a fixture (or smoke-check an unlabeled run)."
    )
    parser.add_argument("--candidates", required=True, help="Path to candidates JSON (from run_extractor_dry)")
    parser.add_argument("--fixture", default=None, help="Path to fixture questions.json")
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Skip fixture matching; print unlabeled smoke stats only",
    )
    args = parser.parse_args()

    with open(args.candidates, encoding="utf-8") as f:
        candidates = json.load(f)

    if args.smoke_only or not args.fixture:
        report = run_smoke(candidates)
    else:
        with open(args.fixture, encoding="utf-8") as f:
            fixture = json.load(f)
        report = run_eval(candidates, fixture)

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
