"""Proposal contract for ``scripts/propose_gs_insert_tags.py``: offline,
deterministic, proposals only, slugs identical to the syllabus ingest."""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("propose_gs_insert_tags", _ROOT / "scripts" / "propose_gs_insert_tags.py")
pgt = importlib.util.module_from_spec(_spec)
sys.modules["propose_gs_insert_tags"] = pgt
_spec.loader.exec_module(pgt)

CANDIDATES = [
    {"slug": "b-waste", "name": "Waste management", "doc": "Waste management solid hazardous plastic waste rules"},
    {"slug": "a-banking", "name": "Banking", "doc": "Banking structure RBI digital currency payments"},
    {"slug": "c-cyclones", "name": "Tropical cyclones", "doc": "Tropical cyclones formation movement intensity"},
]
HEADER = {"paper": "GS3", "paper_code": "UPSC-CSE-MAINS-GS-2026-GS3", "year": 2026}


def q(text):
    return {"text": text, "content_hash": pgt.egm.content_hash(text), "official_number": 1, "sub_part": None}


def test_rank_picks_the_topical_candidate_and_is_deterministic():
    text = "What are the challenges to solid waste management in India? Discuss the policy framework."
    first = pgt.rank(text, CANDIDATES)
    assert first[0][1]["slug"] == "b-waste"
    assert first == pgt.rank(text, list(reversed(CANDIDATES)))


def test_directive_words_carry_no_signal():
    assert pgt.terms("Discuss and examine critically in the Indian context") == []


def test_proposal_row_is_a_proposal_only():
    row = pgt.propose(q("Explain the working of the Digital Rupee issued by the RBI."), HEADER,
                      {"GS3": CANDIDATES}, [])
    assert row["status"] == "MAPPED" and row["proposed_slug"] == "a-banking"
    assert row["subject_slug"] == "upsc-cse-mains-gs3" and row["kind"] == "topic"
    assert row["approved"] == "" and row["edited_slug"] == ""
    assert row["runner_up_slug"] and row["proposer_version"] == pgt.PROPOSER_VERSION


def test_no_overlap_is_unmapped():
    row = pgt.propose(q("Quantum chromodynamics of gluons."), HEADER, {"GS3": CANDIDATES}, [])
    assert row["status"] == "UNMAPPED" and row["proposed_slug"] == ""


def test_essay_without_a_theme_export_is_unmapped():
    header = {"paper": "ESSAY", "paper_code": "UPSC-CSE-MAINS-GS-2026-ESSAY", "year": 2026}
    row = pgt.propose(q("A grateful mind is very beautiful."), header, {}, [])
    assert row["kind"] == "essay_theme" and row["status"] == "UNMAPPED" and row["subject_slug"] == ""


def test_essay_theme_catalogue_reads_active_rows_only(tmp_path):
    path = tmp_path / "themes.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in [
        {"theme_code": "ethics", "theme_name": "Ethics and values", "status": "active"},
        {"theme_code": "future", "theme_name": "Reserved", "status": "reserved"},
    ]), encoding="utf-8")
    assert [c["slug"] for c in pgt.essay_catalogue(path)] == ["ethics"]


def test_syllabus_slugs_match_the_ingest():
    cat = pgt.catalogue_from_syllabus()
    assert set(cat) == {"GS1", "GS2", "GS3", "GS4"}
    doc = json.loads(pgt.SYLLABUS_JSON.read_text(encoding="utf-8"))
    paper = doc["papers"][0]
    node = paper["syllabus_nodes"][0]
    theme = node["micro_themes"][0].strip()
    expected = pgt.slugify(f"{paper['paper_id']}:{node['macro_topic'].strip()}:{theme}")
    assert expected in {c["slug"] for c in cat["GS1"]}


def test_rerun_keeps_reviewer_columns(tmp_path):
    row = pgt.propose(q("Explain the Digital Rupee."), HEADER, {"GS3": CANDIDATES}, [])
    path = tmp_path / "tag_review.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=pgt.FIELDS)
        w.writeheader()
        w.writerow({**row, "approved": "Y", "edited_slug": "c-cyclones"})
    [merged] = pgt.merge_human([dict(row)], path)
    assert merged["approved"] == "Y" and merged["edited_slug"] == "c-cyclones"
