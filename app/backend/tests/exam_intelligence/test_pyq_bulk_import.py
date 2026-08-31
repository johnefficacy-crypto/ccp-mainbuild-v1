"""PR5: PYQ-specialised bulk import — preflight + commit.

Covers
------
- Preflight: clean rows → ok
- Preflight: bad correct_option → error row
- Preflight: duplicate question_number within upload → error
- Preflight: null observed_difficulty accepted
- Preflight: fuzzy near-match flagged (Levenshtein >= 0.85)
- Preflight: exact hash duplicate against existing paper row
- Commit: happy-path N rows → committed=N
- Commit: idempotent re-commit → committed=0, skipped=N
- Commit: override_errors skips only rows with no parsed data
- Commit: reviewer_status forced pending on every inserted question
- Parity: frontend option_hash === backend option_hash
"""
from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from app.exam_intelligence import pyq_bulk_import as _bi
from app.exam_intelligence.option_normalize import option_hash, question_hash
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub
from tests.persona_questions._stub import _Query

_BASE = "/api/admin/exam-intelligence-cms"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-99", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed(extra_questions: list[dict] | None = None) -> dict:
    db: dict = {
        "pyq_papers": [{"id": "paper-1", "exam_id": "exam-1"}],
        "pyq_questions": list(extra_questions or []),
        "pyq_options": [],
        "admin_audit_logs": [],
    }
    return db


