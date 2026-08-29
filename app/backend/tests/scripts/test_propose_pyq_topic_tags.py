"""Unit tests for ``scripts/propose_pyq_topic_tags.py``.

The script lives at the repo root (mirroring scripts/docx_to_pyq_json.py), so it
is loaded by absolute path rather than via the ``scripts`` package.

Coverage targets the three places this pipeline can quietly produce a wrong tag
rather than fail:
- the candidate filter, which is the only thing keeping a proposal inside the
  catalogue and inside the question's own regulator;
- response parsing, which must reject rather than default;
- the writer, whose idempotency key is the only thing standing between a
  re-run and a duplicate row.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "propose_pyq_topic_tags.py"
_spec = importlib.util.spec_from_file_location("propose_pyq_topic_tags", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# ── fixtures ─────────────────────────────────────────────────────────────────

QID_1 = "11111111-1111-4111-8111-111111111111"
QID_2 = "22222222-2222-4222-8222-222222222222"
TID_MONEY = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
TID_PENSION = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
TID_BOARD = "cccccccc-3333-4333-8333-cccccccccccc"


def _catalogue_row(topic_id, slug, subject, exams, level="microtopic", name=None):
    return {
        "id": topic_id,
        "slug": slug,
        "name": name or slug.replace("-", " ").title(),
        "level": level,
        "subject": subject,
        "description": f"Description of {slug}.",
        "metadata": {"exams": list(exams)},
    }


def _catalogue():
    return [
        _catalogue_row(TID_MONEY, "money-market-instruments", "economics",
                       ["sebi", "ifsca"]),
        _catalogue_row(TID_PENSION, "pension-fund-regulation", "economics",
                       ["pfrda"]),
        _catalogue_row(TID_BOARD, "board-composition", "companies-act",
                       ["sebi", "pfrda", "ifsca"]),
        # Right subject and body, wrong granularity — must never be a candidate.
        _catalogue_row("dddddddd-4444-4444-8444-dddddddddddd", "macroeconomics",
                       "economics", ["sebi"], level="topic"),
    ]


def _question(qid=QID_1, subject="Economy", body="sebi", text="What is a T-bill?"):
    return {
        "id": qid,
        "question_text": text,
        "subject": subject,
        "body": body,
        "options": [{"label": "a", "text": "One"}, {"label": "b", "text": "Two"}],
    }


ALIAS_MAP = {"Economy": "economics", "Company Act": "companies-act"}


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    return str(path)


def _write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _loaded(tmp_path, questions=None, catalogue=None, alias_map=None):
    """Load through the real file readers, not by hand-building dicts."""
    amap = mod.load_alias_map(
        _write_json(tmp_path / "alias.json", alias_map or ALIAS_MAP))
    cat = mod.load_catalogue(
        _write_jsonl(tmp_path / "cat.jsonl", catalogue or _catalogue()))
    qs = mod.load_questions(
        _write_jsonl(tmp_path / "q.jsonl", questions or [_question()]), amap)
    return qs, cat


def _response(entries):
    return json.dumps({"proposals": entries})


def _mapped(qid, slug, confidence=0.82, rationale="Stem names the instrument."):
    return {"question_id": qid, "status": "MAPPED", "topic_slug": slug,
            "confidence": confidence, "rationale": rationale, "reason": None}


# ── 1. candidate builder ─────────────────────────────────────────────────────


def test_subject_resolves_only_through_the_alias_map(tmp_path):
    """"Economy" is not "economics". String equality would yield zero candidates
    and turn every question in the subject into a spurious UNMAPPED."""
    questions, catalogue = _loaded(tmp_path)
    q = questions[0]

    assert q["raw_subject"] == "Economy"
    assert q["subject"] == "economics"

    cands = mod.build_candidates(q, catalogue)
    assert [c["slug"] for c in cands] == ["money-market-instruments"]


@pytest.mark.parametrize("printed", ["Economy", "economy", "ECONOMY.", "  Economy  "])
def test_alias_lookup_is_insensitive_to_printed_casing_and_padding(tmp_path, printed):
    """The corpus prints one subject several ways; none is a different subject."""
    questions, _ = _loaded(tmp_path, questions=[_question(subject=printed)])
    assert questions[0]["subject"] == "economics"


def test_second_alias_resolves_to_its_own_subject(tmp_path):
    """Company Act -> companies-act, and it picks up that subject's rows only."""
    questions, catalogue = _loaded(
        tmp_path, questions=[_question(subject="Company Act")])
    cands = mod.build_candidates(questions[0], catalogue)
    assert [c["slug"] for c in cands] == ["board-composition"]


