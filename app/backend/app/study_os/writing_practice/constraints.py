"""`unit_constraints` validation model (architecture §4.4a).

Version-tagged; unknown keys are rejected (``extra='forbid'``). All fields
optional except ``schema_version``. ``max_words >= min_words`` enforced.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class UnitConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    hint_words: list[str] | None = None
    target_structures: list[str] | None = None
    min_words: int | None = None
    max_words: int | None = None

    @model_validator(mode="after")
    def _check_word_bounds(self) -> "UnitConstraints":
        if (
            self.min_words is not None
            and self.max_words is not None
            and self.max_words < self.min_words
        ):
            raise ValueError("max_words must be >= min_words")
        if self.min_words is not None and self.min_words < 0:
            raise ValueError("min_words must be >= 0")
        return self


def validate_unit_constraints(payload: dict | None) -> dict:
    """Validate/normalise a unit_constraints payload; returns a plain dict.

    Raises ``pydantic.ValidationError`` on unknown keys or bad bounds.
    """
    model = UnitConstraints.model_validate(payload or {"schema_version": 1})
    return model.model_dump(exclude_none=True)
