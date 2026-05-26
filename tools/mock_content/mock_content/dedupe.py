from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz

from .fingerprint import compute_fingerprint


def dedupe_against(df: pd.DataFrame, snapshot: pd.DataFrame, threshold: float = 0.6) -> pd.DataFrame:
    required = {"id", "question_fingerprint", "question_text", "exam_family"}
    missing = required - set(snapshot.columns)
    if missing:
        raise ValueError(f"snapshot missing columns: {sorted(missing)}")

    out = []
    for i, row in df.iterrows():
        fp = compute_fingerprint(row.to_dict())
        hard = snapshot[snapshot["question_fingerprint"] == fp]
        if not hard.empty:
            m = hard.iloc[0]
            out.append({"line": i + 2, "external_id": row.get("external_id"), "match_type": "hard", "match_id": m["id"], "score": 1.0})
            continue
        best_score = 0.0
        best_id = None
        stem = str(row.get("question_text", ""))
        for _, snap in snapshot.iterrows():
            s = fuzz.ratio(stem, str(snap["question_text"])) / 100.0
            if s > best_score:
                best_score = s
                best_id = snap["id"]
        if best_score >= threshold:
            out.append({"line": i + 2, "external_id": row.get("external_id"), "match_type": "near", "match_id": best_id, "score": round(best_score, 3)})
    return pd.DataFrame(out)
