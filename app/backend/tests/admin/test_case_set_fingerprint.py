"""REG-CORPUS-04 — a case-set row's fingerprint includes its own stimulus.

Two case sets can ask the same question ("Which step is the last step?") with
the same options over different data (QRE-GIR-B GRB-518 / GRB-522). Without the
stimulus in the fingerprint the second row collides with the first on
``mock_question_bank_fp_uniq``: at import, and again on any later edit.
"""
from __future__ import annotations

from app.admin import authored_content as authored
from app.admin.mock_questions import compute_fingerprint, create_question, update_question
from tests.persona_questions._stub import SBStub

_OPTS = [{"option_text": "Step III"}, {"option_text": "Step IV", "is_correct": True},
         {"option_text": "Step V"}, {"option_text": "Step VIII"}]


def _actor() -> dict:
    return {"id": "author-1", "role": "admin", "permissions": ["mock_questions:author"]}


def _case(stimulus: str) -> dict:
    return {"question_text": "Which step is the last step of the arrangement?",
            "stimulus_group": "G", "options": [dict(o) for o in _OPTS],
            "stimuli": [{"stimulus_type": "passage", "content_text": stimulus}]}


def test_suffix_is_empty_without_stimuli_so_old_fingerprints_hold():
    assert authored.stimulus_fingerprint_suffix(None) == ""
    assert authored.stimulus_fingerprint_suffix([]) == ""
    opts = [{"id": "a", "option_text": "4"}, {"id": "b", "option_text": "5"}]
    assert compute_fingerprint("2+2?", opts, "a") == compute_fingerprint("2+2?", opts, "a", [])


def test_crud_create_gives_same_question_over_different_stimuli_distinct_fingerprints():
    sb = SBStub()
    create_question(sb, _actor(), _case("Input: 92 zebra 18 79"))
    create_question(sb, _actor(), _case("Input: amber plum 38 94"))
    fps = [r["question_fingerprint"] for r in sb.db["mock_question_bank"]]
    assert len(fps) == 2 and len(set(fps)) == 2


def test_crud_edit_of_one_case_row_does_not_collide_with_its_twin():
    sb = SBStub()
    create_question(sb, _actor(), _case("Input: 92 zebra 18 79"))
    second = create_question(sb, _actor(), _case("Input: amber plum 38 94"))
    # a reviewer's wording fix on the second set's row, stimuli untouched
    update_question(sb, _actor(), second["id"], {"explanation": "Reworded."})
    fps = [r["question_fingerprint"] for r in sb.db["mock_question_bank"]]
    assert len(set(fps)) == 2
