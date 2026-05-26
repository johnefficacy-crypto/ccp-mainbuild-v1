import pandas as pd

from mock_content.fingerprint import compute_fingerprint


def test_identical_rows_same_fp():
    df = pd.read_csv("samples/starter.csv", dtype=str).fillna("")
    row = df.iloc[0].to_dict()
    row2 = dict(row)
    row2["option_a"], row2["option_b"] = row["option_b"], row["option_a"]
    assert compute_fingerprint(row) == compute_fingerprint(row2)
