"""Drift detection between the Python source-of-truth and the shared frontend contract.

The Pydantic models in ``app/study_os/mastery_engine/schemas.py`` are the single
source of truth for the PR5a output shapes (``MasteryDelta``, ``ErrorPatternSignal``,
``CorrectionTaskDraft`` and friends). The frontend consumes these shapes via a
hand-synced contract at ``app/frontend/src/types/masteryEngine.schema.json``, from
which ``masteryEngine.js`` derives runtime PropTypes.

This test fails CI whenever ``schemas.py`` adds, removes, renames or retypes a field
without the JSON contract being updated to match. See ``docs/contracts.md``.
"""

from __future__ import annotations

import inspect
import json
import types
import typing
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from app.study_os.mastery_engine import schemas as me_schemas

REPO_ROOT = Path(__file__).resolve().parents[6]
CONTRACT_PATH = REPO_ROOT / "app" / "frontend" / "src" / "types" / "masteryEngine.schema.json"

_SCALAR_TOKENS = {
    str: "str",
    int: "int",
    bool: "bool",
    float: "float",
    Decimal: "Decimal",
    UUID: "UUID",
}


def _is_optional(annotation: object) -> bool:
    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is types.UnionType:
        return type(None) in typing.get_args(annotation)
    return False


def _strip_optional(annotation: object) -> object:
    if not _is_optional(annotation):
        return annotation
    non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
    if len(non_none) == 1:
        return non_none[0]
    return typing.Union[tuple(non_none)]  # type: ignore[return-value]


def _type_token(annotation: object) -> str:
    base = _strip_optional(annotation)
    origin = typing.get_origin(base)
    if origin in (list, typing.List):
        (inner,) = typing.get_args(base)
        return f"list[{_type_token(inner)}]"
    if base in _SCALAR_TOKENS:
        return _SCALAR_TOKENS[base]
    if isinstance(base, type) and issubclass(base, BaseModel):
        return base.__name__
    return getattr(base, "__name__", str(base))


def _field_descriptor(annotation: object, required: bool) -> dict:
    return {
        "type": _type_token(annotation),
        "required": bool(required),
        "nullable": _is_optional(annotation),
    }


def _discover_models() -> dict[str, type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for name, obj in inspect.getmembers(me_schemas, inspect.isclass):
        if obj is BaseModel or not issubclass(obj, BaseModel):
            continue
        if obj.__module__ != me_schemas.__name__:
            continue
        models[name] = obj
    return models


def build_contract_from_schemas() -> dict:
    """Derive the canonical contract dict directly from the Pydantic models."""
    models = {}
    for name, model in sorted(_discover_models().items()):
        fields = {}
        for field_name, field in model.model_fields.items():
            fields[field_name] = _field_descriptor(field.annotation, field.is_required())
        models[name] = fields
    return {
        "_meta": {
            "source": "app/backend/app/study_os/mastery_engine/schemas.py",
            "note": (
                "Hand-synced contract. Source of truth is schemas.py. "
                "test_schema_frontend_parity.py fails CI on drift."
            ),
        },
        "models": models,
    }


def _load_contract() -> dict:
    assert CONTRACT_PATH.exists(), (
        f"Shared frontend contract not found at {CONTRACT_PATH}. "
        "It mirrors mastery_engine/schemas.py and must be committed."
    )
    return json.loads(CONTRACT_PATH.read_text())


def test_contract_covers_exactly_the_schema_models():
    expected = build_contract_from_schemas()["models"]
    actual = _load_contract()["models"]
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    assert not missing, (
        f"Models in schemas.py missing from masteryEngine.schema.json: {missing}. "
        "Update the shared frontend contract."
    )
    assert not extra, (
        f"Models in masteryEngine.schema.json not present in schemas.py: {extra}. "
        "Remove them from the shared frontend contract."
    )


def test_contract_fields_match_schema_fields():
    expected = build_contract_from_schemas()["models"]
    actual = _load_contract()["models"]
    mismatches: list[str] = []
    for model_name, expected_fields in expected.items():
        actual_fields = actual.get(model_name, {})
        exp_names = set(expected_fields)
        act_names = set(actual_fields)
        if exp_names != act_names:
            mismatches.append(
                f"{model_name}: field set drift. "
                f"missing_in_contract={sorted(exp_names - act_names)} "
                f"extra_in_contract={sorted(act_names - exp_names)}"
            )
            continue
        for field_name, descriptor in expected_fields.items():
            if actual_fields[field_name] != descriptor:
                mismatches.append(
                    f"{model_name}.{field_name}: expected {descriptor} "
                    f"but contract has {actual_fields[field_name]}"
                )
    assert not mismatches, "Frontend contract drifted from schemas.py:\n" + "\n".join(mismatches)
