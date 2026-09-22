"""The shape of an answer structure, and the one validator every writer uses.

An answer structure says what a descriptive question DEMANDS and what a good
answer must carry. It is deliberately not a model essay: every field is a list
of short angles or points, never paragraphs an aspirant could memorise.

Three writers go through ``validate_structure``: the generation script (model
output), the admin edit route (a reviewer's patch merged onto the stored row)
and the regenerate route. Migration 303 pins only top-level JSON types; the
shape lives here so a schema revision needs no immutable migration edited.

``word_budget`` is never taken from a model. It is computed from the question's
own ``word_limit`` or ``marks`` by ``word_budget_for`` — a number the question
states, split by a fixed ratio.
"""
from __future__ import annotations

import re
from typing import Any

#: Bumped whenever a field is added, removed or re-shaped.
SCHEMA_VERSION = 1

STATUSES = ("draft", "in_review", "verified", "rejected")

#: Review transitions, mirrored from ``cms_review_answer_structure`` (migration
#: 303). The RPC is authoritative; this copy lets the API reject a bad request
#: before a round-trip and lets the UI offer only legal decisions.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("in_review", "verified", "rejected"),
    "in_review": ("verified", "rejected", "draft"),
    "verified": ("rejected",),
    "rejected": (),
}

#: Only these statuses may be edited in place (the RPC enforces the same).
EDITABLE_STATUSES = frozenset({"draft", "in_review"})

#: Fields a reviewer may edit. Provenance, status and review columns are never
#: part of a content patch.
CONTENT_FIELDS = (
    "directive",
    "demand",
    "intro_angles",
    "body_points",
    "dimensions",
    "examples",
    "conclusion_angles",
    "pitfalls",
    "word_budget",
    "sources_note",
)

_LIST_FIELDS = {
    # field: (min items, max items, max chars per item)
    "intro_angles": (1, 4, 240),
    "dimensions": (0, 10, 60),
    "examples": (0, 8, 240),
    "conclusion_angles": (1, 4, 240),
    "pitfalls": (1, 6, 240),
}

MIN_BODY_POINTS = 2
MAX_BODY_POINTS = 12
MAX_SUB_POINTS = 6

_POINT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,15}$")

_POINT_KEYS = frozenset(
    {"id", "point", "why", "evidence_type", "example", "thinker", "sub_points"}
)


