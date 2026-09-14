"""PHASE-INHERIT-01 — a cycle phase inherits its template's evidence.

The evidence chain (papers → snapshots → coverage) is phase-scoped at every
step, so a cycle phase could only produce coverage if the corpus was physically
moved onto it. UPSC CSE Mains has 60 papers on the null-cycle template and 0 on
the 2026 cycle phase, and `exam_target_window.py:56-57` deliberately excludes
null-cycle phases from targeting — so the planner reads the phase that has no
corpus, and a compute scoped to it found zero papers
(`score_snapshots.py:366-367` filters `pyq_papers` by `exam_phase_id`).

Reads inherit; writes never do.
"""
from __future__ import annotations

from app.exam_intelligence.coverage_derivation import derive_topic_coverage
from app.exam_intelligence.phase_inheritance import resolve_template_phase_id
from app.exam_intelligence.score_snapshots import compute_exam_topic_scores
from tests.persona_questions._stub import SBStub

EXAM = "exam-upsc"
TEMPLATE = "ph-template"
CYCLE_2026 = "ph-2026"
CYCLE_2025 = "ph-2025"


def _phase(pid: str, cycle: str | None, slug: str = "mains", meta: dict | None = None) -> dict:
    return {
        "id": pid, "exam_id": EXAM, "exam_cycle_id": cycle,
        "phase_slug": slug, "phase_name": slug.title(), "status": "active",
        "metadata": meta if meta is not None else {},
    }


def _corpus_on(phase_id: str, prefix: str, years: list[int]) -> dict:
    papers, questions, tags, topics = [], [], [], []
    for i, year in enumerate(years):
        pid = f"{prefix}-p{i}"
        papers.append({"id": pid, "exam_id": EXAM, "exam_phase_id": phase_id,
                       "year": year, "trust_status": "verified"})
        qid = f"{prefix}-q{i}"
        questions.append({"id": qid, "pyq_paper_id": pid, "reviewer_status": "verified"})
        tags.append({"id": f"{prefix}-tag{i}", "question_id": qid,
                     "topic_id": f"{prefix}-topic", "tag_role": "primary",
                     "reviewer_status": "verified"})
    topics.append({"id": f"{prefix}-topic", "subject_id": "s1"})
    return {"pyq_papers": papers, "pyq_questions": questions,
            "pyq_question_topic_tags": tags, "topics": topics}


def _db(*, phases: list[dict], corpora: list[dict]) -> dict:
    db = {
        "exams": [{"id": EXAM, "slug": "upsc-cse"}],
        "exam_phases": phases,
        "subjects": [{"id": "s1", "slug": "mains-gs1"}],
        "pyq_papers": [], "pyq_questions": [], "pyq_question_topic_tags": [],
        "topics": [], "exam_topic_coverage": [], "exam_topic_score_snapshots": [],
        "syllabus_topic_mentions": [],
    }
    for c in corpora:
        for k, v in c.items():
            db[k].extend(v)
    return db


def _snapshots(sb: SBStub) -> list[dict]:
    return sb.db.get("exam_topic_score_snapshots", [])


# ── 1. The defect and the fix ────────────────────────────────────────────────
def test_a_cycle_phase_computes_from_the_templates_corpus():
    """The headline, and it fails against `main`: with the corpus only on the
    template, a compute scoped to the 2026 cycle phase found zero papers and
    wrote nothing. It now reads the template's papers."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(TEMPLATE, "tpl", [1991, 2001, 2011])],
    ))
    result = compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)

    assert result["read_error"] is False
    assert result["written"] == 1, result


def test_snapshots_are_written_to_the_cycle_phase_not_the_template():
    """Reads inherit; writes never do. A snapshot carrying the template's id
    would be invisible to the planner all over again."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(TEMPLATE, "tpl", [1991, 2001, 2011])],
    ))
    compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)

    rows = _snapshots(sb)
    assert rows
    assert all(r["exam_phase_id"] == CYCLE_2026 for r in rows)
    assert not any(r["exam_phase_id"] == TEMPLATE for r in rows)


def test_the_explicit_promotion_link_is_used_when_present():
    """`POST /exam-phases/promote-template` records the parent in
    `metadata.promoted_from_template_phase_id` (`admin_exam_intel_cms.py:811`).
    That link is preferred over resolving by slug."""
    sb = SBStub(_db(
        phases=[
            _phase(TEMPLATE, None, slug="mains"),
            _phase(CYCLE_2026, "cyc-2026", slug="mains-renamed",
                   meta={"promoted_from_template_phase_id": TEMPLATE}),
        ],
        corpora=[_corpus_on(TEMPLATE, "tpl", [1991, 2001, 2011])],
    ))
    # The slugs differ, so only the explicit link can resolve this.
    assert resolve_template_phase_id(sb, EXAM, CYCLE_2026) == TEMPLATE
    assert compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)["written"] == 1


# ── 2. Direction safety (G2) ─────────────────────────────────────────────────
def test_a_template_never_inherits():
    """Only cycle-reads-template. A template resolving to anything would mean
    reading a cycle's data — leaking one year's evidence into another."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(CYCLE_2026, "cyc", [2026])],
    ))
    assert resolve_template_phase_id(sb, EXAM, TEMPLATE) is None
    # …and the template's own compute sees no papers, exactly as before.
    assert compute_exam_topic_scores(sb, EXAM, exam_phase_id=TEMPLATE)["written"] == 0


def test_one_cycle_never_sees_another_cycles_papers():
    """2025's corpus must not reach 2026. The resolved parent must itself be a
    template, so a cycle can only ever inherit upward."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2025, "cyc-2025"),
                _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(CYCLE_2025, "y25", [2025])],
    ))
    result = compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)
    assert result["written"] == 0
    assert _snapshots(sb) == []


