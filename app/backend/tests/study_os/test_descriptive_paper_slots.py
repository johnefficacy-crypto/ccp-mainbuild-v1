"""The paper-slot contract, against the shape the GS split actually left on demo.

THE BUG THIS FILE EXISTS FOR. The Essay tab encoded itself as
``paper_number=99``. The endpoint validated ``1 <= paper_number <= 10``, so
every Essay click answered 422: a magic number one side knew and the other
refused. Alongside it, the tab counts were computed from the half that the
SELECTED tab had already filtered, so the response said "General Studies · 934
questions" while reading GS1 0, GS2 0, GS3 0, GS4 192, Essay 0.

So the fixture is the demo's shape and not a convenient one: ``gs_paper`` is a
STRING on the paper metadata, the paper codes are the split's real codes, and
the GS questions carry their tags on the SITTING — General Studies has no
thematic half at all, which is why its by-syllabus lens read "No syllabus
themes" on 873 tagged questions.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.persona_questions._stub import SBStub

from app.api import descriptive_practice as routes
from app.core.auth import get_current_user
from app.study_os import descriptive as d

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-demo"
PSIR = "Political Science and International Relations"
GS = d.GENERAL_STUDIES

#: Demo's real GS paper codes.
def _code(year: int, slot: str) -> str:
    return f"UPSC-CSE-MAINS-GS-{year}-{slot}"


def _paper(pid, year, code, meta, trust="pending"):
    return {"id": pid, "exam_id": EXAM, "year": year, "paper_code": code,
            "trust_status": trust, "metadata": meta}


def _q(qid, paper, number, text, meta=None):
    return {"id": qid, "pyq_paper_id": paper, "question_number": number,
            "question_text": text, "question_type": "descriptive",
            "reviewer_status": "verified", "metadata": meta or {}}


def _seed(*, gs_paper_as_string: bool = True) -> dict[str, Any]:
    """Two GS years and one optional subject, in the split's own shape.

    `gs_paper` IS A STRING ON DEMO. `str()`/`int()` confusion here is the
    difference between GS3 holding its questions and GS3 reading zero, so the
    fixture is parameterised on it and both forms are asserted.
    """
    def gsv(n: int) -> Any:
        return str(n) if gs_paper_as_string else n

    papers = []
    questions = []
    tags = []
    for year in (2024, 2025):
        for n in (1, 2, 3, 4):
            pid = f"gs-{year}-{n}"
            papers.append(_paper(pid, year, _code(year, f"GS{n}"),
                                 {"paper_kind": "gs", "gs_paper": gsv(n),
                                  "paper_code": _code(year, f"GS{n}"),
                                  "split_from_bucket_id": f"bucket-{year}"}))
            # Three questions per GS paper per year: 24 GS questions in all,
            # so a slot that collapses to another's count is visible.
            for i in (1, 2, 3):
                qid = f"{pid}-q{i}"
                questions.append(_q(qid, pid, i, f"GS{n} {year} question {i}."))
                tags.append({"question_id": qid, "topic_id": f"micro-gs{n}",
                             "tag_role": "primary", "reviewer_status": "verified"})
        epid = f"essay-{year}"
        papers.append(_paper(epid, year, _code(year, "ESSAY"),
                             {"paper_kind": "essay", "gs_paper": "ESSAY",
                              "paper_code": _code(year, "ESSAY"),
                              "split_from_bucket_id": f"bucket-{year}"}))
        for i in (1, 2):
            questions.append(_q(f"{epid}-q{i}", epid, i,
                                f"Write an essay, {year}, prompt {i}."))

    # The retired bucket both years were split out of.
    for year in (2024, 2025):
        papers.append(_paper(f"bucket-{year}", year, None,
                             {"paper_kind": "gs", "retired": True}, trust="verified"))

    # One optional subject, so P1/P2 are exercised by the same contract.
    for n in (1, 2):
        pid = f"psir-2025-p{n}"
        papers.append(_paper(pid, 2025, f"UPSC-CSE-MAINS-OPT-2025-PSIR-P{n}",
                             {"paper_kind": "optional", "optional_subject": PSIR,
                              "optional_paper_number": n}))
        questions.append(_q(f"{pid}-q1", pid, 1, f"PSIR P{n} question.",
                            {"optional_subject": PSIR, "optional_paper_number": n}))

    return {
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": [
            {"id": f"micro-gs{n}", "name": f"GS{n} microtopic", "level": "microtopic",
             "parent_topic_id": f"macro-gs{n}", "subject_id": f"subj-gs{n}",
             "metadata": {}}
            for n in (1, 2, 3, 4)
        ] + [
            {"id": f"macro-gs{n}", "name": f"GS{n} section", "level": "topic",
             "parent_topic_id": None, "subject_id": f"subj-gs{n}", "metadata": {}}
            for n in (1, 2, 3, 4)
        ],
        "subjects": [
            {"id": f"subj-gs{n}", "slug": f"upsc-cse-mains-gs{n}"} for n in (1, 2, 3, 4)
        ],
        "descriptive_attempts": [],
    }


def _sb(**kw) -> Any:
    return SBStub(_seed(**kw))


def _client(sb, monkeypatch) -> TestClient:
    monkeypatch.setattr(routes, "get_supabase_admin", lambda: sb)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_current_user] = lambda: {"id": USER}
    return TestClient(app)


def _slots(out) -> dict[str, int]:
    return {s["slot"]: s["question_count"] for s in out["paper_slots"]}


# ── 1. every tab slot answers, for GS and for an optional ──────────────────

GS_SLOTS = ["GS1", "GS2", "GS3", "GS4", "ESSAY"]
OPT_SLOTS = ["P1", "P2"]


@pytest.mark.parametrize("slot", GS_SLOTS)
def test_every_gs_tab_slot_is_a_200_on_the_catalog(slot, monkeypatch):
    """Including ESSAY, which was a 422 for as long as it travelled as 99."""
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": GS, "paper": slot})
    assert res.status_code == 200, res.text
    assert res.json()["paper"] == slot


@pytest.mark.parametrize("slot", OPT_SLOTS)
def test_every_optional_tab_slot_is_a_200_on_the_catalog(slot, monkeypatch):
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": PSIR, "paper": slot})
    assert res.status_code == 200, res.text
    assert res.json()["paper"] == slot


@pytest.mark.parametrize("slot", GS_SLOTS + OPT_SLOTS)
def test_every_tab_slot_is_a_200_on_the_question_list(slot, monkeypatch):
    client = _client(_sb(), monkeypatch)
    subject = GS if slot in GS_SLOTS else PSIR
    res = client.get("/study/descriptive/questions",
                     params={"exam_id": EXAM, "subject": subject, "paper": slot,
                             "year": 2025})
    assert res.status_code == 200, res.text


def test_a_lowercase_slot_is_the_same_slot(monkeypatch):
    """The tab's own label is "Essay". A client echoing it must not 400."""
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": GS, "paper": "essay"})
    assert res.status_code == 200
    assert res.json()["paper"] == "ESSAY"


