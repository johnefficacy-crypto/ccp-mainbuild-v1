"""Acceptance gate test: extractor vs. 2026 GS-I fixture.

Marked as 'integration' and 'slow'. Requires live Supabase credentials
(SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY) and the Tesseract binary.

Recall threshold: >= 0.80 (80% of fixture questions matched).
Zero invented question_numbers. Zero duplicate question_numbers.

This test gates merge. Run locally with:
    pytest tests/exam_intelligence/extraction/test_pipeline_against_fixture.py \
        -m integration -v -s
"""
from __future__ import annotations

import logging
import re
import statistics

import pytest

RECALL_THRESHOLD = 0.80
IOU_THRESHOLD = 0.50
TEXT_SIM_THRESHOLD = 0.95


def _percentiles(values: list[float], ps=(10, 25, 50, 75, 90)) -> dict[int, float]:
    """Return {p: value} percentiles; empty input yields zeros."""
    if not values:
        return {p: 0.0 for p in ps}
    s = sorted(values)
    out: dict[int, float] = {}
    for p in ps:
        if len(s) == 1:
            out[p] = s[0]
            continue
        rank = (p / 100.0) * (len(s) - 1)
        lo = int(rank)
        hi = min(lo + 1, len(s) - 1)
        frac = rank - lo
        out[p] = s[lo] + (s[hi] - s[lo]) * frac
    return out


def _best_metrics(extracted_list, fixture_q: dict) -> tuple[float, float]:
    """Best (iou, text_sim) over extracted regions on the fixture q's page."""
    fix_page = fixture_q["regions"][0]["page"]
    fix_bbox = tuple(fixture_q["regions"][0]["bbox"])
    fix_text = fixture_q["question_text"]
    best_iou = 0.0
    best_sim = 0.0
    for eq in extracted_list:
        sim = _text_similarity(eq.question_text, fix_text)
        for region in eq.regions:
            if region.page != fix_page:
                continue
            iou = _iou(region.bbox, fix_bbox)
            if iou > best_iou:
                best_iou = iou
            if sim > best_sim:
                best_sim = sim
    return best_iou, best_sim


