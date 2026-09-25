"""REG-CORPUS-03/04 — corpus → import converter (REG + QRE) and SME review worksheets.

No database and no network. The topics export is synthesised from the corpus
catalogue (``workbench/corpus/reg/lists``) with deterministic fake ids.
"""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import math
import sys
import uuid
from pathlib import Path

import pytest

from app.admin.mock_import import commit_import, dry_run
from tests.persona_questions._stub import SBStub

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


conv = _load("reg_corpus_to_import")
ws = _load("reg_corpus_worksheet")


def _id(s: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, s))


def _subject_of(slug: str) -> str:
    return _id("subject:" + slug.split("-")[0])


@pytest.fixture(scope="module")
def catalogue() -> set[str]:
    return conv.load_catalogue()


@pytest.fixture(scope="module")
def corpus() -> dict[str, list[dict]]:
    return conv.load_corpus()


@pytest.fixture(scope="module")
def factcheck() -> dict[str, str]:
    return conv.load_factcheck()


def _topics(catalogue: set[str], drop: set[str] = frozenset()) -> dict[str, dict]:
    return {
        s: {"id": _id(s), "slug": s, "level": "microtopic", "parent_topic_id": None,
            "subject_id": _subject_of(s)}
        for s in catalogue if s not in drop
    }


def _write_topics_csv(path: Path, topics: dict[str, dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "slug", "level", "parent_topic_id", "subject_id"])
        w.writeheader()
        for t in topics.values():
            w.writerow({**t, "parent_topic_id": t["parent_topic_id"] or ""})
    return path


def _cst(corpus) -> list[dict]:
    return copy.deepcopy(corpus["REG-CORPUS-CST"])


# ── converter ─────────────────────────────────────────────────────────────────

def test_whole_corpus_converts_with_no_errors(corpus, catalogue, factcheck):
    rows, errors = conv.build(corpus, topics=_topics(catalogue), catalogue=catalogue, factcheck=factcheck)
    assert all(not e for e in errors.values()), errors
    # 1,850 REG + 3,315 QRE; 16 + 8 batches
    assert sum(len(r) for r in rows.values()) == 5165
    assert len(rows) == 24
    # every factcheck row (REG-FACTCHECK-1 + QRE-FACTCHECK-GK) reaches its row's metadata
    verdicts = [r["metadata"]["factcheck_verdict"] for rs in rows.values() for r in rs]
    assert verdicts.count("confirmed") == 931 + 820
    assert verdicts.count("fix_needed") == 66 + 4
    assert verdicts.count("wrong_key") == 14 + 1


def test_row_shape_is_authored_draft_with_no_exam(corpus, catalogue, factcheck):
    rows, _ = conv.build({"REG-CORPUS-ACT-BANK": corpus["REG-CORPUS-ACT-BANK"]},
                         topics=_topics(catalogue), catalogue=catalogue, factcheck=factcheck)
    by_id = {r["external_id"]: r for r in rows["REG-CORPUS-ACT-BANK"]}
    row = by_id["ACTB-042"]
    q = next(q for q in corpus["REG-CORPUS-ACT-BANK"] if q["id"] == "ACTB-042")
    assert "exam_id" not in row
    assert row["source_kind"] == "authored"
    assert row["difficulty"] == q["difficulty"]
    assert row["topic_id"] == _id(q["microtopic_slug"])
    assert row["metadata"] == {
        "corpus_id": "ACTB-042", "batch": "REG-CORPUS-ACT-BANK", "corpus_version": "v1.1",
        "verify_fact": True, "factcheck_verdict": "wrong_key",
    }
    se = row["structured_explanation"]
    assert se["solution_steps"] == q["explanation"]["steps"]
    assert se["formula_used"] == [q["explanation"]["formula_used"]]
    assert row["common_trap"] == q["explanation"]["trap"] == se["common_traps"][0]
    assert se["option_rationales"] == {
        str(i): o["error"] for i, o in enumerate(q["options"]) if not o["is_correct"]
    }