def test_an_unknown_slot_is_refused_by_name_not_silently_ignored(monkeypatch):
    """Coercing it to "no filter" would answer a GS9 request with the whole
    subject, which is a wrong answer rather than an error."""
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": GS, "paper": "GS9"})
    assert res.status_code == 400
    body = res.json()["detail"]
    assert body["code"] == "paper_slot_invalid"
    assert "GS1" in body["message"] and "ESSAY" in body["message"]


def test_a_slot_from_the_other_structure_is_refused(monkeypatch):
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": PSIR, "paper": "GS3"})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "paper_slot_invalid"


# ── 2. the legacy integer still opens the links already sent out ───────────

def test_the_old_essay_number_resolves_instead_of_422ing(monkeypatch):
    """`paper_number=99` was the exact request demo answered 422 to."""
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": GS, "paper_number": 99})
    assert res.status_code == 200, res.text
    assert res.json()["paper"] == "ESSAY"


def test_the_old_integer_resolves_within_the_subject(monkeypatch):
    client = _client(_sb(), monkeypatch)
    for subject, number, slot in ((GS, 3, "GS3"), (PSIR, 2, "P2")):
        res = client.get("/study/descriptive/catalog",
                         params={"exam_id": EXAM, "subject": subject,
                                 "paper_number": number})
        assert res.status_code == 200
        assert res.json()["paper"] == slot


def test_an_integer_no_paper_has_is_refused(monkeypatch):
    client = _client(_sb(), monkeypatch)
    res = client.get("/study/descriptive/catalog",
                     params={"exam_id": EXAM, "subject": PSIR, "paper_number": 4})
    assert res.status_code == 400


# ── 3. the tab counts (demo read GS1 0, GS2 0, GS3 0, GS4 192, Essay 0) ────

@pytest.mark.parametrize("as_string", [True, False])
def test_every_gs_slot_reports_its_own_questions(as_string):
    """`gs_paper` is a STRING on demo. Both forms place the same."""
    out = d.get_catalog(_sb(gs_paper_as_string=as_string), EXAM, subject=GS)
    assert _slots(out) == {"GS1": 6, "GS2": 6, "GS3": 6, "GS4": 6, "ESSAY": 4}