def test_a_subject_missing_from_the_alias_map_aborts_naming_it(tmp_path):
    """Silently empty candidates would read as 'nothing fits' rather than
    'nobody mapped this subject'."""
    with pytest.raises(mod.ProposerError, match=r"no entry in the alias map"):
        _loaded(tmp_path, questions=[_question(subject="Polity")])


def test_body_excludes_most_candidates(tmp_path):
    """A PFRDA question cannot be tagged with a SEBI/IFSCA-only microtopic
    however well the text matches."""
    questions, catalogue = _loaded(
        tmp_path, questions=[_question(subject="Economy", body="pfrda")])
    cands = mod.build_candidates(questions[0], catalogue)

    # Of the two economics microtopics, only the PFRDA-scoped one survives.
    assert [c["slug"] for c in cands] == ["pension-fund-regulation"]

    ifsca = dict(questions[0], body="ifsca")
    assert [c["slug"] for c in mod.build_candidates(ifsca, catalogue)] == [
        "money-market-instruments"]


def test_non_microtopic_levels_are_never_candidates(tmp_path):
    """'macroeconomics' matches subject and body but is level='topic'."""
    questions, catalogue = _loaded(tmp_path)
    slugs = [c["slug"] for c in mod.build_candidates(questions[0], catalogue)]
    assert "macroeconomics" not in slugs
    assert all(c["level"] == "microtopic"
               for c in mod.build_candidates(questions[0], catalogue))


def test_an_unknown_regulatory_body_is_rejected_at_load(tmp_path):
    with pytest.raises(mod.ProposerError, match=r"body 'rbi' is not one of"):
        _loaded(tmp_path, questions=[_question(body="rbi")])


# ── 2. proposer ──────────────────────────────────────────────────────────────


def test_unmapped_response_parses_cleanly(tmp_path):
    """UNMAPPED is a correct answer, not a failure — it must survive parsing
    with its reason intact and reach the JSONL."""
    questions, catalogue = _loaded(tmp_path)
    cands = {questions[0]["id"]: mod.build_candidates(questions[0], catalogue)}
    text = _response([{
        "question_id": QID_1, "status": "UNMAPPED", "topic_slug": None,
        "confidence": 0.71, "rationale": "No candidate covers treasury bills.",
        "reason": "Candidates address equity markets only.",
    }])

    [p] = mod.parse_response(text, questions, cands)
    assert p["status"] == "UNMAPPED"
    assert p["topic_slug"] is None
    assert p["reason"] == "Candidates address equity markets only."
    assert p["confidence"] == 0.71


def test_unmapped_without_a_reason_is_rejected(tmp_path):
    questions, catalogue = _loaded(tmp_path)
    cands = {QID_1: mod.build_candidates(questions[0], catalogue)}
    text = _response([{"question_id": QID_1, "status": "UNMAPPED",
                       "topic_slug": None, "confidence": 0.5,
                       "rationale": "None fit.", "reason": ""}])
    with pytest.raises(mod.ProposerError, match=r"UNMAPPED requires a non-empty reason"):
        mod.parse_response(text, questions, cands)


@pytest.mark.parametrize("bad,match", [
    ("not json at all", r"not valid JSON"),
    ('{"proposals": "nope"}', r"'proposals' is str"),
    ('{"results": []}', r"no 'proposals' key"),
    ('[]', r"is a list, expected a JSON object"),
])
def test_malformed_response_fails_loudly_rather_than_defaulting(tmp_path, bad, match):
    questions, catalogue = _loaded(tmp_path)
    cands = {QID_1: mod.build_candidates(questions[0], catalogue)}
    with pytest.raises(mod.ProposerError, match=match):
        mod.parse_response(bad, questions, cands)


