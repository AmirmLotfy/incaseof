"""Contract tests: the CompiledPlan schema is the boundary between language and action.

Everything the agent produces passes through this schema before anything real happens.
If these tests are weak, the safety guarantees downstream are decorative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .conftest import invalid_fixtures, load_fixture, valid_fixtures

SUBJECT_ACTIONS = {"PUSH_SUBJECT", "SMS_SUBJECT", "CALL_SUBJECT"}
RESPONDER_ACTIONS = {"MESSAGE_RESPONDER", "CALL_RESPONDER"}


def test_schemas_are_themselves_valid(
    compiled_plan_schema: dict[str, Any], alert_state_schema: dict[str, Any]
) -> None:
    Draft202012Validator.check_schema(compiled_plan_schema)
    Draft202012Validator.check_schema(alert_state_schema)


@pytest.mark.parametrize("fixture", valid_fixtures(), ids=lambda p: p.stem)
def test_valid_fixtures_validate(fixture: Path, compiled_plan_schema: dict[str, Any]) -> None:
    Draft202012Validator(compiled_plan_schema).validate(load_fixture(fixture))


@pytest.mark.parametrize("fixture", invalid_fixtures(), ids=lambda p: p.stem)
def test_invalid_fixtures_are_rejected(fixture: Path, compiled_plan_schema: dict[str, Any]) -> None:
    """Each negative fixture must fail, and must fail for its own reason.

    ``_why`` is stripped by ``load_fixture`` precisely so that a fixture cannot pass this
    test by tripping ``additionalProperties`` on its own documentation.
    """
    with pytest.raises(ValidationError):
        Draft202012Validator(compiled_plan_schema).validate(load_fixture(fixture))


def test_schema_has_no_vocabulary_for_a_raw_endpoint(
    compiled_plan_schema: dict[str, Any],
) -> None:
    """The structural prompt-injection defence, asserted rather than assumed.

    A compromised model must be unable to express "contact this arbitrary person". That
    holds only while no property anywhere in the schema accepts an endpoint, and while
    every object refuses unknown properties.
    """
    forbidden = {"phone", "phonenumber", "number", "msisdn", "email", "endpoint", "url", "to"}
    offenders: list[str] = []
    closed_objects = 0
    open_objects: list[str] = []

    def walk(node: Any, path: str) -> None:
        nonlocal closed_objects
        if not isinstance(node, dict):
            return
        # Only real object *definitions* must be closed. An ``if`` clause inside
        # ``allOf`` is an applicator subschema -- it carries ``properties`` to express a
        # condition, and closing it would change what the condition matches.
        # A genuine object definition always declares its type.
        if node.get("type") == "object":
            if node.get("additionalProperties") is False:
                closed_objects += 1
            else:
                open_objects.append(path)
        for key, value in node.get("properties", {}).items():
            if key.lower() in forbidden:
                offenders.append(f"{path}.{key}")
            walk(value, f"{path}.{key}")
        for section in ("$defs", "items", "then", "if", "not"):
            child = node.get(section)
            if isinstance(child, dict):
                if section == "$defs":
                    for name, sub in child.items():
                        walk(sub, f"{path}.$defs.{name}")
                else:
                    walk(child, f"{path}.{section}")
        for clause in node.get("allOf", []):
            walk(clause, f"{path}.allOf")

    walk(compiled_plan_schema, "$")

    assert not offenders, f"schema exposes a contactable endpoint: {offenders}"
    assert not open_objects, f"objects accepting unknown properties: {open_objects}"
    assert closed_objects >= 3, "expected the plan, its steps and its policy to all be closed"


def test_delivery_is_not_a_stop_condition(compiled_plan_schema: dict[str, Any]) -> None:
    """Acknowledged is not resolved, and delivered is not acknowledged."""
    allowed = set(compiled_plan_schema["properties"]["stopConditions"]["items"]["enum"])
    for forbidden in (
        "NOTIFICATION_DELIVERED",
        "RESPONDER_ACKNOWLEDGED",
        "PHONE_MOVED",
        "MODEL_BELIEVES_SAFE",
    ):
        assert forbidden not in allowed, f"{forbidden} must never close an Alert"


def test_end_bound_is_only_valid_for_recurring_plans(
    compiled_plan_schema: dict[str, Any],
) -> None:
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["trigger"] = {
        "kind": "ONE_TIME",
        "dueAt": "2026-08-26T21:00:00+02:00",
        "untilAt": "2026-08-27T05:00:00+02:00",
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(compiled_plan_schema).validate(document)


def test_context_release_defaults_to_never(compiled_plan_schema: dict[str, Any]) -> None:
    """Every context signal is private until the user opts in, in advance."""
    policy = compiled_plan_schema["properties"]["contextPolicy"]["properties"]
    assert policy, "contextPolicy must enumerate its signals explicitly"
    for signal, spec in policy.items():
        assert spec.get("default") == "NEVER", f"{signal} must default to NEVER"


def test_every_action_is_classified(compiled_plan_schema: dict[str, Any]) -> None:
    """No action may exist that is neither subject-directed nor responder-directed.

    An unclassified action would slip past the targetRole rules entirely.
    """
    step = compiled_plan_schema["$defs"]["escalationStep"]
    actions = set(step["properties"]["action"]["enum"])
    assert actions == SUBJECT_ACTIONS | RESPONDER_ACTIONS
    assert not (SUBJECT_ACTIONS & RESPONDER_ACTIONS)


def test_alert_states_match_the_normative_document(alert_state_schema: dict[str, Any]) -> None:
    """docs/PRODUCT-STATES.md is the source of truth; the enum must not drift from it."""
    assert set(alert_state_schema["enum"]) == {
        "SCHEDULED",
        "DUE",
        "GRACE",
        "SELF_CONTACT",
        "CIRCLE_ESCALATION",
        "CHECKING",
        "RESOLVED",
        "ESCALATION_EXHAUSTED",
        "CANCELLED",
    }


@pytest.mark.parametrize("fixture", valid_fixtures(), ids=lambda p: p.stem)
def test_escalation_ladders_are_ordered(fixture: Path) -> None:
    """Semantic rule the schema cannot express: offsets must not go backwards.

    A ladder that jumps backwards would contact a backup before the primary.
    """
    steps = load_fixture(fixture)["steps"]
    sequences = [s["sequence"] for s in steps]
    offsets = [s["offsetSeconds"] for s in steps]
    assert sequences == sorted(sequences), "sequence numbers out of order"
    assert sequences == list(range(1, len(sequences) + 1)), "sequence numbers must be 1..n"
    assert offsets == sorted(offsets), "escalation offsets must be non-decreasing"


@pytest.mark.parametrize("fixture", valid_fixtures(), ids=lambda p: p.stem)
def test_every_plan_can_actually_close(fixture: Path) -> None:
    """A plan whose stop conditions can never be met would escalate forever."""
    plan = load_fixture(fixture)
    assert plan["stopConditions"], "a plan with no stop condition never terminates"
    assert "SUBJECT_EXPLICIT_CONFIRMATION" in plan["stopConditions"], (
        "the subject must always be able to close their own Alert"
    )
