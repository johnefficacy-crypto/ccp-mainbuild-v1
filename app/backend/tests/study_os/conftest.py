"""Shared setup for the Study OS service tests.

The descriptive catalogue caches one exam's corpus for a minute so four tab
clicks are not four full reads of twelve thousand rows. Every fixture in this
package uses the same exam id with a different corpus, so without this the
second test in a file would answer from the first one's data — which is also
the real hazard the cache carries, stated where it can be seen.
"""
from __future__ import annotations

import pytest

from app.study_os import descriptive as _descriptive


@pytest.fixture(autouse=True)
def _reset_descriptive_caches():
    _descriptive.reset_caches()
    yield
    _descriptive.reset_caches()
