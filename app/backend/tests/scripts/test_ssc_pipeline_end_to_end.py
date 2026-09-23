"""export -> catalog -> propose, chained exactly as the SSC CGL runbook prints it.

WHY THIS FILE EXISTS. Both steps had unit tests and both passed. What nobody
tested was the SEAM between them, and the seam carried two bugs that fire on
first contact with real data:

1. `catalog --out topic_catalog_ssc.json` writes a JSON LIST; `--catalogue`
   read JSONL only and aborted with
   "topic_catalog_ssc.json:1: not valid JSON — Expecting value: line 2 column 1".
2. `catalog` emitted `{id, text, slug, subject_id, level, exams}`; the proposer
   wants `{id, slug, name, level, subject, metadata.exams}`. The subject never
   resolved, every candidate set came back empty, and the whole corpus recorded
   UNMAPPED — WITHOUT RAISING. That is the worse of the two: the first one
   stops you, the second hands you 850 rows of nothing.

So this test runs the three commands against one in-memory fixture and asserts
on what comes out the far end, not on what each step does alone. The fixture's
shape is demo's: three shared body-agnostic subjects whose rows carry no
`metadata.exams`, and section labels as the SSC export prints them.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


review = _load("pyq_question_review")
proposer = _load("propose_pyq_topic_tags")

#: Demo's subject ids, and the section labels the SSC export carries.
QA = "55555555-5555-5555-5555-555555555551"
ENG = "55555555-5555-5555-5555-555555555552"
GIR = "55555555-5555-5555-5555-555555555553"
SUBJECT_SLUG = {
    QA: "quantitative-aptitude",
    ENG: "english-language",
    GIR: "general-intelligence-reasoning",
}
SECTION_LABEL = {
    "sec-qa": "Quantitative Aptitude",
    "sec-gir": "General Intelligence and Reasoning",
    "sec-eng": "English Comprehension",
}
ALIAS_MAP = _ROOT / "workbench" / "audit" / "ssc_cgl" / "ssc_section_aliases.json"

EXAM = "e-ssc-cgl"
PHASE = "p-tier-1"


def _topic(n: int, subject_id: str, name: str) -> dict:
    return {
        "id": f"t-{n:03d}",
        "subject_id": subject_id,
        "parent_topic_id": f"macro-{subject_id[-3:]}",
        "slug": f"s-{n:03d}",
        "name": name,
        "level": "microtopic",
        "is_active": True,
        # Body-agnostic: no metadata.exams, which is the whole reason the
        # runbook mandates --any-body.
        "metadata": {},
    }


TOPICS = (
    [_topic(i, QA, f"QA leaf {i}") for i in range(1, 5)]
    + [_topic(10 + i, GIR, f"Reasoning leaf {i}") for i in range(1, 4)]
    + [_topic(20 + i, ENG, f"English leaf {i}") for i in range(1, 3)]
)

PAPERS = [
    {"id": "pap-1", "exam_id": EXAM, "exam_phase_id": PHASE, "year": 2024,
     "paper_code": "SSC-CGL-2024-T1-S1", "source_type": "official",
     "source_url": "https://example.test/1.pdf", "trust_status": "pending"},
    {"id": "pap-2", "exam_id": EXAM, "exam_phase_id": PHASE, "year": 2024,
     "paper_code": "SSC-CGL-2024-T1-S2", "source_type": "official",
     "source_url": "https://example.test/2.pdf", "trust_status": "pending"},
]

QUESTIONS = [
    {"id": "q-1", "pyq_paper_id": "pap-1", "question_number": 1,
     "question_text": "Find the value of sin A when cos A = 3/5.",
     "question_type": "mcq", "reviewer_status": "pending",
     "section_id": "sec-qa", "metadata": {}},
    {"id": "q-2", "pyq_paper_id": "pap-1", "question_number": 2,
     "question_text": "If A is coded as 3, how is CAT coded?",
     "question_type": "mcq", "reviewer_status": "pending",
     "section_id": "sec-gir", "metadata": {}},
    {"id": "q-3", "pyq_paper_id": "pap-2", "question_number": 1,
     "question_text": "Choose the correctly spelt word.",
     "question_type": "mcq", "reviewer_status": "pending",
     "section_id": "sec-eng", "metadata": {}},
    {"id": "q-4", "pyq_paper_id": "pap-2", "question_number": 2,
     "question_text": "A tower subtends an angle of 30 degrees. Find its height.",
     "question_type": "mcq", "reviewer_status": "pending",
     "section_id": "sec-qa", "metadata": {}},
]


class FakeClient:
    """Enough of `Client.all_items` to run export and catalog offline."""

    def __init__(self):
        self.calls: list[str] = []

    def all_items(self, path, params=None, page=200):
        params = params or {}
        self.calls.append(path)
        if path.endswith("/pyq-papers"):
            return [p for p in PAPERS if p["exam_id"] == params.get("exam_id")]
        if path.endswith("/exam-phase-sections"):
            return [{"id": sid, "section_label": label}
                    for sid, label in SECTION_LABEL.items()]
        if path.endswith("/pyq-questions"):
            return [q for q in QUESTIONS
                    if q["pyq_paper_id"] == params.get("pyq_paper_id")]
        if path.endswith("/pyq-question-topic-tags"):
            return []
        if path.endswith("/pyq-stimuli"):
            return []
        if path.endswith("/pyq-question-stimuli"):
            return []
        if path.endswith("/pyq-options"):
            return []
        if path.endswith("/topics"):
            sid = params.get("subject_id")
            return [t for t in TOPICS if not sid or t["subject_id"] == sid]
        if path.endswith("/subjects"):
            return [{"id": k, "slug": v, "name": v.replace("-", " ").title()}
                    for k, v in SUBJECT_SLUG.items()]
        raise AssertionError(f"unstubbed route {path}")


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _export(tmp_path) -> pathlib.Path:
    out = tmp_path / "review_out_ssc"
    rc = review.do_export(FakeClient(), Args(
        exam_id=EXAM, paper_id=None, exam_phase_id=[PHASE], mains_phase_id=None,
        status="all", out=str(out), apply=True,
    ))
    assert rc == 0
    return out


def _catalog(tmp_path, *, apply=True) -> pathlib.Path:
    out = tmp_path / "topic_catalog_ssc.json"
    rc = review.do_catalog(FakeClient(), Args(
        body=None, any_body=True, subject_id=[QA, GIR, ENG], is_active=True,
        out=str(out), apply=apply,
    ))
    assert rc == 0
    return out


# ── step 1: export ────────────────────────────────────────────────────────

def test_export_writes_the_section_label_the_alias_map_keys_on(tmp_path):
    rows = json.loads((_export(tmp_path) / "questions_export.json").read_text())
    assert len(rows) == 4
    assert {r["section"] for r in rows} == set(SECTION_LABEL.values())


# ── step 2: catalog ───────────────────────────────────────────────────────

def test_catalog_writes_a_json_list_not_jsonl(tmp_path):
    """The format half of bug 1, stated at the source: this IS a JSON list,
    and the proposer has to cope with that rather than the file changing."""
    text = _catalog(tmp_path).read_text()
    assert text.lstrip().startswith("[")
    assert isinstance(json.loads(text), list)


def test_catalog_emits_the_proposers_contract(tmp_path):
    """Bug 2, fixed on the emitting side."""
    rows = json.loads(_catalog(tmp_path).read_text())
    assert len(rows) == len(TOPICS) == 9
    for r in rows:
        assert r["level"] == "microtopic"
        assert r["name"] and r["slug"] and r["id"]
        assert r["subject"] in set(SUBJECT_SLUG.values())
        assert isinstance(r["metadata"]["exams"], list)


def test_catalog_keeps_the_older_keys_for_existing_readers(tmp_path):
    """`load_topic_catalog` and the committed workbench dumps read `text`."""
    rows = json.loads(_catalog(tmp_path).read_text())
    for r in rows:
        assert r["text"] == r["name"]
        assert r["subject_id"] in SUBJECT_SLUG
        assert r["exams"] == r["metadata"]["exams"]


def test_the_catalog_file_still_loads_as_a_topic_catalog(tmp_path):
    """The same file is `apply --topic-catalog`'s input. Changing its shape
    for the proposer must not break the tool that consumes it at the end."""
    valid, orphan, names = review.load_topic_catalog(str(_catalog(tmp_path)))
    assert len(valid) == 9 and not orphan
    assert names["t-001"] == "QA leaf 1"


# ── step 3: propose, chained on the file step 2 wrote ─────────────────────

def _fixture_responses(question_ids, slug_by_subject):
    """One canned model response per batch, naming a real candidate slug.

    Confidence VARIES across the batch on purpose: the proposer rejects a batch
    whose every mapped row carries the same number, because that is a constant
    rather than an estimate. A fixture that trips that guard would be testing
    the guard, not the chain.
    """
    return [json.dumps({"proposals": [
        {"question_id": qid, "status": "MAPPED", "topic_slug": slug,
         "confidence": round(0.72 + 0.05 * i, 2), "difficulty": "medium",
         "rationale": "fixture", "reason": None}
        for i, (qid, slug) in enumerate(zip(question_ids, slug_by_subject))
    ]})]


def _propose(tmp_path, catalogue, questions, extra=(), expect_ids=None):
    """Run the proposer over the file `catalog` wrote, with a canned response.

    `expect_ids` narrows the fixture to the slice `--papers` / `--limit` will
    leave, since the response has to cover its batch exactly.
    """
    fixture = tmp_path / "fixture.json"
    rows = json.loads(pathlib.Path(questions).read_text())
    if expect_ids is not None:
        rows = [r for r in rows if r["id"] in set(expect_ids)]
    cat = json.loads(pathlib.Path(catalogue).read_text())
    by_subject = {}
    for r in cat:
        by_subject.setdefault(r["subject"], r["slug"])
    alias = json.loads(ALIAS_MAP.read_text())
    slugs = [by_subject[alias[r["section"]]] for r in rows]
    fixture.write_text(json.dumps(
        _fixture_responses([r["id"] for r in rows], slugs)))

    argv = [
        "--questions", str(questions),
        "--catalogue", str(catalogue),
        "--alias-map", str(ALIAS_MAP),
        "--subject-field", "section",
        "--any-body",
        "--batch-size", "50",
        "--dry-run", "--fixture", str(fixture),
        "--out-jsonl", str(tmp_path / "proposals.jsonl"),
        "--out-sql", str(tmp_path / "proposals.sql"),
        *extra,
    ]
    rc = proposer.main(argv)
    return rc, tmp_path / "proposals.jsonl"


def test_the_runbook_chain_runs_and_maps_every_question(tmp_path):
    """THE REGRESSION. Before the fix this aborted at the JSON/JSONL check;
    with that patched alone it ran to completion and mapped nothing."""
    out = _export(tmp_path)
    catalogue = _catalog(tmp_path)
    rc, jsonl = _propose(tmp_path, catalogue, out / "questions_export.json")

    assert rc == 0
    proposals = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert len(proposals) == 4
    assert {p["status"] for p in proposals} == {"MAPPED"}
    # The bug's signature: a candidate set of zero on every question.
    assert all(p["candidate_count"] > 0 for p in proposals)


def test_each_question_only_sees_its_own_subjects_leaves(tmp_path):
    """The subject filter is doing real work — a chain that resolved the
    subject to the same wrong value everywhere would also 'map' every row."""
    out = _export(tmp_path)
    catalogue = _catalog(tmp_path)
    questions = proposer.load_questions(
        str(out / "questions_export.json"),
        proposer.load_alias_map(str(ALIAS_MAP)),
        any_body=True, subject_field="section",
    )
    rows = proposer.load_catalogue(str(catalogue))
    counts = {
        q["id"]: len(proposer.build_candidates(q, rows, any_body=True))
        for q in questions
    }
    assert counts == {"q-1": 4, "q-2": 3, "q-3": 2, "q-4": 4}


def test_a_catalogue_without_the_subject_slug_is_refused_by_name(tmp_path):
    """The old shape, as it would arrive from an export taken before this fix.
    Silently empty candidate sets are what made the bug expensive, so a uuid
    the alias map cannot name is an error, not an empty result."""
    legacy = tmp_path / "legacy_catalog.json"
    legacy.write_text(json.dumps([
        {"id": "t-001", "text": "QA leaf 1", "slug": "s-001",
         "subject_id": "99999999-9999-9999-9999-999999999999",
         "level": "microtopic", "exams": []},
    ]))
    with pytest.raises(proposer.ProposerError) as exc:
        proposer.load_catalogue(str(legacy), {})
    assert "is a uuid, not a subject slug" in str(exc.value)


def test_a_legacy_catalogue_resolves_through_the_alias_map(tmp_path):
    """…and with the id in the alias map, an export taken before this fix still
    runs. That is what keeps the committed exports usable."""
    legacy = tmp_path / "legacy_catalog.json"
    legacy.write_text(json.dumps([
        {"id": "t-001", "text": "QA leaf 1", "slug": "s-001",
         "subject_id": QA, "level": "microtopic", "exams": []},
    ]))
    rows = proposer.load_catalogue(
        str(legacy), proposer.load_alias_map(str(ALIAS_MAP)))
    assert rows[0]["subject"] == "quantitative-aptitude"
    assert rows[0]["name"] == "QA leaf 1"


def test_a_jsonl_catalogue_still_loads(tmp_path):
    """The proposer's original format is not dropped by accepting the other."""
    path = tmp_path / "cat.jsonl"
    path.write_text("\n".join(json.dumps({
        "id": "t-001", "slug": "s-001", "name": "QA leaf 1",
        "level": "microtopic", "subject": "quantitative-aptitude",
        "metadata": {"exams": []},
    }) for _ in range(1)))
    assert proposer.load_catalogue(str(path))[0]["subject"] == "quantitative-aptitude"


