"""Tiny in-memory Supabase stub shared across persona_questions tests."""
from __future__ import annotations

import uuid
from typing import Any


class _Exec:
    def __init__(self, data):
        self.data = data


class _NotProxy:
    """Proxy returned by ``_Query.not_`` to negate the next chained filter."""

    def __init__(self, query: "_Query"):
        self._query = query

    def in_(self, key, vals):
        self._query.filters.append((key, "not_in", list(vals)))
        return self._query

    def is_(self, key, val):
        self._query.filters.append((key, "not_is", val))
        return self._query


class _Query:
    def __init__(self, name, db):
        self.name = name
        self.db = db
        self.filters: list[tuple[str, str, Any]] = []
        self._order_key: str | None = None
        self._desc = False
        self._limit: int | None = None
        self._pending_insert: Any = None
        self._pending_update: dict[str, Any] | None = None
        self._pending_upsert: Any = None
        self._on_conflict: list[str] | None = None
        self._ignore_duplicates = False
        self.not_: Any = _NotProxy(self)  # q.not_.in_(...) negates the next filter

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, val):
        self.filters.append((key, "eq", val))
        return self

    def neq(self, key, val):
        self.filters.append((key, "neq", val))
        return self

    def gte(self, key, val):
        self.filters.append((key, "gte", val))
        return self

    def gt(self, key, val):
        self.filters.append((key, "gt", val))
        return self

    def lte(self, key, val):
        self.filters.append((key, "lte", val))
        return self

    def lt(self, key, val):
        self.filters.append((key, "lt", val))
        return self

    def is_(self, key, val):
        self.filters.append((key, "is", val))
        return self

    def in_(self, key, vals):
        self.filters.append((key, "in", list(vals)))
        return self

    def order(self, key, desc=False, **kwargs):
        self._order_key = key
        self._desc = desc
        return self

    def limit(self, n):
        self._limit = n
        return self

    def or_(self, *args, **kwargs):
        # Faithfully model PostgREST `.or_("a.op.v,b.op.v")`: the row must
        # satisfy at least ONE listed condition, and the group is ANDed with the
        # other filters (and any other or_ groups). NULL handling matches
        # PostgREST — `col.neq.x` excludes NULL, `col.is.null` includes it — so
        # `.or_("col.is.null,col.neq.x")` keeps NULL rows and drops col==x.
        if args and isinstance(args[0], str):
            conds = [tuple(part.split(".", 2)) for part in args[0].split(",")]
            self.filters.append(("__or__", "or", conds))
        return self

    def range(self, *args, **kwargs):
        # No-op: SBStub returns all matching rows; API-level pagination is not
        # exercised in unit tests.
        return self

    def insert(self, payload):
        self._pending_insert = payload
        return self

    def update(self, patch):
        self._pending_update = patch
        return self

    def upsert(self, payload, on_conflict=None, **kwargs):
        self._pending_upsert = payload
        self._ignore_duplicates = bool(kwargs.get("ignore_duplicates"))
        if on_conflict:
            self._on_conflict = [c.strip() for c in on_conflict.split(",")]
        return self

    def delete(self):
        self._pending_update = "__delete__"  # marker
        return self

    @staticmethod
    def _coerce(raw):
        """Map PostgREST literal tokens to Python values."""
        if raw == "null":
            return None
        if raw == "true":
            return True
        if raw == "false":
            return False
        return raw

    def _or_cond_true(self, row, col, op, raw):
        """Evaluate a single `col.op.value` condition with PostgREST NULL rules."""
        cell = row.get(col)
        if op == "is":
            return cell is self._coerce(raw)
        if op == "eq":
            target = self._coerce(raw)
            if target is None or isinstance(target, bool):
                return cell is target
            return str(cell) == str(target)
        if op == "neq":
            target = self._coerce(raw)
            if cell is None:
                return False  # NULL <> x is NULL → excluded, like PostgREST
            if isinstance(target, bool):
                return cell is not target
            return str(cell) != str(target)
        if op in ("gt", "gte", "lt", "lte"):
            if cell is None:
                return False
            a, b = str(cell), str(raw)
            return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]
        if op in ("ilike", "like"):
            if cell is None:
                return False
            import re
            pattern = ".*".join(re.escape(p) for p in raw.split("%"))
            flags = re.IGNORECASE if op == "ilike" else 0
            return re.fullmatch(pattern, str(cell), flags) is not None
        return True  # unknown operator: do not exclude

    @staticmethod
    def _cell(row, key):
        """Resolve a filter key that may be a PostgREST JSON path
        (``col->k1->>k2``) against nested dict/JSONB columns, or a plain
        top-level column name."""
        if "->" not in key:
            return row.get(key)
        parts = key.replace("->>", "->").split("->")
        value: Any = row
        for part in parts:
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    def _matches(self, row):
        for key, op, val in self.filters:
            if op == "or":
                if not any(self._or_cond_true(row, c, o, v) for c, o, v in val):
                    return False
                continue
            cell = self._cell(row, key)
            if op == "eq" and cell != val:
                return False
            if op == "neq" and (cell is None or cell == val):
                return False
            if op == "is" and cell is not (None if val is None else val):
                return False
            if op == "not_is" and cell is (None if val is None else val):
                return False
            if op == "gte" and not (cell is not None and cell >= val):
                return False
            if op == "gt" and not (cell is not None and cell > val):
                return False
            if op == "lte" and not (cell is not None and cell <= val):
                return False
            if op == "lt" and not (cell is not None and cell < val):
                return False
            if op == "in" and cell not in val:
                return False
            if op == "not_in" and cell in val:
                return False
        return True

    def execute(self):
        rows_store = self.db.setdefault(self.name, [])

        if self._pending_insert is not None:
            payloads = (
                self._pending_insert
                if isinstance(self._pending_insert, list)
                else [self._pending_insert]
            )
            inserted = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                rows_store.append(row)
                inserted.append(row)
            return _Exec(inserted)

        if self._pending_upsert is not None:
            payloads = (
                self._pending_upsert
                if isinstance(self._pending_upsert, list)
                else [self._pending_upsert]
            )
            keys = self._on_conflict or ["id"]
            upserted = []
            for p in payloads:
                match = None
                for existing in rows_store:
                    if all(existing.get(k) == p.get(k) for k in keys):
                        match = existing
                        break
                if match is not None:
                    if not self._ignore_duplicates:
                        match.update(p)
                    upserted.append(match)
                else:
                    row = dict(p)
                    row.setdefault("id", str(uuid.uuid4()))
                    rows_store.append(row)
                    upserted.append(row)
            return _Exec(upserted)

        matching = [r for r in rows_store if self._matches(r)]
        if self._pending_update is not None:
            if self._pending_update == "__delete__":
                self.db[self.name] = [r for r in rows_store if r not in matching]
                return _Exec(matching)
            for r in matching:
                r.update(self._pending_update)
            return _Exec(matching)

        rows = list(matching)
        if self._order_key:
            rows.sort(
                key=lambda r: (r.get(self._order_key) if r.get(self._order_key) is not None else ""),
                reverse=self._desc,
            )
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Exec(rows)


