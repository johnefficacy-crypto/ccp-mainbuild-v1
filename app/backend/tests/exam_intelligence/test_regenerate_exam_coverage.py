"""Tests for `scripts/regenerate_exam_coverage.py` and the `dry_run` contract
it depends on.

The script computes nothing itself — it wraps
`score_snapshots.compute_exam_topic_scores` and
`coverage_derivation.derive_topic_coverage`. So the tests that matter are:

* a dry run writes NOTHING, on either stage;
* a dry run reports exactly what a live run then does (same rows, same
  numbers) — otherwise the preview is decoration;
* `--assume-locked` cannot be combined with `--live`, and the derivation
  refuses a snapshot override on a live run (PD-1);
* the reporting-only bank comparison counts at the level `pyq_practice`
  practises at, not at `topic_id`.
"""
from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys

import pytest

from tests.persona_questions._stub import SBStub
from app.exam_intelligence.coverage_derivation import (
    DERIVATION_VERSION,
    CoverageDerivationError,
    derive_topic_coverage,
)
from app.exam_intelligence.score_snapshots import MODEL_VERSION, compute_exam_topic_scores

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "regenerate_exam_coverage.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("regenerate_exam_coverage", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["regenerate_exam_coverage"] = mod
    spec.loader.exec_module(mod)
    return mod


rec = _load_script()


def _snapshot_row(**overrides):
    row = {
        "id": "snap-t1",
        "exam_id": "exam-1",
        "exam_phase_id": None,
        "topic_id": "t1",
        "status": "locked",
        "model_version": MODEL_VERSION,
        "exam_priority_score": 72.5,
        "is_high_yield": True,
        "confidence_score": 0.81,
        "evidence_count": 6,
        "computed_at": "2026-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def _evidence_db():
    """A minimal verified-PYQ corpus: one paper, three questions, two topics."""
    return {
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "exam_phase_id": None,
             "trust_status": "verified", "year": 2024},
        ],
        "pyq_questions": [
            {"id": f"q{i}", "pyq_paper_id": "p1", "reviewer_status": "verified"}
            for i in range(1, 4)
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "tag_role": "primary",
             "reviewer_status": "verified"},
            {"question_id": "q2", "topic_id": "t1", "tag_role": "primary",
             "reviewer_status": "verified"},
            {"question_id": "q3", "topic_id": "t2", "tag_role": "primary",
             "reviewer_status": "verified"},
        ],
    }


# ── 1. a dry run writes nothing ───────────────────────────────────────────

def test_snapshot_dry_run_writes_nothing():
    sb = SBStub(_evidence_db())
    result = compute_exam_topic_scores(sb, "exam-1", dry_run=True)
    assert result["dry_run"] is True
    assert result["written"] > 0, "a dry run still reports what it would write"
    assert sb.db.get("exam_topic_score_snapshots", []) == []


def test_coverage_dry_run_writes_nothing():
    sb = SBStub({"exam_topic_score_snapshots": [_snapshot_row()]})
    result = derive_topic_coverage(sb, "exam-1", dry_run=True)
    assert result["dry_run"] is True
    assert result["written"] == 1
    assert sb.db.get("exam_topic_coverage", []) == []


def test_live_run_is_the_default_and_still_writes():
    """The flag defaults to False, so every existing caller — both admin
    routes — keeps writing exactly as before."""
    sb = SBStub({"exam_topic_score_snapshots": [_snapshot_row()]})
    result = derive_topic_coverage(sb, "exam-1")
    assert result["dry_run"] is False
    assert len(sb.db["exam_topic_coverage"]) == 1


# ── 2. the dry run matches the live run ───────────────────────────────────

def test_snapshot_dry_run_proposes_exactly_what_a_live_run_writes():
    """Same corpus, two runs. If the preview and the write can disagree, the
    preview is worthless — this is the assertion that keeps them honest."""
    db = _evidence_db()
    preview = compute_exam_topic_scores(SBStub(copy.deepcopy(db)), "exam-1", dry_run=True)

    sb_live = SBStub(copy.deepcopy(db))
    live = compute_exam_topic_scores(sb_live, "exam-1")

    assert preview["written"] == live["written"]
    assert preview["total_topics"] == live["total_topics"]

    def key(rows):
        return sorted(
            (r["topic_id"], r["exam_priority_score"], r["evidence_count"],
             bool(r["is_high_yield"]), r["confidence_score"])
            for r in rows
        )

    assert key(preview["proposed"]) == key(sb_live.db["exam_topic_score_snapshots"])


