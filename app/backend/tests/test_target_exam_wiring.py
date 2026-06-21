"""Tests: target_exam capture → profiles.target_exam → planner resolves it."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ─── ProfileUpdate accepts target_exam ────────────────────────────────────────

def test_profile_update_accepts_target_exam():
    from app.api.canonical import ProfileUpdate

    m = ProfileUpdate(target_exam="upsc-cse")
    assert m.target_exam == "upsc-cse"


def test_profile_update_target_exam_defaults_none():
    from app.api.canonical import ProfileUpdate

    m = ProfileUpdate()
    assert m.target_exam is None


# ─── _PROFILE_IDENTITY_FIELDS routes target_exam to profiles table ─────────────

def test_target_exam_in_identity_fields():
    from app.api.canonical import _PROFILE_IDENTITY_FIELDS

    assert "target_exam" in _PROFILE_IDENTITY_FIELDS


# ─── planner resolves a matched slug ──────────────────────────────────────────

def test_planner_resolves_target_exam_from_profiles():
    """_resolve_target_exam returns exam row when profiles.target_exam matches a slug."""
    from app.study_os.planner import _resolve_target_exam

    fake_exam = {"id": "exam-uuid", "slug": "upsc-cse", "name": "UPSC CSE"}
    supabase = MagicMock()

    profiles_chain = MagicMock()
    profiles_chain.execute.return_value.data = [{"target_exam": "upsc-cse"}]
    supabase.table.return_value.select.return_value.eq.return_value.limit.return_value = profiles_chain

    with patch("app.study_os.planner.resolve_exam_by_slug", return_value=fake_exam) as mock_slug:
        result = _resolve_target_exam(supabase, "user-1")

    mock_slug.assert_called_once_with(supabase, "upsc-cse")
    assert result == fake_exam


def test_planner_degrades_gracefully_on_unmatched_slug():
    """_resolve_target_exam returns None (no crash) when slug has no matching exam row."""
    from app.study_os.planner import _resolve_target_exam

    supabase = MagicMock()

    profiles_chain = MagicMock()
    profiles_chain.execute.return_value.data = [{"target_exam": "nonexistent-exam"}]
    supabase.table.return_value.select.return_value.eq.return_value.limit.return_value = profiles_chain

    with patch("app.study_os.planner.resolve_exam_by_slug", return_value=None):
        result = _resolve_target_exam(supabase, "user-1")

    assert result is None