def test_case_set_rows_get_their_own_stimulus_and_a_bare_stem(corpus, catalogue, factcheck):
    batch = corpus["REG-CORPUS-ACC"]  # no **Q.** marker: split on the shared prefix
    rows, errors = conv.build({"REG-CORPUS-ACC": batch}, topics=_topics(catalogue),
                              catalogue=catalogue, factcheck=factcheck)
    assert not errors["REG-CORPUS-ACC"]
    case = [r for r in rows["REG-CORPUS-ACC"] if r["stimulus_group"] == "ACC-C1-KAVERI"]
    assert len(case) == 4
    assert all(len(r["stimuli"]) == 1 for r in case)
    assert len({r["stimuli"][0]["content_text"] for r in case}) == 1
    stimulus = case[0]["stimuli"][0]["content_text"]
    for r in case:
        assert stimulus not in r["question_text"]
        original = next(q["stem"] for q in batch if q["id"] == r["external_id"])
        assert original.startswith(stimulus) and original.endswith(r["question_text"])


def test_cst_case_split_matches_the_1216_marker_split(corpus):
    splits, errors = conv.case_splits(_cst(corpus))
    assert not errors
    stimulus, stem = splits["CST-065"]
    assert stem.startswith("**Q.**")
    assert stimulus.startswith("**Case — Sarayu Chemicals")
    assert "|---|" in stimulus


def test_unknown_slug_fails_loudly(corpus, catalogue, factcheck):
    qs = _cst(corpus)
    qs[0]["microtopic_slug"] = "cost-not-a-real-slug-00000000"
    _, errors = conv.build({"REG-CORPUS-CST": qs}, topics=_topics(catalogue),
                           catalogue=catalogue, factcheck=factcheck)
    assert any("unknown microtopic slug" in e and qs[0]["id"] in e for e in errors["REG-CORPUS-CST"])


def test_catalogue_slug_missing_from_the_export_fails_loudly(corpus, catalogue, factcheck):
    qs = _cst(corpus)
    slug = qs[0]["microtopic_slug"]
    _, errors = conv.build({"REG-CORPUS-CST": qs}, topics=_topics(catalogue, drop={slug}),
                           catalogue=catalogue, factcheck=factcheck)
    assert any("missing topic" in e and slug in e for e in errors["REG-CORPUS-CST"])


def test_orphan_microtopic_in_the_export_fails_loudly(corpus, catalogue, factcheck):
    qs = _cst(corpus)
    topics = _topics(catalogue)
    topics[qs[0]["microtopic_slug"]]["parent_topic_id"] = _id("parent-not-exported")
    _, errors = conv.build({"REG-CORPUS-CST": qs}, topics=topics, catalogue=catalogue, factcheck=factcheck)
    assert any("missing topic: parent" in e for e in errors["REG-CORPUS-CST"])


def test_duplicate_fingerprint_within_the_run_fails_loudly(corpus, catalogue, factcheck):
    qs = _cst(corpus)
    dup = copy.deepcopy(next(q for q in qs if not q.get("stimulus_group")))
    dup["id"] = "CST-999"
    qs.append(dup)
    _, errors = conv.build({"REG-CORPUS-CST": qs}, topics=_topics(catalogue),
                           catalogue=catalogue, factcheck=factcheck)
    assert any(e.startswith("CST-999: duplicate fingerprint") for e in errors["REG-CORPUS-CST"])


def test_duplicate_fingerprint_across_batches_fails_loudly(corpus, catalogue, factcheck):
    other = copy.deepcopy(next(q for q in _cst(corpus) if not q.get("stimulus_group")))
    other["id"] = "CST-PILOT-DUP"
    _, errors = conv.build({"REG-CORPUS-CST": _cst(corpus), "REG-CORPUS-X": [other]},
                           topics=_topics(catalogue), catalogue=catalogue, factcheck=factcheck)
    assert any("duplicate fingerprint" in e for e in errors["REG-CORPUS-X"])


def test_case_set_whose_stems_do_not_share_a_stimulus_fails_loudly(corpus, catalogue, factcheck):
    qs = _cst(corpus)
    first = next(q for q in qs if q.get("stimulus_group") == "CST-CASE-PROC")
    first["stem"] = "**Case — something else entirely**\n\n**Q.** Unrelated?"
    _, errors = conv.build({"REG-CORPUS-CST": qs}, topics=_topics(catalogue),
                           catalogue=catalogue, factcheck=factcheck)
    assert any("case set CST-CASE-PROC" in e and "do not share a stimulus" in e
               for e in errors["REG-CORPUS-CST"])


def test_only_ids_restricts_the_run(corpus, catalogue, factcheck):
    rows, errors = conv.build({"REG-CORPUS-CST": _cst(corpus)}, topics=_topics(catalogue),
                              catalogue=catalogue, factcheck=factcheck,
                              only_ids={"CST-001", "CST-065"})
    assert not errors["REG-CORPUS-CST"]
    assert [r["external_id"] for r in rows["REG-CORPUS-CST"]] == ["CST-001", "CST-065"]
    assert rows["REG-CORPUS-CST"][1]["stimuli"]  # its case split still comes from the full set