def test_coverage_dry_run_proposes_exactly_what_a_live_run_writes():
    db = {"exam_topic_score_snapshots": [
        _snapshot_row(),
        _snapshot_row(id="snap-t2", topic_id="t2", evidence_count=2,
                      exam_priority_score=3.28, is_high_yield=False),
    ]}
    preview = derive_topic_coverage(SBStub(copy.deepcopy(db)), "exam-1", dry_run=True)

    sb_live = SBStub(copy.deepcopy(db))
    derive_topic_coverage(sb_live, "exam-1")

    def key(rows):
        return sorted(
            (r["topic_id"], r["coverage_depth"], r["exam_priority_score"],
             r["source_basis"], r["reviewer_status"])
            for r in rows
        )

    assert key(preview["proposed"]) == key(sb_live.db["exam_topic_coverage"])
    assert {r["reviewer_status"] for r in preview["proposed"]} == {"draft"}


def test_the_dry_run_never_proposes_a_locked_row():
    """Neither stage may propose anything a human has not gated. A script that
    emitted reviewer_status='locked' would be an AI job writing into locked
    coverage, which the J3 gate forbids outright."""
    sb = SBStub({"exam_topic_score_snapshots": [_snapshot_row()]})
    result = derive_topic_coverage(sb, "exam-1", dry_run=True)
    for row in result["proposed"]:
        assert row["reviewer_status"] == "draft"
        assert row["source_basis"] == "evidence_derived"
        assert row["model_version"] == DERIVATION_VERSION


# ── 3. a dry run does not touch existing rows ─────────────────────────────

def test_dry_run_does_not_mutate_a_derivation_owned_row():
    """The CAS update path reports "would update" and changes nothing."""
    existing = {
        "id": "cov-1", "exam_id": "exam-1", "exam_cycle_id": None,
        "exam_phase_id": None, "topic_id": "t1", "source_basis": "evidence_derived",
        "model_version": DERIVATION_VERSION, "reviewer_status": "draft",
        "exam_priority_score": 1.0, "coverage_depth": "light",
        "is_high_yield": False, "confidence_score": 0.3,
        "metadata": {"evidence": {"fingerprint": "stale-fp"}},
    }
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [dict(existing)],
    })
    result = derive_topic_coverage(sb, "exam-1", dry_run=True)
    assert result["updated"] == 1
    assert sb.db["exam_topic_coverage"] == [existing], "the row was modified in a dry run"


def test_dry_run_does_not_flag_a_stale_row():
    stale = {
        "id": "cov-old", "exam_id": "exam-1", "exam_cycle_id": None,
        "exam_phase_id": None, "topic_id": "gone", "source_basis": "evidence_derived",
        "model_version": DERIVATION_VERSION, "reviewer_status": "draft",
        "metadata": {},
    }
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [dict(stale)],
    })
    result = derive_topic_coverage(sb, "exam-1", dry_run=True)
    assert result["stale_reconciled"] == 1
    assert sb.db["exam_topic_coverage"][0]["metadata"] == {}


def test_dry_run_still_refuses_to_touch_a_locked_row():
    locked = {
        "id": "cov-locked", "exam_id": "exam-1", "exam_cycle_id": None,
        "exam_phase_id": None, "topic_id": "t1", "source_basis": "evidence_derived",
        "model_version": DERIVATION_VERSION, "reviewer_status": "locked",
        "exam_priority_score": 9.0, "coverage_depth": "deep",
        "metadata": {"evidence": {"fingerprint": "whatever"}},
    }
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "exam_topic_coverage": [dict(locked)],
    })
    result = derive_topic_coverage(sb, "exam-1", dry_run=True)
    assert result["written"] == 0 and result["updated"] == 0
    assert result["skipped"] == 1
    assert result["deltas"], "a skipped locked row still reports its delta"


# ── 4. PD-1: no deriving from unlocked evidence ───────────────────────────

def test_snapshots_override_is_refused_on_a_live_run():
    sb = SBStub({})
    with pytest.raises(CoverageDerivationError, match="dry_run=True"):
        derive_topic_coverage(sb, "exam-1", snapshots_override=[])


