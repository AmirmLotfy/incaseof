"""Model output goes through the same gate as anything else.

If anything, a stricter one: this is the input most likely to be subtly wrong or
deliberately steered, and the only input a stranger can influence by writing text.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.agent.agent import compile_plan_from_utterance
from services.agent.compilation import (
    MAX_UTTERANCE,
    CompiledPlanDraft,
    compile_from_draft,
    guard_utterance,
)
from services.domain.errors import PlanValidationError
from services.domain.ids import PlanId, SequentialIds
from services.domain.plan import ActionType, ResponderRole

from .conftest import StubAgent

PLAN = PlanId("plan-1")


def a_draft(**overrides: object) -> CompiledPlanDraft:
    base: dict[str, object] = {
        "type": "ROUTINE",
        "label": "Evening check",
        "timezone": "Europe/Amsterdam",
        "trigger": {"kind": "RECURRING", "timeOfDay": "21:00"},
        "grace": {"seconds": 600},
        "steps": [
            {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
            {"sequence": 2, "offsetSeconds": 600, "action": "SMS_SUBJECT"},
            {
                "sequence": 3,
                "offsetSeconds": 1200,
                "action": "MESSAGE_RESPONDER",
                "targetRole": "PRIMARY",
            },
        ],
        "stopConditions": ["SUBJECT_EXPLICIT_CONFIRMATION", "RESPONDER_VERIFIED_CONTACT"],
        "contextPolicy": {"location": "NEVER"},
    }
    base.update(overrides)
    return CompiledPlanDraft.model_validate(base)


def compile_it(draft: CompiledPlanDraft):  # type: ignore[no-untyped-def]
    return compile_from_draft(draft, plan_id=PLAN, new_id=SequentialIds("x"))


# -- the happy path -----------------------------------------------------------


def test_a_good_draft_becomes_a_runnable_version() -> None:
    result = compile_it(a_draft())
    version = result.version

    assert version.label == "Evening check"
    assert [s.action for s in version.steps] == [
        ActionType.PUSH_SUBJECT,
        ActionType.SMS_SUBJECT,
        ActionType.MESSAGE_RESPONDER,
    ]
    assert version.responder_roles == frozenset({ResponderRole.PRIMARY})


def test_compiling_never_activates() -> None:
    """Activation is a separate, explicit human step."""
    assert compile_it(a_draft()).version.activated_at is None


# -- the safety layer applies to model output ---------------------------------


def test_a_plan_that_contacts_the_circle_first_is_refused() -> None:
    """Even when the model produced it, and even if it were asked to."""
    draft = a_draft(
        steps=[
            {
                "sequence": 1,
                "offsetSeconds": 0,
                "action": "MESSAGE_RESPONDER",
                "targetRole": "PRIMARY",
            },
            {"sequence": 2, "offsetSeconds": 600, "action": "PUSH_SUBJECT"},
        ]
    )
    with pytest.raises(PlanValidationError, match="first contact must go to the subject"):
        compile_it(draft)


def test_a_plan_the_subject_cannot_close_is_refused() -> None:
    draft = a_draft(stopConditions=["RESPONDER_VERIFIED_CONTACT"])
    with pytest.raises(PlanValidationError, match="close their own Alert"):
        compile_it(draft)


def test_a_ladder_that_goes_backwards_is_refused() -> None:
    draft = a_draft(
        steps=[
            {"sequence": 1, "offsetSeconds": 1200, "action": "PUSH_SUBJECT"},
            {"sequence": 2, "offsetSeconds": 0, "action": "SMS_SUBJECT"},
        ]
    )
    with pytest.raises(PlanValidationError, match="non-decreasing"):
        compile_it(draft)


# -- what the model cannot express at all -------------------------------------


def test_a_person_cannot_be_named_as_a_target() -> None:
    """targetRole is a closed vocabulary. "Maya" is not in it, and neither is a number."""
    for attempt in ("Maya", "+12025550123", "maya@example.com", "PRIMARY_MAYA"):
        with pytest.raises(ValidationError):
            a_draft(
                steps=[
                    {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
                    {
                        "sequence": 2,
                        "offsetSeconds": 600,
                        "action": "MESSAGE_RESPONDER",
                        "targetRole": attempt,
                    },
                ]
            )


def test_an_invented_action_is_refused() -> None:
    with pytest.raises(ValidationError):
        a_draft(steps=[{"sequence": 1, "offsetSeconds": 0, "action": "EMAIL_EVERYONE"}])


def test_an_invented_stop_condition_is_refused() -> None:
    """Notably: delivery is not resolution, and cannot be smuggled in as one."""
    with pytest.raises(ValidationError):
        a_draft(stopConditions=["NOTIFICATION_DELIVERED"])


def test_a_smuggled_field_does_not_survive_the_schema() -> None:
    """Pydantic ignores unknown keys; the JSON Schema refuses them.

    That second gate is the point of validating twice — the contract is stricter than the
    shape we asked the model for.
    """
    draft = a_draft()
    document = draft.model_dump(exclude_none=True)
    document["phoneNumber"] = "+12025550123"

    from services.domain.compiler import compile_plan

    with pytest.raises(PlanValidationError, match="schema"):
        compile_plan(document, plan_id=PLAN, version_number=1, new_id=SequentialIds("x"))


# -- the timezone -------------------------------------------------------------


def test_the_timezone_the_model_returns_is_ignored() -> None:
    """A guessed zone silently moves a safety deadline by hours."""
    agent = StubAgent(result=a_draft(timezone="America/Los_Angeles"))
    preview = compile_plan_from_utterance(
        agent,
        "check on me every evening at nine",
        plan_id=PLAN,
        timezone="Europe/Amsterdam",
        new_id=SequentialIds("x"),
    )

    assert preview.result.version.timezone == "Europe/Amsterdam"


def test_the_preview_reports_that_nothing_is_live() -> None:
    agent = StubAgent(result=a_draft())
    preview = compile_plan_from_utterance(
        agent,
        "evening check at nine",
        plan_id=PLAN,
        timezone="Europe/Amsterdam",
        new_id=SequentialIds("x"),
    )

    assert not preview.is_active
    assert preview.utterance_hash
    assert len(preview.utterance_hash) == 16, "the utterance itself must not be stored"


def test_warnings_reach_the_preview() -> None:
    """A voice rung compiles, and the person is told it will not connect yet."""
    agent = StubAgent(
        result=a_draft(
            steps=[
                {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
                {"sequence": 2, "offsetSeconds": 600, "action": "CALL_SUBJECT"},
            ]
        )
    )
    preview = compile_plan_from_utterance(
        agent,
        "call me if I don't answer",
        plan_id=PLAN,
        timezone="Europe/Amsterdam",
        new_id=SequentialIds("x"),
    )

    assert any("voice" in w for w in preview.warnings)


# -- input bounds -------------------------------------------------------------


def test_an_empty_description_is_refused() -> None:
    with pytest.raises(PlanValidationError):
        guard_utterance("   ")


def test_an_enormous_description_is_refused() -> None:
    with pytest.raises(PlanValidationError):
        guard_utterance("x" * (MAX_UTTERANCE + 1))


def test_a_normal_description_passes_through_unchanged() -> None:
    assert guard_utterance("  check on me at nine  ") == "check on me at nine"
