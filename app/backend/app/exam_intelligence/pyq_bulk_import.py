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


# ── Constants ─────────────────────────────────────────────────────────────────

_CORRECT_OPTIONS = {"A", "B", "C", "D"}
_QUESTION_TYPES = frozenset(("mcq", "numerical", "descriptive", "caselet", "matching", "other"))
_CSV_REQUIRED = {
    "question_number", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct_option", "question_type",
}

# v2: mirrors the pyq_stimuli.stimulus_type check constraint (migration 223).
_STIMULUS_TYPES = frozenset(("passage", "caselet", "table", "chart", "image", "diagram", "other"))

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
    seen_numbers: set[int],
    seen_source_refs: set[str],
    stimulus_refs_available: set[str],
    section_lookup: dict[str, str],
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

    # display_order — optional positive int.
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

    # question_text
    question_text = str(raw.get("question_text") or "").strip()
    if not question_text:
        errors.append("question_text is required")

    # question_type
    qtype = str(raw.get("question_type") or "").strip().lower()
    if qtype not in _QUESTION_TYPES:
        errors.append(f"question_type must be one of {sorted(_QUESTION_TYPES)}; got {qtype!r}")

    # observed_difficulty — nullable
    diff_raw = raw.get("observed_difficulty")
    observed_difficulty: str | None = None
    if diff_raw is not None and str(diff_raw).strip():
        observed_difficulty = str(diff_raw).strip()

    # section_ref — optional, resolved against exam_phase_sections scoped to
    # the paper's exam_phase_id (section_lookup keys are lower-cased labels).
    section_ref_raw = raw.get("section_ref")
    section_ref = str(section_ref_raw).strip() if section_ref_raw not in (None, "") else None
    section_id: str | None = None
    if section_ref:
        section_id = section_lookup.get(section_ref.lower())
        if section_id is None:
            errors.append(
                f"section_ref '{section_ref}' does not resolve to a section in this paper's exam phase"
            )

    # stimulus_refs — each must match a ref declared in the batch's top-level
    # 'stimuli' array.
    stimulus_refs, ref_errors = _parse_v2_stimulus_refs(raw, is_csv)
    errors.extend(ref_errors)
    for ref in stimulus_refs:
        if ref not in stimulus_refs_available:
            errors.append(f"stimulus_refs entry '{ref}' does not match any declared stimulus")

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