class _RpcExec:
    def __init__(self, data):
        self.data = data


class _RpcCall:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return _RpcExec(self._value)


class SBStub:
    def __init__(self, db: dict[str, list[dict[str, Any]]] | None = None):
        self.db: dict[str, list[dict[str, Any]]] = db or {}

    def table(self, name: str):
        return _Query(name, self.db)

    def rpc(self, name: str, params: dict[str, Any] | None = None):
        params = params or {}
        # Emulate the atomic counter RPCs by performing the same UPDATE.
        if name == "community_inc_thread_reply_count":
            return _RpcCall(self._inc("community_threads", params.get("p_thread_id"), "reply_count", params.get("p_delta", 0), floor_at_zero=True))
        if name == "community_inc_thread_vote_count":
            return _RpcCall(self._inc("community_threads", params.get("p_thread_id"), "vote_count", params.get("p_delta", 0)))
        if name == "community_inc_reply_vote_count":
            return _RpcCall(self._inc("community_replies", params.get("p_reply_id"), "vote_count", params.get("p_delta", 0)))
        if name == "community_inc_resource_upvote_count":
            return _RpcCall(self._inc("community_resources", params.get("p_resource_id"), "upvote_count", params.get("p_delta", 0), floor_at_zero=True))
        if name == "community_inc_resource_report_count":
            return _RpcCall(self._inc("community_resources", params.get("p_resource_id"), "report_count", params.get("p_delta", 0), floor_at_zero=True))
        if name == "apply_mock_mastery_delta":
            return _RpcCall(self._apply_mock_mastery_delta(params))
        if name == "claim_mock_mastery_retry":
            return _RpcCall(self._claim_mock_mastery_retry(params))
        if name == "complete_mock_mastery_retry":
            return _RpcCall(self._complete_mock_mastery_retry(params))
        if name == "update_pyq_question_review_atomic":
            return _RpcCall(self._update_pyq_question_review_atomic(params))
        if name == "start_attempt_from_blueprint":
            return _RpcCall(self._start_attempt_from_blueprint(params))
        if name == "ensure_mock_correction_draft":
            return _RpcCall(self._ensure_mock_correction_draft(params))
        if name == "ensure_mock_correction_drafts":
            return _RpcCall(self._ensure_mock_correction_drafts(params))
        if name == "replace_manual_mock_correction_drafts":
            return _RpcCall(self._replace_manual_mock_correction_drafts(params))
        if name == "cms_review_competition_metric":
            return _RpcCall(self._cms_review_competition_metric(params))
        if name == "cms_reopen_competition_metric_for_edit":
            return _RpcCall(self._cms_reopen_competition_metric_for_edit(params))
        if name == "cms_review_candidate_count":
            return _RpcCall(self._cms_review_candidate_count(params))
        if name == "cms_reopen_candidate_count_for_edit":
            return _RpcCall(self._cms_reopen_candidate_count_for_edit(params))
        return _RpcCall(None)


    def _claim_mock_mastery_retry(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        import uuid as _uuid

        attempt_id = params.get("p_attempt_id")
        flag_state = params.get("p_flag_state")
        lease_until = params.get("p_lease_until")
        if flag_state not in {"shadow", "live"}:
            raise RuntimeError("mastery retry flag_state must be shadow or live")
        jobs = self.db.setdefault("mock_attempt_jobs", [])
        for job in jobs:
            if (
                job.get("job_kind") == "mastery_retry"
                and job.get("attempt_id") == attempt_id
                and job.get("status") in {"pending", "running"}
            ):
                return [{"id": job.get("id"), "claimed": False}]
        job = {
            "id": str(_uuid.uuid4()),
            "job_kind": "mastery_retry",
            "attempt_id": attempt_id,
            "mastery_flag_state": flag_state,
            "scheduled_for": lease_until,
            "attempts": 0,
            "status": "running",
            "last_error": None,
        }
        jobs.append(job)
        return [{"id": job["id"], "claimed": True}]

    def _complete_mock_mastery_retry(self, params: dict[str, Any]) -> None:
        job_id = params.get("p_job_id")
        for job in self.db.setdefault("mock_attempt_jobs", []):
            if job.get("id") == job_id and job.get("job_kind") == "mastery_retry":
                job.update({"status": "done", "last_error": None})
                return None
        return None

    def _start_attempt_from_blueprint(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Emulate the atomic generated-attempt write RPC (migration 178).

        Mirrors the PL/pgSQL transaction: insert blueprint (status 'draft'),
        insert the owner-scoped attempt (template_id NULL, generated_blueprint_id
        set, in_progress), freeze the N response rows, flip blueprint -> 'started'
        — ALL OR NOTHING. Idempotent on (user, blueprint) via the in_progress
        unique index: a second call with the same blueprint id returns the
        existing attempt and never double-inserts responses.

        Atomicity is testable: set ``sb._force_response_freeze_failure = True`` to
        make the response-freeze step raise; because the emulation commits only at
        the very end, NOTHING is persisted (full rollback).
        """
        import uuid as _uuid
        from datetime import datetime, timezone

        p_user = params.get("p_user")
        p_exam = params.get("p_exam")
        p_exam_phase = params.get("p_exam_phase")
        p_blueprint = params.get("p_blueprint") or {}
        p_template_snapshot = params.get("p_template_snapshot") or {}
        p_response_rows = params.get("p_response_rows") or []
        p_expires_at = params.get("p_expires_at")
        now_iso = datetime.now(timezone.utc).isoformat()

        blueprints = self.db.setdefault("mock_generated_blueprints", [])
        attempts = self.db.setdefault("mock_attempts", [])
        responses = self.db.setdefault("mock_attempt_responses", [])

        bp_id = p_blueprint.get("id") or str(_uuid.uuid4())

        # Idempotency: an in_progress attempt already backs this blueprint.
        for a in attempts:
            if (
                a.get("user_id") == p_user
                and a.get("generated_blueprint_id") == bp_id
                and a.get("status") == "in_progress"
            ):
                for bp in blueprints:
                    if bp.get("id") == bp_id:
                        bp["status"] = "started"
                        bp.setdefault("started_at", now_iso)
                return [{"blueprint_id": bp_id, "attempt_id": a["id"]}]

        # Atomic rollback hook — raise BEFORE committing anything.
        if getattr(self, "_force_response_freeze_failure", False):
            raise RuntimeError("forced response-freeze failure (atomicity test)")

        # HARDENING (migration 179): a brand-new attempt must freeze >=1 response.
        # Mirrors the PL/pgSQL guard; raising here models the full rollback.
        if not p_response_rows:
            raise RuntimeError(
                "start_attempt_from_blueprint: refusing zero-response attempt"
            )

        # Build everything in locals; commit at the very end so a mid-build raise
        # leaves the store untouched (models the single-transaction rollback).
        existing_bp = next((bp for bp in blueprints if bp.get("id") == bp_id), None)
        new_bp = None
        if existing_bp is None:
            new_bp = {
                "id": bp_id,
                "user_id": p_user,
                "exam_id": p_exam,
                "exam_phase_id": p_exam_phase,
                "source": p_blueprint.get("source") or "exam_realistic",
                "status": "draft",
                "template_snapshot": p_blueprint.get("template_snapshot") or {},
                "section_snapshot": p_blueprint.get("section_snapshot") or [],
                "selector_snapshot": p_blueprint.get("selector_snapshot") or {},
                "question_ids": list(p_blueprint.get("question_ids") or []),
                "readiness_snapshot": p_blueprint.get("readiness_snapshot") or {},
                "expires_at": p_expires_at,
                "created_at": now_iso,
            }

        attempt_id = str(_uuid.uuid4())
        attempt_row = {
            "id": attempt_id,
            "user_id": p_user,
            "template_id": None,
            "generated_blueprint_id": bp_id,
            "template_snapshot": p_template_snapshot,
            "status": "in_progress",
            "started_at": now_iso,
            "expires_at": p_expires_at,
            "current_section_index": 0,
            "section_locks_enabled": bool(
                p_template_snapshot.get("section_locks_enabled", False)
            ),
        }
        new_responses = [
            {
                "id": str(_uuid.uuid4()),
                "attempt_id": attempt_id,
                "question_id": r.get("question_id"),
                "question_snapshot": r.get("question_snapshot") or {},
                "is_visited": False,
                "is_marked_for_review": False,
                "client_seq": 0,
            }
            for r in p_response_rows
        ]

        # Commit.
        target_bp = new_bp if new_bp is not None else existing_bp
        if new_bp is not None:
            blueprints.append(new_bp)
        attempts.append(attempt_row)
        responses.extend(new_responses)
        target_bp["status"] = "started"
        target_bp["started_at"] = now_iso

        return [{"blueprint_id": bp_id, "attempt_id": attempt_id}]

    def _ensure_mock_correction_draft(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Emulate ensure_mock_correction_draft RPC (migration 182).

        Ownership + source_type guard (D2): raises if the mock is not owned by
        p_user_id or is not a platform_attempt.  Idempotent: inserts only when
        no drafted row with the same (mock_test_id, user_id, category, topic)
        exists; otherwise returns the existing row.
        """
        mock_test_id = params.get("p_mock_test_id")
        user_id = params.get("p_user_id")
        category = params.get("p_category")
        topic = params.get("p_topic") or None
        title = params.get("p_title") or ""
        source_questions = params.get("p_source_questions") or []

        mock_rows = [
            r for r in self.db.get("mock_tests", [])
            if r.get("id") == mock_test_id
            and r.get("user_id") == user_id
            and r.get("source_type") == "platform_attempt"
        ]
        if not mock_rows:
            raise RuntimeError("platform_attempt mock not found for user")

        store = self.db.setdefault("mock_correction_tasks", [])

        for row in store:
            if (
                row.get("mock_test_id") == mock_test_id
                and row.get("user_id") == user_id
                and row.get("category") == category
                and row.get("state") == "drafted"
                and (row.get("topic") or None) == topic
            ):
                return row

        new_row: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "mock_test_id": mock_test_id,
            "user_id": user_id,
            "category": category,
            "topic": topic,
            "title": title,
            "source_questions": source_questions,
            "state": "drafted",
            "study_task_id": None,
            "created_at": None,
            "applied_at": None,
        }
        store.append(new_row)
        return new_row

    def _ensure_mock_correction_drafts(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Emulate ensure_mock_correction_drafts RPC (migration 182).

        Atomic bulk upsert (D1 fix): all drafts are processed in one call.
        Ownership + source_type guard (D2): raises if mock is not owned by
        p_user_id or is not a platform_attempt.  ON CONFLICT DO NOTHING per key.
        """
        mock_test_id = params.get("p_mock_test_id")
        user_id = params.get("p_user_id")
        drafts: list[dict[str, Any]] = params.get("p_drafts") or []

        mock_rows = [
            r for r in self.db.get("mock_tests", [])
            if r.get("id") == mock_test_id
            and r.get("user_id") == user_id
            and r.get("source_type") == "platform_attempt"
        ]
        if not mock_rows:
            raise RuntimeError("platform_attempt mock not found for user")

        store = self.db.setdefault("mock_correction_tasks", [])

        for d in drafts:
            cat = d.get("category")
            topic = d.get("topic") or None
            title = d.get("title") or ""
            src_qs = d.get("source_questions") or []

            existing = any(
                row.get("mock_test_id") == mock_test_id
                and row.get("user_id") == user_id
                and row.get("category") == cat
                and row.get("state") == "drafted"
                and (row.get("topic") or None) == topic
                for row in store
            )
            if not existing:
                store.append({
                    "id": str(uuid.uuid4()),
                    "mock_test_id": mock_test_id,
                    "user_id": user_id,
                    "category": cat,
                    "topic": topic,
                    "title": title,
                    "source_questions": src_qs,
                    "state": "drafted",
                    "study_task_id": None,
                    "created_at": None,
                    "applied_at": None,
                })

        return [
            r for r in store
            if r.get("mock_test_id") == mock_test_id
            and r.get("user_id") == user_id
            and r.get("state") == "drafted"
        ]

    def _replace_manual_mock_correction_drafts(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Emulate replace_manual_mock_correction_drafts RPC (migration 182).

        Single atomic replacement: upsert desired drafted rows, delete obsolete
        drafted rows (preserving applied/dismissed), update review_state.
        Mirrors the PL/pgSQL transaction: raises on mock-not-found or
        platform_attempt; empty p_drafts deletes all and sets 'reviewed'.
        """
        mock_test_id = params.get("p_mock_test_id")
        user_id = params.get("p_user_id")
        drafts: list[dict[str, Any]] = params.get("p_drafts") or []

        mock_rows = [
            r for r in self.db.get("mock_tests", [])
            if r.get("id") == mock_test_id and r.get("user_id") == user_id
        ]
        if not mock_rows:
            raise RuntimeError("mock not found")

        mock = mock_rows[0]
        if mock.get("source_type") == "platform_attempt":
            raise RuntimeError("PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN")

        store = self.db.setdefault("mock_correction_tasks", [])

        if not drafts:
            self.db["mock_correction_tasks"] = [
                r for r in store
                if not (
                    r.get("mock_test_id") == mock_test_id
                    and r.get("user_id") == user_id
                    and r.get("state") == "drafted"
                )
            ]
            mock["review_state"] = "reviewed"
            return []

        # UPSERT: update existing drafted rows or insert new ones.
        for d in drafts:
            cat = d.get("category")
            topic = d.get("topic") or None
            title = d.get("title") or ""
            src_qs = d.get("source_questions") or []

            existing = None
            for row in self.db.get("mock_correction_tasks", []):
                if (
                    row.get("mock_test_id") == mock_test_id
                    and row.get("user_id") == user_id
                    and row.get("state") == "drafted"
                    and row.get("category") == cat
                    and (row.get("topic") or None) == topic
                ):
                    existing = row
                    break

            if existing is not None:
                existing["state"] = "drafted"
                existing["title"] = title
                existing["source_questions"] = src_qs
            else:
                self.db["mock_correction_tasks"].append({
                    "id": str(uuid.uuid4()),
                    "mock_test_id": mock_test_id,
                    "user_id": user_id,
                    "category": cat,
                    "topic": topic,
                    "title": title,
                    "source_questions": src_qs,
                    "state": "drafted",
                    "study_task_id": None,
                    "created_at": None,
                    "applied_at": None,
                })

        # DELETE obsolete drafted rows not in the desired set.
        desired_keys = {
            (d.get("category"), d.get("topic") or None)
            for d in drafts
        }
        self.db["mock_correction_tasks"] = [
            r for r in self.db["mock_correction_tasks"]
            if not (
                r.get("mock_test_id") == mock_test_id
                and r.get("user_id") == user_id
                and r.get("state") == "drafted"
                and (r.get("category"), r.get("topic") or None) not in desired_keys
            )
        ]

        mock["review_state"] = "correction_drafted"

        return [
            r for r in self.db.get("mock_correction_tasks", [])
            if r.get("mock_test_id") == mock_test_id
            and r.get("user_id") == user_id
            and r.get("state") == "drafted"
        ]

    def _update_pyq_question_review_atomic(self, params: dict[str, Any]) -> dict[str, Any] | None:
        """Emulate the atomic question-review cascade RPC (migration 151)."""
        question_id = params.get("p_question_id")
        status = params.get("p_reviewer_status")
        reviewed_by = params.get("p_reviewed_by")
        reviewed_at = params.get("p_reviewed_at")

        question = None
        for q in self.db.get("pyq_questions", []):
            if q.get("id") == question_id:
                q["reviewer_status"] = status
                q["reviewed_by"] = reviewed_by
                q["reviewed_at"] = reviewed_at
                question = q
                break

        if question is None:
            return None  # caller maps None → 404

        option_count = 0
        if status in ("verified", "rejected", "needs_correction"):
            for opt in self.db.get("pyq_options", []):
                if opt.get("question_id") == question_id:
                    opt["reviewer_status"] = status
                    opt["reviewed_by"] = reviewed_by
                    opt["reviewed_at"] = reviewed_at
                    option_count += 1

        return {"question": question, "cascaded_option_count": option_count}

    # Publication (aspirant visibility) happens at pending_review -> reviewed,
    # NOT at reviewed -> locked (reviewed and locked are both published
    # states per AGENTS.md "reviewed or locked feed the planner, locked
    # preferred"). Once published, the only correction path is
    # reopen-for-edit (clone-to-draft) — reviewed has no direct path to
    # rejected, which would otherwise silently remove published availability.
    _ECM_TRANSITIONS = {
        "draft": {"pending_review", "rejected"},
        "pending_review": {"reviewed", "rejected", "draft"},
        "reviewed": {"locked"},
        "locked": {"reviewed"},
        "rejected": {"draft"},
    }

    def _cms_review_competition_metric(self, params: dict[str, Any]) -> dict[str, Any]:
        """Emulate cms_review_competition_metric (migration 216): transition
        matrix + CAS + atomic current-published supersession on publish."""
        metric_id = params.get("p_metric_id")
        expected_status = params.get("p_expected_status")
        new_status = params.get("p_new_status")
        reviewer_notes = params.get("p_reviewer_notes")
        actor_id = params.get("p_actor_user_id")
        actor_email = params.get("p_actor_email")

        if not actor_id:
            raise RuntimeError("missing_actor_id: p_actor_user_id must not be NULL")
        if new_status not in ("draft", "pending_review", "reviewed", "locked", "rejected"):
            raise RuntimeError(f"invalid_target_status: {new_status} is not a recognised status")

        row = next((r for r in self.db.get("exam_competition_metrics", []) if r.get("id") == metric_id), None)
        if row is None:
            raise RuntimeError(f"not_found: metric {metric_id} does not exist")

        current_status = row.get("reviewer_status")
        if current_status != expected_status:
            raise RuntimeError(
                f"concurrent_modification: expected status={expected_status} but found {current_status}"
            )
        if new_status not in self._ECM_TRANSITIONS.get(current_status, set()):
            raise RuntimeError(f"transition_not_allowed: {current_status} -> {new_status} is not permitted")
        if current_status == "locked" and new_status == "reviewed" and not (reviewer_notes or "").strip():
            raise RuntimeError("invalid_reviewer_notes: reviewer_notes required when reopening a locked row")
        if current_status == "draft" and new_status == "pending_review" and row.get("source_basis") == "model_generated":
            raise RuntimeError(
                "model_generated_requires_evidence: attach primary evidence and change source_basis "
                "to official or reviewed_analysis before submitting a model_generated row for review"
            )

        row["reviewer_status"] = new_status
        row["reviewed_by"] = actor_id
        row["reviewed_at"] = "2026-07-03T00:00:00Z"
        if reviewer_notes is not None:
            row["reviewer_notes"] = reviewer_notes

        if new_status == "reviewed" and current_status == "pending_review":
            scope = (row.get("exam_id"), row.get("exam_cycle_id"), row.get("exam_phase_id"), row.get("metric_kind"))
            for other in self.db.get("exam_competition_metrics", []):
                other_scope = (
                    other.get("exam_id"), other.get("exam_cycle_id"),
                    other.get("exam_phase_id"), other.get("metric_kind"),
                )
                if other is not row and other.get("is_current_published") and other_scope == scope:
                    other["is_current_published"] = False
                    other["superseded_at"] = "2026-07-03T00:00:00Z"
            row["is_current_published"] = True
        # reviewed<->locked keeps whatever is_current_published it already
        # has; every other transition never had it set (draft/pending_review/
        # rejected rows are never current-published).

        import uuid as _uuid

        audit_id = str(_uuid.uuid4())
        self.db.setdefault("admin_audit_logs", []).append({
            "id": audit_id, "actor_id": actor_id, "actor_email": actor_email,
            "admin_user_id": actor_id, "action": "competition_metric_status_transition",
            "entity_type": "exam_competition_metric", "entity_id": metric_id,
            "old_value": {"status": expected_status}, "new_value": {"status": new_status},
            "notes": reviewer_notes,
        })
        return {
            "ok": True, "audit_id": audit_id, "metric_id": metric_id,
            "prev_status": expected_status, "new_status": new_status,
        }

    def _cms_reopen_competition_metric_for_edit(self, params: dict[str, Any]) -> dict[str, Any]:
        """Emulate cms_reopen_competition_metric_for_edit (migration 216):
        clone-to-draft, never mutates the published row in place."""
        import uuid as _uuid

        metric_id = params.get("p_metric_id")
        reviewer_notes = params.get("p_reviewer_notes")
        actor_id = params.get("p_actor_user_id")
        actor_email = params.get("p_actor_email")

        if not actor_id:
            raise RuntimeError("missing_actor_id: p_actor_user_id must not be NULL")
        if not (reviewer_notes or "").strip():
            raise RuntimeError("invalid_reviewer_notes: reviewer_notes required to reopen for edit")

        pub = next((r for r in self.db.get("exam_competition_metrics", []) if r.get("id") == metric_id), None)
        if pub is None:
            raise RuntimeError(f"not_found: metric {metric_id} does not exist")
        if pub.get("reviewer_status") not in ("reviewed", "locked"):
            raise RuntimeError("not_published: only a reviewed/locked row can be reopened for edit")

        new_row = dict(pub)
        new_row["id"] = str(_uuid.uuid4())
        new_row["reviewer_status"] = "draft"
        new_row["supersedes_id"] = pub["id"]
        new_row["version_no"] = (pub.get("version_no") or 1) + 1
        new_row["is_current_published"] = False
        new_row["superseded_at"] = None
        self.db.setdefault("exam_competition_metrics", []).append(new_row)
        self.db.setdefault("admin_audit_logs", []).append({
            "id": str(_uuid.uuid4()), "actor_id": actor_id, "actor_email": actor_email,
            "admin_user_id": actor_id, "action": "competition_metric_reopen_for_edit",
            "entity_type": "exam_competition_metric", "entity_id": metric_id,
            "old_value": {"published_id": pub["id"]}, "new_value": {"draft_id": new_row["id"]},
            "notes": reviewer_notes,
        })
        return new_row

    # Same transition matrix as competition metrics (migration 218 mirrors
    # 216's lifecycle RPC exactly).
    _ECC_TRANSITIONS = _ECM_TRANSITIONS

    def _cms_review_candidate_count(self, params: dict[str, Any]) -> dict[str, Any]:
        """Emulate cms_review_candidate_count (migration 218): transition
        matrix + CAS + evidence claim-value-match promotion gate + atomic
        current-published supersession on publish."""
        count_id = params.get("p_count_id")
        expected_status = params.get("p_expected_status")
        new_status = params.get("p_new_status")
        reviewer_notes = params.get("p_reviewer_notes")
        actor_id = params.get("p_actor_user_id")
        actor_email = params.get("p_actor_email")

        if not actor_id:
            raise RuntimeError("missing_actor_id: p_actor_user_id must not be NULL")
        if new_status not in ("draft", "pending_review", "reviewed", "locked", "rejected"):
            raise RuntimeError(f"invalid_target_status: {new_status} is not a recognised status")

        row = next((r for r in self.db.get("exam_candidate_counts", []) if r.get("id") == count_id), None)
        if row is None:
            raise RuntimeError(f"not_found: candidate count {count_id} does not exist")

        current_status = row.get("reviewer_status")
        if current_status != expected_status:
            raise RuntimeError(
                f"concurrent_modification: expected status={expected_status} but found {current_status}"
            )
        if new_status not in self._ECC_TRANSITIONS.get(current_status, set()):
            raise RuntimeError(f"transition_not_allowed: {current_status} -> {new_status} is not permitted")
        if current_status == "locked" and new_status == "reviewed" and not (reviewer_notes or "").strip():
            raise RuntimeError("invalid_reviewer_notes: reviewer_notes required when reopening a locked row")
        if current_status == "draft" and new_status == "pending_review" and row.get("source_basis") == "model_generated":
            raise RuntimeError(
                "model_generated_requires_evidence: attach primary evidence and change source_basis "
                "to official or reviewed_analysis before submitting a model_generated row for review"
            )

        if current_status == "pending_review" and new_status == "reviewed":
            cat_code = None
            if row.get("reservation_category_id"):
                cat = next(
                    (c for c in self.db.get("reservation_categories", []) if c.get("id") == row.get("reservation_category_id")),
                    None,
                )
                cat_code = cat.get("code") if cat else None
            qualifying = False
            for e in self.db.get("exam_candidate_count_evidence", []):
                if e.get("count_id") != count_id:
                    continue
                if e.get("evidence_role") != "primary" or e.get("evidence_kind") == "reviewed_analysis":
                    continue
                cv = e.get("claim_value") or {}
                # claim_value shape/type guard (§7): count_value must be a
                # real number, else the row is malformed and never qualifies
                # (mirrors the migration's jsonb_typeof guard before the cast).
                raw_cv = cv.get("count_value")
                if not isinstance(raw_cv, (int, float)) or isinstance(raw_cv, bool):
                    continue
                if raw_cv != row.get("count_value"):
                    continue
                if cv.get("count_type") != row.get("count_type"):
                    continue
                if cv.get("scope_kind") != row.get("scope_kind"):
                    continue
                if cv.get("exam_phase_id") != row.get("exam_phase_id"):
                    continue
                if cv.get("reservation_category_code") != cat_code:
                    continue
                # Source-trust (§7): a primary official count REQUIRES an
                # existing, active, verified, non-discovery, non-aggregator
                # source_registry row PLUS an evidence_url or document_asset_id.
                # source_id IS NULL is NOT trusted (checkpost P1-5).
                src_id = e.get("source_id")
                if not src_id:
                    continue
                src = next((s for s in self.db.get("source_registry", []) if s.get("id") == src_id), None)
                if not src or not src.get("is_active") or not src.get("is_verified") \
                        or src.get("discovery_only") or src.get("source_type") == "aggregator":
                    continue
                if not (e.get("evidence_url") or e.get("document_asset_id")):
                    continue
                qualifying = True
                break
            if not qualifying:
                raise RuntimeError("missing_or_stale_evidence: candidate count has no matching, source-trusted primary evidence")

        row["reviewer_status"] = new_status
        row["reviewed_by"] = actor_id
        row["reviewed_at"] = "2026-07-03T00:00:00Z"
        if reviewer_notes is not None:
            row["reviewer_notes"] = reviewer_notes

        if new_status == "reviewed" and current_status == "pending_review":
            scope = (
                row.get("exam_id"), row.get("exam_cycle_id"), row.get("scope_kind"),
                row.get("exam_phase_id"), row.get("count_type"), row.get("reservation_category_id"),
            )
            for other in self.db.get("exam_candidate_counts", []):
                other_scope = (
                    other.get("exam_id"), other.get("exam_cycle_id"), other.get("scope_kind"),
                    other.get("exam_phase_id"), other.get("count_type"), other.get("reservation_category_id"),
                )
                if other is not row and other.get("is_current_published") and other_scope == scope:
                    other["is_current_published"] = False
                    other["superseded_at"] = "2026-07-03T00:00:00Z"
            row["is_current_published"] = True

        import uuid as _uuid

        audit_id = str(_uuid.uuid4())
        self.db.setdefault("admin_audit_logs", []).append({
            "id": audit_id, "actor_id": actor_id, "actor_email": actor_email,
            "admin_user_id": actor_id, "action": "candidate_count_status_transition",
            "entity_type": "exam_candidate_count", "entity_id": count_id,
            "old_value": {"status": expected_status}, "new_value": {"status": new_status},
            "notes": reviewer_notes,
        })
        return {
            "ok": True, "audit_id": audit_id, "count_id": count_id,
            "prev_status": expected_status, "new_status": new_status,
        }

    def _cms_reopen_candidate_count_for_edit(self, params: dict[str, Any]) -> dict[str, Any]:
        """Emulate cms_reopen_candidate_count_for_edit (migration 218):
        clone-to-draft, never mutates the published row in place."""
        import uuid as _uuid

        count_id = params.get("p_count_id")
        reviewer_notes = params.get("p_reviewer_notes")
        actor_id = params.get("p_actor_user_id")
        actor_email = params.get("p_actor_email")

        if not actor_id:
            raise RuntimeError("missing_actor_id: p_actor_user_id must not be NULL")
        if not (reviewer_notes or "").strip():
            raise RuntimeError("invalid_reviewer_notes: reviewer_notes required to reopen for edit")

        pub = next((r for r in self.db.get("exam_candidate_counts", []) if r.get("id") == count_id), None)
        if pub is None:
            raise RuntimeError(f"not_found: candidate count {count_id} does not exist")
        if pub.get("reviewer_status") not in ("reviewed", "locked"):
            raise RuntimeError("not_published: only a reviewed/locked row can be reopened for edit")

        new_row = dict(pub)
        new_row["id"] = str(_uuid.uuid4())
        new_row["reviewer_status"] = "draft"
        new_row["supersedes_id"] = pub["id"]
        new_row["version_no"] = (pub.get("version_no") or 1) + 1
        new_row["is_current_published"] = False
        new_row["superseded_at"] = None
        self.db.setdefault("exam_candidate_counts", []).append(new_row)
        self.db.setdefault("admin_audit_logs", []).append({
            "id": str(_uuid.uuid4()), "actor_id": actor_id, "actor_email": actor_email,
            "admin_user_id": actor_id, "action": "candidate_count_reopen_for_edit",
            "entity_type": "exam_candidate_count", "entity_id": count_id,
            "old_value": {"published_id": pub["id"]}, "new_value": {"draft_id": new_row["id"]},
            "notes": reviewer_notes,
        })
        return new_row

    def _apply_mock_mastery_delta(self, params: dict[str, Any]) -> dict[str, Any]:
        """Emulate the atomic, idempotent mastery-apply function (migration 145).

        Mirrors the PL/pgSQL: skip when an audit row already exists for
        (user, topic, attempt); otherwise read mastery (default 50), apply the
        [0,100] clamp, write mastery, and append the audit row.
        """
        import uuid as _uuid

        user_id = params.get("p_user_id")
        topic_id = params.get("p_topic_id")
        attempt_id = params.get("p_attempt_id")
        delta_db = float(params.get("p_delta_db") or 0)
        reason = params.get("p_reason") or "mock_submit"

        audit = self.db.setdefault("user_topic_mastery_audit", [])
        for r in audit:
            if r.get("user_id") == user_id and r.get("topic_id") == topic_id and r.get("attempt_id") == attempt_id:
                return {"applied": False, "reason": "already_applied"}

        mastery = self.db.setdefault("user_topic_mastery", [])
        row = None
        for r in mastery:
            if r.get("user_id") == user_id and r.get("topic_id") == topic_id and not r.get("exam_id") and not r.get("exam_phase_id"):
                row = r
                break
        current = float(row.get("mastery_score")) if row is not None and row.get("mastery_score") is not None else 50.0
        new_value = max(0.0, min(100.0, current + delta_db))
        if row is None:
            mastery.append({"id": str(_uuid.uuid4()), "user_id": user_id, "topic_id": topic_id, "mastery_score": new_value})
        else:
            row["mastery_score"] = new_value

        audit.append({
            "id": str(_uuid.uuid4()), "user_id": user_id, "topic_id": topic_id, "attempt_id": attempt_id,
            "before_mastery_db": current, "after_mastery_db": new_value, "delta_applied_db": delta_db, "reason": reason,
        })
        return {"applied": True, "before": current, "after": new_value, "delta": delta_db}

    def _inc(self, table: str, row_id: Any, col: str, delta: int, floor_at_zero: bool = False) -> int | None:
        for r in self.db.get(table, []):
            if r.get("id") == row_id:
                new_val = (r.get(col) or 0) + (delta or 0)
                if floor_at_zero and new_val < 0:
                    new_val = 0
                r[col] = new_val
                return new_val
        return None
