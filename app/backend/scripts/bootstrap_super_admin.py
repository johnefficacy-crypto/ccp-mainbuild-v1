"""Promote an existing Supabase auth user to ``super_admin``.

Usage (from the repo root or app/backend):

    python -m app.backend.scripts.bootstrap_super_admin --email <email>

Env prerequisites:
    SUPABASE_SERVICE_ROLE_KEY   service-role key (never printed)
    SUPABASE_URL                project URL (NEXT_PUBLIC_SUPABASE_URL also accepted)

Behaviour:
    * 0 matches  → exit 2, "no user"
    * >1 matches → exit 3, "ambiguous"
    * already super_admin → exit 0, "already super_admin" (idempotent)
    * otherwise set app_metadata.role="super_admin" (preserving other keys),
      write an admin_audit_logs row, exit 0.

Security: prints only success/failure. Never prints tokens, keys, or JWTs.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Make ``app.*`` (the backend package) importable regardless of cwd. This file
# lives at app/backend/scripts/, so the backend root is two levels up.
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


AUDIT_ACTION = "rbac.bootstrap_super_admin"


def _as_user(resp: Any) -> Any:
    return getattr(resp, "user", None) or resp


def _app_metadata(user_obj: Any) -> dict:
    meta = (
        getattr(user_obj, "app_metadata", None)
        or getattr(user_obj, "raw_app_meta_data", None)
        or {}
    )
    return dict(meta) if isinstance(meta, dict) else {}


def _all_users(sb) -> list[Any]:
    admin = sb.auth.admin
    out: list[Any] = []
    page = 1
    per_page = 200
    while True:
        try:
            res = admin.list_users(page=page, per_page=per_page)
        except TypeError:
            res = admin.list_users()
            out.extend(getattr(res, "users", None) or (res if isinstance(res, list) else []))
            break
        batch = getattr(res, "users", None) or (res if isinstance(res, list) else [])
        out.extend(batch)
        if not batch or len(batch) < per_page:
            break
        page += 1
        if page > 1000:
            break
    return out


def run(email: str, sb=None) -> tuple[int, str]:
    """Core logic. Returns ``(exit_code, message)`` for testability."""
    needle = (email or "").strip().lower()
    if not needle:
        return 1, "email required"

    if sb is None:
        from app.db.supabase_client import get_supabase_admin

        sb = get_supabase_admin()

    matches = [u for u in _all_users(sb) if (getattr(u, "email", "") or "").strip().lower() == needle]
    if not matches:
        return 2, "no user"
    if len(matches) > 1:
        return 3, "ambiguous"

    target = matches[0]
    user_id = getattr(target, "id", None)
    app_meta = _app_metadata(target)
    old_role = app_meta.get("role")
    if old_role == "super_admin":
        return 0, "already super_admin"

    app_meta["role"] = "super_admin"
    sb.auth.admin.update_user_by_id(user_id, {"app_metadata": app_meta})

    try:
        sb.table("admin_audit_logs").insert(
            {
                "actor_id": None,
                "actor_email": None,
                "action": AUDIT_ACTION,
                "entity_type": "auth_user",
                "entity_id": user_id,
                "new_value": {
                    "actor_id": None,
                    "target_user_id": user_id,
                    "target_email": email,
                    "old_role": old_role,
                    "new_role": "super_admin",
                    "route": "scripts.bootstrap_super_admin",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                "notes": "scripts.bootstrap_super_admin",
            }
        ).execute()
    except Exception:  # noqa: BLE001
        # The role change already succeeded; a failed audit insert must not
        # make the bootstrap look failed. Report success but flag it.
        return 0, "super_admin set (audit log insert failed)"

    return 0, "super_admin set"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a Supabase user to super_admin")
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    if not service_key or not url:
        print("FAIL: SUPABASE_SERVICE_ROLE_KEY and SUPABASE_URL are required")
        return 1
    # get_supabase_admin() reads NEXT_PUBLIC_SUPABASE_URL; mirror SUPABASE_URL.
    os.environ.setdefault("NEXT_PUBLIC_SUPABASE_URL", url)

    try:
        code, message = run(args.email)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1

    prefix = "OK" if code == 0 else "FAIL"
    print(f"{prefix}: {message}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