@pytest.mark.parametrize("slot", GS_SLOTS)
def test_the_tabs_report_the_same_counts_whichever_tab_is_open(slot):
    """THE TAB IS HOW THE ASPIRANT LEAVES THE PAPER THEY ARE ON. Counting the
    tabs off the filtered half made every other tab read 0 — a tab bar that
    says the corpus is empty everywhere except where you already are."""
    unfiltered = _slots(d.get_catalog(_sb(), EXAM, subject=GS))
    assert _slots(d.get_catalog(_sb(), EXAM, subject=GS, paper=slot)) == unfiltered


def test_the_slot_counts_add_up_to_the_subject_count():
    """934 in the header and 192 across five tabs was the visible symptom."""
    out = d.get_catalog(_sb(), EXAM, subject=GS)
    assert sum(_slots(out).values()) == out["total_questions"] == 28


def test_choosing_a_tab_still_scopes_the_sittings_and_years():
    out = d.get_catalog(_sb(), EXAM, subject=GS, paper="GS3")
    assert {p["paper_slot"] for p in out["papers"]} == {"GS3"}
    assert [y["question_count"] for y in out["years"]] == [3, 3]


def test_the_essay_tab_holds_the_essay_papers():
    out = d.get_catalog(_sb(), EXAM, subject=GS, paper="ESSAY")
    assert {p["paper_slot"] for p in out["papers"]} == {"Essay"}
    assert sum(p["question_count"] for p in out["papers"]) == 4


def test_an_optional_subject_is_unchanged_by_the_slot_rewrite():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert _slots(out) == {"P1": 1, "P2": 1}


# ── 4. the by-syllabus lens under General Studies ──────────────────────────

def _themes(out) -> set[str]:
    return {t["theme"] for p in out["themes"] for s in p["sections"] for t in s["themes"]}


def test_general_studies_has_a_syllabus_tree():
    """It read "No syllabus themes" on demo. GS has no thematic half — the
    split produced 55 real sittings — so a tree built from the thematic half
    alone was empty while every one of its questions carried a tag."""
    out = d.get_catalog(_sb(), EXAM, subject=GS)
    assert _themes(out) == {f"GS{n} microtopic" for n in (1, 2, 3, 4)}
    assert out["syllabus_supported"] is True


def test_the_gs_tree_is_grouped_by_its_subject_paper():
    out = d.get_catalog(_sb(), EXAM, subject=GS)
    assert {p["paper_number"] for p in out["themes"]} == {1, 2, 3, 4}
    assert {s["section"] for p in out["themes"] for s in p["sections"]} == {
        f"GS{n} section" for n in (1, 2, 3, 4)
    }


def test_a_gs_tab_filters_the_tree_to_that_paper():
    out = d.get_catalog(_sb(), EXAM, subject=GS, paper="GS2")
    assert _themes(out) == {"GS2 microtopic"}


def test_the_essay_tab_says_it_has_no_tree_rather_than_showing_an_empty_one():
    """Essay's tags are the Essay taxonomy, not GS microtopics. "No themes yet"
    reads as missing data and invites waiting for something never coming."""
    out = d.get_catalog(_sb(), EXAM, subject=GS, paper="ESSAY")
    assert out["syllabus_supported"] is False
    assert out["themes"] == []


def test_a_gs_theme_opens_its_questions():
    """The catalogue offering a theme whose question list is empty is the same
    bug one level down: `list_questions` restricted a theme to the thematic
    half, and General Studies has none."""
    out = d.list_questions(_sb(), USER, exam_id=EXAM, subject=GS,
                           theme="GS3 microtopic")
    assert out["total_matching"] == 6
    assert all("GS3" in i["text"] for i in out["items"])


def test_an_untagged_gs_sitting_is_not_an_untagged_pile_on_the_tree():
    """Tagging coverage is the platform's to-do list, not something an aspirant
    can use — and a sitting is still reachable by year."""
    seed = _seed()
    seed["pyq_question_topic_tags"] = [
        t for t in seed["pyq_question_topic_tags"] if not t["question_id"].endswith("q3")
    ]
    out = d.get_catalog(SBStub(seed), EXAM, subject=GS)
    assert d.UNTAGGED_THEME not in _themes(out)
    assert _slots(out)["GS1"] == 6          # the tab still counts every question


# ── 5. performance: the corpus is read once, not once per tab ──────────────