class StructureSchemaError(ValueError):
    """A structure that does not match the schema. ``errors`` lists every
    problem found, not just the first — a reviewer fixing one field at a time
    against a validator that reports one error at a time is a slow loop."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _text(value: Any, *, field: str, max_len: int, errors: list[str],
          required: bool = True) -> str | None:
    if value is None:
        if required:
            errors.append(f"{field} is required")
        return None
    if not isinstance(value, str):
        errors.append(f"{field} must be a string")
        return None
    text = value.strip()
    if required and not text:
        errors.append(f"{field} must not be empty")
        return None
    if len(text) > max_len:
        errors.append(f"{field} must be at most {max_len} characters")
        return None
    return text or None


def _str_list(value: Any, *, field: str, min_items: int, max_items: int,
              max_len: int, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list of strings")
        return []
    out: list[str] = []
    for i, item in enumerate(value):
        text = _text(item, field=f"{field}[{i}]", max_len=max_len, errors=errors)
        if text:
            out.append(text)
    if len(out) < min_items:
        errors.append(f"{field} needs at least {min_items} item(s)")
    if len(out) > max_items:
        errors.append(f"{field} allows at most {max_items} items")
    return out


def _body_points(value: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("body_points must be a list")
        return []
    points: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw in enumerate(value):
        where = f"body_points[{i}]"
        if not isinstance(raw, dict):
            errors.append(f"{where} must be an object")
            continue
        unknown = sorted(set(raw) - _POINT_KEYS)
        if unknown:
            errors.append(f"{where} has unknown keys: {', '.join(unknown)}")
        pid = raw.get("id")
        if not isinstance(pid, str) or not _POINT_ID.match(pid):
            errors.append(f"{where}.id must match {_POINT_ID.pattern}")
            pid = None
        elif pid in seen:
            errors.append(f"{where}.id '{pid}' is duplicated")
        else:
            seen.add(pid)
        subs_raw = raw.get("sub_points", [])
        subs = _str_list(
            subs_raw if subs_raw is not None else [],
            field=f"{where}.sub_points", min_items=0, max_items=MAX_SUB_POINTS,
            max_len=200, errors=errors,
        )
        points.append({
            "id": pid,
            "point": _text(raw.get("point"), field=f"{where}.point", max_len=240, errors=errors),
            "why": _text(raw.get("why"), field=f"{where}.why", max_len=300, errors=errors,
                         required=False),
            "evidence_type": _text(raw.get("evidence_type"), field=f"{where}.evidence_type",
                                   max_len=200, errors=errors, required=False),
            "example": _text(raw.get("example"), field=f"{where}.example", max_len=240,
                             errors=errors, required=False),
            "thinker": _text(raw.get("thinker"), field=f"{where}.thinker", max_len=120,
                             errors=errors, required=False),
            "sub_points": subs,
        })
    if len(points) < MIN_BODY_POINTS:
        errors.append(f"body_points needs at least {MIN_BODY_POINTS} points")
    if len(points) > MAX_BODY_POINTS:
        errors.append(f"body_points allows at most {MAX_BODY_POINTS} points")
    return points


def _word_budget(value: Any, errors: list[str]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append("word_budget must be an object or null")
        return None
    out: dict[str, Any] = {}
    for key in ("total", "intro", "body", "conclusion"):
        v = value.get(key)
        if v is None:
            out[key] = None
        elif isinstance(v, bool) or not isinstance(v, int) or v <= 0 or v > 5000:
            errors.append(f"word_budget.{key} must be a positive integer or null")
        else:
            out[key] = v
    basis = value.get("basis")
    if basis is not None and basis not in ("word_limit", "marks"):
        errors.append("word_budget.basis must be 'word_limit', 'marks' or null")
    out["basis"] = basis
    return out


def validate_structure(payload: Any) -> dict[str, Any]:
    """Validate and normalise a full structure. Raises ``StructureSchemaError``.

    Returns only the content fields, trimmed, with unknown top-level keys
    rejected — a model that invents a field is a model not following the
    schema, and silently dropping it would hide that.
    """
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise StructureSchemaError(["structure must be a JSON object"])
    allowed = set(CONTENT_FIELDS) | {"uncertainty"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        errors.append(f"unknown fields: {', '.join(unknown)}")

    out: dict[str, Any] = {
        "directive": _text(payload.get("directive"), field="directive", max_len=80, errors=errors),
        "demand": _text(payload.get("demand"), field="demand", max_len=400, errors=errors),
        "body_points": _body_points(payload.get("body_points"), errors),
        "word_budget": _word_budget(payload.get("word_budget"), errors),
        "sources_note": _text(payload.get("sources_note"), field="sources_note",
                              max_len=600, errors=errors, required=False),
    }
    for field, (lo, hi, max_len) in _LIST_FIELDS.items():
        out[field] = _str_list(
            payload.get(field, [] if lo == 0 else None),
            field=field, min_items=lo, max_items=hi, max_len=max_len, errors=errors,
        )
    if errors:
        raise StructureSchemaError(errors)
    return out


# ── the model's own uncertainty flags ────────────────────────────────────────


def uncertainty_of(payload: Any) -> list[str]:
    """The model's ``uncertainty`` list, if it gave one. Stored in
    generation_meta for the reviewer; never part of the structure itself."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("uncertainty")
    if not isinstance(raw, list):
        return []
    return [str(x).strip()[:300] for x in raw if str(x).strip()][:10]


# ── fabrication lint ─────────────────────────────────────────────────────────
#
# The prompt forbids invented statistics, report names, case names and
# citations. A prompt is a request, not a guarantee, so the output is linted
# too. The lint WARNS — it does not reject — because "Article 21" or "73rd
# Amendment" are legitimate and look numeric. Warnings are stored in
# generation_meta and shown to the reviewer beside the fields they hit.

_LINT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("percentage", re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|per\s?cent)", re.I)),
    ("currency_amount", re.compile(r"(?:₹|rs\.?|inr|\$|usd)\s?\d", re.I)),
    ("large_quantity", re.compile(r"\b\d+(?:\.\d+)?\s?(?:crore|lakh|million|billion|trillion)\b", re.I)),
    ("named_case", re.compile(r"\b[A-Z][\w.]+ v(?:s)?\.? [A-Z][\w.]+", re.U)),
    ("dated_report", re.compile(
        r"\b(?:report|survey|index|study)\b[^.]{0,40}\b(?:19|20)\d{2}\b"
        r"|\b(?:19|20)\d{2}\b[^.]{0,40}\b(?:report|survey|index|study)\b", re.I)),
)