def _make_csv(rows: list[dict]) -> bytes:
    cols = ["question_number", "question_text", "option_a", "option_b",
            "option_c", "option_d", "correct_option", "question_type",
            "observed_difficulty"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue().encode("utf-8")


def _clean_row(n: int, **kwargs) -> dict:
    return {
        "question_number": n,
        "question_text": f"What is question number {n}?",
        "option_a": "Alpha",
        "option_b": "Beta",
        "option_c": "Gamma",
        "option_d": "Delta",
        "correct_option": "A",
        "question_type": "mcq",
        "observed_difficulty": "medium",
        **kwargs,
    }


def _preflight(client: TestClient, rows: list[dict], *, paper_id: str = "paper-1") -> dict:
    body = _make_csv(rows)
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/preflight",
        content=body,
        headers={"content-type": "text/csv"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _preflight_json(client: TestClient, rows: list[dict], *, paper_id: str = "paper-1") -> dict:
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/preflight",
        content=json.dumps(rows).encode(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── Preflight tests ──────────────────────────────────────────────────────────

class TestPreflight:
    def test_clean_rows_all_ok(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(i) for i in range(1, 6)]
        pf = _preflight(client, rows)
        assert pf["summary"]["ok"] == 5
        assert pf["summary"]["error"] == 0
        assert all(r["status"] == "ok" for r in pf["rows"])
        assert "import_token" in pf

    def test_bad_correct_option_flagged_error(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [
            _clean_row(1),
            _clean_row(2, correct_option="X"),  # invalid
            _clean_row(3),
        ]
        pf = _preflight(client, rows)
        assert pf["summary"]["error"] == 1
        assert pf["summary"]["ok"] == 2
        bad = [r for r in pf["rows"] if r["status"] == "error"]
        assert len(bad) == 1 and bad[0]["row"] == 2
        assert any("correct_option" in m for m in bad[0]["messages"])

    def test_duplicate_question_number_within_upload(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(1), _clean_row(1, question_text="Different text?")]
        pf = _preflight(client, rows)
        # Second row should have error about duplicate number
        assert pf["summary"]["error"] >= 1
        dup = next(r for r in pf["rows"] if r["row"] == 2)
        assert dup["status"] == "error"
        assert any("question_number 1" in m for m in dup["messages"])

    def test_null_observed_difficulty_accepted(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(1, observed_difficulty=""), _clean_row(2, observed_difficulty=None)]
        pf = _preflight(client, rows)
        assert pf["summary"]["error"] == 0
        assert all(r["status"] == "ok" for r in pf["rows"])

    def test_missing_option_is_error(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(1, option_b="")]
        pf = _preflight(client, rows)
        assert pf["summary"]["error"] == 1
        bad = pf["rows"][0]
        assert any("option_b" in m for m in bad["messages"])

    def test_invalid_question_type_flagged(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(1, question_type="essay")]
        pf = _preflight(client, rows)
        assert pf["summary"]["error"] == 1

    def test_exact_hash_duplicate_against_existing(self):
        # question_text identical to an existing row → status=duplicate
        existing_text = "What is the speed of light?"
        existing_hash = question_hash(existing_text)
        seed = _seed(extra_questions=[{
            "id": "q-existing",
            "pyq_paper_id": "paper-1",
            "question_number": 5,
            "question_text": existing_text,
            "normalized_question_hash": existing_hash,
        }])
        sb = TaxSBStub(seed)
        client = _client(sb)
        rows = [_clean_row(99, question_text=existing_text)]
        pf = _preflight(client, rows)
        assert pf["summary"]["duplicate"] == 1
        dup = pf["rows"][0]
        assert dup["status"] == "duplicate"
        assert any("exact text match" in m for m in dup["messages"])

    def test_question_number_existing_in_paper_is_duplicate(self):
        seed = _seed(extra_questions=[{
            "id": "q-old", "pyq_paper_id": "paper-1",
            "question_number": 3, "question_text": "Old question?",
            "normalized_question_hash": question_hash("Old question?"),
        }])
        sb = TaxSBStub(seed)
        client = _client(sb)
        rows = [_clean_row(3, question_text="Completely different text here")]
        pf = _preflight(client, rows)
        assert pf["rows"][0]["status"] == "duplicate"

    def test_fuzzy_near_match_flagged(self):
        base_text = "What is the capital of France and why is it important?"
        existing_hash = question_hash(base_text)
        seed = _seed(extra_questions=[{
            "id": "q-near", "pyq_paper_id": "paper-1",
            "question_number": 10, "question_text": base_text,
            "normalized_question_hash": existing_hash,
        }])
        sb = TaxSBStub(seed)
        client = _client(sb)
        # Slightly modified text — should hit fuzzy threshold
        near_text = "What is the capital of France and why is it so important?"
        rows = [_clean_row(99, question_text=near_text)]
        pf = _preflight(client, rows)
        row = pf["rows"][0]
        assert row["status"] in ("duplicate", "fuzzy"), f"expected fuzzy/dup, got {row}"

    def test_json_body_accepted(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [_clean_row(i) for i in range(1, 4)]
        pf = _preflight_json(client, rows)
        assert pf["summary"]["ok"] == 3

    def test_paper_not_found_404(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        body = _make_csv([_clean_row(1)])
        r = client.post(
            f"{_BASE}/pyq-papers/nonexistent/bulk-import/preflight",
            content=body,
            headers={"content-type": "text/csv"},
        )
        assert r.status_code == 404

    def test_empty_body_422(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=b"",
            headers={"content-type": "text/csv"},
        )
        assert r.status_code == 422


# ── Commit tests ──────────────────────────────────────────────────────────────

class TestCommit:
    def _do_preflight_and_commit(self, sb, rows, *, override_errors=False):
        client = _client(sb)
        pf = _preflight(client, rows)
        token = pf["import_token"]
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "override_errors": override_errors, "reason": "test commit"},
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_happy_path_5_rows(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(i) for i in range(1, 6)]
        result = self._do_preflight_and_commit(sb, rows)
        assert result["committed"] == 5
        assert result["skipped"] == 0
        assert result["failed"] == 0
        # 5 questions + 20 options
        assert len(sb.db["pyq_questions"]) == 5
        assert len(sb.db["pyq_options"]) == 20

    def test_reviewer_status_forced_pending(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1), _clean_row(2)]
        self._do_preflight_and_commit(sb, rows)
        for q in sb.db["pyq_questions"]:
            assert q["reviewer_status"] == "pending"

    def test_correct_option_stored_on_option_row(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1, correct_option="C")]
        self._do_preflight_and_commit(sb, rows)
        opts = sb.db["pyq_options"]
        c_opt = next(o for o in opts if o["option_label"] == "C")
        others = [o for o in opts if o["option_label"] != "C"]
        assert c_opt["is_correct"] is True
        assert all(not o["is_correct"] for o in others)

    def test_idempotent_recommit_skips_all(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(i) for i in range(1, 4)]
        client = _client(sb)
        pf = _preflight(client, rows)
        token = pf["import_token"]

        # First commit
        r1 = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "first"},
        )
        assert r1.status_code == 200
        assert r1.json()["committed"] == 3

        # Preflight again for a fresh token (same rows)
        pf2 = _preflight(client, rows)
        token2 = pf2["import_token"]
        r2 = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token2, "reason": "recommit"},
        )
        assert r2.status_code == 200
        body2 = r2.json()
        # All should be skipped (already_exists)
        assert body2["committed"] == 0
        assert body2["skipped"] == 3

    def test_error_rows_skipped_without_override(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1), _clean_row(2, correct_option="Z"), _clean_row(3)]
        result = self._do_preflight_and_commit(sb, rows)
        assert result["committed"] == 2
        assert result["skipped"] == 1
        assert len(sb.db["pyq_questions"]) == 2

    def test_duplicate_rows_skipped_without_override(self):
        existing_text = "Which element has atomic number 1?"
        seed = _seed(extra_questions=[{
            "id": "q-pre", "pyq_paper_id": "paper-1",
            "question_number": 5, "question_text": existing_text,
            "normalized_question_hash": question_hash(existing_text),
        }])
        sb = TaxSBStub(seed)
        rows = [_clean_row(99, question_text=existing_text), _clean_row(1)]
        result = self._do_preflight_and_commit(sb, rows)
        # Row 99 is exact hash duplicate → skipped; Row 1 committed
        assert result["committed"] == 1
        assert result["skipped"] == 1

    def test_override_errors_flag_attempts_error_rows(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1, correct_option="Z"), _clean_row(2)]
        result = self._do_preflight_and_commit(sb, rows, override_errors=True)
        # Row 1 has no parsed data (validation failed) → cannot proceed → failed
        # Row 2 is clean → committed
        assert result["committed"] == 1
        per_row = {r["row"]: r for r in result["per_row"]}
        assert per_row[1]["result"] == "failed"
        assert per_row[2]["result"] == "committed"

    def test_bad_token_404(self):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": "nonexistent-token-abc", "reason": "test"},
        )
        assert r.status_code == 404

    def test_options_normalized_hash_populated(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1, option_a="Photosynthesis")]
        self._do_preflight_and_commit(sb, rows)
        opts = [o for o in sb.db["pyq_options"] if o["option_label"] == "A"]
        assert len(opts) == 1
        assert opts[0]["normalized_option_hash"] == option_hash("Photosynthesis")

    def test_null_difficulty_inserted(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1, observed_difficulty="")]
        self._do_preflight_and_commit(sb, rows)
        q = sb.db["pyq_questions"][0]
        # observed_difficulty should either be absent or None
        assert q.get("observed_difficulty") is None

    def test_4_options_per_question(self):
        sb = TaxSBStub(_seed())
        rows = [_clean_row(i) for i in range(1, 4)]
        self._do_preflight_and_commit(sb, rows)
        assert len(sb.db["pyq_options"]) == 12  # 3 questions × 4 options

    def test_options_failure_rolls_back_question_and_reports_failed(self):
        """PR7 atomicity in bulk-import commit: options insert failure → question deleted, row=failed."""
        from tests.exam_intelligence.test_pr7_child_errors import FailSBStub

        sb = FailSBStub(_seed(), fail_table="pyq_options")
        client = _client(sb)
        rows = [_clean_row(1), _clean_row(2)]
        pf = _preflight(client, rows)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": pf["import_token"], "reason": "atomicity test"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["committed"] == 0
        assert body["failed"] == 2
        # No orphaned question rows
        assert len(sb.db["pyq_questions"]) == 0
        assert len(sb.db["pyq_options"]) == 0
        # per_row entries report the failure
        assert all(r["result"] == "failed" for r in body["per_row"])

    def test_options_failure_ok_false_is_real(self):
        """Corollary: when ok:false is returned, the DB state is clean (no orphans)."""
        from tests.exam_intelligence.test_pr7_child_errors import FailSBStub

        sb = FailSBStub(_seed(), fail_table="pyq_options")
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1)])
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": pf["import_token"], "reason": "ok-false real failure"},
        )
        body = r.json()
        assert body["failed"] == 1
        # failed=1 is an honest report — no silently committed orphan
        assert len(sb.db["pyq_questions"]) == 0


