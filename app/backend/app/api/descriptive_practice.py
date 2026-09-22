"""Descriptive answer-writing practice — `/api/study/descriptive`.

Thin routes over `app.study_os.descriptive`. Reads are open to any signed-in
caller; every write requires a permanent account, matching the Essay Builder's
split — an anonymous session should not accumulate answers it will lose.

Ownership is enforced in the service against the authenticated user, because
every query runs on the service-role client and RLS does not constrain it.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, get_current_user_required_permanent
from app.db.supabase_client import get_supabase_admin
from app.study_os import descriptive as service

logger = logging.getLogger("career_copilot.api.descriptive_practice")

router = APIRouter(prefix="/study/descriptive", tags=["study", "descriptive"])


def _fail(exc: service.DescriptiveError) -> HTTPException:
    return HTTPException(
        status_code=exc.status, detail={"code": exc.code, "message": exc.message}
    )


class AttemptCreate(BaseModel):
    pyq_question_id: str


class AttemptPatch(BaseModel):
    """Autosave. `word_count` is deliberately absent — the server computes it."""

    answer_text: str | None = Field(default=None, max_length=200_000)
    # Both counters are running totals and the server keeps the max, so an
    # out-of-order or restarted client can only ever be ignored, never rewind.
    time_spent_seconds: int | None = Field(default=None, ge=0)
    pasted_chars: int | None = Field(default=None, ge=0)


class AttemptSubmit(BaseModel):
    self_scores: dict[str, Any]
    notes: str | None = Field(default=None, max_length=4000)
    # The last autosave can be ten seconds stale; submit carries the finals.
    time_spent_seconds: int | None = Field(default=None, ge=0)
    pasted_chars: int | None = Field(default=None, ge=0)


@router.get("/catalog")
def get_catalog(
    exam_id: str = Query(...),
    subject: str | None = Query(default=None),
    paper_number: int | None = Query(default=None, ge=1, le=10),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Subjects, papers, themes and years for one exam, with counts.

    ``subject`` scopes papers, themes and years. The subject list itself is
    never scoped — it is how the aspirant changes their mind. ``paper_number``
    scopes to one paper within the subject, and scopes the sittings and the
    syllabus themes alike.
    """
    try:
        return service.get_catalog(
            get_supabase_admin(),
            exam_id,
            # Carried so every count can also say how many are DONE. Scoped to
            # the caller by the token, never by a parameter.
            user_id=user.get("id"),
            subject=subject,
            paper_number=paper_number,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive catalog failed for exam=%s", exam_id)
        raise HTTPException(status_code=500, detail="The catalogue is temporarily unavailable.")


@router.get("/questions")
def get_questions(
    exam_id: str = Query(...),
    subject: str | None = Query(default=None),
    paper_id: str | None = Query(default=None),
    paper_number: int | None = Query(default=None, ge=1, le=10),
    theme: str | None = Query(default=None),
    year: int | None = Query(default=None),
    year_from: int | None = Query(default=None, description="inclusive"),
    year_to: int | None = Query(default=None, description="inclusive"),
    exclude_attempted: bool = Query(default=False),
    has_marks: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Verified descriptive questions; map questions excluded and counted."""
    try:
        return service.list_questions(
            get_supabase_admin(),
            user.get("id"),
            exam_id=exam_id,
            subject=subject,
            paper_id=paper_id,
            paper_number=paper_number,
            theme=theme,
            year=year,
            year_from=year_from,
            year_to=year_to,
            exclude_attempted=exclude_attempted,
            has_marks=has_marks,
            limit=limit,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive questions failed for exam=%s", exam_id)
        raise HTTPException(status_code=500, detail="Questions are temporarily unavailable.")


@router.get("/analytics")
def get_analytics(
    weeks: int = Query(default=8, ge=1, le=52),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """How this caller's answer writing is going, week by week.

    Computed from the attempts that already exist. No new tracking.
    """
    try:
        return service.analytics(get_supabase_admin(), user.get("id"), weeks=weeks)
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive analytics failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Your progress is temporarily unavailable.")


@router.get("/coverage")
def get_coverage(
    exam_id: str = Query(...),
    subject: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """What this caller has written and what is still waiting, by group."""
    try:
        return service.coverage(
            get_supabase_admin(), user.get("id"), exam_id=exam_id, subject=subject
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive coverage failed for exam=%s", exam_id)
        raise HTTPException(status_code=500, detail="Coverage is temporarily unavailable.")


@router.post("/attempts")
def create_attempt(
    body: AttemptCreate,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    """Open the draft for this question, or return the one already open."""
    try:
        return service.open_attempt(
            get_supabase_admin(), user.get("id"), body.pyq_question_id
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive attempt create failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Couldn't start that attempt.")


@router.patch("/attempts/{attempt_id}")
def patch_attempt(
    attempt_id: str,
    body: AttemptPatch,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    """Autosave the answer and elapsed time. Rejected once submitted."""
    try:
        return service.save_attempt(
            get_supabase_admin(),
            user.get("id"),
            attempt_id,
            answer_text=body.answer_text,
            time_spent_seconds=body.time_spent_seconds,
            pasted_chars=body.pasted_chars,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive attempt save failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Couldn't save that answer.")


@router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: str,
    body: AttemptSubmit,
    user: dict = Depends(get_current_user_required_permanent),
) -> dict[str, Any]:
    """Close the attempt with the aspirant's own six-criterion rubric."""
    try:
        return service.submit_attempt(
            get_supabase_admin(),
            user.get("id"),
            attempt_id,
            self_scores=body.self_scores,
            notes=body.notes,
            time_spent_seconds=body.time_spent_seconds,
            pasted_chars=body.pasted_chars,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive attempt submit failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Couldn't submit that answer.")


@router.get("/attempts")
def get_attempts(
    pyq_question_id: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    paper_id: str | None = Query(default=None),
    theme: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(draft|submitted)$"),
    since: str | None = Query(default=None, description="ISO date, inclusive"),
    until: str | None = Query(default=None, description="ISO date, inclusive"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """This caller's answer history — every attempt, newest first.

    Scoped to the caller by `user.get("id")`, never by a query parameter: an
    attempt is the most personal thing this product stores, and a user_id the
    client could supply is a user_id the client could change.
    """
    try:
        return service.list_attempts(
            get_supabase_admin(),
            user.get("id"),
            pyq_question_id=pyq_question_id,
            subject=subject,
            paper_id=paper_id,
            theme=theme,
            status=status,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive attempts read failed for %s", user.get("id"))
        raise HTTPException(status_code=500, detail="Your attempts are temporarily unavailable.")


@router.get("/attempts/{attempt_id}")
def get_attempt(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """One of the caller's own attempts, read-only, with its question.

    Ownership is enforced in the service by the same `user_id` predicate every
    other attempt read uses, so another user's id in the path is a 404 rather
    than a leak.
    """
    try:
        return service.attempt_detail(get_supabase_admin(), user.get("id"), attempt_id)
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive attempt read failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="That answer is temporarily unavailable.")


class AnswerModeBody(BaseModel):
    answer_mode: str


class PageUploadRequest(BaseModel):
    page_no: int
    mime_type: str
    size_bytes: int


@router.put("/attempts/{attempt_id}/answer-mode")
def set_answer_mode(
    attempt_id: str,
    body: AnswerModeBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Switch a draft between typing and uploading pages."""
    try:
        return service.set_answer_mode(
            get_supabase_admin(), user.get("id"), attempt_id, body.answer_mode
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive answer mode failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Couldn't switch modes.")


@router.get("/attempts/{attempt_id}/pages")
def get_attempt_pages(
    attempt_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """This attempt's uploaded pages, each with a short-lived signed URL.

    The bucket and object path never appear in the response: two aspirants'
    paths differ only by a user id, so a client that learns one learns the
    shape of them all.
    """
    try:
        return service.list_attempt_pages(
            get_supabase_admin(), user.get("id"), attempt_id
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive pages read failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Your pages are temporarily unavailable.")


@router.post("/attempts/{attempt_id}/pages")
def create_page_upload(
    attempt_id: str,
    body: PageUploadRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """A signed URL to upload one page to.

    Type, size and page number are checked HERE, before a URL exists. A limit
    enforced only in the browser is not a limit.
    """
    try:
        return service.request_page_upload(
            get_supabase_admin(),
            user.get("id"),
            attempt_id,
            page_no=body.page_no,
            mime_type=body.mime_type,
            size_bytes=body.size_bytes,
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive page upload failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Couldn't start that upload.")


@router.delete("/attempts/{attempt_id}/pages/{page_no}")
def remove_attempt_page(
    attempt_id: str,
    page_no: int,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Remove one page and its stored image."""
    try:
        return service.delete_attempt_page(
            get_supabase_admin(), user.get("id"), attempt_id, page_no
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive page delete failed for %s", attempt_id)
        raise HTTPException(status_code=500, detail="Couldn't remove that page.")


@router.get("/questions/{pyq_question_id}/attempts")
def compare_question_attempts(
    pyq_question_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Every attempt the caller has made at one question, oldest first."""
    try:
        return service.compare_attempts(
            get_supabase_admin(), user.get("id"), pyq_question_id
        )
    except service.DescriptiveError as exc:
        raise _fail(exc) from None
    except Exception:  # noqa: BLE001
        logger.exception("descriptive compare failed for %s", pyq_question_id)
        raise HTTPException(status_code=500, detail="Your attempts are temporarily unavailable.")
