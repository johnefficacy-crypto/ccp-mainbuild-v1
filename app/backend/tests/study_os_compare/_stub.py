"""Re-export the shared in-memory Supabase stub for the compare tests.

Historically this module monkeypatched the shared ``_Query`` class to add
``.lt()`` and a partial ``.or_()`` filter. The shared stub
(``tests.persona_questions._stub``) now implements ``.lt()`` natively and a
faithful ``.or_()`` (PostgREST NULL semantics, including ``neq``), so the
monkeypatch was both redundant and actively harmful — it clobbered the shared
``or_``/``_matches`` whenever this module imported first, dropping rows that the
real implementation keeps. The compare tests only need ``SBStub``; they now use
the shared implementation unchanged.
"""
from tests.persona_questions._stub import SBStub, _Exec, _Query  # noqa: F401