def test_snapshots_override_is_accepted_on_a_dry_run():
    """--assume-locked's whole mechanism: project from rows that are not
    locked yet, without writing and without pretending they are locked."""
    sb = SBStub({})   # no locked snapshots at all
    plain = derive_topic_coverage(sb, "exam-1", dry_run=True)
    assert plain["written"] == 0, "nothing is locked, so nothing is derivable today"

    override = rec.as_locked_shape([
        {"topic_id": "t1", "exam_priority_score": 11.41, "is_high_yield": True,
         "confidence_score": 0.72, "evidence_count": 6,
         "model_version": MODEL_VERSION, "score_components": {"x": 1},
         "input_summary": {"fingerprint": "fp-1"}, "predictability": None,
         "predictability_band": None},
    ])
    projected = derive_topic_coverage(
        sb, "exam-1", dry_run=True, snapshots_override=override)
    assert projected["written"] == 1
    row = projected["proposed"][0]
    assert row["topic_id"] == "t1"
    assert row["exam_priority_score"] == 11.41   # copied, not recomputed
    assert row["coverage_depth"] == "deep"        # evidence_count 6 -> deep
    assert sb.db.get("exam_topic_coverage", []) == []


def test_as_locked_shape_invents_no_values():
    """Every field is carried across; `snapshot_id` is None because the row has
    no id — it has not been written."""
    payload = {
        "topic_id": "t9", "exam_priority_score": 3.28, "is_high_yield": False,
        "confidence_score": 0.44, "evidence_count": 2, "model_version": MODEL_VERSION,
        "score_components": {"frequency_component": 0.1},
        "input_summary": {"fingerprint": "fp-9"},
        "predictability": 0.5, "predictability_band": "medium",
    }
    out = rec.as_locked_shape([payload])[0]
    assert out["snapshot_id"] is None
    assert out["computed_at"] is None
    assert out["fingerprint"] == "fp-9"
    for field in ("topic_id", "exam_priority_score", "is_high_yield",
                  "confidence_score", "evidence_count", "score_components",
                  "predictability", "predictability_band"):
        assert out[field] == payload[field], field


# ── 5. the CLI surface ────────────────────────────────────────────────────

def test_dry_run_is_the_default():
    args = rec.build_parser().parse_args(["--exam", "rbi"])
    assert args.live is False
    assert args.assume_locked is False


def test_exam_alias_resolves_to_the_rbi_id():
    assert rec.resolve_exam("rbi") == "aded8ee9-e9ec-4287-9015-6db1919fa67e"
    assert rec.resolve_exam("RBI-Grade-B") == "aded8ee9-e9ec-4287-9015-6db1919fa67e"
    # A raw uuid passes through untouched.
    assert rec.resolve_exam("abc-123") == "abc-123"
    with pytest.raises(rec.CoverageRunError):
        rec.resolve_exam("")


def test_assume_locked_with_live_is_refused_before_any_write(monkeypatch, capsys):
    """The one combination that could derive coverage from unlocked evidence.
    Refused by the script, and independently by the derivation (test above)."""
    sb = SBStub(_evidence_db())
    monkeypatch.setattr(rec, "_load_modules", lambda: (
        lambda: sb,
        __import__("app.exam_intelligence.score_snapshots", fromlist=["x"]),
        __import__("app.exam_intelligence.coverage_derivation", fromlist=["x"]),
    ))
    code = rec.main(["--exam", "exam-1", "--live", "--assume-locked"])
    assert code == 2
    assert "PD-1" in capsys.readouterr().err
    assert sb.db.get("exam_topic_coverage", []) == []


def test_the_script_reports_both_human_gates(monkeypatch, capsys):
    """An operator who reads the output must know that neither stage makes a
    topic practisable on its own."""
    sb = SBStub({**_evidence_db(), "exam_topic_score_snapshots": [_snapshot_row()]})
    monkeypatch.setattr(rec, "_load_modules", lambda: (
        lambda: sb,
        __import__("app.exam_intelligence.score_snapshots", fromlist=["x"]),
        __import__("app.exam_intelligence.coverage_derivation", fromlist=["x"]),
    ))
    assert rec.main(["--exam", "exam-1"]) == 0
    out = capsys.readouterr().out
    assert out.count("[HUMAN GATE]") == 2
    assert "score-snapshots/{id}/review" in out
    assert "topic-coverage/{id}/review" in out
    assert "Only locked rows are reachable by topic-mode practice." in out
    assert "DRY RUN — nothing was written" in out
    assert sb.db.get("exam_topic_coverage", []) == []