def _normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation except ? and ."""
    t = text.lower()
    t = re.sub(r'\s+', ' ', t).strip()
    # Remove leading "Q." or "N." numbering
    t = re.sub(r'^[qn]\.\s*', '', t)
    # Strip punctuation except ? and .
    t = re.sub(r"[^\w\s?.']", '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _iou(a: tuple[float, float, float, float],
         b: tuple[float, float, float, float]) -> float:
    ix_min = max(a[0], b[0])
    iy_min = max(a[1], b[1])
    ix_max = min(a[2], b[2])
    iy_max = min(a[3], b[3])
    if ix_max <= ix_min or iy_max <= iy_min:
        return 0.0
    intersection = (ix_max - ix_min) * (iy_max - iy_min)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _centroid_inside(centroid: tuple[float, float],
                     bbox: tuple[float, float, float, float]) -> bool:
    cx, cy = centroid
    return bbox[0] <= cx <= bbox[2] and bbox[1] <= cy <= bbox[3]


def _text_similarity(a: str, b: str) -> float:
    from Levenshtein import ratio
    return ratio(_normalize_text(a), _normalize_text(b))


def _matches(extracted, fixture_q: dict) -> bool:
    """True if extracted question matches a fixture question per corpus contract."""
    fix_page = fixture_q["regions"][0]["page"]
    fix_bbox = tuple(fixture_q["regions"][0]["bbox"])
    fix_text = fixture_q["question_text"]
    fix_qnum = fixture_q["question_number"]

    for region in extracted.regions:
        if region.page != fix_page:
            continue
        ext_bbox = region.bbox
        cx = (ext_bbox[0] + ext_bbox[2]) / 2.0
        cy = (ext_bbox[1] + ext_bbox[3]) / 2.0
        if (
            _iou(ext_bbox, fix_bbox) >= IOU_THRESHOLD
            or _centroid_inside((cx, cy), fix_bbox)
        ) and (
            _text_similarity(extracted.question_text, fix_text) >= TEXT_SIM_THRESHOLD
            or extracted.question_number == fix_qnum
        ):
            return True
    return False


@pytest.mark.integration
@pytest.mark.slow
def test_recall_against_2026_fixture(pdf_bytes_2026, questions_fixture):
    """Extractor recall >= 0.80 on the 2026 GS-I fixture."""
    # Surface the pipeline's per-page DIAG lines into the captured (-s) output.
    logging.basicConfig(level=logging.DEBUG, force=True)
    logging.getLogger("app.exam_intelligence.extraction.pipeline").setLevel(logging.DEBUG)

    from app.exam_intelligence.extraction.pipeline import extract

    result = extract(pdf_bytes_2026, document_id="83722a86-610b-471d-8b6b-4a8397aa1791")
    extracted = result.questions
    fixture_qs = questions_fixture["expected_questions"]

    # Count matched fixture questions.
    matched_fix_nums: list[int] = []
    unmatched_fix_nums: list[int] = []
    for fq in fixture_qs:
        if any(_matches(eq, fq) for eq in extracted):
            matched_fix_nums.append(fq["question_number"])
        else:
            unmatched_fix_nums.append(fq["question_number"])

    recall = len(matched_fix_nums) / len(fixture_qs) if fixture_qs else 0.0

    # Invented: extracted Q#s not in [1..200]
    extracted_qnums = [q.question_number for q in extracted]
    invented_qnums = [n for n in extracted_qnums if not (1 <= n <= 200)]

    # Duplicates: Q#s appearing more than once in extracted output
    from collections import Counter
    qnum_counts = Counter(extracted_qnums)
    duplicate_qnums = [n for n, c in qnum_counts.items() if c > 1]

    # ----------------------------------------------------------------------
    # Empirical report (printed under -s for the acceptance record).
    # ----------------------------------------------------------------------
    matched_set = set(matched_fix_nums)
    precision = (len(matched_fix_nums) / len(extracted)) if extracted else 0.0

    ious = [_best_metrics(extracted, fq)[0] for fq in fixture_qs]
    sims = [_best_metrics(extracted, fq)[1] for fq in fixture_qs]
    iou_pct = _percentiles(ious)
    sim_pct = _percentiles(sims)

    # Per-page recall table + extracted-by-page.
    by_page_fix: dict[int, list[int]] = {}
    for fq in fixture_qs:
        by_page_fix.setdefault(fq["regions"][0]["page"], []).append(fq["question_number"])
    ext_by_page: dict[int, list[int]] = {}
    for eq in extracted:
        for region in eq.regions:
            ext_by_page.setdefault(region.page, []).append(eq.question_number)

    print("\n========== EXTRACTOR ACCEPTANCE REPORT (2026 GS-I) ==========")
    print(f"Aggregate: recall={recall:.3f}  precision={precision:.3f}  "
          f"extracted={len(extracted)}  fixture={len(fixture_qs)}")
    print(f"text-sim percentiles: " + "  ".join(f"p{p}={sim_pct[p]:.3f}" for p in (10, 25, 50, 75, 90)))
    print(f"IoU      percentiles: " + "  ".join(f"p{p}={iou_pct[p]:.3f}" for p in (10, 25, 50, 75, 90)))
    print(f"invented Q#s: {sorted(invented_qnums)}")
    print(f"duplicate Q#s: {sorted(duplicate_qnums)}")
    print("\nPer-page recall:")
    print(f"{'page':>4} {'exp':>3} {'hit':>3} {'recall':>6}  missed")
    for p in sorted(by_page_fix):
        exp = sorted(by_page_fix[p])
        hit = [n for n in exp if n in matched_set]
        miss = [n for n in exp if n not in matched_set]
        pr = len(hit) / len(exp) if exp else 0.0
        print(f"{p:>4} {len(exp):>3} {len(hit):>3} {pr:>6.2f}  {miss}  ext={sorted(set(ext_by_page.get(p, [])))}")
    print("\nExtracted regions (qnum, page, bbox):")
    for eq in sorted(extracted, key=lambda q: q.question_number):
        b = eq.regions[0].bbox
        print(f"  Q{eq.question_number:>3} p{eq.regions[0].page} "
              f"({b[0]:.3f},{b[1]:.3f},{b[2]:.3f},{b[3]:.3f})")
    print("============================================================\n")

    assert len(invented_qnums) == 0, (
        f"Extractor invented question numbers: {sorted(invented_qnums)}"
    )
    assert len(duplicate_qnums) == 0, (
        f"Extractor produced duplicate question numbers: {sorted(duplicate_qnums)}"
    )
    assert recall >= RECALL_THRESHOLD, (
        f"Recall {recall:.3f} < {RECALL_THRESHOLD}.\n"
        f"Matched ({len(matched_fix_nums)}): {sorted(matched_fix_nums)}\n"
        f"Missed  ({len(unmatched_fix_nums)}): {sorted(unmatched_fix_nums)}\n"
        f"Total extracted: {len(extracted)}"
    )
