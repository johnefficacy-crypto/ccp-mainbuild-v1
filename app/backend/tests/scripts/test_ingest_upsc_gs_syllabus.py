"""Idempotency tests for ``scripts/ingest_upsc_gs_syllabus.py`` (INGEST-FIX-01).

The script lives at the repo root (mirroring ``scripts/docx_to_pyq_json.py``),
so it is loaded by absolute path rather than via a ``scripts`` package. It
imports ``requests`` at module scope and only ever talks to the CMS over HTTP,
so a fake ``requests.Session`` backed by an in-memory store is enough to drive
the whole ingest end to end.

Observed live 2026-09-10: the same source file run twice against the same
backend re-created all 112 topics on the second run. The topic index is the
only thing that can prevent that — ``topics`` is ``unique(subject_id,
parent_topic_id, slug)``, and a NULL ``parent_topic_id`` is SQL-distinct from
every other NULL, so the CMS-side upsert cannot dedupe a macro topic. These
tests pin the index: its key must survive the null-parent round trip, it must
be consulted for micro-themes as well as macro topics, and a short index must
fail loudly rather than silently re-creating the rows it could not see.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
import uuid

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCRIPT = _ROOT / "scripts" / "ingest_upsc_gs_syllabus.py"


# ── Fake CMS backend ───────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status: int, payload: dict) -> None:
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self) -> dict:
        return self._payload


class FakeCms:
    """In-memory stand-in for the admin CMS list/create routes.

    Mirrors the real routes closely enough for idempotency to be meaningful:
    ``GET /topics`` filters on ``subject_id`` and returns ``parent_topic_id``
    explicitly (as JSON null for a macro topic), and ``POST /topics`` upserts
    on ``(subject_id, parent_topic_id, slug)`` with SQL NULL semantics — a
    NULL parent never conflicts, so a repeated macro topic inserts a NEW row.
    That last detail is the whole point: without a working local index the
    script duplicates, exactly as it did live.
    """

    #: Set to omit ``parent_topic_id`` from list rows entirely instead of
    #: rendering it as null, which is the other shape a JSON API can take.
    omit_null_parent = False
    #: Set to under-report rows from the list route while keeping ``total``
    #: honest, simulating a truncated/partial read.
    truncate_topics_to: int | None = None

    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "subjects": [], "topics": [], "syllabus-documents": [],
            "syllabus-topic-mentions": [],
        }
        self.post_calls: list[tuple[str, dict]] = []
        self.headers: dict[str, str] = {}

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _table_for(url: str) -> str:
        return url.rsplit("/", 1)[-1]

    def _rows(self, table: str, params: dict) -> list[dict]:
        rows = list(self.tables[table])
        if table == "subjects" and params.get("q"):
            rows = [r for r in rows if params["q"].lower() in (r.get("name") or "").lower()]
        if table == "topics" and params.get("subject_id"):
            rows = [r for r in rows if r.get("subject_id") == params["subject_id"]]
        if table == "syllabus-documents" and params.get("exam_id"):
            rows = [r for r in rows if r.get("exam_id") == params["exam_id"]]
        if table == "syllabus-topic-mentions" and params.get("syllabus_document_id"):
            rows = [
                r for r in rows
                if r.get("syllabus_document_id") == params["syllabus_document_id"]
            ]
        return rows

    def _render_topic(self, row: dict) -> dict:
        out = dict(row)
        if self.omit_null_parent and out.get("parent_topic_id") is None:
            out.pop("parent_topic_id", None)
        return out

    # -- requests.Session surface -----------------------------------------

    def get(self, url: str, params=None, timeout=None) -> _Resp:
        params = params or {}
        table = self._table_for(url)
        rows = self._rows(table, params)
        total = len(rows)
        if table == "topics":
            rows = [self._render_topic(r) for r in rows]
            if self.truncate_topics_to is not None:
                rows = rows[: self.truncate_topics_to]
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
        return _Resp(200, {"items": rows[offset:offset + limit], "total": total,
                           "limit": limit, "offset": offset})

    def post(self, url: str, data=None, timeout=None) -> _Resp:
        table = self._table_for(url)
        payload = json.loads(data.decode("utf-8"))["payload"]
        self.post_calls.append((table, payload))
        row = dict(payload)
        if table == "topics":
            row.setdefault("parent_topic_id", None)
            parent = row["parent_topic_id"]
            if parent is not None:
                # Non-null parent: the unique key is enforceable, so this is a
                # real upsert and a repeat returns the existing row.
                for existing in self.tables["topics"]:
                    if (existing["subject_id"], existing["parent_topic_id"],
                            existing["slug"]) == (row["subject_id"], parent, row["slug"]):
                        return _Resp(200, {"ok": True, "row": existing})
            # NULL parent never conflicts -> always a fresh row.
        row["id"] = str(uuid.uuid4())
        self.tables[table].append(row)
        return _Resp(200, {"ok": True, "row": row})

    # -- assertions -------------------------------------------------------

    def topic_writes(self) -> int:
        return sum(1 for table, _ in self.post_calls if table == "topics")


@pytest.fixture()
def mod(monkeypatch):
    """Load the script with ``requests`` stubbed out at import time."""
    fake_requests = types.ModuleType("requests")
    fake_requests.Session = lambda: _CURRENT["cms"]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    spec = importlib.util.spec_from_file_location("ingest_upsc_gs_syllabus", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "ingest_upsc_gs_syllabus", module)
    spec.loader.exec_module(module)
    return module


_CURRENT: dict[str, FakeCms] = {}


@pytest.fixture()
def cms():
    backend = FakeCms()
    # Session().headers.update(...) must work.
    backend.headers = {}
    _CURRENT["cms"] = backend
    yield backend
    _CURRENT.clear()


# ── Source fixtures ────────────────────────────────────────────────────────


def _source(macros: list[tuple[str, list[str]]]) -> dict:
    return {
        "examination": "UPSC CSE Mains",
        "document_type": "Official Syllabus",
        "version": "2026.1",
        "papers": [{
            "paper_id": "OPT_PSIR_P2",
            "paper_title": "Optional: PSIR Paper-II",
            "core_subjects": ["Comparative politics"],
            "syllabus_nodes": [
                {"macro_topic": macro, "official_syllabus_line": f"Line for {macro}",
                 "micro_themes": themes}
                for macro, themes in macros
            ],
        }],
    }


_TWO_MACROS = [
    ("Comparative Political Analysis", ["Approaches to comparative study",
                                        "Political economy of development"]),
    ("International Relations", ["Theories of IR", "India and the world"]),
]


def _write(tmp_path: pathlib.Path, payload: dict) -> str:
    path = tmp_path / "syllabus.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def _args(mod, source: str, **over):
    import argparse
    base = dict(source=source, exam_id="exam-1", exam_phase_id="phase-1",
                api_base="http://cms.test", source_url=None, sleep=0.0, dry_run=False)
    base.update(over)
    return argparse.Namespace(**base)


def _run(mod, monkeypatch, cms, source: str, **over) -> object:
    monkeypatch.setenv("CCP_ADMIN_JWT", "token")
    args = _args(mod, source, **over)
    # run() builds its own Stats; capture it by wrapping the dataclass.
    captured = {}
    real_stats = mod.Stats

    def _spy(*a, **kw):
        obj = real_stats(*a, **kw)
        captured["stats"] = obj
        return obj

    monkeypatch.setattr(mod, "Stats", _spy)
    rc = mod.run(args)
    assert rc == 0
    return captured["stats"]


# ── Tests ──────────────────────────────────────────────────────────────────


class TestTopicKey:
    def test_null_parent_is_a_real_value_not_sql_distinct(self, mod):
        """D2: the index side sees JSON null / an absent field, the lookup side
        sees Python None. All three must produce the same key."""
        from_none = mod.topic_key("s", None, "slug-abc")
        from_json_null = mod.topic_key("s", None, "slug-abc")
        from_absent = mod.topic_key("s", {}.get("parent_topic_id"), "slug-abc")
        assert from_none == from_json_null == from_absent
        assert from_none != mod.topic_key("s", "parent-1", "slug-abc")


class TestIdempotency:
    def test_second_run_reuses_every_topic_and_writes_nothing(
        self, mod, monkeypatch, cms, tmp_path
    ):
        """D3: an unchanged file, run twice, must report all reuse and write
        nothing on the second pass."""
        src = _write(tmp_path, _source(_TWO_MACROS))

        first = _run(mod, monkeypatch, cms, src)
        assert (first.macro_created, first.micro_created) == (2, 4)
        assert (first.macro_reused, first.micro_reused) == (0, 0)
        after_first = len(cms.post_calls)
        assert len(cms.tables["topics"]) == 6

        second = _run(mod, monkeypatch, cms, src)
        assert (second.macro_created, second.micro_created) == (0, 0)
        assert (second.macro_reused, second.micro_reused) == (2, 4)
        assert second.subjects_reused == 1
        assert second.document_reused == 1
        # Nothing at all was written on the second pass.
        assert len(cms.post_calls) == after_first
        assert len(cms.tables["topics"]) == 6

    def test_macro_topic_with_null_parent_is_reused_on_second_pass(
        self, mod, monkeypatch, cms, tmp_path
    ):
        """The failure mode that was observed live. The fake backend refuses to
        dedupe a NULL-parent upsert, exactly as Postgres does, so a macro topic
        is reused only if the local index resolves it."""
        src = _write(tmp_path, _source([("Comparative Political Analysis", [])]))
        _run(mod, monkeypatch, cms, src)
        macros = [t for t in cms.tables["topics"] if t["parent_topic_id"] is None]
        assert len(macros) == 1

        second = _run(mod, monkeypatch, cms, src)
        assert second.macro_created == 0
        assert second.macro_reused == 1
        assert len([t for t in cms.tables["topics"] if t["parent_topic_id"] is None]) == 1

    def test_macro_reused_when_api_omits_the_null_parent_field(
        self, mod, monkeypatch, cms, tmp_path
    ):
        """A JSON API may render "no parent" as an absent key rather than null.
        The index key must normalise both to the same thing."""
        src = _write(tmp_path, _source([("Comparative Political Analysis", [])]))
        _run(mod, monkeypatch, cms, src)
        cms.omit_null_parent = True

        second = _run(mod, monkeypatch, cms, src)
        assert second.macro_created == 0
        assert second.macro_reused == 1

    def test_micro_theme_under_a_resolved_parent_is_reused(
        self, mod, monkeypatch, cms, tmp_path
    ):
        src = _write(tmp_path, _source([("International Relations",
                                        ["Theories of IR", "India and the world"])]))
        _run(mod, monkeypatch, cms, src)
        second = _run(mod, monkeypatch, cms, src)
        assert second.micro_created == 0
        assert second.micro_reused == 2
        micros = [t for t in cms.tables["topics"] if t["parent_topic_id"] is not None]
        assert len(micros) == 2

    def test_index_is_consulted_for_micro_themes_not_only_macro_topics(
        self, mod, monkeypatch, cms, tmp_path
    ):
        """G3: the macro and micro resolve_topic call sites are separate. If
        only the macro one were passed the index, the micro-themes would be
        re-POSTed on every run — invisible here unless we count the writes."""
        src = _write(tmp_path, _source(_TWO_MACROS))
        _run(mod, monkeypatch, cms, src)
        writes_after_first = cms.topic_writes()
        assert writes_after_first == 6

        _run(mod, monkeypatch, cms, src)
        # Not one further POST /topics — macro or micro.
        assert cms.topic_writes() == writes_after_first

    def test_a_genuinely_new_topic_in_an_unchanged_file_is_still_created(
        self, mod, monkeypatch, cms, tmp_path
    ):
        src = _write(tmp_path, _source(_TWO_MACROS))
        _run(mod, monkeypatch, cms, src)

        grown = _source(_TWO_MACROS + [("Political Economy", ["Globalisation"])])
        (tmp_path / "grown.json").write_text(json.dumps(grown), encoding="utf-8")
        stats = _run(mod, monkeypatch, cms, str(tmp_path / "grown.json"))

        assert stats.macro_created == 1
        assert stats.micro_created == 1
        assert stats.macro_reused == 2
        assert stats.micro_reused == 4
        assert len(cms.tables["topics"]) == 8


class TestIndexCompleteness:
    def test_short_index_refuses_to_write(self, mod, monkeypatch, cms, tmp_path):
        """A partial index silently re-creates everything it could not see.
        Refuse instead."""
        src = _write(tmp_path, _source(_TWO_MACROS))
        _run(mod, monkeypatch, cms, src)
        before = len(cms.post_calls)

        cms.truncate_topics_to = 2  # route still reports total=6
        monkeypatch.setenv("CCP_ADMIN_JWT", "token")
        monkeypatch.setattr(mod, "Stats", mod.Stats)
        with pytest.raises(RuntimeError, match="topic index .* is incomplete"):
            mod.run(_args(mod, src))
        # Nothing written past the document/subject lookups.
        assert cms.topic_writes() == sum(
            1 for t, _ in cms.post_calls[:before] if t == "topics"
        )


class TestDryRunHonesty:
    def test_dry_run_says_it_cannot_report_reuse(self, mod, monkeypatch, cms, tmp_path,
                                                 capsys):
        """G4: find_all short-circuits to [] under --dry-run, so every existence
        check answers "absent" and the counts are not a plan. The output has to
        say so rather than printing figures that read like one."""
        src = _write(tmp_path, _source(_TWO_MACROS))
        _run(mod, monkeypatch, cms, src)          # populate the backend
        assert len(cms.tables["topics"]) == 6

        capsys.readouterr()  # discard the live run's output

        monkeypatch.setenv("CCP_ADMIN_JWT", "token")
        mod.run(_args(mod, src, dry_run=True))
        out = capsys.readouterr().out

        # Everything already exists, yet the dry run still counts creates —
        # so it must not present them in the same shape a live run does.
        assert "would-create=2" in out
        assert "reused=" not in out
        assert "NOT a plan" in out
        assert "undetected=0" in out
        assert "nothing written, and nothing read" in out

    def test_live_render_is_unchanged(self, mod):
        stats = mod.Stats()
        stats.macro_created = 3
        stats.macro_reused = 4
        rendered = stats.render()
        assert "macro     created=3 reused=4" in rendered
        assert "DRY RUN" not in rendered