# ── the pilot flags ───────────────────────────────────────────────────────

def test_limit_runs_a_pilot_slice_in_file_order(tmp_path):
    out = _export(tmp_path)
    catalogue = _catalog(tmp_path)
    rc, jsonl = _propose(tmp_path, catalogue, out / "questions_export.json",
                         extra=["--limit", "2"], expect_ids=["q-1", "q-2"])
    assert rc == 0
    proposals = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert [p["question_id"] for p in proposals] == ["q-1", "q-2"]


def test_papers_restricts_to_one_paper_before_limit(tmp_path):
    out = _export(tmp_path)
    catalogue = _catalog(tmp_path)
    rc, jsonl = _propose(tmp_path, catalogue, out / "questions_export.json",
                         extra=["--papers", "pap-2"], expect_ids=["q-3", "q-4"])
    assert rc == 0
    proposals = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert sorted(p["question_id"] for p in proposals) == ["q-3", "q-4"]


def test_a_paper_id_that_matches_nothing_is_an_error_not_an_empty_run():
    rows = [{"id": "q-1", "paper_id": "pap-1"}]
    with pytest.raises(proposer.ProposerError) as exc:
        proposer.select_questions(rows, papers=["pap-typo"])
    assert "no question matches --papers" in str(exc.value)