def _strings_of(structure: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in ("directive", "demand", "sources_note"):
        if structure.get(key):
            out.append((key, str(structure[key])))
    for key in _LIST_FIELDS:
        for i, v in enumerate(structure.get(key) or []):
            out.append((f"{key}[{i}]", str(v)))
    for i, p in enumerate(structure.get("body_points") or []):
        for k in ("point", "why", "evidence_type", "example", "thinker"):
            if p.get(k):
                out.append((f"body_points[{i}].{k}", str(p[k])))
        for j, s in enumerate(p.get("sub_points") or []):
            out.append((f"body_points[{i}].sub_points[{j}]", str(s)))
    return out


def lint_structure(structure: dict[str, Any]) -> list[dict[str, str]]:
    """Places a validated structure LOOKS like it states a specific fact that
    the prompt told the model to describe generically instead."""
    warnings: list[dict[str, str]] = []
    for where, text in _strings_of(structure):
        for kind, pattern in _LINT_PATTERNS:
            m = pattern.search(text)
            if m:
                warnings.append({"field": where, "kind": kind, "match": m.group(0)})
    return warnings


# ── word budget from the question itself ─────────────────────────────────────

#: UPSC Mains convention where no explicit limit is printed. Only marks the
#: exam actually uses; anything else yields no budget rather than a guess.
_WORDS_BY_MARKS = {10: 150, 12: 200, 12.5: 200, 15: 250, 20: 300, 25: 400, 50: 700, 125: 1100}


def _round10(n: float) -> int:
    return max(10, int(round(n / 10.0)) * 10)


def word_budget_for(*, word_limit: Any = None, marks: Any = None) -> dict[str, Any] | None:
    """{total, intro, body, conclusion, basis} or None when neither is known.

    The printed word limit wins over the marks convention. Split 15/70/15.
    """
    total: int | None = None
    basis: str | None = None
    try:
        wl = int(word_limit) if word_limit is not None and not isinstance(word_limit, bool) else None
    except (TypeError, ValueError):
        wl = None
    if wl and wl > 0:
        total, basis = wl, "word_limit"
    else:
        try:
            mk = float(marks) if marks is not None and not isinstance(marks, bool) else None
        except (TypeError, ValueError):
            mk = None
        if mk is not None:
            key = int(mk) if mk.is_integer() else mk
            if key in _WORDS_BY_MARKS:
                total, basis = _WORDS_BY_MARKS[key], "marks"
    if not total:
        return None
    intro = _round10(total * 0.15)
    conclusion = _round10(total * 0.15)
    return {
        "total": total,
        "intro": intro,
        "body": max(10, total - intro - conclusion),
        "conclusion": conclusion,
        "basis": basis,
    }


# ── learner-facing projection ────────────────────────────────────────────────


def learner_payload(row: dict[str, Any]) -> dict[str, Any]:
    """What an aspirant sees. Provenance, generation metadata and review notes
    never leave the server — they are the platform's working state, not
    something an aspirant can use."""
    return {
        "id": row.get("id"),
        "version": row.get("version"),
        "directive": row.get("directive"),
        "demand": row.get("demand"),
        "intro_angles": row.get("intro_angles") or [],
        "body_points": [
            {k: p.get(k) for k in ("id", "point", "why", "evidence_type", "example",
                                    "thinker", "sub_points")}
            for p in (row.get("body_points") or []) if isinstance(p, dict)
        ],
        "dimensions": row.get("dimensions") or [],
        "examples": row.get("examples") or [],
        "conclusion_angles": row.get("conclusion_angles") or [],
        "pitfalls": row.get("pitfalls") or [],
        "word_budget": row.get("word_budget"),
        "sources_note": row.get("sources_note"),
    }


def point_ids(row: dict[str, Any] | None) -> list[str]:
    return [
        str(p["id"]) for p in ((row or {}).get("body_points") or [])
        if isinstance(p, dict) and p.get("id")
    ]


def coverage_pct(covered: Any, ids: list[str]) -> float | None:
    """Share of the structure's body points the aspirant ticked, 0..100, one
    decimal. None when there is nothing to measure against."""
    if not ids or not isinstance(covered, list):
        return None
    ticked = {str(c) for c in covered} & set(ids)
    return round(100.0 * len(ticked) / len(ids), 1)