@pytest.mark.parametrize("entry,match", [
    ({"question_id": QID_1, "status": "MAYBE", "topic_slug": None,
      "confidence": 0.5, "rationale": "x"}, r"status 'MAYBE' is not"),
    ({"question_id": QID_1, "status": "MAPPED",
      "topic_slug": "money-market-instruments",
      "confidence": "high", "rationale": "x"}, r"confidence is 'high'"),
    ({"question_id": QID_1, "status": "MAPPED",
      "topic_slug": "money-market-instruments",
      "confidence": 1.4, "rationale": "x"}, r"confidence 1.4 is outside"),
    ({"question_id": QID_1, "status": "MAPPED",
      "topic_slug": "money-market-instruments", "confidence": 0.8,
      "rationale": " ".join(["word"] * 21)}, r"rationale is 21 words"),
])
def test_each_field_violation_is_its_own_loud_error(tmp_path, entry, match):
    questions, catalogue = _loaded(tmp_path)
    cands = {QID_1: mod.build_candidates(questions[0], catalogue)}
    with pytest.raises(mod.ProposerError, match=match):
        mod.parse_response(_response([entry]), questions, cands)


def test_a_slug_outside_the_question_candidates_is_rejected(tmp_path):
    """The most damaging failure: a plausible-looking slug that is not this
    question's to use. Caught before it can reach the writer."""
    questions, catalogue = _loaded(tmp_path)
    cands = {QID_1: mod.build_candidates(questions[0], catalogue)}
    # A real catalogue slug, but scoped to another subject and body.
    text = _response([_mapped(QID_1, "board-composition")])
    with pytest.raises(mod.ProposerError, match=r"is not among this question's"):
        mod.parse_response(text, questions, cands)


def test_a_response_that_drops_a_question_is_rejected(tmp_path):
    questions, catalogue = _loaded(
        tmp_path, questions=[_question(QID_1), _question(QID_2)])
    cands = {q["id"]: mod.build_candidates(q, catalogue) for q in questions}
    text = _response([_mapped(QID_1, "money-market-instruments")])
    with pytest.raises(mod.ProposerError, match=r"missing \['2{8}-"):
        mod.parse_response(text, questions, cands)


def test_a_constant_confidence_across_a_batch_is_rejected(tmp_path):
    """"not always 0.9" enforced, not merely requested in the prompt."""
    qs = [_question(f"{i}1111111-1111-4111-8111-111111111111") for i in range(1, 5)]
    questions, catalogue = _loaded(tmp_path, questions=qs)
    cands = {q["id"]: mod.build_candidates(q, catalogue) for q in questions}
    text = _response([
        _mapped(q["id"], "money-market-instruments", confidence=0.9)
        for q in questions
    ])
    with pytest.raises(mod.ProposerError, match=r"that is a constant, not an estimate"):
        mod.parse_response(text, questions, cands)


def test_varied_confidence_across_a_batch_is_accepted(tmp_path):
    qs = [_question(f"{i}1111111-1111-4111-8111-111111111111") for i in range(1, 5)]
    questions, catalogue = _loaded(tmp_path, questions=qs)
    cands = {q["id"]: mod.build_candidates(q, catalogue) for q in questions}
    text = _response([
        _mapped(q["id"], "money-market-instruments", confidence=c)
        for q, c in zip(questions, (0.91, 0.62, 0.78, 0.55))
    ])
    assert [p["confidence"] for p in mod.parse_response(text, questions, cands)] == [
        0.91, 0.62, 0.78, 0.55]


def test_batch_size_is_honoured(tmp_path):
    qs = [_question(f"{i}1111111-1111-4111-8111-111111111111") for i in range(1, 6)]
    questions, catalogue = _loaded(tmp_path, questions=qs)
    seen = []

    def client(prompt):
        ids = [q["id"] for q in questions if f"question_id: {q['id']}" in prompt]
        seen.append(len(ids))
        return _response([
            _mapped(qid, "money-market-instruments", confidence=0.5 + i / 10)
            for i, qid in enumerate(ids)
        ])

    mod.propose(questions, catalogue, client=client, batch_size=2)
    assert seen == [2, 2, 1]


