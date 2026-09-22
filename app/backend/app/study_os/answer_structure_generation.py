"""Draft an answer structure for one descriptive question with a model.

Used by ``scripts/generate_answer_structures.py`` (batch) and by the Content
Studio "regenerate" action (one question). Everything here produces a DRAFT —
nothing in this module can set a status, and every write goes through
``cms_create_answer_structure_draft``, which only ever inserts 'draft'.

THE MODEL IS A SEAM. ``ModelCall`` is ``(system, user) -> ModelReply``; the
Anthropic adapter is one implementation, tests and ``--dry-run`` inject others.
No code path here reaches the network unless an ``AnthropicModelCall`` is
constructed, and that requires an API key.

STRICT JSON. The model answers through one tool (``record_answer_structure``)
declared ``strict`` with a closed schema; the tool input is then validated
again by ``answer_structure_schema.validate_structure``. A reply that fails
either check is retried with the validator's errors fed back, up to
``max_attempts``, and then reported as a failure — never written.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.study_os.answer_structure_schema import (
    SCHEMA_VERSION,
    StructureSchemaError,
    lint_structure,
    uncertainty_of,
    validate_structure,
    word_budget_for,
)

PROMPT_VERSION = "answer-structure-v1"

#: Default model. Overridable by ANSWER_STRUCTURE_MODEL or --model.
DEFAULT_MODEL = "claude-opus-5"


def resolve_model(explicit: str | None = None) -> str:
    return (explicit or os.getenv("ANSWER_STRUCTURE_MODEL") or DEFAULT_MODEL).strip()


#: USD per 1M tokens (input, output), first-party API rates.
_PRICING: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}
#: An unknown model is priced at the most expensive known rate, so a cost cap
#: errs towards stopping early rather than overspending.
_UNKNOWN_PRICING = (10.00, 50.00)


def pricing_for(model: str) -> tuple[float, float]:
    return _PRICING.get(model, _UNKNOWN_PRICING)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    i, o = pricing_for(model)
    return round(input_tokens / 1e6 * i + output_tokens / 1e6 * o, 6)


def worst_case_cost_usd(model: str, prompt_chars: int, max_tokens: int) -> float:
    """Upper bound for one call: input estimated at ~3 chars/token (pessimistic
    for English), output at the full ``max_tokens``. Used BEFORE a call so the
    cost cap can refuse a call that could cross it."""
    return cost_usd(model, prompt_chars // 3 + 1, max_tokens)


class CostBudget:
    """A hard USD ceiling across a run. ``can_afford`` is asked with the
    worst-case cost BEFORE each call; ``charge`` records the actual cost after.
    A call is refused when it COULD cross the cap, not only when it has."""

    def __init__(self, max_usd: float | None, spent: float = 0.0):
        self.max_usd = max_usd
        self.spent = float(spent)

    def can_afford(self, worst_case: float) -> bool:
        return self.max_usd is None or self.spent + worst_case <= self.max_usd

    def charge(self, amount: float) -> None:
        self.spent = round(self.spent + float(amount), 6)


# ── inputs ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class QuestionInput:
    """Everything the prompt may use about one question. Built from the DB
    (script / regenerate) or a JSONL fixture (dry-run, tests)."""

    id: str
    question_text: str
    subject: str | None = None
    paper: str | None = None
    section: str | None = None
    microtopic: str | None = None
    syllabus_line: str | None = None
    marks: int | None = None
    word_limit: int | None = None
    year: int | None = None
    parent_text: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QuestionInput":
        def _int(v: Any) -> int | None:
            try:
                return int(v) if v is not None and not isinstance(v, bool) else None
            except (TypeError, ValueError):
                return None

        return cls(
            id=str(d["id"]),
            question_text=str(d.get("question_text") or d.get("text") or "").strip(),
            subject=d.get("subject"),
            paper=d.get("paper"),
            section=d.get("section"),
            microtopic=d.get("microtopic"),
            syllabus_line=d.get("syllabus_line"),
            marks=_int(d.get("marks")),
            word_limit=_int(d.get("word_limit")),
            year=_int(d.get("year")),
            parent_text=d.get("parent_text"),
        )


# ── prompt ───────────────────────────────────────────────────────────────────

TOOL_NAME = "record_answer_structure"

_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": {"type": "string"}}

TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "directive": _STR,
        "demand": _STR,
        "intro_angles": _STR_LIST,
        "body_points": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": _STR,
                    "point": _STR,
                    "why": _STR,
                    "evidence_type": _STR,
                    "example": {"type": ["string", "null"]},
                    "thinker": {"type": ["string", "null"]},
                    "sub_points": _STR_LIST,
                },
                "required": ["id", "point", "why", "evidence_type", "example",
                             "thinker", "sub_points"],
            },
        },
        "dimensions": _STR_LIST,
        "examples": _STR_LIST,
        "conclusion_angles": _STR_LIST,
        "pitfalls": _STR_LIST,
        "sources_note": {"type": ["string", "null"]},
        "uncertainty": _STR_LIST,
    },
    "required": ["directive", "demand", "intro_angles", "body_points", "dimensions",
                 "examples", "conclusion_angles", "pitfalls", "sources_note",
                 "uncertainty"],
}

SYSTEM_PROMPT = """\
You write ANSWER STRUCTURES for Indian civil-services (UPSC CSE Mains) \
descriptive questions. An answer structure tells an aspirant, after they have \
written their own answer, what the question demanded and what a good answer \
had to contain. It is a checklist, not an essay: never write finished \
paragraphs an aspirant could memorise.