# ── 6. the reporting-only bank comparison ─────────────────────────────────

def test_bank_counts_are_taken_at_the_practised_level():
    """`pyq_practice._row_level_id`: a row with a `microtopic_id` belongs to
    that microtopic and to nothing else. Counting `topic_id` alone would credit
    a parent with its children's questions."""
    sb = SBStub({"mock_question_bank": [
        # post-270 split rows: parent in topic_id, real level in microtopic_id
        {"id": "b1", "exam_id": "exam-1", "reviewer_status": "verified",
         "topic_id": "parent", "microtopic_id": "micro-a"},
        {"id": "b2", "exam_id": "exam-1", "reviewer_status": "verified",
         "topic_id": "parent", "microtopic_id": "micro-a"},
        {"id": "b3", "exam_id": "exam-1", "reviewer_status": "verified",
         "topic_id": "parent", "microtopic_id": "micro-b"},
        # pre-270 / top-level row: self-describing at topic_id
        {"id": "b4", "exam_id": "exam-1", "reviewer_status": "verified",
         "topic_id": "top", "microtopic_id": None},
    ]})
    counts = rec.bank_counts_by_level(sb, "exam-1")
    assert counts == {"micro-a": 2, "micro-b": 1, "top": 1}
    assert "parent" not in counts


def test_the_bank_count_changes_no_proposed_row():
    """It is a reporting column. Run the same derivation with a populated bank
    and with none, and the proposal must be byte-identical — if the projected
    count ever reached the bucket function, depth would stop being a statement
    about verified evidence."""
    snapshots = {"exam_topic_score_snapshots": [_snapshot_row()]}
    without = derive_topic_coverage(SBStub(copy.deepcopy(snapshots)), "exam-1", dry_run=True)
    with_bank = derive_topic_coverage(
        SBStub({**copy.deepcopy(snapshots), "mock_question_bank": [
            {"id": f"b{i}", "exam_id": "exam-1", "reviewer_status": "verified",
             "topic_id": "t1", "microtopic_id": None}
            for i in range(50)   # 50 projected rows against evidence_count=6
        ]}),
        "exam-1", dry_run=True,
    )
    assert without["proposed"] == with_bank["proposed"]
    assert with_bank["proposed"][0]["coverage_depth"] == "deep"   # from 6, not 50


def test_the_script_reports_the_gap_between_projected_and_locked(monkeypatch, capsys):
    """The 154-microtopic problem, in miniature: a topic with projected bank
    rows and no locked coverage must be named as unreachable, and a topic this
    run proposes nothing for must be named as STILL unreachable."""
    sb = SBStub({
        "exam_topic_score_snapshots": [_snapshot_row()],
        "mock_question_bank": [
            # t1 — this run proposes coverage for it
            {"id": "b1", "exam_id": "exam-1", "reviewer_status": "verified",
             "topic_id": "t1", "microtopic_id": None},
            # t-orphan — projected, but no snapshot, so no proposal
            {"id": "b2", "exam_id": "exam-1", "reviewer_status": "verified",
             "topic_id": "t-orphan", "microtopic_id": None},
        ],
        "exam_topic_coverage": [],
    })
    monkeypatch.setattr(rec, "_load_modules", lambda: (
        lambda: sb,
        __import__("app.exam_intelligence.score_snapshots", fromlist=["x"]),
        __import__("app.exam_intelligence.coverage_derivation", fromlist=["x"]),
    ))
    assert rec.main(["--exam", "exam-1", "--compare-bank"]) == 0
    out = capsys.readouterr().out
    assert "projected-but-unlocked 2 topic(s)" in out
    assert "STILL unreachable      1 topic(s)" in out


def test_depth_order_matches_the_bucket_functions_vocabulary():
    """The script's summary table must not name a bucket the authority cannot
    return, nor omit one it can."""
    from app.exam_intelligence.coverage_derivation import bucket_coverage_depth
    produced = {
        bucket_coverage_depth(e, m, hy)
        for e in range(0, 12) for m in (0, 1, 3) for hy in (False, True)
    } - {None}
    assert produced == set(rec.DEPTH_ORDER)


