"""PYQ-specialised bulk import: preflight + idempotent commit.

Flow
----
1. POST /pyq-papers/{paper_id}/bulk-import/preflight
   Parse CSV or JSON bytes, validate every row, run dedup ladder,
   return per-row preview + import_token.  NO writes.

2. POST /pyq-papers/{paper_id}/bulk-import/commit
   Consume import_token, write question+options (+ stimuli/links for v2)
   per clean row via the same question→options cascade the CMS single-row
   endpoint uses.  Idempotent: rows whose question_number (v1) or
   source_question_ref (v2) already exists in the paper are skipped rather
   than duplicated.

CSV/JSON v1 (legacy) contract
------------------------------
CSV columns: question_number, question_text, option_a, option_b, option_c,
option_d, correct_option, question_type, observed_difficulty. JSON: a bare
list of row objects with the same fields. Always exactly 4 options (A-D).
This legacy shape is preserved byte-for-byte — see PYQ Intelligence v2 PR-2.

CSV/JSON v2 (variable option count, sections, shared stimuli)
--------------------------------------------------------------
JSON: an object envelope::

    {
      "format_version": 2,
      "stimuli": [
        {"ref": "passage-04", "stimulus_type": "passage", "content_text": "...",
         "section_ref": "reasoning", "display_order": 1}
      ],
      "questions": [
        {
          "source_question_ref": "Q17", "display_order": 17,
          "section_ref": "reasoning", "stimulus_refs": ["passage-04"],
          "question_text": "...", "question_type": "mcq",
          "options": [{"label": "1", "source_label": "(1)", "text": "...",
                       "display_order": 1}, ...],
          "correct_option_label": "1", "observed_difficulty": "medium"
        }
      ]
    }

``stimuli`` and every per-question field except ``question_text``/
``question_type``/``options`` are optional. ``options`` supports 2+ entries
with arbitrary unique non-empty ``label`` strings. ``correct_option_label``
must resolve to exactly one supplied option's label when
``question_type == "mcq"``.

CSV v2 is detected by an ``options_json`` column (instead of
``option_a``..``option_d``) holding a JSON-encoded array of
``{"label", "source_label", "text", "display_order"}`` objects, plus
``correct_option_label`` and optionally ``source_question_ref``,
``display_order``, ``section_ref``.

``section_ref`` resolves case-insensitively against
``exam_phase_sections.section_label`` scoped to the target paper's
``exam_phase_id``. ``stimulus_refs`` resolve against the batch's own
``stimuli`` array; the referenced ``pyq_stimuli`` row is created once per
``ref`` during commit (shared across every question in the same commit
call that references it) and linked via ``pyq_question_stimuli``.

Dedup ladder (both formats)
----------------------------
1. Exact: normalized-stem hash (question_hash) matches an existing row
   in the same paper  → status "duplicate"
2. Near-miss only: Levenshtein ratio >= 0.85  → status "fuzzy"
   (fuzzy check is skipped when the exact-hash list is non-empty, since
   that would be redundant noise)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.pyq_bulk_import")

# ── Token store (Supabase-backed) ─────────────────────────────────────────────

_DEFAULT_TTL_SEC = 3600


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_token(
    sb,
    *,
    token: str,
    paper_id: str,
    summary: dict,
    rows: dict,
    ttl_seconds: int = _DEFAULT_TTL_SEC,
    created_by: str | None = None,
) -> None:
    """INSERT into pyq_import_tokens with expires_at = now + ttl."""
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
    sb.table("pyq_import_tokens").insert({
        "token": token,
        "paper_id": paper_id,
        "preflight_summary": summary,
        "preflight_rows": rows,
        "created_by": created_by,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "consumed_at": None,
    }).execute()


def _load_token(sb, *, token: str, paper_id: str) -> dict | None:
    """SELECT row WHERE token=$1 AND paper_id=$2 AND consumed_at IS NULL AND expires_at > now().

    Returns the row dict or None if not found / expired / consumed.
    """
    now_iso = _now_iso()
    rows = (
        sb.table("pyq_import_tokens")
        .select("*")
        .eq("token", token)
        .eq("paper_id", paper_id)
        .is_("consumed_at", None)
        .gt("expires_at", now_iso)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


def _consume_token(sb, *, token: str) -> None:
    """UPDATE pyq_import_tokens SET consumed_at = now() WHERE token=$1."""
    sb.table("pyq_import_tokens").update({"consumed_at": _now_iso()}).eq("token", token).execute()


def _claim_token(sb, *, token: str, paper_id: str) -> dict | None:
    """Atomically claim (consume) a token scoped to ``paper_id``.

    Performs ``UPDATE pyq_import_tokens SET consumed_at = now() WHERE
    token = $1 AND paper_id = $2 AND consumed_at IS NULL`` as a single
    database operation — this IS the consume step, done first, so two
    concurrent callers racing on the same token can never both see it as
    unconsumed. Supabase/PostgREST returns the modified row(s) from an
    UPDATE by default, so ``.data`` on success is the claimed token row.

    Returns the claimed row dict, or ``None`` if no row matched (unknown
    token, wrong paper_id, or already consumed). Does NOT check
    ``expires_at`` — the caller checks expiry separately after claiming
    (an expired-but-unconsumed token is still atomically claimed here;
    the caller then rejects it, which is fine since it was one-shot
    either way).
    """
    rows = (
        sb.table("pyq_import_tokens")
        .update({"consumed_at": _now_iso()})
        .eq("token", token)
        .eq("paper_id", paper_id)
        .is_("consumed_at", None)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


# ── Constants ─────────────────────────────────────────────────────────────────

_CORRECT_OPTIONS = {"A", "B", "C", "D"}
_QUESTION_TYPES = frozenset(("mcq", "numerical", "descriptive", "caselet", "matching", "other"))
_CSV_REQUIRED = {
    "question_number", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct_option", "question_type",
}

# v2: mirrors the pyq_stimuli.stimulus_type check constraint (migration 223).
# This is the full DB-level allow-list — kept for documentation of what the
# schema permits. The importer itself only accepts the smaller
# _STIMULUS_TYPES_V2_SUPPORTED subset below (PR-11 scope note).
_STIMULUS_TYPES = frozenset(("passage", "caselet", "table", "chart", "image", "diagram", "other"))

# v2 importer scope (this PR): text/shared-grouping only. Media/asset types
# (chart, image, diagram) have no asset/locator/alt-text contract yet — that
# is explicitly deferred to PR-11 per docs/status/career-copilot-checklist.md.
_STIMULUS_TYPES_V2_SUPPORTED = frozenset(("passage", "caselet", "table"))

# v2 importer scope (this PR): single-answer MCQ scoring/import only — no
# correct_text_answer import, no multi-select, no descriptive-answer
# handling exists yet for the other _QUESTION_TYPES values.
_QUESTION_TYPES_V2_SUPPORTED = frozenset(("mcq",))

# ── Parse helpers ─────────────────────────────────────────────────────────────


def parse_bytes(content: bytes, content_type: str) -> dict:
    """Parse CSV or JSON bytes into a canonical batch envelope.

    Returns ``{"format_version": 1 | 2, "is_csv": bool, "stimuli": list[dict],
    "rows": list[dict]}``.

    Format detection:
    - JSON array           → v1 (legacy), ``rows`` = the array as-is.
    - JSON object           → v2, must carry a ``questions`` list (the
      object's ``stimuli`` list, if any, is carried alongside).
    - CSV with an ``options_json`` column → v2.
    - CSV with the legacy ``option_a``..``option_d`` columns → v1.
    """
    ct = (content_type or "").lower()
    if "json" in ct:
        raw = json.loads(content.decode("utf-8"))
        if isinstance(raw, list):
            return {"format_version": 1, "is_csv": False, "stimuli": [], "rows": raw}
        if isinstance(raw, dict):
            fmt_version = raw.get("format_version")
            # Must be present and exactly the integer 2 — bool is an int
            # subclass in Python, so explicitly exclude True/False too.
            if (
                not isinstance(fmt_version, int)
                or isinstance(fmt_version, bool)
                or fmt_version != 2
            ):
                raise ValueError(
                    f'JSON v2 object must declare "format_version": 2; got {fmt_version!r}'
                )
            questions = raw.get("questions")
            if not isinstance(questions, list):
                raise ValueError("JSON v2 object must include a 'questions' list")
            stimuli = raw.get("stimuli") or []
            if not isinstance(stimuli, list):
                raise ValueError("JSON v2 'stimuli' must be a list")
            return {"format_version": 2, "is_csv": False, "stimuli": stimuli, "rows": questions}
        raise ValueError("JSON must be a list of row objects, or a v2 object with a 'questions' list")

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty")
    header_keys = {k.strip().lower() for k in rows[0].keys()}
    norm_rows = [{k.strip().lower(): v for k, v in r.items()} for r in rows]

    if "options_json" in header_keys:
        return {"format_version": 2, "is_csv": True, "stimuli": [], "rows": norm_rows}

    missing = _CSV_REQUIRED - header_keys
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    return {"format_version": 1, "is_csv": True, "stimuli": [], "rows": norm_rows}


def _validate_row(raw: dict, seen_numbers: set[int]) -> tuple[dict | None, list[str]]:
    """Validate one raw v1 row. Returns (parsed, errors). observed_difficulty may be None."""
    errors: list[str] = []

    # question_number
    qn_raw = str(raw.get("question_number") or "").strip()
    try:
        qn = int(qn_raw)
    except ValueError:
        errors.append(f"question_number must be an integer; got {qn_raw!r}")
        qn = -1
    else:
        if qn in seen_numbers:
            errors.append(f"question_number {qn} is duplicated within the upload")

    # question_text
    question_text = str(raw.get("question_text") or "").strip()
    if not question_text:
        errors.append("question_text is required")

    # options
    opts: dict[str, str] = {}
    for lbl in ("a", "b", "c", "d"):
        val = str(raw.get(f"option_{lbl}") or "").strip()
        if not val:
            errors.append(f"option_{lbl} is required and must not be empty")
        opts[lbl.upper()] = val

    # correct_option
    correct_raw = str(raw.get("correct_option") or "").strip().upper()
    if correct_raw not in _CORRECT_OPTIONS:
        errors.append(f"correct_option must be one of A/B/C/D; got {correct_raw!r}")
        correct_raw = "A"

    # question_type
    qtype = str(raw.get("question_type") or "").strip().lower()
    if qtype not in _QUESTION_TYPES:
        errors.append(f"question_type must be one of {sorted(_QUESTION_TYPES)}; got {qtype!r}")

    # observed_difficulty — nullable
    diff_raw = raw.get("observed_difficulty")
    observed_difficulty: str | None = None
    if diff_raw is not None and str(diff_raw).strip():
        observed_difficulty = str(diff_raw).strip()

    if errors:
        return None, errors

    seen_numbers.add(qn)
    return {
        "question_number": qn,
        "question_text": question_text,
        "options": opts,          # {A: text, B: text, C: text, D: text}
        "correct_option": correct_raw,
        "question_type": qtype,
        "observed_difficulty": observed_difficulty,
    }, []


# ── v2 parse/validate helpers ─────────────────────────────────────────────────


def _parse_v2_options_field(raw: dict, is_csv: bool) -> tuple[list[Any] | None, str | None]:
    """Return (raw_options_list, error). For CSV, decodes the options_json column."""
    if is_csv:
        raw_opts = raw.get("options_json")
        if raw_opts is None or not str(raw_opts).strip():
            return None, "options_json is required and must not be empty"
        try:
            opts = json.loads(raw_opts)
        except (TypeError, ValueError) as exc:
            return None, f"options_json is not valid JSON: {exc}"
        if not isinstance(opts, list):
            return None, "options_json must be a JSON array"
        return opts, None

    opts = raw.get("options")
    if not isinstance(opts, list):
        return None, "options must be a list"
    return opts, None


def _parse_v2_stimulus_refs(raw: dict, is_csv: bool) -> tuple[list[str], list[str]]:
    """Return (stimulus_refs, errors). Lenient: CSV may carry a JSON array or
    comma-separated string in an (optional, not part of the required v2 CSV
    contract) ``stimulus_refs`` column; JSON carries a real list."""
    errors: list[str] = []
    raw_val = raw.get("stimulus_refs")

    if is_csv:
        if raw_val is None or not str(raw_val).strip():
            return [], errors
        try:
            parsed = json.loads(raw_val)
            if not isinstance(parsed, list):
                raise ValueError("not a list")
            return [str(r).strip() for r in parsed if str(r).strip()], errors
        except (TypeError, ValueError):
            return [s.strip() for s in str(raw_val).split(",") if s.strip()], errors

    if raw_val is None or raw_val == "":
        return [], errors
    if not isinstance(raw_val, list):
        errors.append("stimulus_refs must be a list")
        return [], errors
    return [str(r).strip() for r in raw_val if str(r).strip()], errors


def _validate_row_v2(
    raw: dict,
    *,
    is_csv: bool,
    row_num: int,
    seen_numbers: set[int],
    seen_source_refs: set[str],
    seen_display_orders: dict[int, int],
    stimulus_refs_available: set[str],
    section_lookup: dict[str, list[str]],
) -> tuple[dict | None, list[str]]:
    """Validate one raw v2 row (JSON question object or CSV row with
    options_json). Returns (parsed, errors), mirroring ``_validate_row``'s
    error-accumulation style."""
    errors: list[str] = []

    # source_question_ref — optional, dedup key within the upload when present.
    source_question_ref = str(raw.get("source_question_ref") or "").strip() or None
    if source_question_ref:
        if source_question_ref in seen_source_refs:
            errors.append(f"source_question_ref {source_question_ref!r} is duplicated within the upload")

    # question_number — optional for v2 ("legacy-shaped" v2 rows may still supply one).
    qn_raw = raw.get("question_number")
    qn: int | None = None
    if qn_raw is not None and str(qn_raw).strip():
        try:
            qn = int(qn_raw)
        except (TypeError, ValueError):
            errors.append(f"question_number must be an integer; got {qn_raw!r}")
        else:
            if qn in seen_numbers:
                errors.append(f"question_number {qn} is duplicated within the upload")

    # display_order — optional positive int. Migration 223's
    # pyq_questions_paper_display_order_uidx already backstops cross-batch
    # collisions (against pre-existing DB rows) at commit time as a normal,
    # already-safe per-row failure. This within-upload check is purely a
    # preflight-time UX/DX improvement so a collision is caught before commit
    # rather than surfacing as a late, confusing per-row DB failure.
    do_raw = raw.get("display_order")
    display_order: int | None = None
    if do_raw is not None and str(do_raw).strip():
        try:
            display_order = int(do_raw)
        except (TypeError, ValueError):
            errors.append(f"display_order must be an integer; got {do_raw!r}")
        else:
            if display_order < 1:
                errors.append("display_order must be >= 1")
            elif display_order in seen_display_orders:
                errors.append(
                    f"display_order {display_order} is duplicated within this upload "
                    f"(first used at row {seen_display_orders[display_order]})"
                )

    # question_text
    question_text = str(raw.get("question_text") or "").strip()
    if not question_text:
        errors.append("question_text is required")

    # question_type — v2 currently only supports single-answer MCQ import;
    # other _QUESTION_TYPES values (numerical, descriptive, caselet,
    # matching, other) have no scoring/import path implemented yet.
    qtype = str(raw.get("question_type") or "").strip().lower()
    if qtype not in _QUESTION_TYPES_V2_SUPPORTED:
        errors.append(
            f"question_type {qtype!r} is not yet supported by the v2 importer; "
            f"only 'mcq' is currently supported"
        )

    # observed_difficulty — nullable
    diff_raw = raw.get("observed_difficulty")
    observed_difficulty: str | None = None
    if diff_raw is not None and str(diff_raw).strip():
        observed_difficulty = str(diff_raw).strip()

    # section_ref — optional, resolved against exam_phase_sections scoped to
    # the paper's exam_phase_id (section_lookup keys are lower-cased labels,
    # each mapping to a LIST of ids since section_label is only unique per
    # (exam_phase_id, subject_id) — the same label can legitimately repeat
    # under two different subjects within one phase).
    section_ref_raw = raw.get("section_ref")
    section_ref = str(section_ref_raw).strip() if section_ref_raw not in (None, "") else None
    section_id: str | None = None
    if section_ref:
        matches = section_lookup.get(section_ref.lower(), [])
        if not matches:
            errors.append(
                f"section_ref '{section_ref}' does not resolve to a section in this paper's exam phase"
            )
        elif len(matches) > 1:
            errors.append(
                f"section_ref '{section_ref}' is ambiguous — {len(matches)} sections named "
                f"{section_ref!r} exist in this paper's exam phase; use an unambiguous reference"
            )
        else:
            section_id = matches[0]

    # stimulus_refs — each must match a ref declared in the batch's top-level
    # 'stimuli' array.
    stimulus_refs, ref_errors = _parse_v2_stimulus_refs(raw, is_csv)
    errors.extend(ref_errors)
    seen_stimulus_refs: set[str] = set()
    for ref in stimulus_refs:
        if ref not in stimulus_refs_available:
            errors.append(f"stimulus_refs entry '{ref}' does not match any declared stimulus")
        if ref in seen_stimulus_refs:
            errors.append(f"stimulus_refs contains duplicate ref {ref!r}")
        else:
            seen_stimulus_refs.add(ref)

    # options — 2+ entries, unique non-empty labels.
    raw_opts, opt_err = _parse_v2_options_field(raw, is_csv)
    parsed_opts: list[dict] = []
    if opt_err:
        errors.append(opt_err)
    else:
        if len(raw_opts) < 2:
            errors.append("options must contain at least 2 entries")
        seen_labels: set[str] = set()
        for i, o in enumerate(raw_opts):
            if not isinstance(o, dict):
                errors.append(f"options[{i}] must be an object")
                continue
            label = str(o.get("label") or "").strip()
            text = str(o.get("text") or "").strip()
            if not label:
                errors.append(f"options[{i}].label is required and must not be empty")
            elif label in seen_labels:
                errors.append(f"option label {label!r} is duplicated within the question")
            else:
                seen_labels.add(label)
            if not text:
                errors.append(f"options[{i}].text is required and must not be empty")

            opt_disp_raw = o.get("display_order")
            opt_disp: int | None = None
            if opt_disp_raw is not None and str(opt_disp_raw).strip():
                try:
                    opt_disp = int(opt_disp_raw)
                except (TypeError, ValueError):
                    errors.append(f"options[{i}].display_order must be an integer; got {opt_disp_raw!r}")
                else:
                    if opt_disp < 1:
                        errors.append(f"options[{i}].display_order must be >= 1")
            else:
                # Omitted display_order defaults to the option's 1-based
                # position in the supplied options array — only an explicitly
                # given value is validated as a positive int (above); an
                # omitted one is never left None.
                opt_disp = i + 1

            source_label = o.get("source_label")
            parsed_opts.append({
                "label": label,
                "text": text,
                "display_order": opt_disp,
                "source_label": str(source_label).strip() if source_label not in (None, "") else None,
            })

    # correct_option_label — required + must resolve to exactly one option
    # for mcq; best-effort (unvalidated) for every other question_type.
    correct_raw = raw.get("correct_option_label")
    correct_option_label = str(correct_raw).strip() if correct_raw not in (None, "") else None
    if qtype == "mcq":
        if not correct_option_label:
            errors.append("correct_option_label is required for question_type 'mcq'")
        elif parsed_opts:
            matches = [o for o in parsed_opts if o["label"] == correct_option_label]
            if len(matches) != 1:
                errors.append(
                    f"correct_option_label {correct_option_label!r} must resolve to exactly one "
                    f"supplied option's label; matched {len(matches)}"
                )

    if errors:
        return None, errors

    if source_question_ref:
        seen_source_refs.add(source_question_ref)
    if qn is not None:
        seen_numbers.add(qn)
    if display_order is not None:
        seen_display_orders[display_order] = row_num

    return {
        "source_question_ref": source_question_ref,
        "question_number": qn,
        "display_order": display_order,
        "question_text": question_text,
        "question_type": qtype,
        "observed_difficulty": observed_difficulty,
        "section_ref": section_ref,
        "section_id": section_id,
        "stimulus_refs": stimulus_refs,
        "options": parsed_opts,
        "correct_option_label": correct_option_label,
    }, []


def _validate_stimuli_batch(stimuli: list[Any], section_lookup: dict[str, list[str]]) -> dict[str, dict]:
    """Validate the top-level v2 'stimuli' array and resolve each entry's
    section_ref. Raises ValueError on any structural problem: a stimulus is
    shared infrastructure referenced by many questions, so a broken entry
    invalidates the whole batch rather than becoming one row-level error.
    """
    by_ref: dict[str, dict] = {}
    seen_display_orders: set[int] = set()
    for i, s in enumerate(stimuli):
        if not isinstance(s, dict):
            raise ValueError(f"stimuli[{i}] must be an object")

        ref = str(s.get("ref") or "").strip()
        if not ref:
            raise ValueError(f"stimuli[{i}].ref is required and must not be empty")
        if ref in by_ref:
            raise ValueError(f"stimuli ref {ref!r} is duplicated")

        stype = str(s.get("stimulus_type") or "").strip().lower()
        if stype not in _STIMULUS_TYPES_V2_SUPPORTED:
            raise ValueError(
                f"stimuli[{i}].stimulus_type {stype!r} is not yet supported by the importer "
                f"(PR-11 scope: text/shared-grouping only); use one of "
                f"{sorted(_STIMULUS_TYPES_V2_SUPPORTED)}"
            )

        section_ref_raw = s.get("section_ref")
        section_ref = str(section_ref_raw).strip() if section_ref_raw not in (None, "") else None
        section_id: str | None = None
        if section_ref:
            matches = section_lookup.get(section_ref.lower(), [])
            if not matches:
                raise ValueError(
                    f"stimuli[{i}] section_ref '{section_ref}' does not resolve to a section "
                    "in this paper's exam phase"
                )
            if len(matches) > 1:
                raise ValueError(
                    f"stimuli[{i}] section_ref '{section_ref}' is ambiguous — {len(matches)} "
                    f"sections named {section_ref!r} exist in this paper's exam phase; use an "
                    "unambiguous reference"
                )
            section_id = matches[0]

        do_raw = s.get("display_order")
        display_order: int | None = None
        if do_raw is not None and str(do_raw).strip():
            try:
                display_order = int(do_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"stimuli[{i}].display_order must be an integer; got {do_raw!r}"
                ) from exc
            if display_order < 1:
                raise ValueError(f"stimuli[{i}].display_order must be >= 1")
            # Preflight-time-only UX/DX improvement: migration 223's
            # pyq_stimuli_paper_display_order_uidx already backstops
            # cross-batch collisions against pre-existing DB rows at commit
            # time. This purely catches a WITHIN-batch collision earlier.
            if display_order in seen_display_orders:
                raise ValueError(
                    f"stimuli[{i}].display_order {display_order} is duplicated within this batch"
                )
            seen_display_orders.add(display_order)

        by_ref[ref] = {
            "stimulus_type": stype,
            "content_text": s.get("content_text"),
            "language": s.get("language"),
            "display_order": display_order,
            "section_id": section_id,
        }
    return by_ref


# ── Dedup helpers ─────────────────────────────────────────────────────────────


def _q_hash(text: str) -> str:
    """Stable SHA-256 of the canonical question text (mirrors question_hash)."""
    from app.exam_intelligence.option_normalize import question_hash
    return question_hash(text) or hashlib.sha256(text.lower().encode()).hexdigest()


from app.exam_intelligence.text_utils import levenshtein_ratio as _levenshtein_ratio


# ── Preflight ─────────────────────────────────────────────────────────────────


def preflight(
    supabase: Any,
    actor: dict,
    paper_id: str,
    content: bytes,
    content_type: str,
) -> dict:
    """Parse + validate + dedup. Returns preview and import_token. No writes."""

    try:
        batch = parse_bytes(content, content_type)
    except Exception as exc:
        raise ValueError(f"parse failed: {exc}") from exc

    format_version = batch["format_version"]
    is_csv = batch["is_csv"]
    raw_rows = batch["rows"]

    # Each lowercased section_label maps to a LIST of matching ids:
    # exam_phase_sections is only unique on (exam_phase_id, subject_id,
    # section_label), so the same label can legitimately repeat under two
    # different subjects within one phase — see _validate_row_v2 /
    # _validate_stimuli_batch for how ambiguous (2+) matches are handled.
    section_lookup: dict[str, list[str]] = {}
    stimuli_meta: dict[str, dict] = {}

    if format_version == 2:
        try:
            paper_rows = (
                supabase.table("pyq_papers")
                .select("id, exam_phase_id")
                .eq("id", paper_id)
                .execute()
                .data
            ) or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("preflight: could not fetch pyq_papers.exam_phase_id for %s: %s", paper_id, exc)
            paper_rows = []
        exam_phase_id = paper_rows[0].get("exam_phase_id") if paper_rows else None

        if exam_phase_id:
            try:
                section_rows = (
                    supabase.table("exam_phase_sections")
                    .select("id, section_label")
                    .eq("exam_phase_id", exam_phase_id)
                    .execute()
                    .data
                ) or []
            except Exception as exc:  # noqa: BLE001
                logger.warning("preflight: could not fetch exam_phase_sections for phase %s: %s", exam_phase_id, exc)
                section_rows = []
            for sr in section_rows:
                lbl = sr.get("section_label")
                if lbl:
                    section_lookup.setdefault(str(lbl).strip().lower(), []).append(sr["id"])

        try:
            stimuli_meta = _validate_stimuli_batch(batch["stimuli"], section_lookup)
        except Exception as exc:
            raise ValueError(f"parse failed: {exc}") from exc

    # Fetch existing question_numbers/source_question_refs and hashes for this
    # paper. This powers the dedup ladder's guarantee against re-importing
    # existing content — a failure here must fail closed (raise) rather than
    # silently degrade to "no duplicates found" (that would defeat the whole
    # point of preflight dedup on a transient DB error).
    try:
        existing_rows: list[dict] = (
            supabase.table("pyq_questions")
            .select("id, question_number, question_text, normalized_question_hash, source_question_ref")
            .eq("pyq_paper_id", paper_id)
            .limit(5000)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"preflight: could not fetch existing pyq_questions for paper {paper_id!r}; "
            f"refusing to run dedup with an incomplete existing-row set: {exc}"
        ) from exc

    existing_numbers: set[int] = set()
    existing_source_refs: set[str] = set()
    existing_hash_map: dict[str, dict] = {}   # hash → row
    existing_text_norms: list[tuple[str, dict]] = []  # (norm_text, row)

    for er in existing_rows:
        if er.get("question_number") is not None:
            try:
                existing_numbers.add(int(er["question_number"]))
            except (TypeError, ValueError):
                pass
        if er.get("source_question_ref"):
            existing_source_refs.add(er["source_question_ref"])
        h = er.get("normalized_question_hash")
        if h:
            existing_hash_map[h] = er
        qt = er.get("question_text")
        if qt:
            from app.exam_intelligence.option_normalize import normalize_question_text
            existing_text_norms.append((normalize_question_text(qt), er))

    seen_numbers: set[int] = set()
    seen_source_refs: set[str] = set()
    seen_display_orders: dict[int, int] = {}
    stimulus_refs_available = set(stimuli_meta.keys())
    preview_rows: list[dict] = []
    valid_parsed: list[dict] = []  # only rows that passed validation

    # Same-upload duplicate detection: both identity fields (source_question_ref,
    # question_number) are optional for v2, so two byte-identical v2 questions
    # with neither field set would otherwise both preflight "ok" — the existing
    # dedup ladder below only ever compares against rows already in the DB.
    # Maps normalized-question-hash -> the first row number that produced it,
    # within THIS upload only. Seeded for every row that reaches a final status
    # (ok, duplicate, or fuzzy) — not just "ok" — so that a row whose only fate
    # is "fuzzy" (a near-miss against an EXISTING DB row) still registers as
    # the "original" for a later byte-identical row in the same batch; without
    # this, two identical-hash rows that each independently land on "fuzzy"
    # would never see each other as batch-local duplicates, and since fuzzy
    # rows are committed by default, both would commit as exact-text
    # duplicates of each other (checkpost round 3, fix #2).
    batch_hash_map: dict[str, int] = {}

    for row_idx, raw in enumerate(raw_rows):
        if format_version == 2:
            parsed, errs = _validate_row_v2(
                raw,
                is_csv=is_csv,
                row_num=row_idx + 1,
                seen_numbers=seen_numbers,
                seen_source_refs=seen_source_refs,
                seen_display_orders=seen_display_orders,
                stimulus_refs_available=stimulus_refs_available,
                section_lookup=section_lookup,
            )
        else:
            parsed, errs = _validate_row(raw, seen_numbers)

        if errs:
            preview_rows.append({
                "row": row_idx + 1,
                "status": "error",
                "messages": errs,
                "question_number": None,
            })
            valid_parsed.append(None)  # placeholder to keep index alignment
            continue

        qt = parsed["question_text"]
        h = _q_hash(qt)
        parsed["_normalized_question_hash"] = h
        parsed["_format_version"] = format_version

        messages: list[str] = []
        status = "ok"

        if format_version == 2:
            qn = parsed.get("question_number")
            ident_ref = parsed.get("source_question_ref")
            if ident_ref and ident_ref in existing_source_refs:
                status = "duplicate"
                messages.append(f"source_question_ref {ident_ref!r} already exists in this paper")
            elif qn is not None and qn in existing_numbers:
                status = "duplicate"
                messages.append(f"question_number {qn} already exists in this paper")
        else:
            qn = parsed["question_number"]
            ident_ref = None
            # question_number already in paper
            if qn in existing_numbers:
                status = "duplicate"
                messages.append(f"question_number {qn} already exists in this paper")

        if status == "ok":
            # Same-upload duplicate: check BEFORE the existing-DB hash/fuzzy
            # checks, so a batch-local dupe short-circuits them entirely.
            if h in batch_hash_map:
                status = "duplicate"
                messages.append(
                    f"exact text match with row {batch_hash_map[h]} earlier in this same upload"
                )
            # Exact hash match against the DB
            elif h in existing_hash_map:
                status = "duplicate"
                dup = existing_hash_map[h]
                messages.append(
                    f"exact text match with existing question_number "
                    f"{dup.get('question_number')} (id={dup.get('id')})"
                )
            else:
                # Near-miss: Levenshtein on normalised text
                from app.exam_intelligence.option_normalize import normalize_question_text
                norm_candidate = normalize_question_text(qt)
                best_ratio = 0.0
                best_row: dict | None = None
                for norm_existing, er in existing_text_norms:
                    r = _levenshtein_ratio(norm_candidate, norm_existing)
                    if r > best_ratio:
                        best_ratio = r
                        best_row = er
                if best_ratio >= 0.85 and best_row:
                    status = "fuzzy"
                    messages.append(
                        f"near-duplicate (ratio={best_ratio:.2f}) with existing "
                        f"question_number {best_row.get('question_number')} "
                        f"(id={best_row.get('id')})"
                    )

        # Seed unconditionally (not just for status == "ok") — a row that
        # ends up "fuzzy" (near-miss against an EXISTING DB row) still needs
        # to register its hash so a later byte-identical row in this same
        # batch is caught as a batch-local "duplicate" instead of
        # independently re-running the same fuzzy check and also landing on
        # "fuzzy" (checkpost round 3, fix #2). Re-seeding a row that was
        # already itself flagged "duplicate" via `h in batch_hash_map` above
        # is a harmless no-op re-assignment to the same row number.
        batch_hash_map[h] = row_idx + 1

        if format_version == 2:
            preview_rows.append({
                "row": row_idx + 1,
                "status": status,
                "messages": messages,
                "question_number": qn,
                "source_question_ref": ident_ref,
                "question_text": qt[:120] + ("…" if len(qt) > 120 else ""),
                "question_type": parsed["question_type"],
                "correct_option_label": parsed.get("correct_option_label"),
                "observed_difficulty": parsed["observed_difficulty"],
                "section_ref": parsed.get("section_ref"),
                "stimulus_refs": parsed.get("stimulus_refs") or [],
            })
        else:
            preview_rows.append({
                "row": row_idx + 1,
                "status": status,
                "messages": messages,
                "question_number": qn,
                "question_text": qt[:120] + ("…" if len(qt) > 120 else ""),
                "question_type": parsed["question_type"],
                "correct_option": parsed["correct_option"],
                "observed_difficulty": parsed["observed_difficulty"],
            })
        valid_parsed.append(parsed)

    # Generate token
    token_input = (
        paper_id + actor.get("id", "")
        + str(_now_ts()) + hashlib.sha256(content).hexdigest()
    )
    import_token = hashlib.sha256(token_input.encode()).hexdigest()[:32]

    ok = sum(1 for p in preview_rows if p["status"] == "ok")
    errors = sum(1 for p in preview_rows if p["status"] == "error")
    duplicates = sum(1 for p in preview_rows if p["status"] == "duplicate")
    fuzzy = sum(1 for p in preview_rows if p["status"] == "fuzzy")

    summary = {"ok": ok, "error": errors, "duplicate": duplicates, "fuzzy": fuzzy}
    _store_token(
        supabase,
        token=import_token,
        paper_id=paper_id,
        summary=summary,
        rows={
            "parsed": valid_parsed,
            "preview": preview_rows,
            "format_version": format_version,
            "stimuli_meta": stimuli_meta,
        },
        created_by=actor.get("id"),
    )

    return {
        "import_token": import_token,
        "paper_id": paper_id,
        "total": len(raw_rows),
        "format_version": format_version,
        "summary": summary,
        "rows": preview_rows,
    }


# ── Commit ────────────────────────────────────────────────────────────────────


def commit(
    supabase: Any,
    actor: dict,
    import_token: str,
    *,
    paper_id: str,
    override_errors: bool = False,
) -> dict:
    """Commit previously preflighted rows.

    ``paper_id`` MUST be the URL's ``{paper_id}`` path parameter — the token
    lookup is scoped to it (``.eq("token", ...).eq("paper_id", ...)``), so a
    token preflighted for a different paper can never be committed through
    this paper's URL (it will simply not resolve, raising ``LookupError``).

    Token consumption is atomic: the DB operation that claims it is an
    UPDATE that both claims (sets ``consumed_at``) and reads the token row in
    one statement (see ``_claim_token``), so two concurrent commits racing on
    the same token can never both proceed — only one claims it, the other
    gets ``LookupError``.

    Ordering (checkpost round 3, fix #4): every read-only prerequisite fetch
    that depends only on ``paper_id`` (existing ``pyq_questions`` for the
    idempotency/dedup re-check, existing ``pyq_stimuli`` for durable-stimulus
    identity) runs BEFORE ``_claim_token`` — not after, as in earlier
    versions of this function. Both fetches fail closed (raise
    ``RuntimeError``) on error, so if either raises, the token has NOT been
    touched yet and the caller can safely retry the exact same ``commit()``
    call once the transient DB issue clears, instead of having permanently
    burned a one-shot token for a call that wrote nothing. Only the actual
    per-row parsed data and ``stimuli_meta`` (which live in
    ``store["preflight_rows"]``, only available AFTER the token is claimed)
    are read post-claim — including the stimulus content-mismatch check
    (fix #3b below), which needs both the pre-claim existing-stimuli fetch
    and the post-claim ``stimuli_meta``.

    Idempotent on question_number (v1), or on source_question_ref falling
    back to question_number when present (v2) — and, uniformly for both
    formats, on ``normalized_question_hash`` (checkpost round 3, fix #1):
    two SEPARATE ``commit()`` calls for byte-identical question text with
    neither identity field set would otherwise each pass their own
    within-call idempotency check and double-insert the same question.

    Bearer-token design (checkpost round 3, fix #4, documented not changed):
    ``actor`` is accepted for interface symmetry with ``preflight()`` and
    potential future audit use, but is NOT currently used to restrict who
    may commit. Any actor holding a valid, unexpired, unconsumed token
    string for the correct ``paper_id`` may commit it, regardless of who ran
    the original preflight — tokens are a bearer/transferable capability,
    not bound to ``created_by``. This is an intentional current design
    choice, not a bug; binding commit to the original preflighter would be a
    product decision to make separately.
    """
    # Read-only prerequisite fetches — BEFORE the token claim (fix #4, see
    # docstring). Both depend only on paper_id, which is a required kwarg
    # independent of the token's own content.

    # Existing question_numbers/source_question_refs/hashes for the
    # idempotency + no-identity dedup re-check. Must fail closed: a failure
    # here silently degrading to empty sets would mean a transient DB error
    # causes duplicate inserts instead of the intended idempotent skip.
    try:
        existing_qns_rows = (
            supabase.table("pyq_questions")
            .select("id, question_number, source_question_ref, normalized_question_hash")
            .eq("pyq_paper_id", paper_id)
            .limit(5000)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"commit: could not fetch existing pyq_questions for paper {paper_id!r}; "
            f"refusing to commit with an incomplete idempotency set: {exc}"
        ) from exc
    already_inserted: set[int] = {
        int(er["question_number"])
        for er in existing_qns_rows
        if er.get("question_number") is not None
    }
    already_inserted_refs: set[str] = {
        er["source_question_ref"]
        for er in existing_qns_rows
        if er.get("source_question_ref")
    }
    # Checkpost round 3, fix #1: two SEPARATE commit() calls for the same
    # no-identity question text (neither source_question_ref nor
    # question_number set on either) would otherwise each independently pass
    # the above two checks and double-insert. Re-checking the durable
    # normalized_question_hash here closes that hole uniformly for v1 and v2
    # (v1 always has both a question_number AND a hash, so this is a free
    # extra safety net there; v2 is the format that can lack both other
    # identity fields).
    already_inserted_hashes: set[str] = {
        er["normalized_question_hash"]
        for er in existing_qns_rows
        if er.get("normalized_question_hash")
    }

    # Durable shared-stimulus identity across separate commit() calls/retries:
    # a stimulus we create is tagged with metadata.import_ref = ref, so a
    # later retry (new token, new commit() call) that references the same
    # ref reuses the existing row instead of creating a second one. Fetch
    # fails closed (checkpost round 3, fix #3a) — this used to be the one
    # fail-open lookup left in this module; a transient failure here can now
    # create duplicate canonical stimuli, exactly the failure mode fixes #1/#2
    # close for questions, so it gets the same treatment.
    try:
        existing_stim_rows = (
            supabase.table("pyq_stimuli")
            .select("id, metadata, content_text, stimulus_type, language, section_id")
            .eq("pyq_paper_id", paper_id)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"commit: could not fetch existing pyq_stimuli for paper {paper_id!r}; "
            f"refusing to commit with an incomplete stimulus-identity set: {exc}"
        ) from exc

    # ref -> the full existing pyq_stimuli row (id + content fields), so both
    # id-reuse (below) and the content-mismatch check (fix #3b, post-claim)
    # can use it.
    existing_stimuli_by_ref: dict[str, dict] = {}
    for sr in existing_stim_rows:
        meta = sr.get("metadata")
        if isinstance(meta, dict):
            ref = meta.get("import_ref")
            if ref and ref not in existing_stimuli_by_ref:
                existing_stimuli_by_ref[ref] = sr

    store = _claim_token(supabase, token=import_token, paper_id=paper_id)
    if store is None:
        raise LookupError(
            f"import_token {import_token!r} not found for paper_id {paper_id!r} "
            "(wrong paper, unknown token, or already consumed)"
        )

    # Expiry is checked AFTER the atomic claim above. The token is already
    # consumed either way by this point — an expired token was one-shot
    # regardless, so there is nothing unsafe about claiming-then-rejecting it.
    expires_at_raw = store.get("expires_at")
    if expires_at_raw:
        try:
            expires_dt = datetime.fromisoformat(str(expires_at_raw))
        except ValueError:
            expires_dt = None
        if expires_dt is not None:
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if expires_dt <= datetime.now(timezone.utc):
                raise LookupError(
                    f"import_token {import_token!r} for paper_id {paper_id!r} has expired"
                )

    row_payload: dict = store.get("preflight_rows") or {}
    parsed_rows: list[dict | None] = row_payload.get("parsed", [])
    preview_rows: list[dict] = row_payload.get("preview", [])
    batch_format_version: int = row_payload.get("format_version", 1)
    stimuli_meta: dict[str, dict] = row_payload.get("stimuli_meta") or {}

    # Checkpost round 3, fix #3b: content-mismatch detection. A corrected
    # retry that fixes a typo in a stimulus's content_text (same ref,
    # different content) must not silently link new questions to the STALE,
    # uncorrected stimulus — that would hide the conflict. This must run
    # BEFORE any writes below, so a mismatch aborts the whole commit() call
    # rather than becoming a per-row failure (mirrors _validate_stimuli_batch's
    # existing pattern of raising for shared-infrastructure problems).
    for ref, meta in stimuli_meta.items():
        existing = existing_stimuli_by_ref.get(ref)
        if existing is None:
            continue
        mismatched = any(
            meta.get(field) != existing.get(field)
            for field in ("stimulus_type", "content_text", "language", "section_id")
        )
        if mismatched:
            raise ValueError(
                f"stimulus ref {ref!r} already exists in this paper with different content "
                "(stimulus_type/content_text/language/section_id); a corrected retry must not "
                "silently diverge from the canonical stimulus — resolve the conflict (e.g. "
                "review and update the existing pyq_stimuli row directly, or use a new ref) "
                "before re-importing"
            )

    from app.exam_intelligence.option_normalize import option_hash

    committed: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    per_row: list[dict] = []

    # Shared within this commit call only: a stimulus ref is created once and
    # reused by every subsequent question in the same call that references it.
    # (existing_stimuli_by_ref, above, extends this reuse across calls too.)
    stimulus_cache: dict[str, str] = {}

    for idx, (parsed, preview) in enumerate(zip(parsed_rows, preview_rows)):
        row_num = preview.get("row", idx + 1)
        pre_status = preview.get("status", "ok")

        if parsed is None:
            # Validation error row
            if not override_errors:
                skipped.append({"row": row_num, "reason": "validation_error"})
                per_row.append({"row": row_num, "result": "skipped", "reason": "validation_error"})
                continue
            # override_errors but no parsed data → cannot proceed
            failed.append({"row": row_num, "reason": "no_parsed_data"})
            per_row.append({"row": row_num, "result": "failed", "reason": "no_parsed_data"})
            continue

        row_format = parsed.get("_format_version", batch_format_version)

        if row_format == 2:
            qn = parsed.get("question_number")
            ident_ref = parsed.get("source_question_ref")
        else:
            qn = parsed["question_number"]
            ident_ref = None

        if pre_status in ("duplicate", "error") and not override_errors:
            skipped.append({"row": row_num, "question_number": qn, "reason": pre_status})
            per_row.append({"row": row_num, "result": "skipped", "reason": pre_status, "question_number": qn})
            continue

        # Idempotency: skip if already inserted. The normalized_question_hash
        # check runs uniformly for both formats (checkpost round 3, fix #1) —
        # it's the only guard left standing for a v2 row with neither
        # source_question_ref nor question_number set, and is free extra
        # safety for v1/other v2 rows that do have an identity field.
        q_hash = parsed.get("_normalized_question_hash")
        if row_format == 2:
            already_exists = (
                (ident_ref is not None and ident_ref in already_inserted_refs)
                or (qn is not None and qn in already_inserted)
                or (q_hash is not None and q_hash in already_inserted_hashes)
            )
        else:
            already_exists = (
                qn in already_inserted
                or (q_hash is not None and q_hash in already_inserted_hashes)
            )

        if already_exists:
            skipped.append({"row": row_num, "question_number": qn, "reason": "already_exists"})
            per_row.append({"row": row_num, "result": "skipped", "reason": "already_exists", "question_number": qn})
            continue

        try:
            if row_format == 2:
                q_row: dict[str, Any] = {
                    "pyq_paper_id": paper_id,
                    "question_text": parsed["question_text"],
                    "question_type": parsed["question_type"],
                    "reviewer_status": "pending",
                    "normalized_question_hash": parsed["_normalized_question_hash"],
                }
                if qn is not None:
                    q_row["question_number"] = qn
                if ident_ref:
                    q_row["source_question_ref"] = ident_ref
                if parsed.get("display_order") is not None:
                    q_row["display_order"] = parsed["display_order"]
                if parsed.get("section_id"):
                    q_row["section_id"] = parsed["section_id"]
                if parsed.get("observed_difficulty") is not None:
                    q_row["observed_difficulty"] = parsed["observed_difficulty"]

                inserted_q = supabase.table("pyq_questions").insert(q_row).execute().data or []
                if not inserted_q:
                    raise RuntimeError("question insert returned no row")
                question_id = inserted_q[0]["id"]

                # Insert stimuli links + variable-count options; roll back the
                # question row (and anything already inserted under it) on any
                # failure (PR7 atomicity, extended for v2's extra child tables).
                # Shared pyq_stimuli rows created earlier in this same commit
                # call for a different question are never rolled back — they
                # are reusable, idempotent-within-call infrastructure.
                try:
                    stim_ids: list[str] = []
                    for ref in parsed.get("stimulus_refs") or []:
                        if ref not in stimulus_cache:
                            # Reuse across separate commit()/retry calls first
                            # (fix for durable shared-stimulus identity), then
                            # fall back to creating a new row.
                            if ref in existing_stimuli_by_ref:
                                stimulus_cache[ref] = existing_stimuli_by_ref[ref]["id"]
                            else:
                                meta = stimuli_meta.get(ref) or {}
                                stim_row: dict[str, Any] = {
                                    "pyq_paper_id": paper_id,
                                    "stimulus_type": meta.get("stimulus_type", "other"),
                                    "content_text": meta.get("content_text"),
                                    "language": meta.get("language"),
                                    "reviewer_status": "pending",
                                    "metadata": {"import_ref": ref},
                                }
                                if meta.get("display_order") is not None:
                                    stim_row["display_order"] = meta["display_order"]
                                if meta.get("section_id"):
                                    stim_row["section_id"] = meta["section_id"]
                                inserted_stim = (
                                    supabase.table("pyq_stimuli").insert(stim_row).execute().data or []
                                )
                                if not inserted_stim:
                                    raise RuntimeError(f"stimulus insert for ref {ref!r} returned no row")
                                stimulus_cache[ref] = inserted_stim[0]["id"]
                        stim_ids.append(stimulus_cache[ref])

                    correct_label = parsed.get("correct_option_label")
                    resolved_correct = (
                        correct_label
                        if correct_label and any(o["label"] == correct_label for o in parsed["options"])
                        else None
                    )
                    opt_rows = []
                    for o in parsed["options"]:
                        opt_row: dict[str, Any] = {
                            "question_id": question_id,
                            "option_label": o["label"],
                            "option_text": o["text"],
                            "is_correct": o["label"] == resolved_correct,
                            "normalized_option_hash": option_hash(o["text"]),
                        }
                        if o.get("display_order") is not None:
                            opt_row["display_order"] = o["display_order"]
                        if o.get("source_label"):
                            opt_row["source_label"] = o["source_label"]
                        opt_rows.append(opt_row)

                    supabase.table("pyq_options").insert(opt_rows).execute()

                    # display_order = 1-based position in stimulus_refs (the
                    # order-preserving JSON array / CSV parse) — preserves
                    # e.g. "passage then chart" ordering for a question.
                    for link_order, stim_id in enumerate(stim_ids, start=1):
                        supabase.table("pyq_question_stimuli").insert({
                            "question_id": question_id,
                            "stimulus_id": stim_id,
                            "reviewer_status": "pending",
                            "display_order": link_order,
                        }).execute()
                except Exception as child_exc:  # noqa: BLE001
                    try:
                        supabase.table("pyq_question_stimuli").delete().eq("question_id", question_id).execute()
                    except Exception:  # noqa: BLE001
                        logger.exception("rollback link delete failed for question %s (row %s)", question_id, row_num)
                    try:
                        supabase.table("pyq_options").delete().eq("question_id", question_id).execute()
                    except Exception:  # noqa: BLE001
                        logger.exception("rollback options delete failed for question %s (row %s)", question_id, row_num)
                    try:
                        supabase.table("pyq_questions").delete().eq("id", question_id).execute()
                    except Exception:  # noqa: BLE001
                        logger.exception("rollback delete failed for question %s (row %s)", question_id, row_num)
                    raise RuntimeError(f"options/stimulus-link insert failed: {child_exc}") from child_exc

                if ident_ref:
                    already_inserted_refs.add(ident_ref)
                if qn is not None:
                    already_inserted.add(qn)
                if q_hash is not None:
                    already_inserted_hashes.add(q_hash)

            else:
                q_row = {
                    "pyq_paper_id": paper_id,
                    "question_number": qn,
                    "question_text": parsed["question_text"],
                    "question_type": parsed["question_type"],
                    "reviewer_status": "pending",
                    "normalized_question_hash": parsed["_normalized_question_hash"],
                }
                if parsed.get("observed_difficulty") is not None:
                    q_row["observed_difficulty"] = parsed["observed_difficulty"]

                inserted_q = supabase.table("pyq_questions").insert(q_row).execute().data or []
                if not inserted_q:
                    raise RuntimeError("question insert returned no row")
                question_id = inserted_q[0]["id"]

                # Insert 4 options; roll back the question row on any failure (PR7 atomicity).
                correct = parsed["correct_option"]  # "A"|"B"|"C"|"D"
                opt_rows = [
                    {
                        "question_id": question_id,
                        "option_label": lbl,
                        "option_text": parsed["options"][lbl],
                        "is_correct": lbl == correct,
                        "normalized_option_hash": option_hash(parsed["options"][lbl]),
                    }
                    for lbl in ("A", "B", "C", "D")
                ]
                try:
                    supabase.table("pyq_options").insert(opt_rows).execute()
                except Exception as opt_exc:  # noqa: BLE001
                    # Delete the orphaned question row before surfacing the error.
                    try:
                        supabase.table("pyq_questions").delete().eq("id", question_id).execute()
                    except Exception:  # noqa: BLE001
                        logger.exception("rollback delete failed for question %s (row %s)", question_id, row_num)
                    raise RuntimeError(f"options insert failed: {opt_exc}") from opt_exc

                already_inserted.add(qn)
                if q_hash is not None:
                    already_inserted_hashes.add(q_hash)

            committed.append({"row": row_num, "question_number": qn, "question_id": question_id})
            per_row.append({"row": row_num, "result": "committed", "question_number": qn, "question_id": question_id})

        except Exception as exc:  # noqa: BLE001
            logger.error("commit: row %s (qn=%s) failed: %s", row_num, qn, exc)
            failed.append({"row": row_num, "question_number": qn, "reason": str(exc)[:200]})
            per_row.append({"row": row_num, "question_number": qn, "result": "failed", "reason": str(exc)[:200]})

    # Token is already consumed — the atomic claim at the top of this
    # function (_claim_token) IS the consume step; no separate call needed.

    return {
        "paper_id": paper_id,
        "committed": len(committed),
        "skipped": len(skipped),
        "failed": len(failed),
        "per_row": per_row,
    }
