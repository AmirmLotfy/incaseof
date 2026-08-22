"""Compiler tests.

These close the loop between Phase 0's contracts and the domain: the golden fixtures are
not just schema-valid documents, they must become real PlanVersions that the state machine
can actually run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.domain.compiler import (
    CompilationResult,
    compile_plan,
    validate_safety,
    validate_semantics,
)
from services.domain.errors import PlanValidationError
from services.domain.ids import PlanId, SequentialIds
from services.domain.plan import ActionType, ContextSignal, ReleaseLevel, StopCondition
from services.tests.conftest import invalid_fixtures, load_fixture, valid_fixtures

PLAN = PlanId("plan-1")


def compile_fixture(path: Path) -> CompilationResult:
    return compile_plan(
        load_fixture(path), plan_id=PLAN, version_number=1, new_id=SequentialIds("x")
    )


# -- the golden fixtures ------------------------------------------------------


@pytest.mark.parametrize("fixture", valid_fixtures(), ids=lambda p: p.stem)
def test_every_valid_fixture_compiles_to_a_runnable_version(fixture: Path) -> None:
    result = compile_fixture(fixture)
    version = result.version

    assert version.steps, "a compiled plan must have a ladder"
    assert version.subject_steps, "escalation must begin with the subject"
    assert StopCondition.SUBJECT_EXPLICIT_CONFIRMATION in version.stop_conditions


@pytest.mark.parametrize("fixture", invalid_fixtures(), ids=lambda p: p.stem)
def test_every_invalid_fixture_is_rejected(fixture: Path) -> None:
    with pytest.raises(PlanValidationError):
        compile_fixture(fixture)


def test_the_canonical_hike_compiles_exactly_as_written() -> None:
    """The worked example from the build contract, end to end."""
    result = compile_fixture(Path("packages/test-fixtures/valid/solo-hike.json"))
    version = result.version

    assert version.timezone == "Africa/Cairo"
    assert version.grace_seconds == 1800
    assert [s.action for s in version.steps] == [
        ActionType.PUSH_SUBJECT,
        ActionType.CALL_SUBJECT,
        ActionType.MESSAGE_RESPONDER,
        ActionType.CALL_RESPONDER,
    ]
    assert [s.offset_seconds for s in version.steps] == [0, 600, 900, 1500]
    assert version.context_policy.level_for(ContextSignal.LOCATION) is ReleaseLevel.NEVER, (
        "the hike shares no location"
    )
    assert (
        version.context_policy.level_for(ContextSignal.BATTERY)
        is ReleaseLevel.AFTER_SUBJECT_CALL_FAILED
    )


def test_voice_steps_compile_but_warn_that_the_channel_is_not_connected() -> None:
    """CALL rungs stay first-class in the model even though Connect is P1."""
    result = compile_fixture(Path("packages/test-fixtures/valid/solo-hike.json"))
    assert any("voice" in w for w in result.warnings), result.warnings


def test_a_p0_ladder_compiles_without_channel_warnings() -> None:
    result = compile_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    assert not any("voice" in w for w in result.warnings), result.warnings


# -- the safety layer ---------------------------------------------------------


def test_a_plan_the_subject_cannot_close_is_refused() -> None:
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["stopConditions"] = ["RESPONDER_VERIFIED_CONTACT"]

    with pytest.raises(PlanValidationError, match="close their own Alert"):
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))


def test_a_plan_that_skips_the_subject_entirely_is_refused() -> None:
    """Contacting the Circle without first asking the person defeats the product."""
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["steps"] = [
        {
            "sequence": 1,
            "offsetSeconds": 0,
            "action": "MESSAGE_RESPONDER",
            "targetRole": "PRIMARY",
        }
    ]

    with pytest.raises(PlanValidationError, match="escalation must start with the subject"):
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))


def test_a_ladder_that_reaches_the_circle_before_the_subject_is_refused() -> None:
    """Subject rungs exist, but a responder is contacted first. Still refused."""
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["steps"] = [
        {
            "sequence": 1,
            "offsetSeconds": 0,
            "action": "MESSAGE_RESPONDER",
            "targetRole": "PRIMARY",
        },
        {"sequence": 2, "offsetSeconds": 600, "action": "PUSH_SUBJECT"},
    ]

    with pytest.raises(PlanValidationError, match="first contact must go to the subject"):
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))


def test_an_unknown_timezone_is_caught_at_compile_time_not_at_nine_pm() -> None:
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["timezone"] = "Africa/Nowhere"

    with pytest.raises(PlanValidationError):
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))


def test_compiling_reports_every_schema_problem_at_once() -> None:
    """One-problem-per-round-trip is how a validation step gets disabled."""
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    del document["timezone"]
    document["stopConditions"] = []

    with pytest.raises(PlanValidationError) as caught:
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))

    message = str(caught.value)
    assert "timezone" in message
    assert "stopConditions" in message or "stopconditions" in message.lower()


# -- compiling is not activating ----------------------------------------------


def test_compiling_never_activates() -> None:
    """Activation is a separate, explicit human step. See docs/AI-SAFETY.md section 5."""
    result = compile_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    assert result.version.activated_at is None


# -- warnings are advisory, not blocking --------------------------------------


def test_a_plan_with_no_responders_compiles_but_says_so() -> None:
    document = load_fixture(Path("packages/test-fixtures/valid/evening-routine.json"))
    document["steps"] = [
        {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
        {"sequence": 2, "offsetSeconds": 600, "action": "SMS_SUBJECT"},
    ]

    result = compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))
    assert any("never contacts anyone else" in w for w in result.warnings)


def test_semantic_and_safety_layers_are_independently_callable() -> None:
    """Composable layers, so the API can preview without duplicating rules."""
    version = compile_fixture(Path("packages/test-fixtures/valid/evening-routine.json")).version
    assert isinstance(validate_semantics(version), tuple)
    validate_safety(version)