def test_a_paper_named_alongside_a_real_one_is_still_reported():
    """`--papers pap-1 pap-typo` must not quietly run pap-1 alone."""
    rows = [{"id": "q-1", "paper_id": "pap-1"}]
    with pytest.raises(proposer.ProposerError) as exc:
        proposer.select_questions(rows, papers=["pap-1", "pap-typo"])
    assert "pap-typo" in str(exc.value)


def test_limit_larger_than_the_corpus_is_not_an_error():
    rows = [{"id": "q-1", "paper_id": "p"}, {"id": "q-2", "paper_id": "p"}]
    assert len(proposer.select_questions(rows, limit=99)) == 2


# ── the runbook's argv, not just its functions ────────────────────────────

def test_the_printed_commands_parse_and_run_as_written(tmp_path, monkeypatch):
    """The README prints argv, not function calls. A flag renamed or a path
    that does not exist is a broken runbook even when the functions are fine —
    which is how `--catalogue catalogue_ssc.jsonl` (a file the repo never had)
    survived review.

    `Client` is stubbed at the transport; everything above it is the real CLI.
    """
    monkeypatch.setenv("CCP_API_BASE", "https://example.test")
    monkeypatch.setenv("CCP_ADMIN_JWT", "token")
    monkeypatch.setattr(review, "Client", lambda *a, **k: FakeClient())

    out = tmp_path / "review_out_ssc"
    assert review.main([
        "export",
        "--exam-id", EXAM,
        "--exam-phase-id", PHASE,
        "--status", "all",
        "--out", str(out), "--apply",
    ]) == 0

    catalogue = tmp_path / "topic_catalog_ssc.json"
    assert review.main([
        "catalog",
        "--any-body",
        "--subject-id", QA, "--subject-id", GIR, "--subject-id", ENG,
        "--is-active",
        "--out", str(catalogue), "--apply",
    ]) == 0

    rc, jsonl = _propose(tmp_path, catalogue, out / "questions_export.json")
    assert rc == 0
    assert len(jsonl.read_text().strip().splitlines()) == 4


