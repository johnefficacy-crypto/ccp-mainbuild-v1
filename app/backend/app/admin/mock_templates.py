from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MOCK_PUBLISHER_PERMISSION = "mock.publisher"


class TemplateValidationError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_selector(selector: dict, question_count: int) -> None:
    mode = selector.get("mode")
    if mode == "criteria":
        mix = ((selector.get("filters") or {}).get("difficulty_mix") or {})
        if mix:
            total = float(sum(float(v or 0) for v in mix.values()))
            if abs(total - 1.0) > 0.001:
                raise TemplateValidationError("difficulty_mix must sum to 1.0 ±0.001")
    elif mode == "fixed":
        qids = selector.get("question_ids") or []
        if len(qids) != int(question_count):
            raise TemplateValidationError("fixed selector question_ids length must equal question_count")
    else:
        raise TemplateValidationError("selector.mode must be one of ['criteria','fixed']")


def preview_selection(supabase: Any, template_id: str, user_id: str | None = None) -> dict:
    sec_rows = supabase.table("mock_template_sections").select("*").eq("template_id", template_id).order("section_index").execute().data or []
    sections = []
    for sec in sec_rows:
        selector = sec.get("selector") or {}
        _validate_selector(selector, int(sec.get("question_count") or 0))
        requested = int(sec.get("question_count") or 0)
        available = requested
        gaps: list[dict] = []
        if selector.get("mode") == "fixed":
            qids = selector.get("question_ids") or []
            rows = supabase.table("mock_question_bank").select("id,reviewer_status").in_("id", qids).eq("reviewer_status", "published").execute().data or []
            available = len(rows)
            if available < requested:
                gaps.append({"reason": "fixed_unpublished", "needed": requested, "available": available})
        sections.append({"name": sec["name"], "requested": requested, "available": available, "gaps": gaps})
    return {"sections": sections, "has_gaps": any(s["gaps"] for s in sections)}
