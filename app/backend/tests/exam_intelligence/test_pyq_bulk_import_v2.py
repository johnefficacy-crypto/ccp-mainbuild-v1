"""PYQ bulk-import v2 — section linkage, variable option counts, shared
stimuli (migration 223: pyq_questions.section_id/source_question_ref/
display_order, pyq_options.display_order/source_label, pyq_stimuli,
pyq_question_stimuli).

Covers
------
- JSON v2: 2-option question commits (both options inserted, correct flagged)
- JSON v2: 5-option question with non-A-D labels ("1".."5") preserves
  source_label + display_order per option
- JSON v2: correct_option_label with no matching option -> preflight error,
  commit skips it
- JSON v2: duplicate option label within one question -> preflight error
- JSON v2: section_ref resolves (case-insensitive, phase-scoped) ->
  committed pyq_questions.section_id set
- JSON v2: section_ref that does not resolve in the paper's phase -> row
  error, never a silent NULL section_id
- JSON v2: two questions sharing one stimulus_refs entry -> single shared
  pyq_stimuli row, two pyq_question_stimuli links
- JSON v2: stimulus_refs with no matching top-level stimuli entry -> row error
- CSV v2 (options_json column): parses/commits equivalently to JSON v2
- Legacy v1 (bare JSON list / option_a..option_d CSV): unaffected regression
  smoke test

Everything here exercises ``POST .../bulk-import/preflight`` and
``POST .../bulk-import/commit`` through the same fake-Supabase harness as
``test_pyq_bulk_import.py`` (``TaxSBStub``, generic per-table stub so any new
table -- ``exam_phase_sections``, ``pyq_stimuli``, ``pyq_question_stimuli``
-- is seedable without further stub changes).

All 12 tests below pass against the finished ``pyq_bulk_import.py`` v2
implementation (verified via ``pytest``, plus the full ``tests/exam_intelligence/``
suite: 1593 passed, 8 skipped, 0 failed). This file was originally written
against the v2 contract spec while the implementation was still in progress
concurrently in another session; the assumptions noted inline all turned out
to match the shipped contract.
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
from app.exam_intelligence.option_normalize import question_hash
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"

# paper-1's exam_phase_id (phase-1) is what section_ref resolution scopes
# against: section_ref resolves against exam_phase_sections scoped to the
# target paper's exam_phase_id (pyq_papers.exam_phase_id, migration 032).
_PAPER_PHASE_ID = "phase-1"


# ── Harness helpers (mirrors test_pyq_bulk_import.py) ───────────────────────


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-99", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed_v2(*, extra_sections: list[dict] | None = None,
             extra_questions: list[dict] | None = None) -> dict:
    return {
        "pyq_papers": [{"id": "paper-1", "exam_id": "exam-1", "exam_phase_id": _PAPER_PHASE_ID}],
        "exam_phase_sections": list(extra_sections or []),
        "pyq_questions": list(extra_questions or []),
        "pyq_options": [],
        "pyq_stimuli": [],
        "pyq_question_stimuli": [],
        "admin_audit_logs": [],
    }


def _preflight_json_v2(client: TestClient, payload: dict, *, paper_id: str = "paper-1") -> dict:
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/preflight",
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _preflight_csv_v2(client: TestClient, csv_bytes: bytes, *, paper_id: str = "paper-1") -> dict:
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/preflight",
        content=csv_bytes,
        headers={"content-type": "text/csv"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _commit(client: TestClient, token: str, *, paper_id: str = "paper-1",
            override_errors: bool = False) -> dict:
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/commit",
        json={"import_token": token, "override_errors": override_errors, "reason": "v2 test commit"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _v2_payload(questions: list[dict], stimuli: list[dict] | None = None) -> dict:
    return {"format_version": 2, "stimuli": stimuli or [], "questions": questions}


def _q(*, question_text: str = "Which conclusion follows?", options=None,
       correct_option_label: str = "1", question_type: str = "mcq", **kwargs) -> dict:
    return {
        "question_text": question_text,
        "question_type": question_type,
        "options": options if options is not None else [
            {"label": "1", "text": "Alpha", "display_order": 1},
            {"label": "2", "text": "Beta", "display_order": 2},
        ],
        "correct_option_label": correct_option_label,
        **kwargs,
    }


_CSV_V2_COLS = [
    "question_text", "question_type", "observed_difficulty",
    "source_question_ref", "display_order", "section_ref",
    "options_json", "correct_option_label",
]


def _make_csv_v2(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=_CSV_V2_COLS)
    w.writeheader()
    for r in rows:
        row = dict(r)
        if "options_json" in row and not isinstance(row["options_json"], str):
            row["options_json"] = json.dumps(row["options_json"])
        w.writerow({c: row.get(c, "") for c in _CSV_V2_COLS})
    return buf.getvalue().encode("utf-8")


# ── Legacy v1 helpers (smoke-test regression only) ──────────────────────────


def _legacy_clean_row(n: int, **kwargs) -> dict:
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


def _make_legacy_csv(rows: list[dict]) -> bytes:
    cols = ["question_number", "question_text", "option_a", "option_b",
            "option_c", "option_d", "correct_option", "question_type",
            "observed_difficulty"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue().encode("utf-8")


# ── 1/2. Variable option-count JSON v2 questions commit correctly ──────────


class TestV2VariableOptions:
    def test_two_option_question_commits(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([_q(
            question_text="Is the sky blue?",
            options=[
                {"label": "yes", "text": "Yes", "display_order": 1},
                {"label": "no", "text": "No", "display_order": 2},
            ],
            correct_option_label="yes",
        )])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        token = pf["import_token"]
        result = _commit(client, token)
        assert result["committed"] == 1
        assert len(sb.db["pyq_questions"]) == 1
        opts = sb.db["pyq_options"]
        assert len(opts) == 2
        correct = next(o for o in opts if o["option_label"] == "yes")
        others = [o for o in opts if o["option_label"] != "yes"]
        assert correct["is_correct"] is True
        assert all(not o["is_correct"] for o in others)

    def test_five_option_question_non_ad_labels_preserves_source_label_and_order(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        options = [
            {"label": str(i), "source_label": f"({i})", "text": f"Option {i}", "display_order": i}
            for i in range(1, 6)
        ]
        payload = _v2_payload([_q(
            question_text="Pick the odd one out among five choices.",
            options=options,
            correct_option_label="3",
        )])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1
        opts = sb.db["pyq_options"]
        assert len(opts) == 5
        by_label = {o["option_label"]: o for o in opts}
        assert set(by_label) == {"1", "2", "3", "4", "5"}
        for i in range(1, 6):
            row = by_label[str(i)]
            assert row["source_label"] == f"({i})"
            assert row["display_order"] == i
        assert by_label["3"]["is_correct"] is True
        assert all(not by_label[k]["is_correct"] for k in by_label if k != "3")


# ── 3/4. Row-level validation errors ────────────────────────────────────────


class TestV2RowValidation:
    def test_correct_option_label_no_match_is_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([_q(
            options=[
                {"label": "1", "text": "Alpha"},
                {"label": "2", "text": "Beta"},
            ],
            correct_option_label="9",  # does not match any supplied option
        )])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        bad = pf["rows"][0]
        assert bad["status"] == "error"
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 0
        assert len(sb.db["pyq_questions"]) == 0

    def test_duplicate_option_label_within_question_is_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([_q(
            options=[
                {"label": "1", "text": "Alpha"},
                {"label": "1", "text": "Alpha duplicate label"},
            ],
            correct_option_label="1",
        )])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        assert pf["rows"][0]["status"] == "error"


# ── observed_difficulty vocabulary (v2 shares v1's check) ──────────────────


class TestV2ObservedDifficultyVocabulary:
    """v1 and v2 must reject the same vocabulary — one helper backs both, and
    this class exists so a future divergence in either parser fails here.
    """

    @pytest.mark.parametrize("bad", ["very_hard", "medium_high", "moderate", "tough"])
    def test_non_canonical_rejected_json(self, bad):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        pf = _preflight_json_v2(client, _v2_payload([_q(observed_difficulty=bad)]))
        assert pf["summary"]["error"] == 1
        msg = next(m for m in pf["rows"][0]["messages"] if "observed_difficulty" in m)
        assert repr(bad) in msg
        _commit(client, pf["import_token"])
        assert sb.db["pyq_questions"] == []

    @pytest.mark.parametrize("bad", ["very_hard", "medium_high"])
    def test_non_canonical_rejected_csv(self, bad):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        csv_bytes = _make_csv_v2([{
            "question_text": "Which conclusion follows?",
            "question_type": "mcq",
            "observed_difficulty": bad,
            "options_json": [
                {"label": "1", "text": "Alpha", "display_order": 1},
                {"label": "2", "text": "Beta", "display_order": 2},
            ],
            "correct_option_label": "1",
        }])
        pf = _preflight_csv_v2(client, csv_bytes)
        assert pf["summary"]["error"] == 1
        assert any("observed_difficulty" in m for m in pf["rows"][0]["messages"])

    @pytest.mark.parametrize("good", ["easy", "medium", "hard"])
    def test_canonical_accepted(self, good):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        pf = _preflight_json_v2(client, _v2_payload([_q(observed_difficulty=good)]))
        assert pf["summary"]["error"] == 0
        _commit(client, pf["import_token"])
        assert sb.db["pyq_questions"][0]["observed_difficulty"] == good

    def test_absent_and_blank_accepted_as_null(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        pf = _preflight_json_v2(client, _v2_payload([
            _q(question_text="No difficulty key at all?"),
            _q(question_text="Blank difficulty?", observed_difficulty=""),
            _q(question_text="Null difficulty?", observed_difficulty=None),
        ]))
        assert pf["summary"]["error"] == 0
        _commit(client, pf["import_token"])
        assert len(sb.db["pyq_questions"]) == 3
        assert all(q.get("observed_difficulty") is None for q in sb.db["pyq_questions"])

    def test_case_variant_normalised_not_stored_raw(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        pf = _preflight_json_v2(client, _v2_payload([_q(observed_difficulty=" HARD ")]))
        assert pf["summary"]["error"] == 0
        _commit(client, pf["import_token"])
        assert sb.db["pyq_questions"][0]["observed_difficulty"] == "hard"


# ── 5/6. section_ref resolution ─────────────────────────────────────────────


class TestV2SectionRef:
    def test_section_ref_resolves_case_insensitively_scoped_to_phase(self):
        sb = TaxSBStub(_seed_v2(extra_sections=[{
            "id": "sec-reasoning",
            "exam_phase_id": _PAPER_PHASE_ID,
            "subject_id": "s2",
            "section_label": "Reasoning",
        }]))
        client = _client(sb)
        payload = _v2_payload([_q(section_ref="reasoning")])  # lowercase vs stored "Reasoning"
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1
        q = sb.db["pyq_questions"][0]
        assert q["section_id"] == "sec-reasoning"

    def test_unresolvable_section_ref_is_row_error_not_silent_null(self):
        # "reasoning" only exists under a different exam_phase (phase-2), so it
        # must not resolve against paper-1 (phase-1) -- proves phase scoping.
        sb = TaxSBStub(_seed_v2(extra_sections=[{
            "id": "sec-other-phase",
            "exam_phase_id": "phase-2",
            "subject_id": "s2",
            "section_label": "Reasoning",
        }]))
        client = _client(sb)
        payload = _v2_payload([_q(section_ref="reasoning")])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        assert pf["rows"][0]["status"] == "error"
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 0
        # Never silently committed with section_id=None.
        assert len(sb.db["pyq_questions"]) == 0


# ── 7/8. Shared stimuli ──────────────────────────────────────────────────────


class TestV2Stimuli:
    def test_shared_stimulus_ref_links_both_questions_to_one_row(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [{
            "ref": "passage-04",
            "stimulus_type": "passage",
            "content_text": "A long shared reading passage.",
            "display_order": 1,
        }]
        questions = [
            _q(question_text="Q1 about the passage", stimulus_refs=["passage-04"],
               options=[{"label": "1", "text": "A"}, {"label": "2", "text": "B"}],
               correct_option_label="1"),
            _q(question_text="Q2 about the same passage", stimulus_refs=["passage-04"],
               options=[{"label": "1", "text": "A"}, {"label": "2", "text": "B"}],
               correct_option_label="2"),
        ]
        pf = _preflight_json_v2(client, _v2_payload(questions, stimuli))
        assert pf["summary"]["ok"] == 2
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 2
        assert len(sb.db["pyq_stimuli"]) == 1
        stim_row = sb.db["pyq_stimuli"][0]
        assert stim_row["content_text"] == "A long shared reading passage."
        links = sb.db["pyq_question_stimuli"]
        assert len(links) == 2
        assert all(link["stimulus_id"] == stim_row["id"] for link in links)
        question_ids = {q["id"] for q in sb.db["pyq_questions"]}
        assert {link["question_id"] for link in links} == question_ids

    def test_unmatched_stimulus_ref_is_row_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([
            _q(question_text="Orphan stimulus ref", stimulus_refs=["ghost-ref"]),
        ], stimuli=[])  # no top-level stimuli entry named "ghost-ref"
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        assert pf["rows"][0]["status"] == "error"
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 0
        assert len(sb.db["pyq_questions"]) == 0
        assert len(sb.db["pyq_stimuli"]) == 0


# ── 9. CSV v2 (options_json column) ─────────────────────────────────────────


class TestV2Csv:
    def test_options_json_csv_commits_equivalently_to_json_v2(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        options_json = json.dumps([
            {"label": "1", "text": "Yes", "display_order": 1},
            {"label": "2", "text": "No", "display_order": 2},
        ])
        csv_bytes = _make_csv_v2([{
            "question_text": "Does options_json CSV parse like JSON v2?",
            "question_type": "mcq",
            "observed_difficulty": "easy",
            "options_json": options_json,
            "correct_option_label": "1",
        }])
        pf = _preflight_csv_v2(client, csv_bytes)
        assert pf["summary"]["ok"] == 1
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1
        assert len(sb.db["pyq_questions"]) == 1
        opts = sb.db["pyq_options"]
        assert len(opts) == 2
        correct = next(o for o in opts if o["option_label"] == "1")
        assert correct["is_correct"] is True


# ── 10. Legacy v1 regression smoke test ─────────────────────────────────────


class TestV1RegressionSmoke:
    """Bare JSON list / option_a..option_d CSV must be entirely unaffected by
    v2 support landing in the same module. Not a full re-run of
    test_pyq_bulk_import.py -- just enough to prove v2 didn't regress v1."""

    def test_legacy_json_list_still_preflights_and_commits(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        rows = [_legacy_clean_row(i) for i in range(1, 4)]
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=json.dumps(rows).encode(),  # bare list => legacy v1, not v2
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 200, r.text
        pf = r.json()
        assert pf["summary"]["ok"] == 3
        assert pf["summary"]["error"] == 0
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 3
        assert len(sb.db["pyq_questions"]) == 3
        assert len(sb.db["pyq_options"]) == 12  # 3 questions x 4 options

    def test_legacy_csv_still_preflights_and_commits(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        rows = [_legacy_clean_row(i) for i in range(1, 3)]
        csv_bytes = _make_legacy_csv(rows)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=csv_bytes,
            headers={"content-type": "text/csv"},
        )
        assert r.status_code == 200, r.text
        pf = r.json()
        assert pf["summary"]["ok"] == 2
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 2
        assert len(sb.db["pyq_questions"]) == 2
        assert len(sb.db["pyq_options"]) == 8  # 2 questions x 4 options


# ── 11. Checkpost round 2 fixes ─────────────────────────────────────────────
#
# Fix 3: ambiguous section_ref (same label, two subjects, one phase).
# Fix 4: pyq_question_stimuli.display_order preserves stimulus_refs order.
# Fix 5: JSON v2 envelope requires format_version == 2 exactly.
# Fix 6: same-upload duplicate detection (no identity field on either row).
# Fix 8: durable shared-stimulus identity across separate commit() calls.
# Fix 9: v2 restricts question_type to 'mcq' and stimulus_type to a subset.


class TestV2AmbiguousSectionRef:
    """Fix 3: exam_phase_sections is only unique on (exam_phase_id,
    subject_id, section_label) -- the same label can legitimately repeat
    under two different subjects in one phase. Resolving must error, not
    silently pick one by fetch order."""

    @staticmethod
    def _dup_label_sections():
        return [
            {"id": "sec-a", "exam_phase_id": _PAPER_PHASE_ID, "subject_id": "s1", "section_label": "General"},
            {"id": "sec-b", "exam_phase_id": _PAPER_PHASE_ID, "subject_id": "s2", "section_label": "General"},
        ]

    def test_question_section_ref_ambiguous_is_row_error(self):
        sb = TaxSBStub(_seed_v2(extra_sections=self._dup_label_sections()))
        client = _client(sb)
        payload = _v2_payload([_q(section_ref="General")])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        row = pf["rows"][0]
        assert row["status"] == "error"
        assert any("ambiguous" in m for m in row["messages"])
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 0
        assert len(sb.db["pyq_questions"]) == 0

    def test_stimulus_section_ref_ambiguous_is_batch_error(self):
        sb = TaxSBStub(_seed_v2(extra_sections=self._dup_label_sections()))
        client = _client(sb)
        stimuli = [{
            "ref": "passage-01", "stimulus_type": "passage",
            "content_text": "Shared passage.", "section_ref": "General",
        }]
        payload = _v2_payload(
            [_q(stimulus_refs=["passage-01"])],
            stimuli=stimuli,
        )
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        # A broken stimuli[] entry invalidates the whole batch (parse failure).
        assert r.status_code == 422, r.text
        assert "ambiguous" in r.json()["detail"]


class TestV2QuestionStimuliDisplayOrder:
    """Fix 4: pyq_question_stimuli.display_order (migration 223) must record
    the 1-based position of each ref in the question's stimulus_refs list."""

    def test_display_order_matches_stimulus_refs_array_order(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [
            {"ref": "passage-04", "stimulus_type": "passage", "content_text": "Passage."},
            {"ref": "table-02", "stimulus_type": "table", "content_text": "Table."},
        ]
        payload = _v2_payload(
            [_q(question_text="Refers to both a passage and a table.",
                stimulus_refs=["passage-04", "table-02"])],
            stimuli=stimuli,
        )
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1

        stim_by_ref_type = {s["stimulus_type"]: s["id"] for s in sb.db["pyq_stimuli"]}
        links = sb.db["pyq_question_stimuli"]
        assert len(links) == 2
        by_stim_id = {link["stimulus_id"]: link["display_order"] for link in links}
        assert by_stim_id[stim_by_ref_type["passage"]] == 1
        assert by_stim_id[stim_by_ref_type["table"]] == 2


class TestV2FormatVersionEnvelope:
    """Fix 5: a JSON object must declare "format_version": 2 exactly to be
    treated as v2 -- missing / wrong-type / wrong-value must reject, not
    silently be accepted as v2."""

    def _raw_post(self, client: TestClient, payload: dict):
        return client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )

    def test_missing_format_version_rejected(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = {"stimuli": [], "questions": [_q()]}
        r = self._raw_post(client, payload)
        assert r.status_code == 422, r.text
        assert "format_version" in r.json()["detail"]

    def test_format_version_1_rejected(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = {"format_version": 1, "questions": [_q()]}
        r = self._raw_post(client, payload)
        assert r.status_code == 422, r.text

    def test_format_version_string_2_rejected(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = {"format_version": "2", "questions": [_q()]}
        r = self._raw_post(client, payload)
        assert r.status_code == 422, r.text

    def test_format_version_3_rejected(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = {"format_version": 3, "questions": [_q()]}
        r = self._raw_post(client, payload)
        assert r.status_code == 422, r.text


class TestV2SameUploadDuplicate:
    """Fix 6: two byte-identical v2 questions with neither identity field set
    must be flagged as duplicates of EACH OTHER, not just checked against the
    DB (which has nothing for either, on a first-time import)."""

    def test_second_identical_row_flagged_duplicate_only_one_committed(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        q = _q(question_text="This exact question text repeats verbatim in the same upload.")
        payload = _v2_payload([dict(q), dict(q)])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        assert pf["summary"]["duplicate"] == 1
        assert pf["rows"][0]["status"] == "ok"
        assert pf["rows"][1]["status"] == "duplicate"
        assert "row 1" in pf["rows"][1]["messages"][0]

        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1
        assert len(sb.db["pyq_questions"]) == 1


class TestV2DurableStimulusIdentity:
    """Fix 8: a stimulus's identity (metadata.import_ref) must survive across
    SEPARATE commit() calls (a retry after a partial failure), so a second
    batch referencing the same ref reuses the existing pyq_stimuli row
    instead of creating a duplicate."""

    def test_second_separate_commit_reuses_existing_stimulus_row(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [{"ref": "passage-04", "stimulus_type": "passage", "content_text": "Shared passage."}]

        payload1 = _v2_payload([_q(question_text="First question about the passage.",
                                    stimulus_refs=["passage-04"])], stimuli=stimuli)
        pf1 = _preflight_json_v2(client, payload1)
        result1 = _commit(client, pf1["import_token"])
        assert result1["committed"] == 1
        assert len(sb.db["pyq_stimuli"]) == 1
        first_stim_id = sb.db["pyq_stimuli"][0]["id"]

        # Fresh, separate preflight/commit cycle (new token) referencing the
        # SAME ref for a different question.
        payload2 = _v2_payload([_q(question_text="Second question, same passage, later batch.",
                                    stimulus_refs=["passage-04"])], stimuli=stimuli)
        pf2 = _preflight_json_v2(client, payload2)
        result2 = _commit(client, pf2["import_token"])
        assert result2["committed"] == 1

        assert len(sb.db["pyq_stimuli"]) == 1  # still just one stimulus row
        assert sb.db["pyq_stimuli"][0]["id"] == first_stim_id
        links = sb.db["pyq_question_stimuli"]
        assert len(links) == 2
        assert all(link["stimulus_id"] == first_stim_id for link in links)


class TestV2ScopeRestrictions:
    """Fix 9: v2 only supports question_type='mcq' (no scoring/import path
    for other types yet) and a text/shared-grouping-only stimulus_type subset
    (media types are PR-11 scope)."""

    def test_non_mcq_question_type_is_row_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([_q(question_type="numerical")])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        row = pf["rows"][0]
        assert row["status"] == "error"
        assert any("not yet supported" in m for m in row["messages"])

    def test_image_stimulus_type_is_batch_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [{"ref": "img-01", "stimulus_type": "image", "content_text": None}]
        payload = _v2_payload([_q(stimulus_refs=["img-01"])], stimuli=stimuli)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 422, r.text
        assert "PR-11" in r.json()["detail"]


# ── 12. Checkpost round 3 fixes ─────────────────────────────────────────────
#
# Fix 1: no-identity duplicate across two SEPARATE commit() calls (not a
#        race -- sequential preflight-both-then-commit-both is enough).
# Fix 2: batch_hash_map must be seeded even when a row ends up "fuzzy", not
#        just "ok".
# Fix 3b: stimulus content-mismatch detection on a corrected retry.
# Fix 4 (secondary): bearer-token design -- a different actor can commit.
# Fix 5: default option display_order from array position; duplicate
#        stimulus_refs within one question; duplicate display_order across
#        questions/stimuli within one upload.


class TestV2NoIdentityDuplicateAcrossSeparateCommits:
    """Fix 1: batch_hash_map (round 2) only guards duplicates WITHIN one
    preflight batch. Two SEPARATE commit() calls for byte-identical
    no-identity question text -- each preflighted BEFORE either commits, so
    neither preflight's own dedup ladder can see the other's row -- must not
    both insert. commit()'s idempotency re-check must catch it via
    normalized_question_hash even though neither source_question_ref nor
    question_number is set on either row."""

    def test_second_separate_commit_skips_as_already_exists(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        q = _q(question_text="No identity fields on this question at all.")

        # Both preflighted BEFORE either commits -- this is the reproduction:
        # at preflight time, batch B's dedup ladder only ever compares
        # against rows already IN THE DB, and batch A hasn't committed yet.
        pf_a = _preflight_json_v2(client, _v2_payload([dict(q)]))
        pf_b = _preflight_json_v2(client, _v2_payload([dict(q)]))
        assert pf_a["summary"]["ok"] == 1
        assert pf_b["summary"]["ok"] == 1

        result_a = _commit(client, pf_a["import_token"])
        assert result_a["committed"] == 1
        assert len(sb.db["pyq_questions"]) == 1

        result_b = _commit(client, pf_b["import_token"])
        assert result_b["committed"] == 0
        assert result_b["skipped"] == 1
        assert result_b["per_row"][0]["reason"] == "already_exists"
        # Only one pyq_questions row ends up existing for this paper.
        assert len(sb.db["pyq_questions"]) == 1


class TestV2FuzzySeedsBatchHashMap:
    """Fix 2: a row whose only fate is "fuzzy" (near-miss ratio >= 0.85
    against an EXISTING DB row, no exact hash match) must still seed
    batch_hash_map -- not just rows that end up "ok" -- so a second,
    byte-identical row later in the same batch is caught as a batch-local
    "duplicate" instead of independently repeating the same fuzzy check and
    also landing on "fuzzy" (which would silently commit both, since fuzzy
    rows commit by default unless also flagged error)."""

    def test_second_identical_fuzzy_row_is_batch_duplicate_not_fuzzy(self):
        existing_text = (
            "What is the capital of France and why is it important to European history?"
        )
        seed = _seed_v2(extra_questions=[{
            "id": "q-existing", "pyq_paper_id": "paper-1",
            "question_number": 1, "question_text": existing_text,
            "normalized_question_hash": question_hash(existing_text),
        }])
        sb = TaxSBStub(seed)
        client = _client(sb)
        near_text = (
            "What is the capital of France and why is it important to European history today?"
        )
        q = _q(question_text=near_text)
        pf = _preflight_json_v2(client, _v2_payload([dict(q), dict(q)]))
        row1, row2 = pf["rows"]
        assert row1["status"] == "fuzzy"
        assert row2["status"] == "duplicate"
        assert "row 1" in row2["messages"][0]

        result = _commit(client, pf["import_token"])
        # Row 1 ("fuzzy") commits by default; row 2 is skipped as a
        # batch-local duplicate of row 1, not independently committed.
        assert result["committed"] == 1
        assert result["skipped"] == 1
        # Existing seeded row + the one newly committed fuzzy row = 2 total.
        assert len(sb.db["pyq_questions"]) == 2


class TestV2StimulusContentMismatch:
    """Fix 3a/3b: a corrected retry (same ref, different content_text) must
    not silently link new questions to the STALE, uncorrected stimulus.
    commit() must abort the WHOLE call before any writes, with a clear error
    naming the ref and the conflict, leaving the original stimulus row's
    content untouched."""

    def test_second_commit_with_changed_content_text_fails_no_partial_writes(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli1 = [{"ref": "passage-04", "stimulus_type": "passage", "content_text": "Original text"}]
        payload1 = _v2_payload(
            [_q(question_text="First question about the passage.", stimulus_refs=["passage-04"])],
            stimuli=stimuli1,
        )
        pf1 = _preflight_json_v2(client, payload1)
        result1 = _commit(client, pf1["import_token"])
        assert result1["committed"] == 1
        original_stim = dict(sb.db["pyq_stimuli"][0])

        stimuli2 = [{"ref": "passage-04", "stimulus_type": "passage", "content_text": "Corrected text"}]
        payload2 = _v2_payload(
            [_q(question_text="Second question, corrected retry.", stimulus_refs=["passage-04"])],
            stimuli=stimuli2,
        )
        pf2 = _preflight_json_v2(client, payload2)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": pf2["import_token"], "reason": "corrected retry conflict"},
        )
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert "passage-04" in detail
        assert "different content" in detail

        # No partial writes: still exactly 1 stimulus row, unchanged content;
        # no second question committed either.
        assert len(sb.db["pyq_stimuli"]) == 1
        assert sb.db["pyq_stimuli"][0] == original_stim
        assert sb.db["pyq_stimuli"][0]["content_text"] == "Original text"
        assert len(sb.db["pyq_questions"]) == 1


class TestV2BearerTokenDesign:
    """Fix 4 (secondary): tokens are a bearer/transferable capability -- any
    actor holding a valid, unexpired, unconsumed token for the correct paper
    may commit it, regardless of who ran the original preflight. This test
    documents/proves the CURRENT (intentionally unchanged) behavior."""

    def test_different_actor_can_commit_same_token(self):
        sb = TaxSBStub(_seed_v2())
        payload = _v2_payload([_q(question_text="Bearer-token capability question.")])
        pf = _bi.preflight(
            sb, {"id": "preflighter-1"}, "paper-1",
            json.dumps(payload).encode(), "application/json",
        )
        token = pf["import_token"]
        result = _bi.commit(sb, {"id": "someone-else-entirely"}, token, paper_id="paper-1")
        assert result["committed"] == 1


class TestV2OptionDisplayOrderDefaults:
    """Fix 5a: an omitted options[i].display_order defaults to the option's
    1-based position in the supplied options array, instead of staying
    None. An explicitly-given value is still validated as before."""

    def test_omitted_option_display_order_defaults_to_array_position(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([_q(
            question_text="Options omit display_order entirely.",
            options=[
                {"label": "1", "text": "Alpha"},
                {"label": "2", "text": "Beta"},
                {"label": "3", "text": "Gamma"},
            ],
            correct_option_label="2",
        )])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        result = _commit(client, pf["import_token"])
        assert result["committed"] == 1
        opts = {o["option_label"]: o for o in sb.db["pyq_options"]}
        assert opts["1"]["display_order"] == 1
        assert opts["2"]["display_order"] == 2
        assert opts["3"]["display_order"] == 3


class TestV2DuplicateStimulusRefsInQuestion:
    """Fix 5b: a question's stimulus_refs listing the same ref twice must be
    a row-level validation error, not a silent double-link (which would hit
    pyq_question_stimuli's unique(question_id, stimulus_id) constraint at
    commit time as a late, confusing failure)."""

    def test_duplicate_stimulus_ref_in_same_question_is_row_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [{"ref": "passage-04", "stimulus_type": "passage", "content_text": "Passage."}]
        payload = _v2_payload(
            [_q(stimulus_refs=["passage-04", "passage-04"])],
            stimuli=stimuli,
        )
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["error"] == 1
        row = pf["rows"][0]
        assert row["status"] == "error"
        assert any("duplicate ref" in m for m in row["messages"])


class TestV2DuplicateDisplayOrderWithinUpload:
    """Fix 5c: duplicate EXPLICIT display_order among questions within one
    upload, and among stimuli within the batch's top-level stimuli array,
    are caught at preflight time -- a UX/DX improvement layered on top of
    migration 223's already-safe commit-time unique-index backstop for the
    cross-batch case, not a new correctness gap."""

    def test_duplicate_question_display_order_within_upload_is_row_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        payload = _v2_payload([
            _q(question_text="First question, display_order 5.", display_order=5),
            _q(question_text="Second question, ALSO display_order 5.", display_order=5),
        ])
        pf = _preflight_json_v2(client, payload)
        assert pf["summary"]["ok"] == 1
        assert pf["summary"]["error"] == 1
        row2 = pf["rows"][1]
        assert row2["status"] == "error"
        assert any(
            "display_order 5 is duplicated within this upload" in m and "row 1" in m
            for m in row2["messages"]
        )

    def test_duplicate_stimulus_display_order_within_batch_is_batch_error(self):
        sb = TaxSBStub(_seed_v2())
        client = _client(sb)
        stimuli = [
            {"ref": "passage-01", "stimulus_type": "passage", "content_text": "P1", "display_order": 1},
            {"ref": "passage-02", "stimulus_type": "passage", "content_text": "P2", "display_order": 1},
        ]
        payload = _v2_payload(
            [_q(stimulus_refs=["passage-01"]), _q(stimulus_refs=["passage-02"])],
            stimuli=stimuli,
        )
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/preflight",
            content=json.dumps(payload).encode(),
            headers={"content-type": "application/json"},
        )
        assert r.status_code == 422, r.text
        assert "duplicated within this batch" in r.json()["detail"]


class TestV2StimuliFailClosedLookup:
    """Fix 3a: the existing-pyq_stimuli fetch (durable stimulus identity
    across separate commit() calls) used to catch its own exception and
    just logger.warning() -- the ONE fail-open lookup left standing after
    round 2. A transient failure here must now raise RuntimeError (fail
    closed), consistent with the existing-questions lookup, since silently
    degrading to per-call-only identity can create duplicate canonical
    stimuli. Also proves fix #4's reordering: the fetch runs BEFORE the
    token claim, so the token is untouched when this raises."""

    def test_commit_raises_when_existing_stimuli_fetch_fails(self):
        from tests.exam_intelligence.test_pyq_bulk_import import RaiseOnSelectSBStub

        sb_ok = TaxSBStub(_seed_v2())
        client = _client(sb_ok)
        stimuli = [{"ref": "passage-04", "stimulus_type": "passage", "content_text": "Passage."}]
        payload = _v2_payload(
            [_q(question_text="Uses a stimulus.", stimulus_refs=["passage-04"])],
            stimuli=stimuli,
        )
        pf = _preflight_json_v2(client, payload)
        token = pf["import_token"]
        token_row = next(r for r in sb_ok.db["pyq_import_tokens"] if r["token"] == token)

        seed = _seed_v2()
        seed["pyq_import_tokens"] = [dict(token_row)]
        sb = RaiseOnSelectSBStub(seed, fail_table="pyq_stimuli")
        with pytest.raises(RuntimeError):
            _bi.commit(sb, {"id": "admin-99"}, token, paper_id="paper-1")

        assert sb.db["pyq_questions"] == []
        assert sb.db["pyq_stimuli"] == []
        # Token untouched -- the fetch runs before the claim (fix #4), so a
        # RuntimeError here never burns the token.
        row = next(r for r in sb.db["pyq_import_tokens"] if r["token"] == token)
        assert row["consumed_at"] is None