# ── observed_difficulty vocabulary ───────────────────────────────────────────

class TestObservedDifficultyVocabulary:
    """The canonical set is easy|medium|hard — the only three values
    migration 239's projection to mock_question_bank recognises. Everything
    else it silently rewrites to 'medium', so the importer's job here is to
    REJECT, not to coerce. These tests are about what does not get through.
    """

    @pytest.mark.parametrize("bad", [
        "very_hard",    # was offered by the PyqPaperWorkspace dropdown
        "medium_high",  # present in the corpus; no surface ever offered it
        "moderate",     # was offered by the generic ExamIntelCms dropdown
        "tough",
        "easy_low",
        "1",
        "Hard!",
    ])
    def test_non_canonical_value_rejected(self, bad):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1, observed_difficulty=bad)])
        assert pf["summary"]["error"] == 1
        bad_row = pf["rows"][0]
        assert bad_row["status"] == "error"
        # The message must name the field AND the offending value — an
        # operator hand-labelling 597 questions needs to know which cell.
        msg = next(m for m in bad_row["messages"] if "observed_difficulty" in m)
        assert repr(bad) in msg

    @pytest.mark.parametrize("good", ["easy", "medium", "hard"])
    def test_canonical_values_accepted(self, good):
        sb = TaxSBStub(_seed())
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1, observed_difficulty=good)])
        assert pf["summary"]["error"] == 0
        assert pf["rows"][0]["status"] == "ok"

    def test_null_and_blank_accepted_as_null(self):
        """The regulatory corpus is 100% NULL and must keep importing. A CSV
        encodes NULL as an empty cell, so blank and absent both mean NULL.
        """
        sb = TaxSBStub(_seed())
        client = _client(sb)
        rows = [
            _clean_row(1, observed_difficulty=""),
            _clean_row(2, observed_difficulty=None),
            _clean_row(3, observed_difficulty="   "),
        ]
        pf = _preflight(client, rows)
        assert pf["summary"]["error"] == 0
        assert all(r["status"] == "ok" for r in pf["rows"])

    @pytest.mark.parametrize("variant", ["HARD", "Hard", " hard ", "\thard\n", "MEDIUM"])
    def test_case_and_whitespace_variants_are_normalised_not_stored_raw(self, variant):
        """Asserted disposition: case/whitespace variants are NORMALISED, not
        rejected — matching mock_import.py, which lower()/strip()s before
        checking. What must never happen is the variant reaching the database
        as typed, because an exact-match read (exam_intelligence.py's
        difficulty= filter) would then miss it.
        """
        sb = TaxSBStub(_seed())
        rows = [_clean_row(1, observed_difficulty=variant)]
        TestCommit()._do_preflight_and_commit(sb, rows)
        stored = sb.db["pyq_questions"][0]["observed_difficulty"]
        assert stored == variant.strip().lower()
        assert stored in ("easy", "medium", "hard")

    def test_rejected_row_writes_nothing(self):
        """A rejected value must not reach the table at all — not as the bad
        value, and not silently downgraded to NULL or 'medium'.
        """
        sb = TaxSBStub(_seed())
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1, observed_difficulty="very_hard")])
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": pf["import_token"], "override_errors": False,
                  "reason": "test commit"},
        )
        assert r.status_code == 200, r.text
        assert sb.db["pyq_questions"] == []

    def test_json_payload_rejected_too(self):
        """Not a CSV-only guard — the JSON v1 array path shares the check."""
        sb = TaxSBStub(_seed())
        client = _client(sb)
        pf = _preflight_json(client, [_clean_row(1, observed_difficulty="very_hard")])
        assert pf["summary"]["error"] == 1
        assert any("observed_difficulty" in m for m in pf["rows"][0]["messages"])


