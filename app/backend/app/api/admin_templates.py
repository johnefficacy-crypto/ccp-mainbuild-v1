from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.admin.mock_templates import MOCK_PUBLISHER_PERMISSION, preview_selection
from app.core.auth import require_permission
from app.db.supabase_client import get_supabase_admin

router = APIRouter(prefix="/api/admin/mocks/templates", tags=["admin-mock-templates"])


@router.get("/")
def list_templates(status: str | None = None, exam_family: str | None = None, _admin: dict = Depends(require_permission(MOCK_PUBLISHER_PERMISSION))):
    q = get_supabase_admin().table("mock_templates").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if exam_family:
        q = q.eq("exam_family", exam_family)
    return {"items": q.execute().data or []}


@router.post("/{template_id}/preview-selection")
def template_preview_selection(template_id: str, _admin: dict = Depends(require_permission(MOCK_PUBLISHER_PERMISSION))):
    return preview_selection(get_supabase_admin(), template_id)


@router.post("/{template_id}/publish")
def publish_template(template_id: str, force: bool = Query(default=False), notes: str | None = None, admin: dict = Depends(require_permission(MOCK_PUBLISHER_PERMISSION))):
    sb = get_supabase_admin()
    preview = preview_selection(sb, template_id)
    if preview["has_gaps"] and not force:
        raise HTTPException(status_code=409, detail={"message": "preview has gaps", "preview": preview})
    sb.table("mock_templates").update({"status": "published", "published_at": "now()"}).eq("id", template_id).eq("status", "draft").execute()
    sb.table("mock_template_audit_log").insert({"template_id": template_id, "actor_id": admin.get("id"), "action": "publish", "from_status": "draft", "to_status": "published", "diff": {"force": force, "preview": preview}, "notes": notes}).execute()
    return {"ok": True, "forced": force, "preview": preview}
