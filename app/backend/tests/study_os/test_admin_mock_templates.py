from app.admin.mock_templates import TemplateValidationError, _validate_selector


def test_validate_selector_criteria_mix_sum():
    _validate_selector({"mode": "criteria", "filters": {"difficulty_mix": {"easy": 0.3, "medium": 0.5, "hard": 0.2}}}, 30)


def test_validate_selector_criteria_mix_invalid_sum():
    try:
        _validate_selector({"mode": "criteria", "filters": {"difficulty_mix": {"easy": 0.4, "medium": 0.5, "hard": 0.2}}}, 30)
    except TemplateValidationError:
        return
    assert False


def test_validate_selector_fixed_count_must_match():
    try:
        _validate_selector({"mode": "fixed", "question_ids": ["1", "2"]}, 3)
    except TemplateValidationError:
        return
    assert False