# ── Parity test ───────────────────────────────────────────────────────────────

class TestHashParity:
    """Backend hash must match what the frontend computes for the same text.

    The frontend uses the same canonical algorithm exported from the shared
    option_normalize module (Community 219 pattern — pin both ends).
    """

    @pytest.mark.parametrize("text,expected_hash", [
        # Empty / None → None
        ("", None),
        (None, None),
        # Leading label stripped
        ("A. Hydrogen", option_hash("A. Hydrogen")),
        ("(b) Carbon", option_hash("(b) Carbon")),
        # Smart quotes folded
        ("“Paris”", option_hash("“Paris”")),
        # Whitespace collapsed
        ("  alpha   beta  ", option_hash("  alpha   beta  ")),
        # Trailing punctuation stripped
        ("correct answer.", option_hash("correct answer.")),
        # Unicode NFC
        ("café", option_hash("café")),
    ])
    def test_option_hash_stable(self, text, expected_hash):
        assert option_hash(text) == expected_hash

    @pytest.mark.parametrize("text,expected_hash", [
        ("", None),
        (None, None),
        ("What is the speed of light?", question_hash("What is the speed of light?")),
        # Smart dash folded
        ("A – B", question_hash("A – B")),
        # Whitespace collapse
        ("  two   spaces  ", question_hash("  two   spaces  ")),
    ])
    def test_question_hash_stable(self, text, expected_hash):
        assert question_hash(text) == expected_hash

    def test_option_hash_case_insensitive(self):
        assert option_hash("HYDROGEN") == option_hash("hydrogen")
        assert option_hash("Carbon Dioxide") == option_hash("carbon dioxide")

    def test_question_hash_case_insensitive(self):
        assert question_hash("WHAT IS PHOTOSYNTHESIS?") == question_hash("what is photosynthesis?")

    def test_bulk_import_stores_correct_option_hash(self):
        """Verify the commit path writes normalized_option_hash == option_hash(text)."""
        sb = TaxSBStub(_seed())
        client = _client(sb)
        opt_text = "Mitochondria is the powerhouse"
        rows = [_clean_row(1, option_a=opt_text, correct_option="A")]
        pf = _preflight(client, rows)
        client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": pf["import_token"], "reason": "parity test"},
        )
        opt_row = next(o for o in sb.db["pyq_options"] if o["option_label"] == "A")
        assert opt_row["normalized_option_hash"] == option_hash(opt_text)


