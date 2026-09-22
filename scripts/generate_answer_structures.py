#!/usr/bin/env python3
"""Draft answer structures for descriptive PYQs.

Three modes, from safest to least safe:

  (default)      DRY RUN. No model call, no database write. Prints each
                 question's prompt inputs and worst-case cost. With
                 ``--responses FILE`` it replays canned model output through
                 the real validator and lint, so the whole pipeline can be
                 exercised offline (and in CI) without an API key.
  --call-model   Calls the model and validates the output. Still writes
                 NOTHING to the database — results go to ``--output`` only.
  --live         Calls the model and writes each valid structure as a new
                 DRAFT version through ``cms_create_answer_structure_draft``.
                 That RPC can only insert status 'draft'; nothing this script
                 does can make a structure learner-visible. A human reviewer
                 in Content Studio does that.

Inputs per question: text, subject, paper, section, microtopic, official
syllabus line, marks, word limit (read from the DB, or from ``--questions-file``
JSONL with the same keys).

Safety rails:
  --max-questions N   stop after N model-called questions (default 25)
  --max-usd X         hard cost ceiling for the run (default 5.00). A call
                      whose WORST-CASE cost could cross it is not made, and the
                      run stops.
  --output FILE       JSONL log, appended. ``--resume`` skips every question
                      already logged as written (or generated, in
                      --call-model mode) or skipped_existing.
  Existing structures: any question with a structure in a status other than
                      'rejected' is skipped (draft awaiting review, in review,
                      or verified).

Examples:
  python scripts/generate_answer_structures.py \\
      --questions-file app/backend/tests/fixtures/answer_structures/questions.jsonl \\
      --responses app/backend/tests/fixtures/answer_structures/responses.json

  python scripts/generate_answer_structures.py --subject "General Studies" \\
      --paper GS2 --years 2019-2024 --call-model --max-questions 3 --max-usd 1

  python scripts/generate_answer_structures.py --paper GS2 --years 2024 \\
      --live --max-questions 20 --max-usd 4 --resume
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "app" / "backend"))

from app.study_os import answer_structure_generation as gen  # noqa: E402

DEFAULT_OUTPUT = "answer_structures_run.jsonl"
DEFAULT_MAX_QUESTIONS = 25
DEFAULT_MAX_USD = 5.00

#: Log statuses that mean "done — do not redo on --resume", per mode.
_DONE = {
    "live": {"written", "skipped_existing"},
    "call": {"generated", "written", "skipped_existing"},
    "dry": set(),
}


def parse_years(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = value.split("-", 1)
    try:
        lo = int(parts[0])
        hi = int(parts[1]) if len(parts) == 2 else lo
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--years must be YYYY or YYYY-YYYY, got {value!r}") from exc
    if lo > hi:
        raise argparse.ArgumentTypeError("--years range is reversed")
    return lo, hi


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="call the model AND write drafts")
    mode.add_argument("--call-model", action="store_true", help="call the model, write nothing")
    p.add_argument("--questions-file", help="JSONL of question inputs instead of the database")
    p.add_argument("--responses", help="dry run: JSON {question_id: structure} to replay")
    p.add_argument("--exam-id")
    p.add_argument("--subject")
    p.add_argument("--paper", help="slot code: GS1..GS4, ESSAY, P1, P2")
    p.add_argument("--years", type=parse_years, help="YYYY or YYYY-YYYY (inclusive)")
    p.add_argument("--model", help=f"default: $ANSWER_STRUCTURE_MODEL or {gen.DEFAULT_MODEL}")
    p.add_argument("--max-questions", type=int, default=DEFAULT_MAX_QUESTIONS)
    p.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    p.add_argument("--max-attempts", type=int, default=3, help="per question, malformed/transient retries")
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--reason", default="Batch draft via scripts/generate_answer_structures.py")
    return p


def mode_of(args: argparse.Namespace) -> str:
    return "live" if args.live else ("call" if args.call_model else "dry")


def read_questions_file(path: str) -> list[gen.QuestionInput]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(gen.QuestionInput.from_dict(json.loads(line)))
    return out


def read_done(path: str, mode: str) -> set[str]:
    done_statuses = _DONE[mode]
    p = Path(path)
    if not p.exists() or not done_statuses:
        return set()
    done = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("status") in done_statuses and rec.get("question_id"):
            done.add(str(rec["question_id"]))
    return done


def replay_call(responses: dict[str, Any], current: dict[str, str]) -> gen.ModelCall:
    """A ModelCall that returns the canned structure for the current question.
    No network. Token counts are zero, so a replay costs nothing."""

    def _call(system: str, user: str) -> gen.ModelReply:
        return gen.ModelReply(structure=responses.get(current["id"]), stop_reason="tool_use")

    return _call


def run(
    args: argparse.Namespace,
    *,
    questions: list[gen.QuestionInput],
    call: gen.ModelCall | None,
    existing: set[str],
    writer: Callable[[gen.GenerationResult], dict] | None,
    emit: Callable[[dict], None],
    current: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The loop, with every side effect injected. Returns a summary."""
    mode = mode_of(args)
    model = gen.resolve_model(args.model)
    done = read_done(args.output, mode) if args.resume else set()
    budget = gen.CostBudget(max_usd=args.max_usd)
    summary = {"mode": mode, "model": model, "considered": 0, "generated": 0,
               "written": 0, "failed": 0, "skipped_existing": 0,
               "skipped_resume": 0, "stopped": None, "cost_usd": 0.0}
    called = 0
    for q in questions:
        summary["considered"] += 1
        if q.id in done:
            summary["skipped_resume"] += 1
            continue
        if q.id in existing:
            summary["skipped_existing"] += 1
            emit({"question_id": q.id, "status": "skipped_existing"})
            continue
        if called >= args.max_questions:
            summary["stopped"] = "max_questions"
            break

        if call is None:
            # Pure dry run: show what WOULD be sent, and what it could cost.
            user = gen.build_user_prompt(q)
            emit({
                "question_id": q.id, "status": "dry_run",
                "prompt_inputs": user,
                "worst_case_usd": gen.worst_case_cost_usd(
                    model, len(gen.SYSTEM_PROMPT) + len(user), 4000),
            })
            called += 1
            continue

        if current is not None:
            current["id"] = q.id
        called += 1
        result = gen.generate_one(q, call, model=model, budget=budget,
                                  max_attempts=args.max_attempts)
        summary["cost_usd"] = budget.spent
        if not result.ok and result.error == "cost_cap_reached":
            summary["stopped"] = "max_usd"
            emit({"question_id": q.id, "status": "stopped_cost_cap", "spent_usd": budget.spent})
            break
        if not result.ok:
            summary["failed"] += 1
            emit({"question_id": q.id, "status": "failed", "error": result.error,
                  "cost_usd": result.cost_usd})
            continue
        record = {"question_id": q.id, "status": "generated", "cost_usd": result.cost_usd,
                  "structure": result.structure, "generation_meta": result.generation_meta}
        summary["generated"] += 1
        if mode == "live" and writer is not None:
            try:
                created = writer(result)
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                emit({**record, "status": "failed", "error": f"write: {exc}"})
                continue
            record.update(status="written", structure_id=created.get("id"),
                          version=created.get("version"))
            summary["written"] += 1
        elif mode == "dry":
            record["status"] = "dry_run_validated"
        emit(record)
    summary["cost_usd"] = budget.spent
    return summary