def test_a_cycle_phase_with_its_own_corpus_does_not_inherit():
    """Inheritance is "empty → inherit". A phase carrying its own papers uses
    them; mixing the two sets would double-count."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(TEMPLATE, "tpl", [1991, 2001, 2011]),
                 _corpus_on(CYCLE_2026, "own", [2026])],
    ))
    compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)
    rows = _snapshots(sb)
    assert {r["topic_id"] for r in rows} == {"own-topic"}


# ── 3. Unchanged where there is no template (G3, D3) ─────────────────────────
def test_an_exam_with_no_template_phase_is_bit_for_bit_unchanged():
    sb = SBStub(_db(
        phases=[_phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(CYCLE_2026, "own", [2026])],
    ))
    assert resolve_template_phase_id(sb, EXAM, CYCLE_2026) is None
    assert compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)["written"] == 1


def test_a_cycle_phase_with_no_template_and_no_papers_still_writes_nothing():
    sb = SBStub(_db(phases=[_phase(CYCLE_2026, "cyc-2026")], corpora=[]))
    assert compute_exam_topic_scores(sb, EXAM, exam_phase_id=CYCLE_2026)["written"] == 0


def test_an_exam_wide_compute_is_untouched():
    """No phase scoped → nothing to inherit from."""
    sb = SBStub(_db(
        phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
        corpora=[_corpus_on(TEMPLATE, "tpl", [1991, 2001, 2011])],
    ))
    assert resolve_template_phase_id(sb, EXAM, None) is None
    assert compute_exam_topic_scores(sb, EXAM)["written"] == 1


def test_an_unknown_phase_id_resolves_to_nothing():
    sb = SBStub(_db(phases=[_phase(TEMPLATE, None)], corpora=[]))
    assert resolve_template_phase_id(sb, EXAM, "no-such-phase") is None


# ── 4. Derivation inherits syllabus mentions, never coverage (G4) ────────────
def _mention(mid: str, topic: str, phase: str) -> dict:
    return {"id": mid, "exam_id": EXAM, "topic_id": topic,
            "exam_phase_id": phase, "reviewer_status": "verified"}


def test_derivation_reads_the_templates_syllabus_mentions():
    """A syllabus is cycle-independent evidence and lives on the template
    beside the corpus, so a cycle phase with none of its own reads it."""
    db = _db(phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
             corpora=[])
    db["topics"] = [{"id": "t-syl", "subject_id": "s1"}]
    db["syllabus_topic_mentions"] = [_mention("m1", "t-syl", TEMPLATE)]

    sb = SBStub(db)
    result = derive_topic_coverage(sb, EXAM, exam_phase_id=CYCLE_2026)

    assert result.get("read_error") is False, result
    written = sb.db.get("exam_topic_coverage", [])
    assert len(written) == 1
    # Written to the CYCLE phase — reads inherit, writes never do.
    assert written[0]["exam_phase_id"] == CYCLE_2026
    assert written[0]["coverage_depth"] == "mentioned"


def test_derivation_does_not_inherit_coverage_rows():
    """Coverage rows are what this derivation owns and rewrites at the target
    scope. Reading the template's would make it treat another phase's rows as
    its own — so the cycle phase writes a fresh row rather than adopting one."""
    db = _db(phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
             corpora=[])
    db["topics"] = [{"id": "t-syl", "subject_id": "s1"}]
    db["syllabus_topic_mentions"] = [_mention("m1", "t-syl", TEMPLATE)]
    db["exam_topic_coverage"] = [{
        "id": "cov-template", "exam_id": EXAM, "topic_id": "t-syl",
        "exam_phase_id": TEMPLATE, "exam_cycle_id": None,
        "source_basis": "evidence_derived", "model_version": "v1",
        "reviewer_status": "draft", "coverage_depth": "mentioned",
        "exam_priority_score": 0, "is_high_yield": False,
        "confidence_score": 0, "metadata": {},
    }]

    sb = SBStub(db)
    derive_topic_coverage(sb, EXAM, exam_phase_id=CYCLE_2026)

    rows = sb.db["exam_topic_coverage"]
    template_rows = [r for r in rows if r["exam_phase_id"] == TEMPLATE]
    cycle_rows = [r for r in rows if r["exam_phase_id"] == CYCLE_2026]
    assert len(template_rows) == 1          # untouched
    assert template_rows[0]["id"] == "cov-template"
    assert len(cycle_rows) == 1             # its own, freshly written


def test_derivation_with_its_own_mentions_does_not_inherit():
    db = _db(phases=[_phase(TEMPLATE, None), _phase(CYCLE_2026, "cyc-2026")],
             corpora=[])
    db["topics"] = [{"id": "t-tpl", "subject_id": "s1"},
                    {"id": "t-own", "subject_id": "s1"}]
    db["syllabus_topic_mentions"] = [_mention("m1", "t-tpl", TEMPLATE),
                                     _mention("m2", "t-own", CYCLE_2026)]

    sb = SBStub(db)
    derive_topic_coverage(sb, EXAM, exam_phase_id=CYCLE_2026)

    written = sb.db.get("exam_topic_coverage", [])
    assert {r["topic_id"] for r in written} == {"t-own"}
