import pandas as pd

from mock_content.validate import validate_frame


def test_validate_clean_sample():
    df = pd.read_csv("samples/starter.csv", dtype=str).fillna("")
    assert validate_frame(df) == []


def test_validate_broken_rows():
    df = pd.read_csv("samples/starter.csv", dtype=str).fillna("")
    df.loc[0, "question_type"] = "bad"
    df.loc[1, "is_conceptual"] = "maybe"
    df.loc[2, "question_text"] = ""
    errs = validate_frame(df)
    assert any("question_type invalid" in e for e in errs)
    assert any("boolean fields" in e for e in errs)
    assert any("question_text required" in e for e in errs)
