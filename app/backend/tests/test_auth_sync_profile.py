"""_sync_profile_from_auth: phone-OTP signup users get a profile row with their
phone + name, and existing non-null fields are never overwritten."""
from __future__ import annotations

from app.api.auth import _sync_profile_from_auth


class _Query:
    """Minimal fluent stand-in for the supabase-py query builder."""

    def __init__(self, table: "_Table"):
        self._table = table
        self._select_rows = table.existing_rows

    # select(...).eq(...).limit(...).execute().data
    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return type("Resp", (), {"data": self._select_rows})()

    def upsert(self, payload, **_k):
        self._table.upserts.append(payload)
        return self

    def update(self, payload, **_k):
        self._table.updates.append(payload)
        return self


class _Table:
    def __init__(self, existing_rows):
        self.existing_rows = existing_rows
        self.upserts: list[dict] = []
        self.updates: list[dict] = []


class _FakeSB:
    def __init__(self, existing_rows):
        self._table = _Table(existing_rows)

    def table(self, _name):
        return _Query(self._table)


def test_sync_profile_creates_row_for_new_phone_user():
    sb = _FakeSB(existing_rows=[])
    _sync_profile_from_auth(sb, "u-1", email=None, phone="+919999900001", name="Asha")
    [payload] = sb._table.upserts
    assert payload["id"] == "u-1"
    assert payload["phone"] == "+919999900001"
    assert payload["full_name"] == "Asha"
    assert "email" not in payload  # no email supplied


def test_sync_profile_creates_row_with_email():
    sb = _FakeSB(existing_rows=[])
    _sync_profile_from_auth(sb, "u-1", email="asha@example.com", phone="+919999900001", name="Asha")
    [payload] = sb._table.upserts
    assert payload["email"] == "asha@example.com"
    assert payload["phone"] == "+919999900001"
    assert payload["full_name"] == "Asha"


def test_sync_profile_backfills_only_null_fields():
    sb = _FakeSB(existing_rows=[{"id": "u-1", "full_name": "Existing Name", "phone": None, "email": None}])
    _sync_profile_from_auth(sb, "u-1", email=None, phone="+919999900001", name="New Name")
    [update] = sb._table.updates
    # phone was NULL → backfilled; full_name already set → NOT overwritten; no email supplied.
    assert update == {"phone": "+919999900001"}


def test_sync_profile_backfills_email_when_null():
    sb = _FakeSB(existing_rows=[{"id": "u-1", "full_name": "Asha", "phone": "+919999900001", "email": None}])
    _sync_profile_from_auth(sb, "u-1", email="asha@example.com", phone="+919999900001", name="Asha")
    [update] = sb._table.updates
    assert update == {"email": "asha@example.com"}


def test_sync_profile_does_not_overwrite_existing_email():
    sb = _FakeSB(existing_rows=[{"id": "u-1", "full_name": "Asha", "phone": "+919999900001", "email": "old@example.com"}])
    _sync_profile_from_auth(sb, "u-1", email="new@example.com", phone="+919999900001", name="Asha")
    assert sb._table.updates == []
    assert sb._table.upserts == []


def test_sync_profile_noop_when_all_present():
    sb = _FakeSB(existing_rows=[{"id": "u-1", "full_name": "Asha", "phone": "+919999900001", "email": "asha@example.com"}])
    _sync_profile_from_auth(sb, "u-1", email="asha@example.com", phone="+919999900001", name="Asha")
    assert sb._table.updates == []
    assert sb._table.upserts == []


def test_sync_profile_falls_back_to_email_local_part_for_name():
    sb = _FakeSB(existing_rows=[])
    _sync_profile_from_auth(sb, "u-1", email="asha@example.com", phone=None, name=None)
    [payload] = sb._table.upserts
    assert payload["full_name"] == "asha"
    assert payload["email"] == "asha@example.com"
    assert "phone" not in payload  # no phone supplied