Report the structure ONLY by calling the record_answer_structure tool, once.

Fields:
- directive: the instruction word(s) the answer must obey, as printed or \
implied ("Critically examine", "Discuss", "Analyse", "Comment", ...).
- demand: one or two lines on what the question is really asking, including \
any sub-parts it contains.
- intro_angles: 1-3 alternative ways to open (one line each).
- body_points: 3-8 ordered points a good answer must cover. id is a short \
lowercase slug ("p1", "p2", ...). why = why the examiner expects it. \
evidence_type = the KIND of support to cite. example / thinker: a well-known, \
uncontroversial example or thinker when one genuinely fits, else null. \
sub_points: up to 4 short sub-points.
- dimensions: the lenses the answer should span (e.g. "Social", "Economic", \
"Ethical", "Federal") — only those that fit.
- examples: up to 5 kinds of illustration that would strengthen the answer.
- conclusion_angles: 1-3 ways to close (way forward, balanced verdict, ...).
- pitfalls: 2-5 common mistakes for this question.
- sources_note: one line on where an aspirant should look (standard texts, \
official documents by type) or null.
- uncertainty: anything you are not sure of — an ambiguous directive, a \
syllabus fit you guessed, an example you are unsure is apt. Empty if none.

HARD RULES — a reviewer will reject any structure that breaks them:
1. Do NOT invent statistics, figures, percentages, amounts or dates.
2. Do NOT name specific reports, surveys, indices, committees, court cases, \
judgments or citations unless you are certain they exist and say what the \
question needs. When in doubt, describe the evidence TYPE instead: \
"recent NFHS data on child stunting", "a Supreme Court judgment on the right \
to privacy", "an Economic Survey chapter on informal employment".
3. Never quote anyone.
4. If you are unsure of a fact, leave it out and say so in uncertainty.
5. Stay within the question and the syllabus line given; do not pad.
"""


def build_user_prompt(q: QuestionInput) -> str:
    lines = ["Question:"]
    if q.parent_text:
        lines.append(f"(Part of) {q.parent_text.strip()}")
    lines.append(q.question_text)
    lines.append("")
    lines.append("Context:")
    for label, value in (
        ("Subject", q.subject),
        ("Paper", q.paper),
        ("Syllabus section", q.section),
        ("Microtopic", q.microtopic),
        ("Official syllabus line", q.syllabus_line),
        ("Marks", q.marks),
        ("Word limit", q.word_limit),
        ("Year", q.year),
    ):
        lines.append(f"- {label}: {value if value not in (None, '') else 'not known'}")
    budget = word_budget_for(word_limit=q.word_limit, marks=q.marks)
    if budget:
        lines.append(
            f"- Expected length: about {budget['total']} words, so scale the number "
            "of body points to what fits."
        )
    return "\n".join(lines)


# ── the model seam ───────────────────────────────────────────────────────────


@dataclass
class ModelReply:
    """What one model call produced. ``structure`` is the raw tool input (or a
    dict parsed from text), ``None`` when the model did not call the tool."""

    structure: Any
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None
    raw_text: str | None = None


ModelCall = Callable[[str, str], ModelReply]


class TransientModelError(RuntimeError):
    """Rate limit, overload, timeout, connection — worth retrying."""


class FatalModelError(RuntimeError):
    """Bad request, auth, not found — retrying will not help."""


class AnthropicModelCall:
    """The live adapter. Constructed only by ``--call-model`` / ``--live`` and
    the admin regenerate route; never by tests or ``--dry-run``.

    Tool use with ``strict: true`` and ``tool_choice: auto`` plus an explicit
    instruction: forced ``tool_choice`` is rejected by some current models, and
    ``auto`` + strict works on all of them. A reply without the tool call is a
    malformed reply and goes back through the retry loop.
    """

    def __init__(self, *, model: str, api_key: str | None = None,
                 max_tokens: int = 4000, timeout_s: float = 120.0):
        import anthropic  # local: nothing imports the SDK unless it is used

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise FatalModelError("ANTHROPIC_API_KEY is not set")
        self._anthropic = anthropic
        self.model = model
        self.max_tokens = max_tokens
        # SDK-level retries off: the generator owns retry + cost accounting,
        # and a hidden retry would be spend the cost cap never saw.
        self._client = anthropic.Anthropic(api_key=key, timeout=timeout_s, max_retries=0)

    def __call__(self, system: str, user: str) -> ModelReply:
        a = self._anthropic
        try:
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=[{
                    "name": TOOL_NAME,
                    "description": "Record the answer structure for the question.",
                    "input_schema": TOOL_SCHEMA,
                    "strict": True,
                }],
                tool_choice={"type": "auto"},
                messages=[{"role": "user", "content": user}],
            )
        except (a.RateLimitError, a.APITimeoutError, a.APIConnectionError,
                a.InternalServerError) as exc:
            raise TransientModelError(str(exc)) from exc
        except a.APIStatusError as exc:
            if getattr(exc, "status_code", 0) in (408, 409, 429) or getattr(exc, "status_code", 0) >= 500:
                raise TransientModelError(str(exc)) from exc
            raise FatalModelError(str(exc)) from exc

        structure = None
        text_parts: list[str] = []
        for block in resp.content or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == TOOL_NAME:
                structure = block.input
            elif getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        usage = getattr(resp, "usage", None)
        return ModelReply(
            structure=structure,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            stop_reason=getattr(resp, "stop_reason", None),
            raw_text="\n".join(text_parts) or None,
        )


# ── one question ─────────────────────────────────────────────────────────────


@dataclass
class GenerationResult:
    question_id: str
    ok: bool
    structure: dict[str, Any] | None = None
    generation_meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cost_usd: float = 0.0


def _coerce(structure: Any) -> Any:
    """Tool input is already a dict; a text reply is parsed as JSON strictly —
    no fence stripping, no repair. Anything else is malformed."""
    if isinstance(structure, dict):
        return structure
    if isinstance(structure, str):
        return json.loads(structure)
    return structure


def generate_one(
    q: QuestionInput,
    call: ModelCall,
    *,
    model: str,
    max_attempts: int = 3,
    backoff_s: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    budget: CostBudget | None = None,
    max_tokens: int = 4000,
) -> GenerationResult:
    """Draft one structure. Retries malformed output (with the validator's
    errors fed back) and transient provider errors. ``budget`` is asked before
    EVERY call, retries included; a call that could cross the cap is not made.
    """
    if not q.question_text:
        return GenerationResult(q.id, False, error="empty_question_text")

    system = SYSTEM_PROMPT
    base_user = build_user_prompt(q)
    user = base_user
    total_in = total_out = 0
    spent = 0.0
    last_error = None
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        worst = worst_case_cost_usd(model, len(system) + len(user), max_tokens)
        if budget is not None and not budget.can_afford(worst):
            return GenerationResult(q.id, False, error="cost_cap_reached", cost_usd=spent,
                                    generation_meta={"attempts": attempts})
        attempts = attempt
        try:
            reply = call(system, user)
        except TransientModelError as exc:
            last_error = f"transient: {exc}"
            if attempt < max_attempts:
                sleep(backoff_s * (2 ** (attempt - 1)))
            continue
        except FatalModelError as exc:
            return GenerationResult(q.id, False, error=f"fatal: {exc}", cost_usd=spent,
                                    generation_meta={"attempts": attempts})

        total_in += reply.input_tokens
        total_out += reply.output_tokens
        call_cost = cost_usd(model, reply.input_tokens, reply.output_tokens)
        spent += call_cost
        if budget is not None:
            budget.charge(call_cost)

        if reply.stop_reason == "refusal":
            last_error = "refusal"
            break
        try:
            raw = _coerce(reply.structure)
            structure = validate_structure(
                {k: v for k, v in (raw or {}).items() if k != "word_budget"}
                if isinstance(raw, dict) else raw
            )
        except (StructureSchemaError, json.JSONDecodeError, TypeError) as exc:
            errors = getattr(exc, "errors", None) or [str(exc)]
            last_error = "schema: " + "; ".join(errors)[:500]
            user = (
                base_user
                + "\n\nYour previous structure was rejected by the validator:\n- "
                + "\n- ".join(errors[:15])
                + f"\nCall {TOOL_NAME} again with a corrected structure."
            )
            continue

        structure["word_budget"] = word_budget_for(word_limit=q.word_limit, marks=q.marks)
        meta = {
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "attempts": attempts,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "cost_usd": round(spent, 6),
            "uncertainty": uncertainty_of(raw),
            "lint_warnings": lint_structure(structure),
            "inputs": {
                "subject": q.subject, "paper": q.paper, "section": q.section,
                "microtopic": q.microtopic, "syllabus_line": q.syllabus_line,
                "marks": q.marks, "word_limit": q.word_limit, "year": q.year,
            },
        }
        return GenerationResult(q.id, True, structure=structure, generation_meta=meta,
                                cost_usd=spent)

    return GenerationResult(
        q.id, False, error=last_error or "failed", cost_usd=spent,
        generation_meta={"attempts": attempts, "input_tokens": total_in,
                         "output_tokens": total_out, "model": model},
    )


def write_draft(supabase: Any, result: GenerationResult, *, reason: str,
                actor_user_id: str | None = None, actor_email: str | None = None) -> dict:
    """Insert ``result`` as a new DRAFT version. The RPC allocates the version
    and writes the audit row; it cannot create any other status."""
    if not result.ok or not result.structure:
        raise ValueError("only a successful generation can be written")
    res = supabase.rpc("cms_create_answer_structure_draft", {
        "p_question_id": result.question_id,
        "p_payload": result.structure,
        "p_generated_by": f"ai:{result.generation_meta.get('model')}",
        "p_generation_meta": result.generation_meta,
        "p_reason": reason,
        "p_actor_user_id": actor_user_id,
        "p_actor_email": actor_email,
    }).execute()
    data = getattr(res, "data", None)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data or {}


# ── inputs from the database (read-only) ─────────────────────────────────────


def question_inputs(supabase: Any, question_ids: list[str]) -> dict[str, QuestionInput]:
    """question_id → QuestionInput, read from pyq_questions / pyq_papers and
    the verified primary topic tag. Verified descriptive questions only: a
    structure is never drafted for a question learners cannot see."""
    from app.study_os import descriptive as d

    questions, papers = d._attempt_questions(supabase, question_ids)
    questions = {
        qid: q for qid, q in questions.items()
        if q.get("question_type") == d.QUESTION_TYPE
        and q.get("reviewer_status") == d.QUESTION_REVIEWER_STATUS
    }
    topics = d._primary_topics(supabase, list(questions))
    out: dict[str, QuestionInput] = {}
    for qid, q in questions.items():
        meta = d._meta(q)
        paper = papers.get(str(q.get("pyq_paper_id") or "")) or {}
        topic = topics.get(qid) or {}
        _, slot = d.paper_slot(paper)
        out[qid] = QuestionInput(
            id=qid,
            question_text=str(q.get("question_text") or "").strip(),
            subject=d.subject_of(q, paper),
            paper=slot,
            section=(str(meta.get("section_ref") or "").strip() or topic.get("parent_topic_name")),
            microtopic=topic.get("name"),
            syllabus_line=topic.get("parent_official_line"),
            marks=d._as_int(meta.get("marks")),
            word_limit=d._as_int(meta.get("word_limit")),
            year=d._as_int(paper.get("year")),
            parent_text=(str(meta.get("parent_text") or "").strip() or None),
        )
    return out


def scoped_question_ids(
    supabase: Any,
    *,
    exam_id: str | None = None,
    subject: str | None = None,
    paper: str | None = None,
    years: tuple[int, int] | None = None,
) -> list[str]:
    """Verified descriptive question ids in scope, oldest paper first.

    ``paper`` is a slot code ("GS2", "P1", "ESSAY"), ``subject`` matches the
    catalogue subject case-insensitively, ``years`` is an inclusive range.
    Map questions are excluded — the practice surface cannot host them.
    """
    from app.study_os import descriptive as d

    if exam_id:
        papers = d._papers_for_exam(supabase, exam_id) or []
    else:
        papers = d._safe(
            lambda: d._paginate_all(
                lambda a, b: (
                    supabase.table("pyq_papers").select(d._PAPER_COLUMNS)
                    .order("id").range(a, b).execute().data
                )
            ),
            default=[],
        ) or []
    if years:
        lo, hi = years
        papers = [p for p in papers if lo <= (d._as_int(p.get("year")) or 0) <= hi]
    if paper:
        want = paper.strip().upper()
        papers = [p for p in papers if d.paper_slot_code(p) == want]
    by_id = {str(p["id"]): p for p in papers if p.get("id")}
    rows = d._verified_questions_for_papers(supabase, list(by_id)) or []
    want_subject = (subject or "").strip().lower()
    picked = []
    for q in rows:
        p = by_id.get(str(q.get("pyq_paper_id") or "")) or {}
        if d.requires_map_sheet(q):
            continue
        if want_subject and (d.subject_of(q, p) or "").strip().lower() != want_subject:
            continue
        picked.append((d._as_int(p.get("year")) or 0, str(p.get("id")),
                       str(q.get("question_number") or ""), str(q["id"])))
    picked.sort()
    return [qid for *_, qid in picked]


def questions_with_live_structure(supabase: Any, question_ids: list[str]) -> set[str]:
    """Questions that already carry a structure in any status but 'rejected'.
    The batch generator skips these: a draft awaiting review or a verified
    structure must not get a competing draft from a re-run."""
    from app.study_os import descriptive as d

    out: set[str] = set()
    for chunk in d._chunks(sorted(set(question_ids))):
        rows = d._safe(
            lambda ids=chunk: (
                supabase.table("answer_structures")
                .select("pyq_question_id, status")
                .in_("pyq_question_id", ids)
                .neq("status", "rejected")
                .execute()
                .data
            ),
            default=None,
        )
        if rows is None:
            # Fail closed: an unreadable table must not look like "no
            # structures", or a re-run would draft duplicates of everything.
            raise RuntimeError("could not read answer_structures to check for existing drafts")
        out.update(str(r.get("pyq_question_id")) for r in rows if r.get("status") != "rejected")
    return out
