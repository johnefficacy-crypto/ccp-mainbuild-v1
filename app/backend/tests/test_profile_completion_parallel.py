"""Profile completion fan-out must parallelise the optional reads.

`profile_completion` issues eight independent Supabase reads. The
identity (profile) read runs first so the supabase-py sync client
doesn't race eight concurrent requests over one httpx connection; the
remaining seven reads still gather. Sequential is ~150 ms × 8 ≈ 1.2 s,
the current shape is ~150 ms (profile) + ~150 ms (rest), which keeps
dashboard boot fast while avoiding the "Server disconnected" warnings
the old fully-parallel form produced.

The test asserts that shape structurally, not by wall-clock: it records
when each fetcher runs and checks (a) the profile read finishes before
any other read starts and (b) the other seven actually overlap. A
wall-clock bound failed on a saturated CI runner (0.828 s against a
0.4 s limit) without the code having re-serialised anything.
"""
from __future__ import annotations

import asyncio
import threading

from app.api import canonical

# How long a gathered fetcher waits for a second one to be in flight
# before concluding the fan-out is serial. Generous on purpose: a
# concurrent gather reaches overlap in milliseconds even on a loaded
# runner, and a serial one never reaches it at all.
_OVERLAP_TIMEOUT_S = 5.0


def _user() -> dict:
    return {"id": "u-1", "email": "u@example.com"}


class _SBStub:
    """Inert supabase; the fetcher monkeypatches are what actually run."""

    def table(self, _name):  # pragma: no cover - never reached in this test
        raise AssertionError(
            "fetcher was not monkeypatched; supabase.table() must not be called"
        )


class _FanOutProbe:
    """Records ordering and overlap of the patched fetchers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.profile_done = threading.Event()
        self.overlap_seen = threading.Event()
        self.in_flight = 0
        self.max_in_flight = 0
        self.started_before_profile: list[str] = []
        self.gathered_calls: list[str] = []

    def profile(self, value):
        def _inner(*_args, **_kwargs):
            with self._lock:
                if self.in_flight:
                    self.started_before_profile.append("profile overlapped a gathered read")
            self.profile_done.set()
            return value
        return _inner

    def gathered(self, name, value):
        def _inner(*_args, **_kwargs):
            with self._lock:
                if not self.profile_done.is_set():
                    self.started_before_profile.append(name)
                self.gathered_calls.append(name)
                self.in_flight += 1
                self.max_in_flight = max(self.max_in_flight, self.in_flight)
                if self.in_flight >= 2:
                    self.overlap_seen.set()
            try:
                # Serial execution never gets a second call in flight, so
                # this times out; any real gather releases it at once.
                self.overlap_seen.wait(timeout=_OVERLAP_TIMEOUT_S)
                return value
            finally:
                with self._lock:
                    self.in_flight -= 1
        return _inner


def test_profile_completion_runs_eight_fetchers_in_parallel(monkeypatch):
    monkeypatch.setattr(canonical, "get_supabase_admin", lambda: _SBStub())

    profile_row = {
        "full_name": "A",
        "phone": "9",
        "date_of_birth": "2000-01-01",
        "category": "general",
        "domicile_state": "Karnataka",
        "nationality": "Indian",
        "govt_employee": False,
        "weekly_hours_goal": 14,
    }
    education_row = {"qualification": "B.A.", "qualification_year": 2022}
    prefs_row = {
        "target_exams": ["ssc"],
        "preferred_states": ["KA"],
        "study_hours_per_day": 2.0,
    }
    location_row = {"state": "Karnataka"}
    reservations_row = {"category": "general"}

    probe = _FanOutProbe()
    monkeypatch.setattr(canonical, "_read_profile_row", probe.profile(profile_row))
    gathered = {
        "_get_primary_education": education_row,
        "_get_preferences": prefs_row,
        "_get_location": location_row,
        "_get_reservations": reservations_row,
        "_count_certifications": [{"id": "c1"}],
        "_count_experience": [{"id": "e1"}],
        "_count_exam_attempts": [{"id": "a1"}],
    }
    for name, value in gathered.items():
        monkeypatch.setattr(canonical, name, probe.gathered(name, value))

    out = asyncio.run(canonical.profile_completion(user=_user()))

    # Sanity: response shape preserved.
    assert "identity_profile" in out
    assert "certification_profile" in out
    assert out["certification_profile"]["completion_pct"] == 100
    assert out["experience_profile"]["completion_pct"] == 100
    assert out["attempts_profile"]["completion_pct"] == 100

    # All seven optional reads ran, each exactly once.
    assert sorted(probe.gathered_calls) == sorted(gathered)

    # The profile read is serial and comes first.
    assert probe.started_before_profile == [], (
        f"reads started before the profile read finished: {probe.started_before_profile}"
    )

    # The remaining seven overlap: at least two were in flight at once.
    assert probe.overlap_seen.is_set() and probe.max_in_flight >= 2, (
        "profile_completion ran the optional reads sequentially "
        f"(max in flight: {probe.max_in_flight})"
    )
