from __future__ import annotations

from decimal import Decimal


def D(v):
    return Decimal(str(v if v is not None else 0))


def compute_topic_breakdown(responses: list[dict], dwell_by_q: dict[str, int]) -> list[dict]:
    groups: dict[tuple[str | None, str | None], dict] = {}
    for r in responses:
        q = r.get("question_snapshot") or {}
        key = (q.get("topic_id"), q.get("microtopic_id"))
        g = groups.setdefault(key, {
            "topic_id": key[0], "microtopic_id": key[1], "attempted": 0, "correct": 0, "wrong": 0,
            "time_total": 0, "difficulty_breakdown": {"easy": {"att": 0, "corr": 0}, "medium": {"att": 0, "corr": 0}, "hard": {"att": 0, "corr": 0}}
        })
        diff = q.get("difficulty") or "medium"
        sel = r.get("selected_option_id")
        if sel is not None:
            g["attempted"] += 1
            g["difficulty_breakdown"][diff]["att"] += 1
            if r.get("is_correct"):
                g["correct"] += 1
                g["difficulty_breakdown"][diff]["corr"] += 1
            else:
                g["wrong"] += 1
        g["time_total"] += int(dwell_by_q.get(r["question_id"], 0))

    out = []
    for g in groups.values():
        att = g["attempted"]
        out.append({
            "topic_id": g["topic_id"], "microtopic_id": g["microtopic_id"], "attempted": att,
            "correct": g["correct"], "wrong": g["wrong"],
            "accuracy_pct": (D(g["correct"]) / D(att) * D("100")) if att else D("0"),
            "avg_time_sec": (D(g["time_total"]) / D(att if att else 1)),
            "difficulty_breakdown": g["difficulty_breakdown"],
        })
    return out
