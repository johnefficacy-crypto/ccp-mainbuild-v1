#!/usr/bin/env python3
"""Ingest the UPSC CSE Mains GS syllabus micro-theme map into the CMS.

Writes through the admin Exam-Intelligence CMS HTTP API (never direct SQL) so
every row lands in the review queue with an audit entry:

    subjects            <- papers[].paper_title              (GS I..IV)
    topics(topic)       <- syllabus_nodes[].macro_topic
    topics(microtopic)  <- syllabus_nodes[].micro_themes[]
    syllabus_documents  <- one row for the whole source file (trust_status=pending)
    syllabus_topic_mentions <- one per macro topic + one per micro theme (pending)

Nothing is born verified. An operator promotes the document and the mentions
through the existing review endpoints afterwards (see CLAUDE.md -> verified-only
reads). This script never calls a review endpoint.

Idempotent: every entity is resolved by its natural key (subject slug,
subject+parent+slug for topics, content_hash for the document, document+topic
for mentions) before being created, so re-running after a partial failure
resumes instead of duplicating.

Usage:

    export CCP_API_BASE=https://api.example.com
    export CCP_ADMIN_JWT=eyJ...
    python scripts/ingest_upsc_gs_syllabus.py \
        docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json \
        --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 \
        --exam-phase-id 626ec667-4bbf-4420-8715-48c5b83e0d11 \
        --dry-run

Drop --dry-run to write. Requires the ``exam_intelligence.cms`` permission and
``ADMIN_STUDY_OS_ENABLED=true`` on the target backend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

CMS = "/api/admin/exam-intelligence-cms"

# Reason strings are mandatory on every WriteEnvelope (8..500 chars).
REASON = "UPSC GS syllabus micro-theme ingest: seed syllabus tree for Study OS planning"

# Roman numerals used by the official paper titles, for slug generation.
_ROMAN = {"GS_1": "gs1", "GS_2": "gs2", "GS_3": "gs3", "GS_4": "gs4"}


def slugify(text: str, *, maxlen: int = 80) -> str:
    """Deterministic, collision-resistant slug.

    Micro-theme strings are long prose sentences, so a truncated slug alone
    would collide (many themes share a prefix). We append a short hash of the
    full string to keep the natural key stable across runs.
    """
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{base[:maxlen].rstrip('-')}-{digest}"


@dataclass
class Stats:
    subjects_created: int = 0
    subjects_reused: int = 0
    macro_created: int = 0
    macro_reused: int = 0
    micro_created: int = 0
    micro_reused: int = 0
    document_created: int = 0
    document_reused: int = 0
    mentions_created: int = 0
    mentions_reused: int = 0
    errors: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (
            f"subjects  created={self.subjects_created} reused={self.subjects_reused}\n"
            f"macro     created={self.macro_created} reused={self.macro_reused}\n"
            f"micro     created={self.micro_created} reused={self.micro_reused}\n"
            f"document  created={self.document_created} reused={self.document_reused}\n"
            f"mentions  created={self.mentions_created} reused={self.mentions_reused}\n"
            f"errors    {len(self.errors)}"
        )


class CmsClient:
    def __init__(self, base: str, token: str, *, dry_run: bool, timeout: int = 30) -> None:
        self.base = base.rstrip("/")
        self.dry_run = dry_run
        self.timeout = timeout
        self._dry_seq = 0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
        )

    def get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        r = self.session.get(f"{self.base}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a WriteEnvelope. Returns the created row.

        The CMS wraps every write as ``{reason, payload}``; a flat body returns
        a misleading 422.
        """
        if self.dry_run:
            # Unique per call: callers key dedupe maps on the returned id, so a
            # constant placeholder would collapse every row into one.
            self._dry_seq += 1
            return {"id": f"dry-run:{self._dry_seq}:{path}", "_dry_run": True}
        body = json.dumps({"reason": REASON, "payload": payload}, ensure_ascii=False)
        r = self.session.post(
            f"{self.base}{path}", data=body.encode("utf-8"), timeout=self.timeout
        )
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:400]}")
        return (r.json() or {}).get("row") or {}

    # -- paged lookup helpers -------------------------------------------------

    def find_all(self, path: str, params: dict[str, Any], *, page: int = 200) -> list[dict]:
        # Dry run stays fully offline so it can be executed without a reachable
        # backend or an admin token — it reports what a first, empty-database
        # pass would write.
        if self.dry_run:
            return []
        out: list[dict] = []
        offset = 0
        while True:
            data = self.get(path, {**params, "limit": page, "offset": offset})
            items = data.get("items") or []
            out.extend(items)
            if len(items) < page:
                return out
            offset += page