def test_prompt_carries_stem_options_and_candidate_descriptions(tmp_path):
    questions, catalogue = _loaded(tmp_path)
    cands = {questions[0]["id"]: mod.build_candidates(questions[0], catalogue)}
    prompt = mod.build_prompt(questions, cands)

    assert "What is a T-bill?" in prompt
    assert "(a) One" in prompt
    assert "money-market-instruments" in prompt
    assert "Description of money-market-instruments." in prompt
    # A candidate excluded by body must not be shown at all.
    assert "pension-fund-regulation" not in prompt


def test_a_question_with_no_candidates_is_still_put_to_the_model(tmp_path):
    """Otherwise it vanishes: no proposal, no UNMAPPED record, no audit trail."""
    questions, catalogue = _loaded(
        tmp_path, questions=[_question(subject="Company Act", body="ifsca")],
        catalogue=[_catalogue_row(TID_PENSION, "pension-fund-regulation",
                                  "economics", ["pfrda"])])
    prompt = mod.build_prompt(questions, {questions[0]["id"]: []})
    assert "(none — answer UNMAPPED)" in prompt


def test_no_client_refuses_to_reach_the_network(tmp_path):
    with pytest.raises(mod.ProposerError, match=r"does not open a network connection"):
        mod.no_client("any prompt")


# ── 3. writer ────────────────────────────────────────────────────────────────


def _proposal(qid=QID_1, slug="money-market-instruments", confidence=0.82):
    return {"question_id": qid, "status": "MAPPED", "topic_slug": slug,
            "confidence": confidence, "rationale": "Stem names the instrument.",
            "reason": "", "subject": "economics", "body": "sebi",
            "candidate_count": 1}


def test_rerunning_the_writer_upserts_rather_than_duplicating(tmp_path):
    """The idempotency key is deterministic in (question, topic, role), so the
    second run's statement collides with the first instead of inserting again."""
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))

    first = tmp_path / "a.sql"
    second = tmp_path / "b.sql"
    mod.write_sql([_proposal()], catalogue, str(first))
    mod.write_sql([_proposal()], catalogue, str(second))

    assert first.read_text() == second.read_text()

    sql = first.read_text()
    assert sql.count("insert into public.pyq_question_topic_tags") == 1
    assert "on conflict (idempotency_key) where idempotency_key is not null" in sql
    assert "do update set" in sql

    key = mod.idempotency_key(QID_1, TID_MONEY)
    assert key in sql
    assert key == mod.idempotency_key(QID_1, TID_MONEY)

    # A different question or topic is a different row, not a collision.
    assert mod.idempotency_key(QID_2, TID_MONEY) != key
    assert mod.idempotency_key(QID_1, TID_BOARD) != key


def test_the_upsert_never_resets_a_reviewers_verdict(tmp_path):
    """A re-run must not drag a verified or rejected row back to pending."""
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    out = tmp_path / "o.sql"
    mod.write_sql([_proposal()], catalogue, str(out))
    sql = out.read_text()

    update = sql.split("do update set", 1)[1]
    assert "reviewer_status" not in update.split("where")[0]
    assert "reviewed_by" not in update
    assert "reviewed_at" not in update
    assert "where public.pyq_question_topic_tags.reviewer_status = 'pending'" in update


def test_an_unresolvable_slug_aborts_the_run(tmp_path):
    """A slug with no topic_id is a catalogue/proposal version skew. Writing the
    rest and dropping this one would import a partial, unexplained corpus."""
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    out = tmp_path / "o.sql"
    proposals = [_proposal(), _proposal(QID_2, slug="repo-transactions")]

    with pytest.raises(mod.ProposerError, match=r"do not resolve against the catalogue"):
        mod.write_sql(proposals, catalogue, str(out))
    assert not out.exists()


