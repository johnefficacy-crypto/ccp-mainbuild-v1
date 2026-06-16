"""Admin mock question bulk import — CSV/JSON parse, fingerprint dedup, idempotent commit.

Flow:
    1. POST /questions/import/dry-run   — multipart upload → returns import_token + per-row preview
    2. POST /questions/import/commit    — body: {import_token} → idempotent, 0 new rows on re-commit

Import token is a short-lived in-memory store keyed by sha256 of the uploaded file.
Production deployments with multiple workers should replace this with a Supabase table;
the interface is the same.

CSV schema (header row required):
    question_text, option_1, option_2, option_3, option_4,
    correct_option (1-based index),
    difficulty (easy|medium|hard),
    is_conceptual (true/false),
    is_factual (true/false),
    is_current (true/false),
    is_current_based (true/false),
    valid_until (ISO-8601 datetime, optional),
    explanation,
    language,
    exam_id,
    subject_id,
    topic_id,
    source_kind (pyq|official_syllabus|standard_source|current_event|authored),
    source_trust (verified|provisional|unverified),
    source_url,
    external_id   <- used for idempotency key; dedup on (exam_id, source_kind, external_id)

JSON schema: list of objects with same field names.

Mapping validation:
    If the uploaded file contains subject_id or topic_id columns/keys, dry-run treats
    it as a mapped import. Every parsed row must then carry both ids, both ids must
    resolve, and topic_id must belong to subject_id. Invalid rows are reported as
    missing_mapping and are not committed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.admin.mock_questions import _write_log

logger = logging.getLogger("career_copilot.admin.mock_import")

# In-process token store (keyed by content hash → parsed rows).
# Replace with Supabase row for multi-worker deployments.
_IMPORT_STORE: dict[str, dict] = {}
_IMPORT_TTL_SEC = 3600  # 1 hour


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


# ── Parse ──────────────────────────────────────────────────────────────────────

_REQUIRED_COLS = {"question_text", "correct_option"}
_OPTION_COLS = ["option_1", "option_2", "option_3", "option_4", "option_5", "option_6"]


def _row_has_mapping_keys(row: dict) -> bool:
    """Whether a raw CSV/JSON row opts into canary-safe mapped import mode."""
    return "subject_id" in row or "topic_id" in row


def _parse_bool(row: dict, key: str) -> bool:
    v = str(row.get(key) or "false").strip().lower()
    return v in ("true", "1", "yes")


def _parse_valid_until(row: dict, errors: list[str]) -> str | None:
    valid_until = _clean(row.get("valid_until"))
    if not valid_until:
        return None
    try:
        datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
    except ValueError:
        errors.append("valid_until must be ISO-8601 datetime")
    return valid_until


def _parse_row(row: dict, row_num: int) -> tuple[dict | None, list[str]]:
    """Parse one CSV/JSON row into a canonical question dict. Returns (parsed, errors)."""
    errors: list[str] = []

    q_text = (row.get("question_text") or "").strip()
    if not q_text:
        errors.append("question_text is required")

    options_raw: list[str] = []
    for col in _OPTION_COLS:
        val = (row.get(col) or "").strip()
        if val:
            options_raw.append(val)

    if len(options_raw) < 2:
        errors.append(f"at least 2 options required; found {len(options_raw)}")

    correct_raw = str(row.get("correct_option") or "").strip()
    try:
        correct_idx = int(correct_raw) - 1  # 1-based → 0-based
        if not (0 <= correct_idx < len(options_raw)):
            errors.append(f"correct_option {correct_raw!r} out of range")
            correct_idx = 0
    except ValueError:
        errors.append(f"correct_option must be a number; got {correct_raw!r}")
        correct_idx = 0

    difficulty = (row.get("difficulty") or "medium").lower().strip()
    if difficulty not in ("easy", "medium", "hard"):
        errors.append(f"difficulty must be easy|medium|hard; got {difficulty!r}")
        difficulty = "medium"

    source_kind = (row.get("source_kind") or "authored").strip()
    valid_kinds = {"pyq", "official_syllabus", "standard_source", "current_event", "authored"}
    if source_kind not in valid_kinds:
        source_kind = "authored"

    source_trust = (row.get("source_trust") or "unverified").strip()
    if source_trust not in ("verified", "provisional", "unverified"):
        source_trust = "unverified"

    valid_until = _parse_valid_until(row, errors)

    if errors:
        return None, errors

    options = [
        {"option_text": text, "is_correct": (i == correct_idx), "option_index": i}
        for i, text in enumerate(options_raw)
    ]
    correct_opt_text = options_raw[correct_idx] if options_raw else ""

    # Pre-compute fingerprint (without DB ids, so use text representation)
    sorted_opts = sorted(options_raw)
    sorted_correct_idx = sorted_opts.index(options_raw[correct_idx]) if options_raw else 0
    fp_raw = (
        " ".join(q_text.lower().split())
        + "|" + "|".join(sorted_opts)
        + "|" + str(sorted_correct_idx)
    )
    fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

    return {
        "question_text": q_text,
        "difficulty": difficulty,
        "question_type": "mcq",
        "is_conceptual": _parse_bool(row, "is_conceptual"),
        "is_factual": _parse_bool(row, "is_factual"),
        "is_current": _parse_bool(row, "is_current"),
        "is_current_based": _parse_bool(row, "is_current_based"),
        "valid_until": valid_until,
        "explanation": (row.get("explanation") or "").strip() or None,
        "language": (row.get("language") or "en").strip(),
        "exam_id": _clean(row.get("exam_id")),
        "subject_id": _clean(row.get("subject_id")),
        "topic_id": _clean(row.get("topic_id")),
        "source_kind": source_kind,
        "source_trust": source_trust,
        "source_url": _clean(row.get("source_url")),
        "external_id": _clean(row.get("external_id")),
        "options": options,
        "correct_option_text": correct_opt_text,
        "fingerprint": fingerprint,
        "_row_num": row_num,
    }, []


def parse_file(content: bytes, content_type: str) -> list[dict]:
    """Parse CSV or JSON file bytes into raw row dicts."""
    if content_type and "json" in content_type:
        raw = json.loads(content.decode("utf-8"))
        if isinstance(raw, list):
            return raw
        raise ValueError("JSON import must be a list of objects")

    # CSV
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file is empty")
    missing = _REQUIRED_COLS - set(rows[0].keys())
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    return rows


def _fetch_id_map(supabase: Any, table: str, ids: set[str], select_cols: str) -> dict[str, dict]:
    if not ids:
        return {}
    try:
        rows = (
            supabase.table(table)
            .select(select_cols)
            .in_("id", sorted(ids))
            .execute()
            .data
        ) or []
        return {r["id"]: r for r in rows if r.get("id")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s mapping validation query failed: %s", table, exc)
        return {}


# ── Dry-run ────────────────────────────────────────────────────────────────────

def dry_run(
    supabase: Any,
    actor: dict,
    content: bytes,
    content_type: str,
    exam_id_override: str | None = None,
) -> dict:
    """Parse file and return per-row preview without writing anything.

    Returns:
        {import_token, total, ok_count, error_count, duplicate_count,
         missing_mapping_count, rows: [...]}
    Each row: {row_num, status: ok|duplicate|parse_error|missing_mapping, preview, issues}
    """
    try:
        raw_rows = parse_file(content, content_type)
    except Exception as exc:
        raise ValueError(f"file parse failed: {exc}") from exc

    mapping_mode = any(_row_has_mapping_keys(r) for r in raw_rows)

    # Collect all fingerprints in one query for dedup check
    parsed_rows: list[dict] = []
    all_fps: list[str] = []

    preview_results: list[dict] = []
    for row_num, raw in enumerate(raw_rows, start=2):  # 1-indexed, row 1 = header
        parsed, errors = _parse_row(raw, row_num)
        if errors:
            preview_results.append({
                "row_num": row_num,
                "status": "parse_error",
                "preview": None,
                "issues": errors,
            })
        else:
            if exam_id_override:
                parsed["exam_id"] = exam_id_override
            parsed_rows.append(parsed)
            all_fps.append(parsed["fingerprint"])
            preview_results.append({
                "row_num": row_num,
                "status": "ok",  # tentative; updated below
                "preview": {
                    "question_text": parsed["question_text"],
                    "difficulty": parsed["difficulty"],
                    "options_count": len(parsed["options"]),
                    "fingerprint": parsed["fingerprint"],
                    "external_id": parsed["external_id"],
                    "exam_id": parsed.get("exam_id"),
                    "subject_id": parsed.get("subject_id"),
                    "topic_id": parsed.get("topic_id"),
                    "is_current_based": parsed.get("is_current_based"),
                    "valid_until": parsed.get("valid_until"),
                },
                "issues": [],
            })

    # Batch fingerprint dedup check
    existing_fps: set[str] = set()
    if all_fps:
        try:
            rows = (
                supabase.table("mock_question_bank")
                .select("question_fingerprint")
                .in_("question_fingerprint", all_fps)
                .execute()
                .data
            ) or []
            existing_fps = {r["question_fingerprint"] for r in rows}
        except Exception as exc:  # noqa: BLE001
            logger.warning("fingerprint dedup query failed: %s", exc)

    # Check external_id dedup (idempotency key)
    external_ids = [p["external_id"] for p in parsed_rows if p.get("external_id")]
    existing_ext_ids: set[str] = set()
    if external_ids:
        try:
            # We store external_id in sources table; check there
            rows = (
                supabase.table("mock_question_sources")
                .select("evidence_text")
                .eq("source_kind", "authored")
                .in_("evidence_text", [f"ext_id:{eid}" for eid in external_ids])
                .execute()
                .data
            ) or []
            existing_ext_ids = {
                r["evidence_text"].replace("ext_id:", "")
                for r in rows
                if r.get("evidence_text", "").startswith("ext_id:")
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("external_id dedup query failed: %s", exc)

    subject_rows: dict[str, dict] = {}
    topic_rows: dict[str, dict] = {}
    if mapping_mode:
        subject_ids = {p["subject_id"] for p in parsed_rows if p.get("subject_id")}
        topic_ids = {p["topic_id"] for p in parsed_rows if p.get("topic_id")}
        subject_rows = _fetch_id_map(supabase, "subjects", subject_ids, "id")
        topic_rows = _fetch_id_map(supabase, "topics", topic_ids, "id, subject_id")

    # Update statuses
    ok_count = dup_count = err_count = missing_mapping_count = 0
    parsed_idx = 0
    for result in preview_results:
        if result["status"] == "parse_error":
            err_count += 1
            continue
        p = parsed_rows[parsed_idx]
        parsed_idx += 1

        mapping_issues: list[str] = []
        if mapping_mode:
            subject_id = p.get("subject_id")
            topic_id = p.get("topic_id")
            if not subject_id:
                mapping_issues.append("subject_id is required for mapped import")
            elif subject_id not in subject_rows:
                mapping_issues.append(f"subject_id {subject_id!r} does not resolve")
            if not topic_id:
                mapping_issues.append("topic_id is required for mapped import")
            elif topic_id not in topic_rows:
                mapping_issues.append(f"topic_id {topic_id!r} does not resolve")
            elif subject_id and topic_rows[topic_id].get("subject_id") != subject_id:
                mapping_issues.append("topic_id belongs to a different subject_id")

        if mapping_issues:
            result["status"] = "missing_mapping"
            result["issues"] = mapping_issues
            p["_import_status"] = "missing_mapping"
            p["_import_issues"] = mapping_issues
            missing_mapping_count += 1
            continue

        is_dup_fp = p["fingerprint"] in existing_fps
        is_dup_ext = p.get("external_id") and p["external_id"] in existing_ext_ids
        if is_dup_fp or is_dup_ext:
            result["status"] = "duplicate"
            result["issues"] = [
                "fingerprint already exists" if is_dup_fp else "external_id already imported"
            ]
            p["_import_status"] = "duplicate"
            p["_import_issues"] = result["issues"]
            dup_count += 1
        else:
            p["_import_status"] = "ok"
            p["_import_issues"] = []
            ok_count += 1

    # Generate import token
    content_hash = hashlib.sha256(content).hexdigest()
    import_token = content_hash[:32]
    _IMPORT_STORE[import_token] = {
        "parsed_rows": parsed_rows,
        "actor_id": actor.get("id"),
        "created_at": datetime.now(timezone.utc).timestamp(),
        "exam_id_override": exam_id_override,
        "mapping_mode": mapping_mode,
    }

    return {
        "import_token": import_token,
        "total": len(raw_rows),
        "ok_count": ok_count,
        "duplicate_count": dup_count,
        "missing_mapping_count": missing_mapping_count,
        "error_count": err_count,
        "rows": preview_results,
    }


# ── Commit ─────────────────────────────────────────────────────────────────────

def commit_import(supabase: Any, actor: dict, import_token: str) -> dict:
    """Commit a previously dry-run import. Idempotent: duplicate/invalid rows are skipped.

    Returns {created, skipped, failed, question_ids}
    """
    store = _IMPORT_STORE.get(import_token)
    if not store:
        raise LookupError(f"import_token {import_token!r} not found or expired")

    # Basic TTL check
    age = datetime.now(timezone.utc).timestamp() - store["created_at"]
    if age > _IMPORT_TTL_SEC:
        del _IMPORT_STORE[import_token]
        raise LookupError("import_token expired")

    actor_id = actor.get("id")
    parsed_rows: list[dict] = store["parsed_rows"]
    exam_id_override: str | None = store.get("exam_id_override")

    created: list[str] = []
    skipped: list[dict | str] = []
    failed: list[dict] = []

    for p in parsed_rows:
        if p.get("_import_status", "ok") != "ok":
            skipped.append({
                "row_num": p.get("_row_num"),
                "status": p.get("_import_status"),
                "issues": p.get("_import_issues", []),
            })
            continue

        fp = p["fingerprint"]
        ext_id = p.get("external_id")
        exam_id = p.get("exam_id") or exam_id_override

        # Idempotency: check fingerprint
        try:
            existing = (
                supabase.table("mock_question_bank")
                .select("id")
                .eq("question_fingerprint", fp)
                .limit(1)
                .execute()
                .data
            ) or []
            if existing:
                skipped.append(existing[0]["id"])
                continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("fingerprint check failed for row %s: %s", p["_row_num"], exc)

        try:
            q_row = {
                "question_text": p["question_text"],
                "question_type": p["question_type"],
                "difficulty": p["difficulty"],
                "is_conceptual": p["is_conceptual"],
                "is_factual": p["is_factual"],
                "is_current": p["is_current"],
                "is_current_based": p["is_current_based"],
                "valid_until": p["valid_until"],
                "explanation": p["explanation"],
                "language": p["language"],
                "exam_id": exam_id,
                "subject_id": p.get("subject_id"),
                "topic_id": p.get("topic_id"),
                "reviewer_status": "draft",
                "created_by": actor_id,
                "question_fingerprint": fp,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
            result = supabase.table("mock_question_bank").insert(q_row).execute()
            rows = result.data or []
            if not rows:
                failed.append({"row_num": p["_row_num"], "error": "insert returned no row"})
                continue
            question_id = rows[0]["id"]

            # Insert options
            opt_rows = [
                {
                    "question_id": question_id,
                    "option_text": o["option_text"],
                    "option_index": o["option_index"],
                    "is_correct": o["is_correct"],
                }
                for o in p["options"]
            ]
            supabase.table("mock_question_options").insert(opt_rows).execute()

            # Set correct_option_id
            opts = (
                supabase.table("mock_question_options")
                .select("id, is_correct")
                .eq("question_id", question_id)
                .execute()
                .data
            ) or []
            correct_opt = next((o for o in opts if o.get("is_correct")), None)
            if correct_opt:
                supabase.table("mock_question_bank").update({
                    "correct_option_id": correct_opt["id"]
                }).eq("id", question_id).execute()

            # Source row with external_id encoded for idempotency
            source_row = {
                "question_id": question_id,
                "source_kind": p["source_kind"],
                "source_trust": p["source_trust"],
                "source_url": p["source_url"],
                "evidence_text": f"ext_id:{ext_id}" if ext_id else None,
            }
            supabase.table("mock_question_sources").insert(source_row).execute()

            _write_log(supabase, question_id=question_id, actor_id=actor_id,
                       action="import", to_status="draft",
                       diff={"external_id": {"to": ext_id}, "fingerprint": {"to": fp}})

            created.append(question_id)

        except Exception as exc:  # noqa: BLE001
            logger.error("import row %s failed: %s", p["_row_num"], exc)
            failed.append({"row_num": p["_row_num"], "error": str(exc)})

    # Invalidate token after successful commit
    if not failed:
        _IMPORT_STORE.pop(import_token, None)

    return {
        "created": len(created),
        "skipped": len(skipped),
        "failed": len(failed),
        "question_ids": created,
        "failed_rows": failed,
    }
