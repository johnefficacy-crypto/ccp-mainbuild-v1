from __future__ import annotations

from datetime import datetime

import pandas as pd

from .schema import load_schema


def _is_bool(v: str) -> bool:
    return str(v).lower() in {"true", "false"}


def validate_frame(df: pd.DataFrame) -> list[str]:
    schema = load_schema()
    errors: list[str] = []
    cols = schema["columns"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        errors.append(f"missing required columns: {missing}")
        return errors

    dupes = df[df["external_id"].duplicated(keep=False)]["external_id"].tolist()
    if dupes:
        errors.append(f"duplicate external_id values: {sorted(set(dupes))}")

    for i, row in df.iterrows():
        line = i + 2
        qtype = str(row.get("question_type", "")).strip()
        if qtype not in schema["enums"]["question_type"]:
            errors.append(f"line {line}: question_type invalid ({qtype})")
        diff = str(row.get("difficulty", "")).strip()
        if diff not in schema["enums"]["difficulty"]:
            errors.append(f"line {line}: difficulty invalid ({diff})")
        src = str(row.get("source_kind", "")).strip()
        if src not in schema["enums"]["source_kind"]:
            errors.append(f"line {line}: source_kind invalid ({src})")

        bools = [row.get("is_conceptual"), row.get("is_factual"), row.get("is_current")]
        if not all(_is_bool(v) for v in bools):
            errors.append(f"line {line}: boolean fields must be true/false")
        if not any(str(v).lower() == "true" for v in bools):
            errors.append(f"line {line}: one of is_conceptual/is_factual/is_current must be true")

        if str(row.get("is_current", "")).lower() == "true":
            for f in ["valid_from", "valid_until"]:
                v = str(row.get(f, "")).strip()
                if not v:
                    errors.append(f"line {line}: {f} required when is_current=true")
                else:
                    try:
                        datetime.fromisoformat(v.replace("Z", "+00:00"))
                    except ValueError:
                        errors.append(f"line {line}: {f} must be ISO8601")

        q = str(row.get("question_text", ""))
        if not q.strip():
            errors.append(f"line {line}: question_text required")
        if len(q) > 4000:
            errors.append(f"line {line}: question_text exceeds 4000 chars")

        for col in ["option_a", "option_b", "option_c", "option_d", "option_e", "option_f"]:
            if len(str(row.get(col, ""))) > 1000:
                errors.append(f"line {line}: {col} exceeds 1000 chars")
    return errors
