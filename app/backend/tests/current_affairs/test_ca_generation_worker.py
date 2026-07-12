"""ca:generate worker orchestration tests (GQR-G3).

Uses a hand-rolled fake Supabase client (mirrors the EWP evaluation-worker tests):
it returns a claim payload and records every rpc call. No DB — the plpgsql RPCs are
VERIFY DB. The worker's job is to run stages A-D and hand a correct persist payload to
ca_complete_generation; these tests pin that orchestration + shadow/no-authority.
"""
from __future__ import annotations

from app.current_affairs.generation import worker


class _Exec:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return self

    @property
    def data(self):
        return self._data


class FakeSB:
    def __init__(self, responses=None, raise_on=None):
        self._responses = responses or {}
        self._raise_on = raise_on or set()
        self.calls = []
        self.db = {"mock_question_bank": []}

    def rpc(self, name, params=None):
        self.calls.append((name, params or {}))
        if name in self._raise_on:
            raise RuntimeError(f"boom:{name}")
        return _Exec(self._responses.get(name))

    def table(self, name):  # pragma: no cover - guard against accidental table writes
        raise AssertionError(f"worker must not touch tables directly (got {name})")

    def names(self):
        return [n for n, _ in self.calls]

    def params_for(self, name):
        for n, p in self.calls:
            if n == name:
                return p
        raise AssertionError(f"{name} not called")


_CLAIM = {
    "job_id": "job-1",
    "claim_token": "tok-1",
    "job_kind": "ca_generation",
    "document": {
        "id": "doc-1",
        "source_id": "src-1",
        "title": "RBI issues digital lending circular",
        "raw_text": "The Reserve Bank of India issued a digital lending circular on 2026-06-01. "
                    "It sets disclosure norms for regulated entities.",
        "document_type": "press_release",
        "category": "economy",
        "published_at": "2026-06-01",
        "fetched_at": "2026-06-02",
    },
    "source_authority_level": "primary_official",
    "existing_fingerprints": [],
}


def test_idle_when_no_job():
    sb = FakeSB(responses={"ca_claim_generation_job": None})
    out = worker.run_generation_worker_pass(sb)
    assert out == {"processed": 0, "status": "idle"}
    assert sb.names() == ["ca_claim_generation_job"]


def test_full_pass_produces_review_ready_candidate_and_audit():
    sb = FakeSB(responses={
        "ca_claim_generation_job": dict(_CLAIM),
        "ca_complete_generation": {"status": "completed"},
    })
    out = worker.run_generation_worker_pass(sb)
    assert out["status"] == "succeeded"
    assert out["events"] == 1 and out["candidates"] == 1 and out["review_ready"] == 1

    p = sb.params_for("ca_complete_generation")
    assert p["p_job_id"] == "job-1" and p["p_claim_token"] == "tok-1"
    events = p["p_events"]
    assert len(events) == 1
    ev = events[0]
    assert ev["claims"] and ev["claims"][0]["temp_id"] == "e0c0"
    cand = ev["candidates"][0]
    assert cand["status"] == "review_ready", cand["validation_result"]
    assert cand["linked_temp_claim_ids"] == ["e0c0"]
    # Audit lineage (checkpost #966 F1): the candidate carries its own generator +
    # verifier run so the complete RPC can persist candidate-scoped audit rows.
    assert cand["generator_run"]["action"] == "mcq_generation"
    assert cand["verifier_run"]["action"] == "verification"
    # Document-level runs are the Stage-A extraction only (candidate-scoped runs travel
    # on the candidate, not this flat list).
    assert [r["action"] for r in p["p_generation_runs"]] == ["extraction"]


def test_shadow_no_authority_no_promotion():
    # The worker must NEVER promote: only claim + complete are called; the objective
    # bank is untouched and no promotion/publish rpc is invoked.
    sb = FakeSB(responses={
        "ca_claim_generation_job": dict(_CLAIM),
        "ca_complete_generation": {"status": "completed"},
    })
    worker.run_generation_worker_pass(sb)
    assert sb.names() == ["ca_claim_generation_job", "ca_complete_generation"]
    assert sb.db["mock_question_bank"] == []
    assert not any("promote" in n or "publish" in n for n in sb.names())


def test_complete_failure_releases_job_via_fail_rpc():
    sb = FakeSB(
        responses={"ca_claim_generation_job": dict(_CLAIM)},
        raise_on={"ca_complete_generation"},
    )
    out = worker.run_generation_worker_pass(sb)
    assert out["status"] == "failed" and out["job_id"] == "job-1"
    fail = sb.params_for("ca_fail_generation_job")
    assert fail["p_job_id"] == "job-1" and fail["p_claim_token"] == "tok-1"


def test_sweep_delegates_to_rpc():
    sb = FakeSB(responses={"ca_sweep_stale_generation_jobs": 2})
    assert worker.sweep_stale_generation_jobs(sb) == {"swept": 2}
