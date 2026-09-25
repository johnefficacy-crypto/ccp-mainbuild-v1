"""Authored-question side content: metadata, stimuli, structured explanation (REG-CORPUS-02).

Shared by the admin CRUD create (``mock_questions.create_question``) and the
bulk import commit (``mock_import.commit_import``) so both write the same
shapes. Nothing here publishes: bank rows are born ``draft``, explanation rows
``pending``, and both move only through their existing review lifecycles.

Shapes
------
``metadata``        ``{"rubric_level": "L1".."L4", "stimulus_group": str}`` —
                    stored on ``mock_question_bank.metadata`` (migration 309).
``stimuli``         ``[{"stimulus_type": "passage"|"table", "content_text": str,
                    "language"?: str}]`` — written to ``mock_question_stimuli``
                    as THIS row's own snapshot copies. A case set is N rows that
                    share ``metadata.stimulus_group``; each row gets its own
                    copy of the case text. There is no cross-row stimulus FK.
``structured_explanation``
                    ``{"solution_steps": [str], "formula_used": [str],
                    "common_traps": [str], "option_rationales": {option_index: str}}``
                    — written to ``pyq_question_explanations`` keyed by
                    ``mock_question_id`` (migration 310), ``pending``, with the
                    correct option as ``final_answer_mock_option_id`` and the
                    rationales re-keyed from option index to
                    ``mock_question_options.id``.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.admin.authored_content")

RUBRIC_LEVELS = ("L1", "L2", "L3", "L4")
STIMULUS_TYPES = ("passage", "table")
_MAX_STIMULI = 5


def normalise_metadata(rubric_level: Any = None, stimulus_group: Any = None, base: Any = None) -> dict:
    """Validated ``mock_question_bank.metadata``. Raises ``ValueError``."""
    meta: dict[str, Any] = dict(base) if isinstance(base, dict) else {}
    if rubric_level not in (None, ""):
        level = str(rubric_level).strip().upper()
        if level not in RUBRIC_LEVELS:
            raise ValueError(f"rubric_level must be one of {'|'.join(RUBRIC_LEVELS)}; got {rubric_level!r}")
        meta["rubric_level"] = level
    if stimulus_group not in (None, ""):
        group = str(stimulus_group).strip()
        if not group:
            raise ValueError("stimulus_group must be a non-empty string")
        meta["stimulus_group"] = group
    return meta


def normalise_stimuli(stimuli: Any) -> list[dict]:
    """Validated stimulus list (possibly empty). Raises ``ValueError``."""
    if stimuli in (None, ""):
        return []
    if not isinstance(stimuli, list):
        raise ValueError("stimuli must be a list")
    if len(stimuli) > _MAX_STIMULI:
        raise ValueError(f"at most {_MAX_STIMULI} stimuli per question")
    out: list[dict] = []
    for i, s in enumerate(stimuli):
        if not isinstance(s, dict):
            raise ValueError(f"stimuli[{i}] must be an object")
        stype = str(s.get("stimulus_type") or "passage").strip().lower()
        if stype not in STIMULUS_TYPES:
            raise ValueError(f"stimuli[{i}].stimulus_type must be passage|table; got {stype!r}")
        text = str(s.get("content_text") or "").strip()
        if not text:
            raise ValueError(f"stimuli[{i}].content_text is required")
        out.append({
            "stimulus_type": stype,
            "content_text": text,
            "language": (str(s.get("language")).strip() if s.get("language") else None),
        })
    return out


def _str_list(value: Any, field: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of strings")
    return [str(v).strip() for v in value if str(v or "").strip()]


def normalise_structured_explanation(value: Any, option_count: int) -> dict | None:
    """Validated structured explanation, or ``None`` when nothing was supplied.

    ``option_rationales`` is keyed by the 0-based option index the author sees;
    it is re-keyed to option ids at write time."""
    if value in (None, "", {}):
        return None
    if not isinstance(value, dict):
        raise ValueError("structured_explanation must be an object")
    steps = _str_list(value.get("solution_steps"), "solution_steps")
    formulas = _str_list(value.get("formula_used"), "formula_used")
    traps = _str_list(value.get("common_traps"), "common_traps")
    raw_rat = value.get("option_rationales") or {}
    if not isinstance(raw_rat, dict):
        raise ValueError("option_rationales must be an object keyed by option index")
    rationales: dict[int, str] = {}
    for k, text in raw_rat.items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            raise ValueError(f"option_rationales key {k!r} is not an option index") from None
        if not 0 <= idx < option_count:
            raise ValueError(f"option_rationales key {idx} out of range for {option_count} options")
        if str(text or "").strip():
            rationales[idx] = str(text).strip()
    if not (steps or formulas or traps or rationales):
        return None
    return {
        "solution_steps": steps,
        "formula_used": formulas,
        "common_traps": traps,
        "option_rationales": rationales,
    }


def write_stimuli(sb: Any, question_id: str, stimuli: list[dict], *, language: str | None = None) -> int:
    """Insert this row's own stimulus snapshot copies. Returns rows written."""
    if not stimuli:
        return 0
    rows = [
        {
            "mock_question_id": question_id,
            "pyq_stimulus_id": None,  # lineage-only column; authored stimuli have none
            "stimulus_type": s["stimulus_type"],
            "content_text": s["content_text"],
            "language": s.get("language") or language,
            "display_order": i + 1,
        }
        for i, s in enumerate(stimuli)
    ]
    sb.table("mock_question_stimuli").insert(rows).execute()
    return len(rows)


def write_structured_explanation(
    sb: Any, question_id: str, explanation: dict | None, options: list[dict]
) -> str | None:
    """Insert a ``pending`` authored explanation. Returns its id, or ``None``
    when there is nothing to write.

    ``options`` are the persisted ``mock_question_options`` rows (with ``id``,
    ``option_index``, ``is_correct``)."""
    if not explanation:
        return None
    by_index = {o.get("option_index"): o for o in options if o.get("id") is not None}
    correct = next((o for o in options if o.get("is_correct")), None)
    row = {
        "mock_question_id": question_id,
        "solution_steps": explanation["solution_steps"],
        "formula_used": explanation["formula_used"],
        "common_traps": explanation["common_traps"],
        "option_rationales": {
            str(by_index[i]["id"]): text
            for i, text in explanation["option_rationales"].items()
            if i in by_index
        },
        "final_answer_mock_option_id": correct["id"] if correct else None,
        "explanation_source_type": "platform_original",
        "license_status": "owned",
        # Explanations feed the review queue; never born verified.
        "reviewer_status": "pending",
    }
    inserted = sb.table("pyq_question_explanations").insert(row).execute().data or []
    return inserted[0].get("id") if inserted else None
