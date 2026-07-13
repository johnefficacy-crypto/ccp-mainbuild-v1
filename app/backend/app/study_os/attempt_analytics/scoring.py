from __future__ import annotations

from decimal import Decimal


def D(v) -> Decimal:
    return Decimal(str(v if v is not None else 0))


def compute_scoring(attempt: dict, responses: list[dict], dwell_by_q: dict[str, int]):
    snap = attempt.get("template_snapshot") or {}
    total_q = len(responses)
    c = w = u = m = 0
    score = Decimal("0")
    sec_map: dict[int, dict] = {}
    for r in responses:
        q = r.get("question_snapshot") or {}
        section_index = int(q.get("section_index") or 0)
        section_name = q.get("section_name") or "General"
        marks = D(q.get("marks") or snap.get("marks_per_correct") or 1)
        neg = D(q.get("negative_marks") or snap.get("marks_per_wrong") or 0)
        sid = section_index
        sec = sec_map.setdefault(sid, {"section_index": sid, "section_name": section_name, "correct": 0, "wrong": 0, "unattempted": 0, "marks": Decimal("0"), "time_used_sec": 0})
        # Key off the authoritative per-response grade set by the deterministic
        # scorer (_finalize_submission): True=correct, False=wrong, None=
        # unattempted/ungradeable. This spans MCQ and integer/numerical uniformly
        # and, critically, keeps a typed-but-ungradeable answer OUT of the wrong
        # bucket so negative marking never penalizes a fail-closed response.
        ic = r.get("is_correct")
        if ic is True:
            c += 1; sec["correct"] += 1; score += marks; sec["marks"] += marks
        elif ic is False:
            w += 1; sec["wrong"] += 1; score -= neg; sec["marks"] -= neg
        else:
            u += 1; sec["unattempted"] += 1
        if r.get("is_marked_for_review"):
            m += 1
        sec["time_used_sec"] += int(dwell_by_q.get(r["question_id"], 0))

    attempted = c + w
    duration = int(snap.get("duration_sec") or 0)
    used = sum(dwell_by_q.values())
    summary = {
        "score_raw": score,
        "score_percentage": (score / D(total_q) * D("100")) if total_q else D("0"),
        "total_correct": c,
        "total_wrong": w,
        "total_unattempted": u,
        "total_marked": m,
        "net_marks": score,
        "accuracy_pct": (D(c) / D(attempted) * D("100")) if attempted else D("0"),
        "time_used_sec": used,
        "time_remaining_sec": max(0, duration - used),
        "avg_time_per_q_sec": (D(used) / D(total_q)) if total_q else D("0"),
    }
    sections = []
    for _, sec in sorted(sec_map.items()):
        att = sec["correct"] + sec["wrong"]
        sec["accuracy_pct"] = (D(sec["correct"]) / D(att) * D("100")) if att else D("0")
        sections.append(sec)
    return summary, sections
