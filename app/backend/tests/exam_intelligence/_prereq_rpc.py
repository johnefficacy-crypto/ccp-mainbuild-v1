"""Shared in-memory emulation of the `cms_write_topic_prerequisite` RPC.

Mirrors migration 208's SECURITY DEFINER function so stub-based API tests can
exercise the cycle-safe write path (single-writer, so the advisory lock is a
no-op here; the transitive recursive cycle check IS emulated). Used by both
the Manage Exam prerequisite tests and the Advanced Repair CMS taxonomy tests.
"""
from __future__ import annotations

from typing import Any

_ORDERING = {"requires", "recommended_before"}
_RELATIONS = ("requires", "recommended_before", "supports", "foundation_for")


def emulate_cms_write_topic_prerequisite(db: dict, params: dict) -> dict[str, Any]:
    rel = params.get("p_relation_type")
    if rel not in _RELATIONS:
        raise Exception(f"invalid_relation_type: {rel}")
    topic_id = params["p_topic_id"]
    prereq_id = params["p_prerequisite_topic_id"]
    if topic_id == prereq_id:
        raise Exception("self_edge: a topic cannot be its own prerequisite")

    rows = db.setdefault("topic_prerequisites", [])
    pid = params.get("p_id")

    # Transitive cycle check over ORDERING edges, excluding the row under update.
    if rel in _ORDERING:
        adj: dict[str, set[str]] = {}
        for r in rows:
            if pid and r.get("id") == pid:
                continue
            if r.get("relation_type") in _ORDERING:
                adj.setdefault(r["topic_id"], set()).add(r["prerequisite_topic_id"])
        # Adding topic_id -> prereq_id closes a cycle iff prereq_id already
        # (transitively) depends on topic_id. Walk from prereq_id.
        seen: set[str] = set()
        stack = [prereq_id]
        while stack:
            node = stack.pop()
            if node == topic_id:
                raise Exception("cycle: adding this prerequisite would create a transitive cycle")
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adj.get(node, ()))

    if pid is None:
        for r in rows:
            if r["topic_id"] == topic_id and r["prerequisite_topic_id"] == prereq_id:
                raise Exception("duplicate: edge already exists")
        new = {
            "id": f"pre-{len(rows) + 1}",
            "topic_id": topic_id,
            "prerequisite_topic_id": prereq_id,
            "relation_type": rel,
            "strength": params.get("p_strength", 1.0),
            "source_basis": params.get("p_source_basis"),
            "created_by": params.get("p_created_by"),
            "reviewer_status": "draft",
        }
        rows.append(new)
        return new

    row = next((r for r in rows if r.get("id") == pid), None)
    if not row:
        raise Exception("not_found")
    row.update({
        "topic_id": topic_id,
        "prerequisite_topic_id": prereq_id,
        "relation_type": rel,
        "strength": params.get("p_strength"),
        "source_basis": params.get("p_source_basis"),
    })
    return row
