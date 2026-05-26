from __future__ import annotations

import pandas as pd


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    group = df.groupby(["exam_family", "subject"], dropna=False)
    rows = []
    for (exam, subject), part in group:
        total = len(part)
        conceptual = (part["is_conceptual"].astype(str).str.lower() == "true").mean()
        factual = (part["is_factual"].astype(str).str.lower() == "true").mean()
        current = (part["is_current"].astype(str).str.lower() == "true").mean()
        rows.append({
            "exam_family": exam,
            "subject": subject,
            "total": total,
            "conceptual_pct": round(conceptual * 100, 1),
            "factual_pct": round(factual * 100, 1),
            "current_pct": round(current * 100, 1),
            "any_bucket_lt_10": any(x < 0.1 for x in [conceptual, factual, current]),
        })
    return pd.DataFrame(rows)
