import pandas as pd

from mock_content.dedupe import dedupe_against
from mock_content.fingerprint import compute_fingerprint


def test_dedupe_hard_and_near():
    df = pd.read_csv("samples/starter.csv", dtype=str).fillna("")
    fp = compute_fingerprint(df.iloc[0].to_dict())
    snap = pd.DataFrame([
        {"id": "1", "question_fingerprint": fp, "question_text": "x", "exam_family": "upsc"},
        {"id": "2", "question_fingerprint": "other", "question_text": "Who abolished sati in India?", "exam_family": "upsc"},
    ])
    report = dedupe_against(df.iloc[:2], snap, threshold=0.6)
    assert "hard" in set(report["match_type"])
    assert "near" in set(report["match_type"])
