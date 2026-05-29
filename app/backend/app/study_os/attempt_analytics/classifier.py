from __future__ import annotations

from typing import Callable

Rule = tuple[Callable[[dict], bool], str]


def _opt_tag_role(row: dict) -> str | None:
    tags = row.get("option_tags") or {}
    sel = row.get("selected_option_id")
    return (tags.get(sel) or {}).get("role")


RULES: list[Rule] = [
    (lambda r: bool(r.get("is_correct")), "correct"),
    (lambda r: (not r.get("is_correct")) and r.get("selected_option_id") is not None and r.get("difficulty") in {"easy", "medium"} and int(r.get("time_spent_sec") or 0) < 0.5 * int(r.get("expected_time_sec") or 0), "silly_mistake"),
    (lambda r: (not r.get("is_correct")) and (r.get("subject") in {"Quant", "Reasoning"}) and _opt_tag_role(r) == "calculation_layer", "calc_error"),
    (lambda r: (not r.get("is_correct")) and _opt_tag_role(r) == "trap", "option_trap"),
    (lambda r: (not r.get("is_correct")) and r.get("selected_option_id") is not None and r.get("difficulty") in {"medium", "hard"} and int(r.get("time_spent_sec") or 0) > 1.5 * int(r.get("expected_time_sec") or 0), "concept_gap"),
    (lambda r: bool(r.get("is_marked_for_review")) and r.get("selected_option_id") is None, "marked_unanswered"),
    (lambda r: (not bool(r.get("was_visited"))) or (bool(r.get("was_visited")) and r.get("selected_option_id") is None and not bool(r.get("is_marked_for_review"))), "time_pressure_unattempted"),
    (lambda r: (not r.get("is_correct")) and r.get("selected_option_id") is not None, "knowledge_gap"),
]


def classify_response(row: dict) -> tuple[str, dict]:
    for pred, label in RULES:
        if pred(row):
            return label, {
                "time_spent_sec": int(row.get("time_spent_sec") or 0),
                "expected_time_sec": int(row.get("expected_time_sec") or 0),
                "difficulty": row.get("difficulty"),
                "selected_option_id": row.get("selected_option_id"),
                "was_visited": bool(row.get("was_visited")),
                "is_marked_for_review": bool(row.get("is_marked_for_review")),
            }
    return "knowledge_gap", {}
