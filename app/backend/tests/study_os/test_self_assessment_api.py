"""API tests for the hardened self-assessment / calibration surface (PR #778).

Covers the owner-review bugs:
  * PUT verifies submitted subjects against the exam's required calibration set
    (rejects empty / duplicate / foreign / partial submissions).
  * GET derives ``calibrated`` from an explicit ``user_exam_calibration`` gate
    record, NOT from "any evidence row exists".
  * ``band='new'`` evidence rows persist (prior_mastery None).
  * Server owns the band→prior_mastery and attempts→report_confidence mapping.
  * POST /self-assessment/skip writes a 'skipped' gate.

Mirrors the existing harness (SBStub + FastAPI TestClient) used across
``tests/study_os``.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

# Stable UUIDs so BandItem.subject_id (typed UUID) validates and the stub's
# strict-equality filters line up.
EXAM_ID = "11111111-1111-4111-8111-111111111111"
S_QUANT = "22222222-2222-4222-8222-222222222221"
S_ENG = "22222222-2222-4222-8222-222222222222"
S_GK = "22222222-2222-4222-8222-222222222223"
T_QUANT = "33333333-3333-4333-8333-333333333331"
T_ENG = "33333333-3333-4333-8333-333333333332"
T_GK = "33333333-3333-4333-8333-333333333333"
FOREIGN_SUBJECT = "44444444-4444-4444-8444-444444444444"


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    # resolve_exam_by_slug/by_id memoise in a module-level cache; clear it so a
    # unique-per-test exam row is never shadowed by a sibling test.
    import app.exam_intelligence.lookup as lookup

    lookup._EXAM_CACHE.clear()
    yield
    lookup._EXAM_CACHE.clear()


def _app(sb: SBStub, user_id: str = "u-1") -> FastAPI:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app


def _client(sb: SBStub, user_id: str = "u-1") -> TestClient:
    return TestClient(_app(sb, user_id))


def _seed(*, locked_subjects=("quant", "eng"), unique_slug: str | None = None) -> dict:
    """Seed an exam whose locked coverage spans the given subjects.

    ``locked_subjects`` picks among quant/eng/gk; each maps to one locked
    coverage topic in its own subject. No validated mastery by default → every
    such subject is REQUIRED.
    """
    slug = unique_slug or f"exam-{uuid.uuid4().hex[:8]}"
    sub_map = {
        "quant": (S_QUANT, T_QUANT, "Quantitative Aptitude"),
        "eng": (S_ENG, T_ENG, "English"),
        "gk": (S_GK, T_GK, "General Knowledge"),
    }
    coverage = []
    topics = []
    subjects = []
    for key in locked_subjects:
        sid, tid, name = sub_map[key]
        coverage.append({
            "id": f"cov-{key}",
            "exam_id": EXAM_ID,
            "topic_id": tid,
            "reviewer_status": "locked",
        })
        topics.append({"id": tid, "subject_id": sid, "name": name, "is_active": True})
        subjects.append({"id": sid, "name": name})

    return {
        "profiles": [{"id": "u-1", "target_exam": slug}],
        "exams": [{"id": EXAM_ID, "slug": slug, "name": "Test Exam", "is_active": True}],
        "exam_topic_coverage": coverage,
        "topics": topics,
        "subjects": subjects,
    }


# ── server-side derivation constants (mirror of the endpoint mapping) ─────────
from app.api.study_os import _BAND_TO_PRIOR_MASTERY, _report_confidence_from_attempts


# ─────────────────────────────── PUT validation ─────────────────────────────

def test_put_rejects_empty_bands():
    sb = SBStub(_seed())
    r = _client(sb).put("/api/study/self-assessment", json={"bands": [], "attempts_used": 0})
    assert r.status_code == 422
    assert "No bands submitted" in r.json()["detail"]
    # no evidence, no gate written
    assert sb.db.get("user_topic_self_assessment", []) == []
    assert sb.db.get("user_exam_calibration", []) == []


def test_put_rejects_duplicate_subject():
    sb = SBStub(_seed())
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={
            "bands": [
                {"subject_id": S_QUANT, "band": "strong"},
                {"subject_id": S_QUANT, "band": "weak"},
            ],
            "attempts_used": 0,
        },
    )
    assert r.status_code == 422
    assert "Duplicate subject" in r.json()["detail"]
    assert sb.db.get("user_topic_self_assessment", []) == []


def test_put_rejects_foreign_subject_not_in_required_set():
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": FOREIGN_SUBJECT, "band": "strong"}], "attempts_used": 0},
    )
    assert r.status_code == 422
    assert "is not part of this exam's calibration set" in r.json()["detail"]
    assert sb.db.get("user_topic_self_assessment", []) == []
    assert sb.db.get("user_exam_calibration", []) == []


def test_put_no_target_exam_returns_422():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_QUANT, "band": "strong"}], "attempts_used": 0},
    )
    assert r.status_code == 422


# ─────────────────────────── PUT partial vs full set ────────────────────────

def test_put_partial_required_set_not_calibrated_no_gate():
    """Submitting only some required subjects → calibrated False, NO gate row."""
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_QUANT, "band": "strong"}], "attempts_used": 0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["calibrated"] is False
    assert body["missing_subject_ids"] == [S_ENG]
    assert body["upserted_count"] == 1
    # evidence written, but gate NOT written
    assert len(sb.db.get("user_topic_self_assessment", [])) == 1
    assert sb.db.get("user_exam_calibration", []) == []


def test_put_full_required_set_writes_completed_gate():
    """Answering the full required set → completed gate w/ hash + attempts."""
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={
            "bands": [
                {"subject_id": S_QUANT, "band": "strong"},
                {"subject_id": S_ENG, "band": "decent"},
            ],
            "attempts_used": 2,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["calibrated"] is True
    assert body["missing_subject_ids"] == []

    cal = sb.db.get("user_exam_calibration", [])
    assert len(cal) == 1
    row = cal[0]
    assert row["status"] == "completed"
    assert row["attempts_used"] == 2
    assert row["completed_at"] is not None
    # hash is the sha256 of the sorted required subject set
    from app.api.study_os import _required_subject_set_hash
    assert row["required_subject_set_hash"] == _required_subject_set_hash([S_QUANT, S_ENG])


def test_put_completes_gate_across_two_calls():
    """Existing evidence from a prior call counts toward the required set."""
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    client = _client(sb)
    r1 = client.put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_QUANT, "band": "strong"}], "attempts_used": 1},
    )
    assert r1.json()["calibrated"] is False
    assert sb.db.get("user_exam_calibration", []) == []

    r2 = client.put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_ENG, "band": "weak"}], "attempts_used": 1},
    )
    assert r2.json()["calibrated"] is True
    assert r2.json()["missing_subject_ids"] == []
    assert sb.db["user_exam_calibration"][0]["status"] == "completed"


# ───────────────────────── evidence persistence / derivation ────────────────

def test_put_band_new_persists_with_null_prior():
    sb = SBStub(_seed(locked_subjects=("quant",)))
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_QUANT, "band": "new"}], "attempts_used": 0},
    )
    assert r.status_code == 200
    rows = sb.db.get("user_topic_self_assessment", [])
    assert len(rows) == 1
    assert rows[0]["band"] == "new"
    assert rows[0]["prior_mastery"] is None


def test_server_derives_prior_and_confidence_client_cannot_set_them():
    """Client submits band + attempts only; server fills prior_mastery and
    report_confidence from its own mapping (even if a client tried to inject
    other fields, the body model ignores them)."""
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={
            "bands": [
                # extra junk fields are ignored by the Pydantic model
                {"subject_id": S_QUANT, "band": "strong", "prior_mastery": 1.0, "report_confidence": 0.0},
                {"subject_id": S_ENG, "band": "weak"},
            ],
            "attempts_used": 1,
        },
    )
    assert r.status_code == 200
    rows = {row["subject_id"]: row for row in sb.db["user_topic_self_assessment"]}

    assert rows[S_QUANT]["prior_mastery"] == _BAND_TO_PRIOR_MASTERY["strong"]
    assert rows[S_ENG]["prior_mastery"] == _BAND_TO_PRIOR_MASTERY["weak"]
    # attempts_used=1 → report_confidence 0.75 for every row
    expected_conf = _report_confidence_from_attempts(1)
    assert rows[S_QUANT]["report_confidence"] == expected_conf
    assert rows[S_ENG]["report_confidence"] == expected_conf
    assert rows[S_QUANT]["source"] == "onboarding_self_report"


# ─────────────────────────────── GET calibration ────────────────────────────

def test_get_not_calibrated_when_evidence_exists_but_no_gate():
    """THE CORE BUG: evidence rows present but no gate record → calibrated False."""
    seed = _seed(locked_subjects=("quant", "eng"))
    seed["user_topic_self_assessment"] = [
        {
            "id": "sa-1", "user_id": "u-1", "exam_id": EXAM_ID, "subject_id": S_QUANT,
            "topic_id": None, "band": "strong", "prior_mastery": 80.0,
            "report_confidence": 0.5, "attempts_used": 0, "source": "onboarding_self_report",
        }
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is False
    assert body["status"] == "none"
    # evidence still surfaced for prefill
    assert len(body["items"]) == 1
    assert body["items"][0]["subject_id"] == S_QUANT


def test_get_calibrated_true_after_completed_gate():
    seed = _seed(locked_subjects=("quant", "eng"))
    from app.api.study_os import _required_subject_set_hash
    seed["user_exam_calibration"] = [
        {
            "id": "cal-1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "completed",
            "required_subject_set_hash": _required_subject_set_hash([S_QUANT, S_ENG]),
            "attempts_used": 2, "completed_at": "2026-06-01T00:00:00+00:00",
        }
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is True
    assert body["status"] == "completed"
    assert body["needs_update"] is False
    assert body["attempts_used"] == 2
    # required subjects sorted by subject_id
    assert [s["subject_id"] for s in body["required_subjects"]] == sorted([S_QUANT, S_ENG])


def test_get_status_reflects_skipped_gate():
    seed = _seed(locked_subjects=("quant", "eng"))
    seed["user_exam_calibration"] = [
        {
            "id": "cal-1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "skipped",
            "required_subject_set_hash": "stale-or-current", "attempts_used": None,
        }
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is True
    assert body["status"] == "skipped"


def test_get_needs_update_when_hash_differs():
    seed = _seed(locked_subjects=("quant", "eng"))
    seed["user_exam_calibration"] = [
        {
            "id": "cal-1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "completed",
            "required_subject_set_hash": "OLD-HASH-DOES-NOT-MATCH",
            "attempts_used": 1, "completed_at": "2026-06-01T00:00:00+00:00",
        }
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is True
    assert body["needs_update"] is True


def test_get_no_target_exam_returns_empty_contract():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body == {
        "exam_id": None,
        "calibrated": False,
        "status": "none",
        "needs_update": False,
        "required_subjects": [],
        "items": [],
        "attempts_used": None,
    }


def test_get_required_empty_means_calibrated_true():
    """Every locked topic already has validated mastery → nothing to calibrate
    → calibrated True automatically, even with no gate record."""
    seed = _seed(locked_subjects=("quant", "eng"))
    seed["user_topic_mastery"] = [
        {"id": "m1", "user_id": "u-1", "topic_id": T_QUANT, "mastery_score": 70.0},
        {"id": "m2", "user_id": "u-1", "topic_id": T_ENG, "mastery_score": 65.0},
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["required_subjects"] == []
    assert body["calibrated"] is True
    assert body["status"] == "completed"
    assert body["needs_update"] is False


def test_required_set_excludes_fully_validated_subject_only():
    """A subject is required only if at least ONE locked topic lacks validated
    mastery. A subject with one validated + one unvalidated locked topic stays
    required."""
    slug = f"exam-{uuid.uuid4().hex[:8]}"
    sb = SBStub({
        "profiles": [{"id": "u-1", "target_exam": slug}],
        "exams": [{"id": EXAM_ID, "slug": slug, "name": "Test Exam", "is_active": True}],
        "exam_topic_coverage": [
            {"id": "c1", "exam_id": EXAM_ID, "topic_id": T_QUANT, "reviewer_status": "locked"},
            {"id": "c2", "exam_id": EXAM_ID, "topic_id": "t-quant-2", "reviewer_status": "locked"},
            {"id": "c3", "exam_id": EXAM_ID, "topic_id": T_ENG, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": T_QUANT, "subject_id": S_QUANT, "name": "Q1"},
            {"id": "t-quant-2", "subject_id": S_QUANT, "name": "Q2"},
            {"id": T_ENG, "subject_id": S_ENG, "name": "E1"},
        ],
        "subjects": [
            {"id": S_QUANT, "name": "Quant"},
            {"id": S_ENG, "name": "English"},
        ],
        # English fully validated → dropped. Quant has one validated (T_QUANT)
        # and one unvalidated (t-quant-2) → stays required.
        "user_topic_mastery": [
            {"id": "m1", "user_id": "u-1", "topic_id": T_QUANT, "mastery_score": 70.0},
            {"id": "m2", "user_id": "u-1", "topic_id": T_ENG, "mastery_score": 65.0},
        ],
    })
    body = _client(sb).get("/api/study/self-assessment").json()
    assert [s["subject_id"] for s in body["required_subjects"]] == [S_QUANT]


# ─────────────────────────────── POST skip ──────────────────────────────────

def test_skip_writes_skipped_gate_then_get_calibrated():
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    client = _client(sb)
    r = client.post("/api/study/self-assessment/skip", json={"attempts_used": 3})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "calibrated": True, "status": "skipped"}

    cal = sb.db.get("user_exam_calibration", [])
    assert len(cal) == 1
    assert cal[0]["status"] == "skipped"
    assert cal[0]["attempts_used"] == 3

    body = client.get("/api/study/self-assessment").json()
    assert body["calibrated"] is True
    assert body["status"] == "skipped"


def test_skip_without_body_defaults_attempts_none():
    sb = SBStub(_seed(locked_subjects=("quant",)))
    r = _client(sb).post("/api/study/self-assessment/skip")
    assert r.status_code == 200
    cal = sb.db["user_exam_calibration"][0]
    assert cal["status"] == "skipped"
    assert cal["attempts_used"] is None


def test_skip_no_target_exam_returns_422():
    sb = SBStub({"profiles": [{"id": "u-1", "target_exam": None}]})
    r = _client(sb).post("/api/study/self-assessment/skip", json={})
    assert r.status_code == 422


# ───────────────── GET grandfather: existing-plan user, no gate ──────────────

def test_get_existing_plan_user_no_gate_is_calibrated():
    """FIX D: a user who already generated a first plan (existing study_plans
    row for this exam) but has NO calibration gate must NOT be reported
    uncalibrated — otherwise the migration retroactively blocks them. The
    required set is non-empty here; the existing plan grandfathers them."""
    seed = _seed(locked_subjects=("quant", "eng"))
    seed["study_plans"] = [
        {"id": "p-1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "active"}
    ]
    sb = SBStub(seed)
    body = _client(sb).get("/api/study/self-assessment").json()
    # required set is genuinely non-empty (neither subject has validated mastery)
    assert [s["subject_id"] for s in body["required_subjects"]] == sorted([S_QUANT, S_ENG])
    assert body["calibrated"] is True
    # no explicit gate → status stays "none", needs_update only meaningful w/ a gate
    assert body["status"] == "none"
    assert body["needs_update"] is False


def test_get_no_plan_no_gate_is_not_calibrated():
    """Counterpart to the grandfather: without an existing plan AND without a
    gate, a non-empty required set is still uncalibrated."""
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is False
    assert body["status"] == "none"


# ─────────────── PUT normalization across multi-call completion ──────────────

def test_put_normalizes_attempts_and_confidence_across_two_calls():
    """FIX E: the required set may be answered over several PUTs. The attempts
    answer is exam-level, so the LATEST submission must apply uniformly — every
    evidence row for the (user, exam) ends with the final attempts_used and the
    matching report_confidence, not the per-call value it was first written with.
    """
    sb = SBStub(_seed(locked_subjects=("quant", "eng")))
    client = _client(sb)

    # First call: Quant @ attempts_used=0 → report_confidence 0.5.
    r1 = client.put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_QUANT, "band": "strong"}], "attempts_used": 0},
    )
    assert r1.status_code == 200
    # Second call: English (disjoint) @ attempts_used=2 → report_confidence 1.0.
    r2 = client.put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_ENG, "band": "decent"}], "attempts_used": 2},
    )
    assert r2.status_code == 200
    assert r2.json()["calibrated"] is True

    rows = sb.db["user_topic_self_assessment"]
    assert len(rows) == 2
    final_conf = _report_confidence_from_attempts(2)
    # EVERY row — including the Quant row written in the first call — now carries
    # the latest exam-level attempts answer and its derived confidence.
    for row in rows:
        assert row["attempts_used"] == 2
        assert row["report_confidence"] == final_conf
    # The completed gate also records the latest attempts answer.
    cal = sb.db["user_exam_calibration"][0]
    assert cal["status"] == "completed"
    assert cal["attempts_used"] == 2


def test_put_partial_submission_still_normalizes_existing_rows():
    """Normalization rewrites the user's prior evidence rows to the latest
    exam-level attempts answer, even when only a strict subset is submitted now.

    Here a single unanswered required subject (English) is needed, while Quant
    already has stale evidence; submitting English completes the set and the
    stale Quant row is normalized to the new attempts answer rather than keeping
    its old attempts_used=0 / confidence 0.5."""
    seed = _seed(locked_subjects=("quant", "eng"))
    # Pre-existing Quant evidence with stale attempts_used=0 / confidence 0.5.
    seed["user_topic_self_assessment"] = [
        {
            "id": "sa-old", "user_id": "u-1", "exam_id": EXAM_ID, "subject_id": S_QUANT,
            "topic_id": None, "band": "weak", "prior_mastery": 35.0,
            "report_confidence": 0.5, "attempts_used": 0, "source": "onboarding_self_report",
        }
    ]
    sb = SBStub(seed)
    # Submit only English @ attempts_used=1; Quant is supplied by the stale row.
    r = _client(sb).put(
        "/api/study/self-assessment",
        json={"bands": [{"subject_id": S_ENG, "band": "decent"}], "attempts_used": 1},
    )
    assert r.status_code == 200

    final_conf = _report_confidence_from_attempts(1)
    rows = {row["subject_id"]: row for row in sb.db["user_topic_self_assessment"]}
    # The stale Quant row was normalized to the latest attempts answer too.
    assert rows[S_QUANT]["attempts_used"] == 1
    assert rows[S_QUANT]["report_confidence"] == final_conf
    assert rows[S_ENG]["attempts_used"] == 1
    assert rows[S_ENG]["report_confidence"] == final_conf
