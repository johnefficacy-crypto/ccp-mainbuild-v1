#!/usr/bin/env python3
r"""Compile the twelve optional + one GS syllabus files into one lookup index.

WHY THIS EXISTS, AND WHY IT IS NOT A MIGRATION
----------------------------------------------
The syllabus hierarchy is already in the database. `scripts/ingest_upsc_gs_syllabus.py`
writes it from these same files:

    subjects            <- papers[].paper_title      (the subject row IS the paper)
    topics(topic)       <- syllabus_nodes[].macro_topic   (the numbered unit)
    topics(microtopic)  <- syllabus_nodes[].micro_themes[]  (the themes)

and it stamps `topics.metadata.paper_id` on both levels and
`topics.metadata.macro_topic` on every microtopic. So a theme already knows its
paper and its syllabus section without a join, a walk, or a guess.

What the database does NOT carry is ORDER. `public.topics` has no sort column,
and `unique(subject_id, parent_topic_id, slug)` says nothing about sequence, so
reading the tree back gives the right nesting in an arbitrary order. Syllabus
order is a property of the official document, and the official document is
these files.

This script turns their order into a data file the backend reads. No new table,
no new migration, no second copy of the tree: only the one fact the schema
cannot express. The alternative — a syllabus_nodes table plus a topic→node
mapping — would duplicate `topics` and require a human-reviewed mapping for
rows the ingest already placed deterministically.

Decision M10-rev3 (docs/status/2026-09-10-mains-optionals-strategy-rev3.md)
governs the shape: the numbered units ARE the topic level, a syllabus's named
parts are node metadata, and parts must never become `exam_phase_sections`.
`section_ref` is carried here as `part` for display grouping only.

Run:

    python scripts/build_syllabus_index.py            # check, non-zero if stale
    python scripts/build_syllabus_index.py --write    # regenerate
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "docs" / "reference" / "syllabus"
OUT = ROOT / "app" / "backend" / "app" / "study_os" / "syllabus_index.json"

#: The GS paper ids, in sitting order. The optionals order by their own file.
GS_PAPER_ORDER = ["GS_1", "GS_2", "GS_3", "GS_4"]

SOURCE_GLOBS = ("upsc_opt_*_syllabus_v*.json", "upsc_cse_mains_gs_micro_themes_v*.json")


def paper_label(paper_id: str) -> str:
    """"GS_1" -> "GS1"; "opt-anthropology-p1" -> "P1".

    The label a chip carries. The subject name is already above it, so the
    label says only which paper within that subject.
    """
    m = re.fullmatch(r"GS_(\d)", paper_id)
    if m:
        return f"GS{m.group(1)}"
    m = re.search(r"-p(\d)$", paper_id)
    if m:
        return f"P{m.group(1)}"
    if paper_id.lower().endswith("essay"):
        return "Essay"
    return paper_id


def paper_sort_key(paper_id: str) -> int:
    m = re.fullmatch(r"GS_(\d)", paper_id)
    if m:
        return int(m.group(1))
    m = re.search(r"-p(\d)$", paper_id)
    if m:
        return int(m.group(1))
    if paper_id.lower().endswith("essay"):
        return 99
    return 50


def build(source_dir: Path = SOURCE_DIR) -> dict:
    """{papers: [...], themes: {theme name -> placement}} from the source files.

    Themes are keyed by their NAME, because that is what the catalogue has: the
    theme chips come from `topics.name` via the verified primary tag. The name
    is unique within a paper by construction (the ingest slugs
    `paper_id:macro:theme`), and a name colliding ACROSS papers is recorded
    against every paper it appears in, so the lookup stays honest rather than
    silently picking one.
    """
    files = sorted(
        {p for pattern in SOURCE_GLOBS for p in source_dir.glob(pattern)},
        key=lambda p: p.name,
    )
    if not files:
        raise SystemExit(f"no syllabus source files under {source_dir}")

    papers: dict[str, dict] = {}
    themes: dict[str, list[dict]] = {}

    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for paper in doc.get("papers", []):
            paper_id = (paper.get("paper_id") or "").strip()
            if not paper_id:
                continue
            nodes = paper.get("syllabus_nodes") or []
            sections = []
            for index, node in enumerate(nodes):
                macro = (node.get("macro_topic") or "").strip()
                if not macro:
                    continue
                sections.append(
                    {
                        "section": macro,
                        "part": (node.get("section_ref") or "").strip() or None,
                        "order": index,
                    }
                )
                for theme_index, theme in enumerate(node.get("micro_themes") or []):
                    theme = (theme or "").strip()
                    if not theme:
                        continue
                    themes.setdefault(theme, []).append(
                        {
                            "paper_id": paper_id,
                            "section": macro,
                            "section_order": index,
                            "order": theme_index,
                        }
                    )
            papers[paper_id] = {
                "paper_id": paper_id,
                "label": paper_label(paper_id),
                "title": (paper.get("paper_title") or paper_id).strip(),
                "sort": paper_sort_key(paper_id),
                "source_file": path.name,
                "source_version": doc.get("version"),
                "sections": sections,
            }

    return {
        "generated_by": "scripts/build_syllabus_index.py",
        "sources": [p.name for p in files],
        "gs_paper_order": GS_PAPER_ORDER,
        "papers": [papers[k] for k in sorted(papers, key=lambda k: (paper_sort_key(k), k))],
        "themes": themes,
    }


def serialise(index: dict) -> str:
    return json.dumps(index, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="regenerate (default: check only)")
    args = ap.parse_args(argv)

    text = serialise(build())
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
        return 0

    current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if current == text:
        print(f"{OUT.relative_to(ROOT)} is up to date")
        return 0
    print(f"{OUT.relative_to(ROOT)} is STALE — run with --write", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