# ── 7. the findings doc matches the code it documents ─────────────────────

_DOC = _ROOT / "docs" / "architecture" / "evidence-derived-coverage-regeneration.md"


def test_the_doc_names_the_real_generator():
    """The question the doc answers is "where does this live". A stale path here
    sends the next reader hunting for a script that does not exist."""
    doc = _DOC.read_text()
    for path in ("app/backend/app/exam_intelligence/score_snapshots.py",
                 "app/backend/app/exam_intelligence/coverage_derivation.py",
                 "app/backend/app/study_os/pyq_practice.py",
                 "scripts/regenerate_exam_coverage.py"):
        assert path in doc, path
        assert (_ROOT / path).exists(), path
    for route in ("/score-snapshots/compute", "/coverage/derive",
                  "/score-snapshots/{id}/review", "/topic-coverage/{id}/review"):
        assert route in doc, route


def test_the_documented_depth_table_matches_the_bucket_function():
    """Recomputed from the authority, not eyeballed — a drifted table would be
    read as the rule by the next person to touch this."""
    from app.exam_intelligence.coverage_derivation import bucket_coverage_depth
    assert bucket_coverage_depth(0, 0, False) is None
    assert bucket_coverage_depth(0, 1, False) == "mentioned"
    for n in (1, 2):
        assert bucket_coverage_depth(n, 0, False) == "light"
    for n in (3, 4, 5):
        assert bucket_coverage_depth(n, 0, False) == "normal"
    for n in (6, 7, 8, 9):
        assert bucket_coverage_depth(n, 0, False) == "deep"
    assert bucket_coverage_depth(10, 1, True) == "core"
    assert bucket_coverage_depth(10, 1, False) == "deep"
    assert bucket_coverage_depth(10, 0, True) == "deep"

    doc = _DOC.read_text()
    table = doc.split("## 2. How `coverage_depth` is computed")[1].split("## 3.")[0]
    for bucket in ("mentioned", "light", "normal", "deep", "core"):
        assert f"`{bucket}`" in table, bucket
    assert "1–2" in table and "3–5" in table and "6–9" in table


def test_the_documented_priority_formula_matches_the_constants():
    """The doc quotes 10.0 and 3.0 by value. If either constant moves, the
    formula in the doc is wrong and this fails."""
    import app.exam_intelligence.score_snapshots as ss
    assert ss._LIFT_FULL_MARKS == 10.0
    assert ss._HIGH_YIELD_LIFT == 3.0
    doc = _DOC.read_text()
    formula = doc.split("## 3. How `exam_priority_score` is computed")[1].split("## 4.")[0]
    for fragment in ("min(cohort_lift / 10.0, 1.0)", "_LIFT_FULL_MARKS = 10",
                     "cohort_lift >= 3.0", "_HIGH_YIELD_LIFT",
                     "cov_component * 40", "evidence_quality * 10",
                     "min(0.3 + evidence_quality * 0.7, 1.0)"):
        assert fragment in formula, fragment


def test_the_doc_does_not_decompose_the_quoted_scores():
    """It would need the cohort each topic fell into, and no live read was made.
    An invented decomposition is the failure mode the brief named outright."""
    doc = _DOC.read_text()
    section = doc.split("### Reading the reported values back")[1].split("## 4.")[0]
    assert "does not decompose" in section
    assert "no live read was performed" in section
    # It explains WHY a guess would mislead, rather than just declining.
    assert "_cohort_weight" in section and "non-zero" in section


def test_the_doc_states_no_live_writes_and_no_invented_scores():
    doc = _DOC.read_text()
    assert "It proposes no score of its own" in doc
    assert "It never locks anything" in doc
    assert "No live writes were made while writing this" in doc


def test_the_doc_records_the_evidence_vs_projection_distinction():
    """The brief asked to regenerate "from projected question counts"; the
    governed input is the verified tags those projections came from. The doc has
    to say so plainly or the next operator will assume the bank is the input."""
    doc = _DOC.read_text()
    section = doc.split("### What `evidence_count` actually counts")[1].split("## 3.")[0]
    assert "It is not `mock_question_bank`" in section
    assert "pyq_question_topic_tags" in section
    assert "valid_until" in section