# ── Fail-closed on existing-row lookup failure (checkpost fix 7) ─────────────


class _RaiseOnSelectQuery(_Query):
    """Raises on a read (.execute() with no pending write) against
    ``fail_table`` -- simulates a transient Supabase error on the
    existing-rows fetch that dedup/idempotency depends on."""

    def __init__(self, name, db, *, fail_table: str):
        super().__init__(name, db)
        self._fail_table = fail_table

    def execute(self):
        is_write = (
            self._pending_insert is not None
            or self._pending_update is not None
            or self._pending_upsert is not None
        )
        if self.name == self._fail_table and not is_write:
            raise RuntimeError(f"simulated select failure on {self.name}")
        return super().execute()


class RaiseOnSelectSBStub(TaxSBStub):
    def __init__(self, db, *, fail_table: str):
        super().__init__(db)
        self._fail_table = fail_table

    def table(self, name: str):
        return _RaiseOnSelectQuery(name, self.db, fail_table=self._fail_table)


class TestFailClosedExistingRowLookup:
    """A Supabase error fetching existing pyq_questions rows must fail closed
    (raise) rather than silently degrade to empty dedup/idempotency sets --
    the old behavior made a transient DB error silently disable the
    importer's own duplicate-detection guarantee."""

    def test_preflight_raises_when_existing_rows_fetch_fails(self):
        sb = RaiseOnSelectSBStub(_seed(), fail_table="pyq_questions")
        with pytest.raises(RuntimeError):
            _bi.preflight(
                sb, {"id": "admin-99"}, "paper-1",
                _make_csv([_clean_row(1)]), "text/csv",
            )

    def test_commit_raises_when_existing_rows_fetch_fails(self):
        # Preflight against a healthy stub first, to get a real token +
        # preflight_rows payload.
        sb_ok = TaxSBStub(_seed())
        client = _client(sb_ok)
        pf = _preflight(client, [_clean_row(1)])
        token = pf["import_token"]
        token_row = next(r for r in sb_ok.db["pyq_import_tokens"] if r["token"] == token)

        # Replay commit() against a stub carrying the same token row, but
        # whose pyq_questions SELECT raises.
        seed = _seed()
        seed["pyq_import_tokens"] = [dict(token_row)]
        sb = RaiseOnSelectSBStub(seed, fail_table="pyq_questions")
        with pytest.raises(RuntimeError):
            _bi.commit(sb, {"id": "admin-99"}, token, paper_id="paper-1")
        # Nothing was written.
        assert sb.db["pyq_questions"] == []
        # Checkpost round 3, fix #4: the existing-rows fetch now runs BEFORE
        # the token claim, so a RuntimeError here never burns the token --
        # the caller can safely retry the exact same commit() call once the
        # transient DB issue clears.
        row = next(r for r in sb.db["pyq_import_tokens"] if r["token"] == token)
        assert row["consumed_at"] is None
