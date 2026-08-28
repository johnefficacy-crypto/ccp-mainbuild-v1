"""Unit tests for ``scripts/repair_pyq_mojibake.py``.

The script lives at the repo root (mirroring scripts/pyq_question_review.py), so
it is loaded by absolute path rather than via the ``scripts`` package.

The tool rewrites stored exam content, so the tests are weighted towards what it
must NOT do:

- known mangled strings repair to the exact original;
- clean ASCII, genuine Latin-1 accents, and Devanagari are never touched;
- double-mangled text is flagged, not silently repaired twice;
- repair only ever writes rows the scan classified MANGLED;
- --apply without --confirm writes nothing, and --apply --confirm without an
  audit file refuses to run;
- the PATCH payload never carries a hash, so the server re-hashes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "repair_pyq_mojibake.py"
_spec = importlib.util.spec_from_file_location("repair_pyq_mojibake", _SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# ─── the inverse mapping ─────────────────────────────────────────────────────
@pytest.mark.parametrize("clean", [
    "India’s satellite launch vehicles",          # right single quote  E2 80 99
    "the ‘Global Alliance’ for agriculture",      # left single quote   E2 80 98
    'He said “reforms are needed”',               # curly double quotes E2 80 9C / 9D
    "1857 – 1947 was the period",                 # en dash             E2 80 93
    "the Act — and its amendments — apply",       # em dash             E2 80 94
    "and so on…",                                 # ellipsis            E2 80 A6
    "a non breaking space",                  # NBSP                C2 A0
    "café culture",                               # plain Latin-1       C3 A9
])
def test_known_mangled_repairs_to_the_original(clean):
    """Damage the string the way the import did, then prove the inverse is exact."""
    damaged = mod.mangle(clean)
    assert damaged != clean, "test string must actually be affected by the bug"
    cls, repaired = mod.classify(damaged)
    assert cls == mod.MANGLED
    assert repaired == clean


def test_the_reported_symptom_specifically():
    """The exact case from the bug report."""
    cls, repaired = mod.classify("Indiaâ€™s")
    assert (cls, repaired) == (mod.MANGLED, "India’s")


def test_right_double_quote_survives_the_cp1252_undefined_slot():
    """U+201D ends in byte 0x9D, which strict cp1252 cannot encode.

    A naive .encode('cp1252') inverse raises here; the C1 passthrough is the
    whole reason this tool models .NET's Windows-1252 instead.
    """
    damaged = mod.mangle("“reforms”")
    with pytest.raises(UnicodeEncodeError):
        damaged.encode("cp1252")
    assert mod.classify(damaged) == (mod.MANGLED, "“reforms”")


# ─── what must never be touched ──────────────────────────────────────────────
def test_clean_ascii_is_never_rewritten():
    for s in ["Consider the following statements:", "(a) 1 and 2 only", "", None]:
        cls, repaired = mod.classify(s)
        assert cls == mod.CLEAN
        assert repaired is None


def test_already_correct_smart_punctuation_is_left_alone():
    """The repaired form must be a fixed point — re-running is a no-op."""
    for s in ["India’s reforms", "“quoted”", "1857 – 1947", "and so on…"]:
        cls, repaired = mod.classify(s)
        assert cls == mod.CLEAN, f"{s!r} would have been rewritten"
        assert repaired is None


def test_devanagari_is_classified_non_latin_and_untouched():
    """Bilingual papers carry Hindi; it cannot have come from this bug."""
    cls, repaired = mod.classify("भारत के संविधान के अनुसार")
    assert cls == mod.NON_LATIN
    assert repaired is None


def test_mixed_english_and_devanagari_is_untouched():
    cls, repaired = mod.classify("Which of the following? / निम्नलिखित में से कौन-सा?")
    assert cls == mod.NON_LATIN
    assert repaired is None


def test_genuine_latin1_accents_are_not_mistaken_for_mojibake():
    """'café' encodes to bytes that are not valid UTF-8 — correctly ignored."""
    cls, repaired = mod.classify("café culture in Pondichéry")
    assert cls == mod.CLEAN
    assert repaired is None


def test_double_mangled_text_is_flagged_not_silently_fixed():
    """Repairing twice is a different operation; a human decides."""
    twice = mod.mangle(mod.mangle("India’s"))
    cls, repaired = mod.classify(twice)
    assert cls == mod.AMBIGUOUS
    assert repaired is None


def test_repair_is_idempotent_over_a_realistic_corpus():
    """Every repaired string must classify CLEAN on a second pass."""
    for clean in ["India’s “reforms” — 1857 – 1947…", "a b", "plain ascii"]:
        cls, repaired = mod.classify(mod.mangle(clean))
        if cls == mod.MANGLED:
            assert mod.classify(repaired)[0] == mod.CLEAN


# ─── scan is pure and classifies both kinds ──────────────────────────────────
def test_scan_rows_covers_questions_and_options():
    questions = [{"id": "q1", "question_number": 1, "question_text": mod.mangle("India’s")}]
    options = {"q1": [
        {"id": "o1", "option_label": "a", "option_text": mod.mangle("“yes”")},
        {"id": "o2", "option_label": "b", "option_text": "plain"},
    ]}
    rows = mod.scan_rows(questions, options)
    by_id = {r["id"]: r for r in rows}
    assert by_id["q1"]["classification"] == mod.MANGLED
    assert by_id["q1"]["new"] == "India’s"
    assert by_id["o1"]["classification"] == mod.MANGLED
    assert by_id["o1"]["new"] == "“yes”"
    assert by_id["o2"]["classification"] == mod.CLEAN
    assert by_id["o1"]["question_id"] == "q1"
    counts = mod.summarise(rows)
    assert counts["question"][mod.MANGLED] == 1
    assert counts["option"][mod.MANGLED] == 1
    assert counts["option"][mod.CLEAN] == 1


# ─── the PATCH payload must not carry a hash ─────────────────────────────────
def test_patch_payload_omits_the_hash_so_the_server_rehashes():
    """update_pyq_question re-hashes only when no hash is supplied."""
    q = mod._patch_payload("question", "India’s", "because it was mangled")
    assert q["payload"] == {"question_text": "India’s"}
    assert "normalized_question_hash" not in q["payload"]
    o = mod._patch_payload("option", "“yes”", "because it was mangled")
    assert o["payload"] == {"option_text": "“yes”"}
    assert "normalized_option_hash" not in o["payload"]
    assert len(q["reason"]) >= 8, "CMS WriteEnvelope requires reason >= 8 chars"


def test_hash_collisions_detects_rows_that_would_violate_the_unique_index():
    rows = [
        {"kind": "question", "classification": mod.MANGLED, "id": "q1", "new": "Same  stem"},
        {"kind": "question", "classification": mod.MANGLED, "id": "q2", "new": "same stem"},
        {"kind": "question", "classification": mod.MANGLED, "id": "q3", "new": "different"},
    ]
    got = mod.hash_collisions(rows)
    assert len(got) == 1
    assert sorted(got[0][1]) == ["q1", "q2"]


def test_hash_collisions_ignores_options_and_unrepaired_rows():
    rows = [
        {"kind": "option", "classification": mod.MANGLED, "id": "o1", "new": "dup"},
        {"kind": "option", "classification": mod.MANGLED, "id": "o2", "new": "dup"},
        {"kind": "question", "classification": mod.AMBIGUOUS, "id": "q1", "new": None},
    ]
    assert mod.hash_collisions(rows) == []


# ─── repair write gates ──────────────────────────────────────────────────────
class FakeClient:
    def __init__(self, live: dict | None = None):
        self.patches: list[tuple[str, dict]] = []
        self.live = live or {}

    def get(self, path, params=None):
        return self.live.get(path, {})

    def patch(self, path, body):
        self.patches.append((path, body))
        return {"ok": True}


def _scan_file(tmp_path, rows, paper_id="p1"):
    p = tmp_path / "scan.json"
    p.write_text(json.dumps({"exam_id": "e1", "papers": [
        {"paper_id": paper_id, "year": 2018, "rows": rows}]}), encoding="utf-8")
    return str(p)


def _args(tmp_path, scan, **kw):
    base = dict(scan=scan, out=str(tmp_path / "diff.json"), audit=None,
                reason="repair mojibake for the tests", sleep=0,
                apply=False, confirm=False)
    base.update(kw)
    return argparse.Namespace(**base)


_MANGLED_ROW = {"kind": "question", "id": "q1", "question_id": "q1",
                "question_number": 1, "classification": "mangled",
                "old": "Indiaâ€™s", "new": "India’s"}


def test_dry_run_writes_nothing(tmp_path):
    fake = FakeClient()
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [_MANGLED_ROW])))
    assert rc == 0
    assert fake.patches == []
    assert json.loads((tmp_path / "diff.json").read_text())["planned"][0]["id"] == "q1"


def test_apply_without_confirm_writes_nothing(tmp_path):
    fake = FakeClient()
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [_MANGLED_ROW]), apply=True))
    assert rc == 0
    assert fake.patches == []


def test_apply_and_confirm_without_an_audit_file_refuses(tmp_path):
    fake = FakeClient()
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [_MANGLED_ROW]),
                                   apply=True, confirm=True))
    assert rc == 2
    assert fake.patches == []


def test_apply_confirm_patches_and_audits(tmp_path):
    fake = FakeClient(live={f"{mod.CMS}/pyq-questions/q1": {"question_text": "Indiaâ€™s"}})
    audit = tmp_path / "audit.jsonl"
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [_MANGLED_ROW]),
                                   apply=True, confirm=True, audit=str(audit)))
    assert rc == 0
    assert len(fake.patches) == 1
    path, body = fake.patches[0]
    assert path == f"{mod.CMS}/pyq-questions/q1"
    assert body["payload"] == {"question_text": "India’s"}
    line = json.loads(audit.read_text(encoding="utf-8").strip())
    assert line["row_id"] == "q1" and line["old"] == "Indiaâ€™s" and line["new"] == "India’s"


def test_ambiguous_and_non_latin_rows_are_never_patched(tmp_path):
    rows = [
        {"kind": "question", "id": "q2", "classification": "ambiguous",
         "old": "weird", "new": None},
        {"kind": "question", "id": "q3", "classification": "non_latin",
         "old": "भारत", "new": None},
        {"kind": "option", "id": "o9", "classification": "clean",
         "old": "fine", "new": None},
    ]
    fake = FakeClient()
    audit = tmp_path / "audit.jsonl"
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, rows),
                                   apply=True, confirm=True, audit=str(audit)))
    assert rc == 0
    assert fake.patches == []
    assert not audit.exists() or audit.read_text() == ""


def test_row_whose_live_text_drifted_is_skipped_not_overwritten(tmp_path):
    fake = FakeClient(live={f"{mod.CMS}/pyq-questions/q1":
                            {"question_text": "someone edited this"}})
    audit = tmp_path / "audit.jsonl"
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [_MANGLED_ROW]),
                                   apply=True, confirm=True, audit=str(audit)))
    assert rc == 0
    assert fake.patches == []


def test_repair_aborts_on_a_hash_collision_before_writing(tmp_path):
    rows = [
        {"kind": "question", "id": "q1", "classification": "mangled",
         "old": mod.mangle("Same stem"), "new": "Same stem"},
        {"kind": "question", "id": "q2", "classification": "mangled",
         "old": mod.mangle("Same  stem"), "new": "Same  stem"},
    ]
    fake = FakeClient()
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, rows),
                                   apply=True, confirm=True,
                                   audit=str(tmp_path / "a.jsonl")))
    assert rc == 2
    assert fake.patches == []


# ─── scope ───────────────────────────────────────────────────────────────────
_PAPERS = [
    {"id": "p1", "exam_phase_id": "PRELIMS"},
    {"id": "p2", "exam_phase_id": "MAINS"},
    {"id": "p3", "exam_phase_id": None},
]


def test_scan_scope_defaults_to_every_paper():
    """A corruption sweep wants the widest view; scan cannot write."""
    assert {p["id"] for p in mod.select_papers(_PAPERS, None, None)} == {"p1", "p2", "p3"}


def test_scan_scope_by_phase_and_by_explicit_id():
    assert {p["id"] for p in mod.select_papers(_PAPERS, {"MAINS"}, None)} == {"p2"}
    assert {p["id"] for p in mod.select_papers(_PAPERS, {"MAINS"}, {"p1"})} == {"p1"}


def test_option_drift_check_reads_through_the_parent_question():
    """There is no GET /pyq-options/{id}; options must be read via the list route."""
    fake = FakeClient(live={f"{mod.CMS}/pyq-options": {"items": [
        {"id": "o1", "option_text": "liveâ€™text"},
        {"id": "o2", "option_text": "other"},
    ]}})
    got = mod._read_live_text(fake, "option", {"id": "o1", "question_id": "q1"})
    assert got == "liveâ€™text"


def test_option_repair_actually_patches_end_to_end(tmp_path):
    """The bug this guards: a 404 on every option would skip the whole set."""
    row = {"kind": "option", "id": "o1", "question_id": "q1",
           "option_label": "a", "classification": "mangled",
           "old": "Indiaâ€™s", "new": "India’s"}
    fake = FakeClient(live={f"{mod.CMS}/pyq-options": {"items": [
        {"id": "o1", "option_text": "Indiaâ€™s"}]}})
    audit = tmp_path / "audit.jsonl"
    rc = mod.do_repair(fake, _args(tmp_path, _scan_file(tmp_path, [row]),
                                   apply=True, confirm=True, audit=str(audit)))
    assert rc == 0
    assert len(fake.patches) == 1
    path, body = fake.patches[0]
    assert path == f"{mod.CMS}/pyq-options/o1"
    assert body["payload"] == {"option_text": "India’s"}


def test_option_missing_from_its_question_is_skipped_not_patched():
    fake = FakeClient(live={f"{mod.CMS}/pyq-options": {"items": []}})
    assert mod._read_live_text(fake, "option", {"id": "gone", "question_id": "q1"}) is None
