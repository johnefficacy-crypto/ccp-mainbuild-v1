"""PYQ-specialised bulk import: preflight + idempotent commit.

Flow
----
1. POST /pyq-papers/{paper_id}/bulk-import/preflight
   Parse CSV or JSON bytes, validate every row, run dedup ladder,
   return per-row preview + import_token.  NO writes.

2. POST /pyq-papers/{paper_id}/bulk-import/commit
   Consume import_token, write question+4 options per clean row via
   the same question→options cascade the CMS single-row endpoint uses.
   Idempotent: rows whose question_number already exists in the paper
   are skipped rather than duplicated.

CSV contract columns
--------------------
question_number, question_text, option_a, option_b, option_c, option_d,
correct_option, question_type, observed_difficulty

Dedup ladder
------------
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
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.pyq_bulk_import")

# ── Token store ───────────────────────────────────────────────────────────────

_STORE: dict[str, dict] = {}
_TTL_SEC = 3600


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Constants ─────────────────────────────────────────────────────────────────

_CORRECT_OPTIONS = {"A", "B", "C", "D"}
_QUESTION_TYPES = frozenset(("mcq", "numerical", "descriptive", "caselet", "matching", "other"))
_CSV_REQUIRED = {
    "question_number", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct_option", "question_type",
}

# ── Parse helpers ─────────────────────────────────────────────────────────────


def parse_bytes(content: bytes, content_type: str) -> list[dict]:
    """Return raw row dicts from CSV or JSON bytes."""
    ct = (content_type or "").lower()
    if "json" in ct:
        raw = json.loads(content.decode("utf-8"))
        if not isinstance(raw, list):
            raise ValueError("JSON must be a list of objects")
        return raw

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty")
    missing = _CSV_REQUIRED - {k.strip().lower() for k in (rows[0].keys())}
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    return [{k.strip().lower(): v for k, v in r.items()} for r in rows]


def _validate_row(raw: dict, seen_numbers: set[int]) -> tuple[dict | None, list[str]]:
    """Validate one raw row. Returns (parsed, errors). observed_difficulty may be None."""
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


# ── Dedup helpers ─────────────────────────────────────────────────────────────


def _q_hash(text: str) -> str:
    """Stable SHA-256 of the canonical question text (mirrors question_hash)."""
    from app.exam_intelligence.option_normalize import question_hash
    return question_hash(text) or hashlib.sha256(text.lower().encode()).hexdigest()


def _levenshtein_ratio(a: str, b: str) -> float:
    try:
        from Levenshtein import ratio
        return ratio(a, b)
    except ImportError:
        pass
    # Pure-Python fallback (DP edit distance)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    dist = prev[lb]
    return 1 - dist / max(la, lb)


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
        raw_rows = parse_bytes(content, content_type)
    except Exception as exc:
        raise ValueError(f"parse failed: {exc}") from exc

    # Fetch existing question_numbers and hashes for this paper
    existing_rows: list[dict] = []
    try:
        existing_rows = (
            supabase.table("pyq_questions")
            .select("id, question_number, question_text, normalized_question_hash")
            .eq("pyq_paper_id", paper_id)
            .limit(5000)
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("preflight: could not fetch existing rows for paper %s: %s", paper_id, exc)

    existing_numbers: set[int] = set()
    existing_hash_map: dict[str, dict] = {}   # hash → row
    existing_text_norms: list[tuple[str, dict]] = []  # (norm_text, row)

    for er in existing_rows:
        if er.get("question_number") is not None:
            try:
                existing_numbers.add(int(er["question_number"]))
            except (TypeError, ValueError):
                pass
        h = er.get("normalized_question_hash")
        if h:
            existing_hash_map[h] = er
        qt = er.get("question_text")
        if qt:
            from app.exam_intelligence.option_normalize import normalize_question_text
            existing_text_norms.append((normalize_question_text(qt), er))

    seen_numbers: set[int] = set()
    preview_rows: list[dict] = []
    valid_parsed: list[dict] = []  # only rows that passed validation

    for row_idx, raw in enumerate(raw_rows):
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

        qn = parsed["question_number"]
        qt = parsed["question_text"]
        h = _q_hash(qt)
        parsed["_normalized_question_hash"] = h

        messages: list[str] = []
        status = "ok"

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
    _STORE[import_token] = {
        "paper_id": paper_id,
        "actor_id": actor.get("id"),
        "created_at": _now_ts(),
        "rows": valid_parsed,       # None entries = validation error rows
        "preview": preview_rows,
    }

    ok = sum(1 for p in preview_rows if p["status"] == "ok")
    errors = sum(1 for p in preview_rows if p["status"] == "error")
    duplicates = sum(1 for p in preview_rows if p["status"] == "duplicate")
    fuzzy = sum(1 for p in preview_rows if p["status"] == "fuzzy")

    return {
        "import_token": import_token,
        "paper_id": paper_id,
        "total": len(raw_rows),
        "summary": {"ok": ok, "error": errors, "duplicate": duplicates, "fuzzy": fuzzy},
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
    """Commit previously preflighted rows. Idempotent on question_number."""
    store = _STORE.get(import_token)
    if not store:
        raise LookupError(f"import_token {import_token!r} not found or expired")
    if _now_ts() - store["created_at"] > _TTL_SEC:
        _STORE.pop(import_token, None)
        raise LookupError("import_token expired")

    paper_id: str = store["paper_id"]
    parsed_rows: list[dict | None] = store["rows"]
    preview_rows: list[dict] = store["preview"]

    # Re-fetch existing question_numbers for idempotency check
    try:
        existing_qns_rows = (
            supabase.table("pyq_questions")
            .select("id, question_number")
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("commit: could not fetch existing qns for paper %s: %s", paper_id, exc)
        already_inserted = set()

    from app.exam_intelligence.option_normalize import option_hash

    committed: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    per_row: list[dict] = []

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

        qn = parsed["question_number"]

        if pre_status in ("duplicate", "error") and not override_errors:
            skipped.append({"row": row_num, "question_number": qn, "reason": pre_status})
            per_row.append({"row": row_num, "result": "skipped", "reason": pre_status, "question_number": qn})
            continue

        # Idempotency: skip if already inserted
        if qn in already_inserted:
            skipped.append({"row": row_num, "question_number": qn, "reason": "already_exists"})
            per_row.append({"row": row_num, "result": "skipped", "reason": "already_exists", "question_number": qn})
            continue

        try:
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

            # Insert 4 options
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
            supabase.table("pyq_options").insert(opt_rows).execute()

            already_inserted.add(qn)
            committed.append({"row": row_num, "question_number": qn, "question_id": question_id})
            per_row.append({"row": row_num, "result": "committed", "question_number": qn, "question_id": question_id})

        except Exception as exc:  # noqa: BLE001
            logger.error("commit: row %s (qn=%s) failed: %s", row_num, qn, exc)
            failed.append({"row": row_num, "question_number": qn, "reason": str(exc)[:200]})
            per_row.append({"row": row_num, "result": "failed", "question_number": qn, "reason": str(exc)[:200]})

    return {
        "paper_id": paper_id,
        "committed": len(committed),
        "skipped": len(skipped),
        "failed": len(failed),
        "per_row": per_row,
    }