def _emitter(path: str, echo: bool) -> Callable[[dict], None]:
    fh = open(path, "a", encoding="utf-8")

    def _emit(rec: dict) -> None:
        line = json.dumps(rec, ensure_ascii=False)
        fh.write(line + "\n")
        fh.flush()
        if echo:
            print(json.dumps(rec, ensure_ascii=False, indent=2))

    return _emit


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    mode = mode_of(args)
    if args.responses and mode != "dry":
        print("--responses replays canned output and is dry-run only", file=sys.stderr)
        return 2
    if args.max_usd is None or args.max_usd <= 0:
        print("--max-usd must be positive", file=sys.stderr)
        return 2

    supabase = None
    if not args.questions_file or mode == "live":
        from app.db.supabase_client import get_supabase_admin
        supabase = get_supabase_admin()

    if args.questions_file:
        questions = read_questions_file(args.questions_file)
    else:
        ids = gen.scoped_question_ids(
            supabase, exam_id=args.exam_id, subject=args.subject,
            paper=args.paper, years=args.years,
        )
        by_id = gen.question_inputs(supabase, ids)
        questions = [by_id[i] for i in ids if i in by_id]

    existing: set[str] = set()
    if supabase is not None:
        existing = gen.questions_with_live_structure(supabase, [q.id for q in questions])

    current: dict[str, str] = {"id": ""}
    call: gen.ModelCall | None = None
    if args.responses:
        call = replay_call(json.loads(Path(args.responses).read_text(encoding="utf-8")), current)
    elif mode in ("call", "live"):
        call = gen.AnthropicModelCall(model=gen.resolve_model(args.model))

    writer = None
    if mode == "live":
        def writer(result: gen.GenerationResult) -> dict:  # noqa: E306
            return gen.write_draft(supabase, result, reason=args.reason)

    summary = run(args, questions=questions, call=call, existing=existing,
                  writer=writer, emit=_emitter(args.output, echo=(mode == "dry")),
                  current=current)
    print(json.dumps({"summary": summary}, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