def resolve_subject(client: CmsClient, stats: Stats, *, slug: str, name: str, group: str,
                    description: str) -> str:
    for row in client.find_all(f"{CMS}/subjects", {"q": name}):
        if row.get("slug") == slug:
            stats.subjects_reused += 1
            return row["id"]
    row = client.post(
        f"{CMS}/subjects",
        {
            "slug": slug,
            "name": name,
            "subject_group": group,
            "description": description,
            "is_active": True,
            "metadata": {"source": "upsc_gs_micro_theme_map", "paper_id": group},
        },
    )
    stats.subjects_created += 1
    return row["id"]


def resolve_topic(client: CmsClient, stats: Stats, *, subject_id: str, parent_id: str | None,
                  slug: str, name: str, level: str, description: str | None,
                  metadata: dict[str, Any], existing: dict[tuple, str]) -> str:
    key = (subject_id, parent_id, slug)
    if key in existing:
        if level == "microtopic":
            stats.micro_reused += 1
        else:
            stats.macro_reused += 1
        return existing[key]
    payload: dict[str, Any] = {
        "subject_id": subject_id,
        "slug": slug,
        "name": name[:300],
        "level": level,
        "is_active": True,
        "metadata": metadata,
    }
    if parent_id:
        payload["parent_topic_id"] = parent_id
    if description:
        payload["description"] = description
    row = client.post(f"{CMS}/topics", payload)
    topic_id = row["id"]
    existing[key] = topic_id
    if level == "microtopic":
        stats.micro_created += 1
    else:
        stats.macro_created += 1
    return topic_id


def load_topic_index(client: CmsClient, subject_id: str) -> dict[tuple, str]:
    """Pre-load every topic for a subject so lookups don't hit the API per row.

    The topics upsert key is (subject_id, parent_topic_id, slug), but Postgres
    treats NULL parent_topic_id values as distinct, so a macro topic would be
    duplicated on re-run if we relied on upsert alone. Resolving locally first
    keeps the ingest genuinely idempotent.
    """
    index: dict[tuple, str] = {}
    for row in client.find_all(f"{CMS}/topics", {"subject_id": subject_id}):
        index[(row.get("subject_id"), row.get("parent_topic_id"), row.get("slug"))] = row["id"]
    return index


def resolve_document(client: CmsClient, stats: Stats, *, exam_id: str, title: str,
                     content_hash: str, source_url: str | None,
                     metadata: dict[str, Any]) -> str:
    for row in client.find_all(f"{CMS}/syllabus-documents", {"exam_id": exam_id}):
        if row.get("content_hash") == content_hash:
            stats.document_reused += 1
            return row["id"]
    payload: dict[str, Any] = {
        "exam_id": exam_id,
        "document_type": "official_page",
        "title": title,
        "content_hash": content_hash,
        "metadata": metadata,
    }
    if source_url:
        payload["source_url"] = source_url
    row = client.post(f"{CMS}/syllabus-documents", payload)
    stats.document_created += 1
    return row["id"]


def load_mention_index(client: CmsClient, document_id: str) -> set[str]:
    rows = client.find_all(
        f"{CMS}/syllabus-topic-mentions", {"syllabus_document_id": document_id}
    )
    return {r["topic_id"] for r in rows if r.get("topic_id")}


def create_mention(client: CmsClient, stats: Stats, *, document_id: str, exam_id: str,
                   exam_phase_id: str | None, topic_id: str, raw_text: str,
                   mention_type: str, seen: set[str]) -> None:
    if topic_id in seen:
        stats.mentions_reused += 1
        return
    payload: dict[str, Any] = {
        "syllabus_document_id": document_id,
        "exam_id": exam_id,
        "topic_id": topic_id,
        "raw_text": raw_text,
        "normalized_text": " ".join(raw_text.lower().split()),
        "mention_type": mention_type,
        # Deterministic extraction from a structured source file: the mapping is
        # exact, but reviewer_status stays 'pending' regardless — confidence is
        # not a substitute for review.
        "confidence_score": 1.0,
        "extraction_method": "structured_json_import_v1",
    }
    if exam_phase_id:
        payload["exam_phase_id"] = exam_phase_id
    client.post(f"{CMS}/syllabus-topic-mentions", payload)
    seen.add(topic_id)
    stats.mentions_created += 1