class CountingSB(SBStub):
    """SBStub that records round trips by table. One `.table(...)` is one."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.tables: list[str] = []

    def table(self, name):
        self.tables.append(name)
        return super().table(name)

    def hits(self, name: str) -> int:
        return self.tables.count(name)


def test_switching_tabs_does_not_re_read_the_corpus():
    """THE 12-15 SECOND CATALOGUE. Every tab click re-read every paper and
    every verified question for the exam. Four clicks were four full reads of
    twelve thousand rows, and the aspirant watched each one.

    The corpus is exam-scoped and identical for every aspirant, so it is the
    part that can be shared; attempts are user-scoped and are read every time.
    """
    sb = CountingSB(_seed())
    d.get_catalog(sb, EXAM, subject=GS, user_id=USER)
    # The baseline is one full build. A read is more than one round trip — the
    # range walk asks for a page and then for the page after it — so the claim
    # is that the corpus reads do not RECUR, not that they are single calls.
    corpus = {t: sb.hits(t) for t in ("pyq_papers", "pyq_questions",
                                      "pyq_question_topic_tags")}
    attempts = sb.hits("descriptive_attempts")

    for slot in GS_SLOTS:
        d.get_catalog(sb, EXAM, subject=GS, paper=slot, user_id=USER)

    assert {t: sb.hits(t) for t in corpus} == corpus
    # Attempts are user-scoped, so they are read every time: one aspirant's
    # progress is never served from another's request.
    assert sb.hits("descriptive_attempts") > attempts


def test_the_first_catalogue_is_a_bounded_number_of_round_trips():
    """A guard on the SHAPE of the read, not on wall-clock: the corpus is two
    reads plus a bounded tail for tags, topics and attempts. A regression that
    reintroduces a per-paper or per-question read shows up here as the fixture
    grows."""
    small = CountingSB(_seed())
    d.get_catalog(small, EXAM, subject=GS)
    d.reset_caches()          # the second client is a different corpus

    # The same shape with eight times the questions must cost the same number
    # of round trips — the read is paginated, not per row.
    seed = _seed()
    extra = []
    for q in seed["pyq_questions"]:
        for i in range(8):
            extra.append({**q, "id": f"{q['id']}-copy{i}"})
    seed["pyq_questions"].extend(extra)
    big = CountingSB(seed)
    d.get_catalog(big, EXAM, subject=GS)

    assert big.hits("pyq_papers") == small.hits("pyq_papers")
    assert big.hits("pyq_questions") == small.hits("pyq_questions")
    # Nine times the questions costs a handful more calls — the id-filtered
    # reads are chunked at 200 ids — and nothing that scales with a row. A
    # per-paper or per-question read would show here as a multiple.
    assert len(small.tables) <= 12
    assert len(big.tables) <= len(small.tables) + 4


def test_a_failed_read_is_never_cached_as_the_answer():
    """An outage must not become "this exam has no questions" for a minute."""
    class Broken(SBStub):
        def table(self, name):
            if name == "pyq_papers":
                raise RuntimeError("PostgREST is down")
            return super().table(name)

    with pytest.raises(d.DescriptiveError):
        d.get_catalog(Broken(_seed()), EXAM, subject=GS)
    # The next caller, on a working client, gets the real corpus.
    assert _slots(d.get_catalog(_sb(), EXAM, subject=GS))["GS1"] == 6


def test_the_question_list_reuses_the_catalogues_corpus():
    sb = CountingSB(_seed())
    d.get_catalog(sb, EXAM, subject=GS)
    # `pyq_papers` is read ONLY by the corpus load, so it is the unambiguous
    # witness: the page-scoped reads that follow (parent stems, labels) touch
    # `pyq_questions` by id and are not the twelve-thousand-row walk.
    papers = sb.hits("pyq_papers")

    d.list_questions(sb, USER, exam_id=EXAM, subject=GS, paper="GS1", year=2025)
    d.coverage(sb, USER, exam_id=EXAM)

    assert sb.hits("pyq_papers") == papers


def test_the_cache_expires_rather_than_holding_a_stale_corpus(monkeypatch):
    """A split or an ingest lands out of process, so the only invalidation this
    module can honour is time. Stating the bound is the point."""
    clock = [0.0]
    monkeypatch.setattr(d, "_monotonic", lambda: clock[0])
    sb = CountingSB(_seed())
    d.get_catalog(sb, EXAM, subject=GS)
    before = sb.hits("pyq_papers")
    clock[0] = d.CORPUS_TTL_SECONDS + 1
    d.get_catalog(sb, EXAM, subject=GS)
    assert sb.hits("pyq_papers") > before