def _validate_stimuli_batch(stimuli: list[Any], section_lookup: dict[str, str]) -> dict[str, dict]:
    """Validate the top-level v2 'stimuli' array and resolve each entry's
    section_ref. Raises ValueError on any structural problem: a stimulus is
    shared infrastructure referenced by many questions, so a broken entry
    invalidates the whole batch rather than becoming one row-level error.
    """
    by_ref: dict[str, dict] = {}
    for i, s in enumerate(stimuli):
        if not isinstance(s, dict):
            raise ValueError(f"stimuli[{i}] must be an object")

        ref = str(s.get("ref") or "").strip()
        if not ref:
            raise ValueError(f"stimuli[{i}].ref is required and must not be empty")
        if ref in by_ref:
            raise ValueError(f"stimuli ref {ref!r} is duplicated")

        stype = str(s.get("stimulus_type") or "").strip().lower()
        if stype not in _STIMULUS_TYPES:
            raise ValueError(
                f"stimuli[{i}].stimulus_type must be one of {sorted(_STIMULUS_TYPES)}; got {stype!r}"
            )

        section_ref_raw = s.get("section_ref")
        section_ref = str(section_ref_raw).strip() if section_ref_raw not in (None, "") else None
        section_id: str | None = None
        if section_ref:
            section_id = section_lookup.get(section_ref.lower())
            if section_id is None:
                raise ValueError(
                    f"stimuli[{i}] section_ref '{section_ref}' does not resolve to a section "
                    "in this paper's exam phase"
                )

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

    section_lookup: dict[str, str] = {}
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
                    section_lookup[str(lbl).strip().lower()] = sr["id"]

        try:
            stimuli_meta = _validate_stimuli_batch(batch["stimuli"], section_lookup)
        except Exception as exc:
            raise ValueError(f"parse failed: {exc}") from exc

    # Fetch existing question_numbers/source_question_refs and hashes for this paper
    existing_rows: list[dict] = []
    try:
        existing_rows = (
            supabase.table("pyq_questions")
            .select("id, question_number, question_text, normalized_question_hash, source_question_ref")
            .eq("pyq_paper_id", paper_id)
            .limit(5000)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("preflight: could not fetch existing rows for paper %s: %s", paper_id, exc)

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
    stimulus_refs_available = set(stimuli_meta.keys())
    preview_rows: list[dict] = []
    valid_parsed: list[dict] = []  # only rows that passed validation

    for row_idx, raw in enumerate(raw_rows):
        if format_version == 2:
            parsed, errs = _validate_row_v2(
                raw,
                is_csv=is_csv,
                seen_numbers=seen_numbers,
                seen_source_refs=seen_source_refs,
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
            # Exact hash match
            if h in existing_hash_map:
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
    override_errors: bool = False,
) -> dict:
    """Commit previously preflighted rows.

    Idempotent on question_number (v1), or on source_question_ref falling
    back to question_number when present (v2).
    """
    # Derive paper_id from token lookup — we need it to scope the query.
    # The caller (router) passes paper_id implicitly via the URL; commit()
    # receives it indirectly by loading the token which carries paper_id.
    # We do a two-phase lookup: first find the token without paper_id
    # constraint to get paper_id, then validate it matches.
    token_rows = (
        supabase.table("pyq_import_tokens")
        .select("*")
        .eq("token", import_token)
        .is_("consumed_at", None)
        .gt("expires_at", _now_iso())
        .execute()
        .data
    ) or []
    if not token_rows:
        raise LookupError(f"import_token {import_token!r} not found or expired")
    store = token_rows[0]

    paper_id: str = store["paper_id"]
    row_payload: dict = store.get("preflight_rows") or {}
    parsed_rows: list[dict | None] = row_payload.get("parsed", [])
    preview_rows: list[dict] = row_payload.get("preview", [])
    batch_format_version: int = row_payload.get("format_version", 1)
    stimuli_meta: dict[str, dict] = row_payload.get("stimuli_meta") or {}

    # Re-fetch existing question_numbers/source_question_refs for idempotency check
    try:
        existing_qns_rows = (
            supabase.table("pyq_questions")
            .select("id, question_number, source_question_ref")
            .eq("pyq_paper_id", paper_id)
            .limit(5000)
            .execute()
            .data
        ) or []
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("commit: could not fetch existing qns for paper %s: %s", paper_id, exc)
        already_inserted = set()
        already_inserted_refs = set()

    from app.exam_intelligence.option_normalize import option_hash

    committed: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    per_row: list[dict] = []

    # Shared within this commit call only: a stimulus ref is created once and
    # reused by every subsequent question in the same call that references it.
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

        # Idempotency: skip if already inserted
        if row_format == 2:
            already_exists = (
                (ident_ref is not None and ident_ref in already_inserted_refs)
                or (qn is not None and qn in already_inserted)
            )
        else:
            already_exists = qn in already_inserted

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
                            meta = stimuli_meta.get(ref) or {}
                            stim_row: dict[str, Any] = {
                                "pyq_paper_id": paper_id,
                                "stimulus_type": meta.get("stimulus_type", "other"),
                                "content_text": meta.get("content_text"),
                                "language": meta.get("language"),
                                "reviewer_status": "pending",
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

                    for stim_id in stim_ids:
                        supabase.table("pyq_question_stimuli").insert({
                            "question_id": question_id,
                            "stimulus_id": stim_id,
                            "reviewer_status": "pending",
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

            committed.append({"row": row_num, "question_number": qn, "question_id": question_id})
            per_row.append({"row": row_num, "result": "committed", "question_number": qn, "question_id": question_id})

        except Exception as exc:  # noqa: BLE001
            logger.error("commit: row %s (qn=%s) failed: %s", row_num, qn, exc)
            failed.append({"row": row_num, "question_number": qn, "reason": str(exc)[:200]})
            per_row.append({"row": row_num, "question_number": qn, "result": "failed", "reason": str(exc)[:200]})

    _consume_token(supabase, token=import_token)

    return {
        "paper_id": paper_id,
        "committed": len(committed),
        "skipped": len(skipped),
        "failed": len(failed),
        "per_row": per_row,
    }