def test_unresolvable_slugs_are_reported_together(tmp_path):
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    proposals = [_proposal(QID_1, slug="ghost-one"), _proposal(QID_2, slug="ghost-two")]
    with pytest.raises(mod.ProposerError) as exc:
        mod.resolve_topic_ids(proposals, catalogue)
    assert "ghost-one" in str(exc.value) and "ghost-two" in str(exc.value)


def test_every_emitted_row_is_pending_ai_auto_extracted(tmp_path):
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    out = tmp_path / "o.sql"
    mod.write_sql([_proposal()], catalogue, str(out))
    sql = out.read_text()

    assert "'pending'" in sql
    assert "'ai'" in sql
    assert "'auto_extracted'" in sql
    assert "verified" not in sql


def test_module_constants_cannot_be_flipped_to_verified():
    """Belt and braces on the governance rule, asserted on the constants
    themselves so a future edit trips this test rather than shipping."""
    assert mod.REVIEWER_STATUS == "pending"
    assert mod.TAGGING_SOURCE == "ai"
    assert mod.SOURCE_KIND == "auto_extracted"


def test_unmapped_proposals_reach_the_jsonl_but_not_the_sql(tmp_path):
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    unmapped = {"question_id": QID_2, "status": "UNMAPPED", "topic_slug": None,
                "confidence": 0.6, "rationale": "Nothing matches.",
                "reason": "Out of catalogue scope.", "subject": "economics",
                "body": "sebi", "candidate_count": 1}
    jsonl = tmp_path / "o.jsonl"
    sql = tmp_path / "o.sql"

    assert mod.write_jsonl([_proposal(), unmapped], str(jsonl)) == 2
    assert mod.write_sql([_proposal(), unmapped], catalogue, str(sql)) == 1

    lines = [json.loads(x) for x in jsonl.read_text().splitlines()]
    assert [r["status"] for r in lines] == ["MAPPED", "UNMAPPED"]
    assert QID_2 not in sql.read_text()


def test_sql_string_values_are_escaped(tmp_path):
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    out = tmp_path / "o.sql"
    p = _proposal()
    p["rationale"] = "O'Brien's rule; 'quoted'"
    mod.write_sql([p], catalogue, str(out))
    sql = out.read_text()
    assert "O''Brien" in sql or "O\\u0027Brien" in sql
    assert "''" in sql


# ── dry run ──────────────────────────────────────────────────────────────────


def test_dry_run_produces_jsonl_and_sql_with_no_network_or_database(tmp_path):
    """The whole pipeline, fixture-driven. The parser and writer run for real;
    only the model call is replaced."""
    q_path = _write_jsonl(tmp_path / "q.jsonl", [
        _question(QID_1, subject="Economy", body="sebi"),
        _question(QID_2, subject="Company Act", body="pfrda"),
    ])
    c_path = _write_jsonl(tmp_path / "c.jsonl", _catalogue())
    a_path = _write_json(tmp_path / "a.json", ALIAS_MAP)
    f_path = _write_json(tmp_path / "f.json", [
        _response([_mapped(QID_1, "money-market-instruments", confidence=0.88)]),
        _response([{
            "question_id": QID_2, "status": "UNMAPPED", "topic_slug": None,
            "confidence": 0.64, "rationale": "Board rules do not cover this.",
            "reason": "No candidate addresses the stem.",
        }]),
    ])
    out_jsonl = tmp_path / "out.jsonl"
    out_sql = tmp_path / "out.sql"

    rc = mod.main([
        "--questions", q_path, "--catalogue", c_path, "--alias-map", a_path,
        "--batch-size", "1", "--dry-run", "--fixture", f_path,
        "--out-jsonl", str(out_jsonl), "--out-sql", str(out_sql),
    ])

    assert rc == 0
    records = [json.loads(x) for x in out_jsonl.read_text().splitlines()]
    assert len(records) == 2
    assert records[0]["topic_slug"] == "money-market-instruments"
    assert records[1]["status"] == "UNMAPPED"

    sql = out_sql.read_text()
    assert sql.count("insert into public.pyq_question_topic_tags") == 1
    assert "'pending'" in sql and "verified" not in sql
    assert sql.startswith("-- Proposed PYQ microtopic tags")
    assert sql.rstrip().endswith("commit;")


