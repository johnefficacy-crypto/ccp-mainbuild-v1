from __future__ import annotations

import json
from pathlib import Path


def load_schema() -> dict:
    schema_path = Path(__file__).resolve().parent.parent / "schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))