def test_cli_dry_run_prints_counts_writes_nothing_and_exits_by_errors(tmp_path, catalogue, capsys):
    topics_csv = _write_topics_csv(tmp_path / "topics.csv", _topics(catalogue))
    out = tmp_path / "import"
    args = ["--topics", str(topics_csv), "--batch", "REG-CORPUS-CST",
            "--batch", "REG-CORPUS-CST-PILOT", "--out", str(out)]
    assert conv.main(args + ["--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "REG-CORPUS-CST: 80 rows" in printed and "REG-CORPUS-CST-PILOT: 20 rows" in printed
    assert not out.exists()

    bad_csv = _write_topics_csv(tmp_path / "bad.csv", _topics(
        catalogue, drop={"cost-equivalent-production-fifo-and-weighted-average-bcff4541"}))
    assert conv.main(["--topics", str(bad_csv), "--batch", "REG-CORPUS-CST", "--out", str(out)]) == 1
    assert not out.exists()  # an error writes nothing, even without --dry-run

    assert conv.main(args) == 0
    written = json.loads((out / "REG-CORPUS-CST.import.json").read_text(encoding="utf-8"))
    assert len(written) == 80


def test_cli_rejects_an_unknown_batch(tmp_path, catalogue):
    topics_csv = _write_topics_csv(tmp_path / "topics.csv", _topics(catalogue))
    assert conv.main(["--topics", str(topics_csv), "--batch", "REG-CORPUS-NOPE", "--dry-run"]) == 1


def test_converted_batch_passes_the_importer_and_commits_as_draft(corpus, catalogue, factcheck):
    topics = _topics(catalogue)
    batches = {b: corpus[b] for b in ("REG-CORPUS-CST", "REG-CORPUS-CST-PILOT")}
    rows, errors = conv.build(batches, topics=topics, catalogue=catalogue, factcheck=factcheck)
    assert not any(errors.values())
    payload = rows["REG-CORPUS-CST"] + rows["REG-CORPUS-CST-PILOT"]
    sb = SBStub()
    sb.db["subjects"] = [{"id": sid} for sid in {r["subject_id"] for r in payload}]
    sb.db["topics"] = [{"id": t["id"], "subject_id": t["subject_id"]} for t in topics.values()]
    actor = {"id": "author-1", "role": "admin", "permissions": ["mock_questions:author"]}
    preview = dry_run(sb, actor, json.dumps(payload).encode("utf-8"), "application/json")
    assert preview["ok_count"] == 100, [r for r in preview["rows"] if r["status"] != "ok"][:3]
    res = commit_import(sb, actor, preview["import_token"])
    assert res["created"] == 100 and res["failed"] == 0
    bank = sb.db["mock_question_bank"]
    assert {r["reviewer_status"] for r in bank} == {"draft"}
    assert {r["source_kind"] for r in bank} == {"authored"}
    assert all(r["exam_id"] is None for r in bank)
    assert {r["metadata"]["corpus_version"] for r in bank} == {"v1.1"}
    assert len(sb.db["mock_question_stimuli"]) == 20  # 16 CST + 4 pilot case rows, one copy each


def test_importer_still_validates_rubric_level_arriving_in_metadata():
    sb = SBStub()
    row = {"question_text": "Q?", "option_1": "A", "option_2": "B", "correct_option": "1",
           "metadata": {"rubric_level": "L9"}}
    preview = dry_run(sb, {"id": "a"}, json.dumps([row]).encode(), "application/json")
    assert preview["error_count"] == 1
    row["metadata"] = "not-an-object"
    preview = dry_run(sb, {"id": "a"}, json.dumps([row]).encode(), "application/json")
    assert preview["error_count"] == 1


# ── worksheets ────────────────────────────────────────────────────────────────

def test_worksheet_orders_fix1_rows_then_sample_then_rest(corpus, factcheck):
    corpus = conv.load_corpus(conv.CORPUS_DIR)
    batch = "REG-CORPUS-ACT-REC"
    rows = ws.worksheet_rows(corpus[batch], factcheck, batch=batch)
    assert list(rows[0]) == ws.COLUMNS
    verdicts = [r["factcheck_verdict"] for r in rows]
    n_fix = sum(v in ("wrong_key", "fix_needed") for v in verdicts)
    n_conf = verdicts.count("confirmed")
    n_sample = math.ceil(n_conf * 0.10)
    assert n_fix == 11
    assert all(v in ("wrong_key", "fix_needed") for v in verdicts[:n_fix])
    block = rows[n_fix:n_fix + n_sample]
    assert all(r["sample"] == "Y" and r["factcheck_verdict"] == "confirmed" for r in block)
    assert all(r["sample"] == "" for r in rows[n_fix + n_sample:])
    assert len(rows) == len(corpus[batch]) and len({r["id"] for r in rows}) == len(rows)
    assert all(r[c] == "" for r in rows for c in ("reviewer", "decision", "fix_note", "minutes_spent"))


def test_worksheet_sample_is_seeded(corpus, factcheck):
    batch = "REG-CORPUS-CA-B"
    a = [r["id"] for r in ws.worksheet_rows(corpus[batch], factcheck, batch=batch) if r["sample"]]
    b = [r["id"] for r in ws.worksheet_rows(corpus[batch], factcheck, batch=batch) if r["sample"]]
    c = [r["id"] for r in ws.worksheet_rows(corpus[batch], factcheck, batch=batch, seed="other") if r["sample"]]
    assert a == b and a != c


def test_committed_worksheets_match_a_fresh_run(factcheck):
    for batch, qs in conv.load_corpus(conv.CORPUS_DIR).items():
        path = ws.REVIEW_DIR / f"{batch}.csv"
        with path.open(encoding="utf-8-sig", newline="") as f:
            committed = list(csv.DictReader(f))
        fresh = ws.worksheet_rows(qs, factcheck, batch=batch)
        # reviewer columns may be filled in later; everything else is generated
        keep = [c for c in ws.COLUMNS if c not in ("reviewer", "decision", "fix_note", "minutes_spent")]
        assert [{k: r[k] for k in keep} for r in committed] == [{k: r[k] for k in keep} for r in fresh], batch


def test_worksheet_cli_never_overwrites_without_force(tmp_path):
    assert ws.main(["--batch", "REG-CORPUS-CST-PILOT", "--out", str(tmp_path)]) == 0
    path = tmp_path / "REG-CORPUS-CST-PILOT.csv"
    before = path.read_text(encoding="utf-8-sig").replace(",,,,\n", ",sme,verified,,3\n", 1)
    assert ",sme,verified,,3" in before  # a reviewer has started filling it in
    path.write_text(before, encoding="utf-8-sig")
    assert ws.main(["--batch", "REG-CORPUS-CST-PILOT", "--out", str(tmp_path)]) == 1
    assert path.read_text(encoding="utf-8-sig") == before
    assert ws.main(["--batch", "REG-CORPUS-CST-PILOT", "--out", str(tmp_path), "--force"]) == 0


def test_duplicate_export_slug_fails_only_when_the_corpus_uses_it(tmp_path, corpus, catalogue, factcheck):
    topics = _topics(catalogue)
    used = corpus["REG-CORPUS-CST"][0]["microtopic_slug"]
    rows = list(topics.values()) + [
        {"id": _id("dup-a"), "slug": "introduction", "level": "topic", "parent_topic_id": None, "subject_id": _id("s1")},
        {"id": _id("dup-b"), "slug": "introduction", "level": "topic", "parent_topic_id": None, "subject_id": _id("s2")},
        {**topics[used], "id": _id("dup-used"), "subject_id": _id("s3")},
    ]
    path = tmp_path / "topics.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "slug", "level", "parent_topic_id", "subject_id"])
        w.writeheader()
        w.writerows({**r, "parent_topic_id": r["parent_topic_id"] or ""} for r in rows)
    loaded = conv.load_topics(path)
    _, errors = conv.build({"REG-CORPUS-CST": _cst(corpus)}, topics=loaded,
                           catalogue=catalogue, factcheck=factcheck)
    errs = errors["REG-CORPUS-CST"]
    assert errs and all("ambiguous topic" in e and used in e for e in errs)


# ── REG-CORPUS-04: QRE corpus, exam tier, stimulus-aware fingerprint ──────────

def test_qre_qa_a_converts_with_exam_tier_and_its_own_corpus_version(corpus, catalogue, factcheck):
    rows, errors = conv.build({"QRE-QA-A": corpus["QRE-QA-A"]}, topics=_topics(catalogue),
                              catalogue=catalogue, factcheck=factcheck)
    assert not errors["QRE-QA-A"]
    qa = rows["QRE-QA-A"]
    assert len(qa) == 390
    tiers = [r["metadata"]["exam_tier"] for r in qa]
    assert tiers.count("foundation") == 130 and tiers.count("officer") == 260
    assert {r["metadata"]["corpus_version"] for r in qa} == {"v1"}
    assert {r["metadata"]["factcheck_verdict"] for r in qa} == {"not_flagged"}
    assert all(r["source_kind"] == "authored" and "exam_id" not in r for r in qa)


def test_reg_rows_stay_untiered(corpus, catalogue, factcheck):
    rows, _ = conv.build({"REG-CORPUS-CST": _cst(corpus)}, topics=_topics(catalogue),
                         catalogue=catalogue, factcheck=factcheck)
    assert all("exam_tier" not in r["metadata"] for r in rows["REG-CORPUS-CST"])
    assert {r["metadata"]["corpus_version"] for r in rows["REG-CORPUS-CST"]} == {"v1.1"}


def test_gk_factcheck_verdicts_come_from_the_qre_csv(corpus, catalogue, factcheck):
    rows, _ = conv.build({"QRE-GK-A": corpus["QRE-GK-A"]}, topics=_topics(catalogue),
                         catalogue=catalogue, factcheck=factcheck)
    by_id = {r["external_id"]: r for r in rows["QRE-GK-A"]}
    assert by_id["GKA-339"]["metadata"]["factcheck_verdict"] == "wrong_key"
    assert by_id["GKA-001"]["metadata"]["factcheck_verdict"] == "confirmed"


def test_invalid_exam_tier_fails_loudly(corpus, catalogue, factcheck):
    qs = copy.deepcopy(corpus["QRE-QA-A"][:1])
    qs[0]["exam_tier"] = "graduate"
    _, errors = conv.build({"QRE-QA-A": qs}, topics=_topics(catalogue), catalogue=catalogue, factcheck=factcheck)
    assert any("exam_tier must be foundation|officer" in e for e in errors["QRE-QA-A"])


def test_same_question_over_different_case_stimuli_is_not_a_duplicate(corpus, catalogue, factcheck):
    # GRB-518 (set 1) and GRB-522 (set 2) both ask "Which step is the last step?"
    # with the same options; only the case data differs.
    rows, errors = conv.build({"QRE-GIR-B": corpus["QRE-GIR-B"]}, topics=_topics(catalogue),
                              catalogue=catalogue, factcheck=factcheck)
    assert not errors["QRE-GIR-B"]
    by_id = {r["external_id"]: r for r in rows["QRE-GIR-B"]}
    a, b = by_id["GRB-518"], by_id["GRB-522"]
    assert a["question_text"] == b["question_text"]
    assert a["stimuli"][0]["content_text"] != b["stimuli"][0]["content_text"]
    sb = SBStub({"subjects": [{"id": a["subject_id"]}],
                 "topics": [{"id": a["topic_id"], "subject_id": a["subject_id"]}]})
    preview = dry_run(sb, {"id": "a"}, json.dumps([a, b]).encode("utf-8"), "application/json")
    assert preview["ok_count"] == 2, preview["rows"]
    fps = {r["preview"]["fingerprint"] for r in preview["rows"]}
    assert len(fps) == 2


def test_row_without_stimuli_keeps_its_pre_04_fingerprint():
    import hashlib
    row = {"question_text": "What is 2 + 2?", "option_1": "4", "option_2": "5", "correct_option": "1"}
    preview = dry_run(SBStub(), {"id": "a"}, json.dumps([row]).encode(), "application/json")
    legacy = hashlib.sha256("what is 2 + 2?|4|5|0".encode("utf-8")).hexdigest()
    assert preview["rows"][0]["preview"]["fingerprint"] == legacy


def test_cli_dry_run_for_the_qre_pilot_batch(tmp_path, catalogue, capsys):
    topics_csv = _write_topics_csv(tmp_path / "topics.csv", _topics(catalogue))
    assert conv.main(["--topics", str(topics_csv), "--batch", "QRE-QA-A", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "QRE-QA-A: 390 rows" in out and "tier {'foundation': 130, 'officer': 260}" in out


def test_importer_rejects_an_invalid_exam_tier_in_metadata():
    row = {"question_text": "Q?", "option_1": "A", "option_2": "B", "correct_option": "1",
           "metadata": {"exam_tier": "graduate"}}
    preview = dry_run(SBStub(), {"id": "a"}, json.dumps([row]).encode(), "application/json")
    assert preview["error_count"] == 1