def run(args: argparse.Namespace) -> int:
    raw = Path(args.source).read_bytes()
    content_hash = hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw)

    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base:
        print("error: set --api-base or CCP_API_BASE", file=sys.stderr)
        return 2
    if not token and not args.dry_run:
        print("error: set CCP_ADMIN_JWT", file=sys.stderr)
        return 2

    client = CmsClient(base, token, dry_run=args.dry_run)
    stats = Stats()

    title = (
        f"{doc.get('examination', 'UPSC CSE Mains')} — "
        f"{doc.get('document_type', 'Official Syllabus')} v{doc.get('version', '?')}"
    )
    document_id = resolve_document(
        client,
        stats,
        exam_id=args.exam_id,
        title=title[:300],
        content_hash=content_hash,
        source_url=args.source_url,
        metadata={
            "exam_body": doc.get("exam_body"),
            "version": doc.get("version"),
            "last_updated": doc.get("last_updated"),
            "ingest_script": "scripts/ingest_upsc_gs_syllabus.py",
        },
    )
    mentions_seen: set[str] = set() if args.dry_run else load_mention_index(client, document_id)

    for paper in doc.get("papers", []):
        paper_id = paper.get("paper_id", "")
        subject_slug = f"upsc-cse-mains-{_ROMAN.get(paper_id, slugify(paper_id))}"
        subject_id = resolve_subject(
            client,
            stats,
            slug=subject_slug,
            name=paper.get("paper_title", paper_id),
            group=paper_id,
            description="; ".join(paper.get("core_subjects", [])) or None,
        )
        topic_index = {} if args.dry_run else load_topic_index(client, subject_id)

        for node in paper.get("syllabus_nodes", []):
            macro = node.get("macro_topic", "").strip()
            if not macro:
                continue
            official_line = (node.get("official_syllabus_line") or "").strip()
            macro_id = resolve_topic(
                client,
                stats,
                subject_id=subject_id,
                parent_id=None,
                slug=slugify(f"{paper_id}:{macro}"),
                name=macro,
                level="topic",
                description=official_line or None,
                metadata={
                    "paper_id": paper_id,
                    "official_syllabus_line": official_line,
                    "source": "upsc_gs_micro_theme_map",
                },
                existing=topic_index,
            )
            create_mention(
                client,
                stats,
                document_id=document_id,
                exam_id=args.exam_id,
                exam_phase_id=args.exam_phase_id,
                topic_id=macro_id,
                raw_text=official_line or macro,
                mention_type="explicit",
                seen=mentions_seen,
            )

            for theme in node.get("micro_themes", []):
                theme = (theme or "").strip()
                if not theme:
                    continue
                micro_id = resolve_topic(
                    client,
                    stats,
                    subject_id=subject_id,
                    parent_id=macro_id,
                    slug=slugify(f"{paper_id}:{macro}:{theme}"),
                    name=theme,
                    level="microtopic",
                    description=theme if len(theme) > 300 else None,
                    metadata={
                        "paper_id": paper_id,
                        "macro_topic": macro,
                        "source": "upsc_gs_micro_theme_map",
                    },
                    existing=topic_index,
                )
                # A micro theme is a curator's decomposition of the official
                # line, not a phrase quoted from it -> 'derived', not 'explicit'.
                create_mention(
                    client,
                    stats,
                    document_id=document_id,
                    exam_id=args.exam_id,
                    exam_phase_id=args.exam_phase_id,
                    topic_id=micro_id,
                    raw_text=theme,
                    mention_type="derived",
                    seen=mentions_seen,
                )
                if args.sleep:
                    time.sleep(args.sleep)

    print(stats.render())
    if args.dry_run:
        print("\nDRY RUN — nothing written. Re-run without --dry-run to apply.")
    else:
        print(
            f"\nsyllabus_document_id={document_id}\n"
            "All rows are pending. Promote via the review endpoints:\n"
            f"  POST {CMS}/syllabus-documents/{document_id}/review\n"
            f"  PATCH {CMS}/syllabus-topic-mentions/{{mention_id}}"
        )
    return 1 if stats.errors else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source", help="Path to the syllabus micro-theme JSON file")
    p.add_argument("--exam-id", required=True, help="exams.id for UPSC CSE")
    p.add_argument("--exam-phase-id", default=None, help="exam_phases.id for Mains (optional)")
    p.add_argument("--api-base", default=None, help="Backend base URL (or CCP_API_BASE)")
    p.add_argument("--source-url", default=None, help="Official syllabus URL for the evidence row")
    p.add_argument("--sleep", type=float, default=0.0, help="Delay between micro-theme writes")
    p.add_argument("--dry-run", action="store_true", help="Parse and report without writing")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
