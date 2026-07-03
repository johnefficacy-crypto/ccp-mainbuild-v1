"""Validate the committed writing-prompt bank seed (Content Studio bulk-import).

Guards `app/supabase/seeds/writing_prompts/*.json` against the same rules the
merged backend enforces (migration 215 + content_studio.py), so a hand-edited
seed row can't silently drift into a shape the bulk RPC would 422 on import.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

_SEED_DIR = Path(__file__).resolve().parents[4] / "app" / "supabase" / "seeds" / "writing_prompts"

_EXERCISE_TYPES = {
    "sentence_construction", "sentence_correction", "vocabulary_in_context",
    "sentence_rewrite", "sentence_reconstruction", "paragraph_writing",
    "summary_writing", "precis_practice", "essay_practice", "letter_practice",
}
_ALLOWED_ROW_KEYS = {
    "external_key", "exercise_type", "topic_id", "microtopic_id", "prompt_text",
    "source_text", "required_words", "required_sentence_count", "difficulty_level",
    "min_words", "max_words", "max_rewrite_attempts", "rubric_id", "source_document_id",
}
_FORBIDDEN_ROW_KEYS = {"subject_id", "exam_id", "exam_cycle_id", "exam_phase_id", "metadata"}

_WORD_RE = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*", re.UNICODE)
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_EXPECTED_COUNTS = {
    "01_sentence_construction.json": 50,
    "02_sentence_correction.json": 50,
    "03_grammar.json": 100,
    "04_vocabulary.json": 50,
    "05_paragraph.json": 20,
}


def _uuid(seed: str) -> str:
    h = hashlib.md5(seed.encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


_SUBJECT_ID = _uuid("ewp:subject:english-language")
_TOPIC_IDS = {_uuid(f"ewp:topic:{s}") for s in (
    "sentence-construction", "grammar", "vocabulary-in-context", "paragraph-writing",
)}


def _load(name):
    return json.loads((_SEED_DIR / name).read_text())


def test_total_is_270_across_five_batches():
    total = sum(len(_load(n)["rows"]) for n in _EXPECTED_COUNTS)
    assert total == 270


def test_per_batch_counts_and_envelope():
    for name, expected in _EXPECTED_COUNTS.items():
        payload = _load(name)
        assert payload["subject_id"] == _SUBJECT_ID, name
        assert 8 <= len(payload["reason"]) <= 500, name
        assert len(payload["rows"]) == expected, name


def test_every_row_matches_the_backend_contract():
    seen_keys = set()
    for name in _EXPECTED_COUNTS:
        for r in _load(name)["rows"]:
            key = r["external_key"]
            assert key and key not in seen_keys, f"{name}: dup/blank external_key {key!r}"
            seen_keys.add(key)

            assert not (_FORBIDDEN_ROW_KEYS & r.keys()), f"{key}: forbidden keys"
            assert set(r) <= _ALLOWED_ROW_KEYS, f"{key}: unknown keys {set(r) - _ALLOWED_ROW_KEYS}"

            assert r["exercise_type"] in _EXERCISE_TYPES, key
            assert r["topic_id"] in _TOPIC_IDS, f"{key}: unexpected topic_id"
            assert _UUID_RE.match(r["topic_id"]), key
            if "microtopic_id" in r:
                assert _UUID_RE.match(r["microtopic_id"]), key

            assert isinstance(r["prompt_text"], str) and r["prompt_text"].strip(), key
            assert 1 <= r["difficulty_level"] <= 10, key

            if "min_words" in r and "max_words" in r:
                assert r["max_words"] >= r["min_words"], f"{key}: max<min"

            for w in r.get("required_words", []) or []:
                e = unicodedata.normalize("NFC", w).strip()
                toks = _WORD_RE.findall(e)
                assert len(toks) == 1 and toks[0] == e, f"{key}: bad required word {w!r}"


def test_external_keys_are_namespaced():
    for name in _EXPECTED_COUNTS:
        for r in _load(name)["rows"]:
            assert r["external_key"].startswith("ewp-seed-"), r["external_key"]