def test_dry_run_requires_a_fixture(tmp_path, capsys):
    rc = mod.main(["--questions", "x", "--catalogue", "y", "--alias-map", "z",
                   "--out-jsonl", "a", "--out-sql", "b", "--dry-run"])
    assert rc == 2
    assert "--dry-run requires --fixture" in capsys.readouterr().err


def test_a_run_without_dry_run_makes_no_model_call(tmp_path, capsys):
    """Without --dry-run there is no configured client, so the run stops at the
    first batch instead of reaching out."""
    q_path = _write_jsonl(tmp_path / "q.jsonl", [_question()])
    c_path = _write_jsonl(tmp_path / "c.jsonl", _catalogue())
    a_path = _write_json(tmp_path / "a.json", ALIAS_MAP)

    rc = mod.main(["--questions", q_path, "--catalogue", c_path,
                   "--alias-map", a_path, "--out-jsonl", str(tmp_path / "o.jsonl"),
                   "--out-sql", str(tmp_path / "o.sql")])
    assert rc == 1
    assert "no model client configured" in capsys.readouterr().err


def test_fixture_shorter_than_the_run_fails_loudly(tmp_path, capsys):
    q_path = _write_jsonl(tmp_path / "q.jsonl", [_question(QID_1), _question(QID_2)])
    c_path = _write_jsonl(tmp_path / "c.jsonl", _catalogue())
    a_path = _write_json(tmp_path / "a.json", ALIAS_MAP)
    f_path = _write_json(tmp_path / "f.json", [
        _response([_mapped(QID_1, "money-market-instruments")])])

    rc = mod.main(["--questions", q_path, "--catalogue", c_path,
                   "--alias-map", a_path, "--batch-size", "1",
                   "--dry-run", "--fixture", f_path,
                   "--out-jsonl", str(tmp_path / "o.jsonl"),
                   "--out-sql", str(tmp_path / "o.sql")])
    assert rc == 1
    assert "fixture has 1 response(s)" in capsys.readouterr().err


# ── input validation ─────────────────────────────────────────────────────────


def test_duplicate_catalogue_slug_is_rejected(tmp_path):
    """Two rows sharing a slug make topic_id resolution ambiguous, not redundant."""
    rows = _catalogue() + [
        _catalogue_row("eeeeeeee-5555-4555-8555-eeeeeeeeeeee",
                       "money-market-instruments", "economics", ["sebi"])]
    with pytest.raises(mod.ProposerError, match=r"already used by topic"):
        mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", rows))


def test_malformed_input_line_names_the_line(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text('{"id": "a"}\nnot json\n', encoding="utf-8")
    with pytest.raises(mod.ProposerError, match=r"c\.jsonl:2: not valid JSON"):
        mod.load_catalogue(str(path))


def test_an_export_gaining_a_column_still_loads(tmp_path):
    """Unknown keys are tolerated; a new export column must not break the run."""
    rows = [dict(r, unexpected_new_column="x") for r in _catalogue()]
    assert len(mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", rows))) == 4


def test_generated_sql_parses_under_the_real_postgres_grammar(tmp_path):
    """Syntax checked against libpg_query, not a regex.

    Skipped where pglast is absent — it is a developer convenience, not a
    runtime or CI dependency of this repo.
    """
    pglast = pytest.importorskip("pglast")
    catalogue = mod.load_catalogue(_write_jsonl(tmp_path / "c.jsonl", _catalogue()))
    out = tmp_path / "o.sql"
    mod.write_sql([_proposal(), _proposal(QID_2, confidence=0.55)], catalogue, str(out))

    statements = pglast.parse_sql(out.read_text())
    kinds = [type(s.stmt).__name__ for s in statements]
    assert kinds == ["TransactionStmt", "InsertStmt", "InsertStmt", "TransactionStmt"]
