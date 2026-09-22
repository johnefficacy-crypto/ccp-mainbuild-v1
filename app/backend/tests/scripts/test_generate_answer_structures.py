"""scripts/generate_answer_structures.py — the batch loop's safety rails.

No network, no database: the model and the writer are injected. Pins dry-run
as the default, the cost cap, --max-questions, --resume, skipping questions
that already carry a non-rejected structure, and that --live writes drafts
only through the injected draft writer.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "generate_answer_structures.py"
_spec = importlib.util.spec_from_file_location("generate_answer_structures", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
gen = mod.gen

_FIX = _ROOT / "app" / "backend" / "tests" / "fixtures" / "answer_structures"
QUESTIONS_FILE = str(_FIX / "questions.jsonl")
RESPONSES_FILE = str(_FIX / "responses.json")
RESPONSES = json.loads(pathlib.Path(RESPONSES_FILE).read_text(encoding="utf-8"))
QUESTIONS = mod.read_questions_file(QUESTIONS_FILE)


def _args(tmp_path, *extra):
    return mod.build_parser().parse_args(
        ["--questions-file", QUESTIONS_FILE, "--output", str(tmp_path / "run.jsonl"), *extra])


class Model:
    """Counts calls; answers from the fixture responses by the question in the prompt."""

    def __init__(self, cost_tokens=(1000, 2000)):
        self.calls = 0
        self.tokens = cost_tokens

    def __call__(self, system, user):
        self.calls += 1
        q = next(q for q in QUESTIONS if q.question_text in user)
        return gen.ModelReply(structure=RESPONSES[q.id], input_tokens=self.tokens[0],
                              output_tokens=self.tokens[1], stop_reason="tool_use")


def _collect():
    out = []
    return out, out.append


def test_default_mode_is_dry_run_and_calls_nothing(tmp_path):
    args = _args(tmp_path)
    assert mod.mode_of(args) == "dry"
    records, emit = _collect()
    summary = mod.run(args, questions=QUESTIONS, call=None, existing=set(),
                      writer=None, emit=emit)
    assert [r["status"] for r in records] == ["dry_run"] * 3
    assert all(r["worst_case_usd"] > 0 for r in records)
    assert summary["cost_usd"] == 0.0 and summary["written"] == 0


def test_dry_run_replay_validates_the_fixture_responses(tmp_path):
    args = _args(tmp_path, "--responses", RESPONSES_FILE)
    current = {"id": ""}
    records, emit = _collect()
    summary = mod.run(args, questions=QUESTIONS, call=mod.replay_call(RESPONSES, current),
                      existing=set(), writer=None, emit=emit, current=current)
    assert summary["generated"] == 3 and summary["failed"] == 0
    assert {r["status"] for r in records} == {"dry_run_validated"}
    assert records[0]["structure"]["word_budget"]["total"] == 250


def test_live_writes_drafts_through_the_writer_only(tmp_path):
    args = _args(tmp_path, "--live")
    written = []
    records, emit = _collect()
    summary = mod.run(args, questions=QUESTIONS, call=Model(), existing=set(),
                      writer=lambda r: written.append(r) or {"id": f"s-{r.question_id}", "version": 1},
                      emit=emit)
    assert summary["written"] == 3 and len(written) == 3
    assert {r["status"] for r in records} == {"written"}


def test_call_model_mode_never_writes(tmp_path):
    args = _args(tmp_path, "--call-model")
    writes = []
    summary = mod.run(args, questions=QUESTIONS, call=Model(), existing=set(),
                      writer=writes.append, emit=lambda r: None)
    assert summary["generated"] == 3 and writes == []


def test_cost_cap_stops_the_run(tmp_path):
    one_call = gen.cost_usd("claude-opus-5", 1000, 2000)
    worst = gen.worst_case_cost_usd(
        "claude-opus-5", len(gen.SYSTEM_PROMPT) + len(gen.build_user_prompt(QUESTIONS[1])), 4000)
    # Room for the first call's actual cost plus ONE worst case, not two.
    cap = one_call + worst + 0.0001
    args = _args(tmp_path, "--call-model", "--max-usd", str(cap))
    model = Model()
    records, emit = _collect()
    summary = mod.run(args, questions=QUESTIONS, call=model, existing=set(),
                      writer=None, emit=emit)
    assert summary["stopped"] == "max_usd"
    assert model.calls == 2
    assert records[-1]["status"] == "stopped_cost_cap"
    assert summary["cost_usd"] <= cap


def test_max_questions_stops_the_run(tmp_path):
    args = _args(tmp_path, "--call-model", "--max-questions", "1")
    model = Model()
    summary = mod.run(args, questions=QUESTIONS, call=model, existing=set(),
                      writer=None, emit=lambda r: None)
    assert model.calls == 1 and summary["stopped"] == "max_questions"


def test_questions_with_a_non_rejected_structure_are_skipped(tmp_path):
    args = _args(tmp_path, "--live")
    model = Model()
    summary = mod.run(args, questions=QUESTIONS, call=model, existing={QUESTIONS[0].id},
                      writer=lambda r: {"id": "s", "version": 1}, emit=lambda r: None)
    assert summary["skipped_existing"] == 1 and model.calls == 2


def test_resume_skips_what_the_log_says_is_done(tmp_path):
    log = tmp_path / "run.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in (
        {"question_id": QUESTIONS[0].id, "status": "written"},
        {"question_id": QUESTIONS[1].id, "status": "failed", "error": "schema"},
    )) + "\n", encoding="utf-8")
    args = _args(tmp_path, "--live", "--resume")
    model = Model()
    summary = mod.run(args, questions=QUESTIONS, call=model, existing=set(),
                      writer=lambda r: {"id": "s", "version": 1}, emit=lambda r: None)
    # The written one is skipped; the failed one is retried.
    assert summary["skipped_resume"] == 1 and model.calls == 2


def test_resume_end_to_end_through_main(tmp_path, capsys):
    out = tmp_path / "run.jsonl"
    argv = ["--questions-file", QUESTIONS_FILE, "--responses", RESPONSES_FILE,
            "--output", str(out)]
    assert mod.main(argv) == 0
    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["status"] for r in lines] == ["dry_run_validated"] * 3


def test_responses_replay_is_refused_outside_dry_run(tmp_path):
    assert mod.main(["--questions-file", QUESTIONS_FILE, "--responses", RESPONSES_FILE,
                     "--call-model", "--output", str(tmp_path / "x.jsonl")]) == 2


@pytest.mark.parametrize("value,expected", [("2024", (2024, 2024)), ("2019-2024", (2019, 2024))])
def test_years_parse(value, expected):
    assert mod.parse_years(value) == expected