def test_the_readme_does_not_reference_a_file_the_repo_lacks(tmp_path):
    readme = (_ROOT / "workbench" / "audit" / "ssc_cgl" / "README.md").read_text()
    # The alias map it names must exist at the path it prints.
    assert "workbench/audit/ssc_cgl/ssc_section_aliases.json" in readme
    assert ALIAS_MAP.is_file()
    # The dangling name it used to print is gone, as is the JSONL claim.
    assert "catalogue_ssc.jsonl" not in readme
    # The proposer is pointed at the file `catalog` actually writes.
    assert "--catalogue topic_catalog_ssc.json" in readme
    # And the pilot is documented, since that is what --papers is for.
    assert "--papers" in readme


# ── the alias map the runbook names ───────────────────────────────────────

def test_the_alias_map_the_readme_references_exists_and_covers_the_sections():
    alias = proposer.load_alias_map(str(ALIAS_MAP))
    for label in SECTION_LABEL.values():
        assert alias[proposer.normalise_subject(label)] in set(SUBJECT_SLUG.values())


def test_the_alias_map_also_names_the_three_subject_ids():
    """So a catalogue exported before this fix resolves without a re-export."""
    alias = proposer.load_alias_map(str(ALIAS_MAP))
    for sid, slug in SUBJECT_SLUG.items():
        assert alias[proposer.normalise_subject(sid)] == slug
