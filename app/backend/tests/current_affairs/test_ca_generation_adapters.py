"""Mock generation-adapter tests (GQR-G3) — deterministic, provider-free."""
from __future__ import annotations

import os

from app.current_affairs.generation import adapters as ad


_DOC = {
    "id": "doc-1",
    "title": "RBI issues digital lending circular",
    "raw_text": "The Reserve Bank of India issued a digital lending circular on 2026-06-01.",
    "document_type": "press_release",
    "published_at": "2026-06-01",
}


def test_default_adapter_is_mock_when_flag_off(monkeypatch):
    monkeypatch.delenv("FF_CA_LLM", raising=False)
    assert isinstance(ad.get_generation_adapter(), ad.MockGenerationAdapter)


def test_shadow_flag_falls_closed_to_mock_without_provider(monkeypatch):
    # No approved provider adapter module → fail closed to the mock (never crash).
    monkeypatch.setenv("FF_CA_LLM", "shadow")
    assert isinstance(ad.get_generation_adapter(), ad.MockGenerationAdapter)


def test_mock_extract_generate_verify_are_deterministic():
    a = ad.MockGenerationAdapter()
    e1 = a.extract(_DOC)
    e2 = a.extract(_DOC)
    assert len(e1.events) == 1
    assert e1.events[0]["event_fingerprint"] == e2.events[0]["event_fingerprint"]
    assert e1.events[0]["claims"] and e1.events[0]["claims"][0]["evidence"]

    claims = [{**c, "id": f"c{i}"} for i, c in enumerate(e1.events[0]["claims"])]
    g = a.generate(e1.events[0], claims)
    assert len(g.candidates) == 1
    payload = g.candidates[0]
    assert [o["id"] for o in payload["options"]] == ["a", "b", "c", "d"]
    assert payload["correct_option_id"] == "a"
    assert payload["linked_claim_ids"] == ["c0"]

    v = a.verify(payload, claims, claims[0]["evidence"])
    assert v.verdict["advisory_only"] is True
    # Every stage emits an audit run with a hashed envelope.
    for res in (e1, g, v):
        assert res.run and res.run.input_hash and res.run.output_hash


def test_empty_document_yields_no_events():
    a = ad.MockGenerationAdapter()
    out = a.extract({"id": "d", "raw_text": "", "title": ""})
    assert out.events == [] and out.run is not None
