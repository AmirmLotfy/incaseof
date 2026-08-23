"""Turning what somebody said into a plan they can look at.

The showcase capability, and the one with the most ways to go wrong. The pipeline is
layered so that no single failure — a confused model, a malformed response, an injected
instruction — can produce something that protects a person incorrectly:

    utterance -> model (typed output) -> JSON Schema -> semantic -> safety -> preview -> confirm

The model's structured output is validated twice on purpose. Pydantic checks it is the
shape we asked for; the JSON Schema in packages/domain-schemas/ then checks it against the
*contract*, which is the artefact the Android app and the API also derive from. A model
that learned a slightly different shape fails at the second gate rather than propagating.

**Compiling never activates.** It produces something to show a human. Activation is a
separate, explicit step — see docs/AI-SAFETY.md section 5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from services.domain.compiler import CompilationResult, compile_plan
from services.domain.errors import PlanValidationError
from services.domain.ids import IdFactory, PlanId, uuid_factory

MAX_UTTERANCE = 2000


class TriggerDraft(BaseModel):
    """When the person expects this to happen."""

    kind: Literal["RECURRING", "ONE_TIME", "RELATIVE"]
    dueAt: str | None = Field(default=None, description="ISO-8601 with offset, ONE_TIME only")
    timeOfDay: str | None = Field(default=None, description="HH:MM 24-hour, RECURRING only")
    daysOfWeek: list[Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]] = Field(
        default_factory=list
    )
    intervalSeconds: int | None = None
    offsetSeconds: int | None = Field(default=None, description="RELATIVE only")


class StepDraft(BaseModel):
    """One rung of the escalation ladder."""

    sequence: int = Field(ge=1, le=12)
    offsetSeconds: int = Field(ge=0, le=86400)
    action: Literal[
        "PUSH_SUBJECT", "SMS_SUBJECT", "CALL_SUBJECT", "MESSAGE_RESPONDER", "CALL_RESPONDER"
    ]
    # A ROLE. There is no field here for a person, a number or an address, and there never
    # can be: the schema this validates against refuses unknown properties.
    targetRole: Literal["PRIMARY", "BACKUP", "TERTIARY"] | None = None


class GraceDraft(BaseModel):
    seconds: int = Field(ge=0, le=21600)


class CompiledPlanDraft(BaseModel):
    """What the model is asked to produce.

    Mirrors packages/domain-schemas/compiled-plan.schema.json. The schema remains the
    contract; this is how the model is asked for it.
    """

    type: Literal["ROUTINE", "JOURNEY", "SOLO", "RECOVERY"]
    label: str = Field(max_length=60)
    timezone: str = Field(description="IANA zone, e.g. Europe/Amsterdam")
    trigger: TriggerDraft
    grace: GraceDraft
    steps: list[StepDraft] = Field(min_length=1, max_length=12)
    stopConditions: list[
        Literal[
            "SUBJECT_EXPLICIT_CONFIRMATION",
            "RESPONDER_VERIFIED_CONTACT",
            "VERIFIED_CALL_RESPONSE",
            "USER_CANCELLED_BEFORE_ESCALATION",
            "PLAN_COMPLETION_SIGNAL",
        ]
    ]
    contextPolicy: dict[str, str] = Field(default_factory=dict)
    leaseSeconds: int = Field(default=600, ge=120, le=3600)


@dataclass(frozen=True, slots=True)
class Preview:
    """What the person is shown before anything becomes real."""

    result: CompilationResult
    utterance_hash: str
    model_id: str

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.result.warnings

    @property
    def is_active(self) -> bool:
        """Always false. Compiling is not activating, and this says so out loud."""
        return self.result.version.activated_at is not None


COMPILER_INSTRUCTIONS = """\
Turn the person's description into a check-in plan.

Rules that are not negotiable:

- Escalation always starts with the person themselves. The first step must be a
  PUSH_SUBJECT, SMS_SUBJECT or CALL_SUBJECT. Never contact anyone else first.
- Always include SUBJECT_EXPLICIT_CONFIRMATION in stopConditions. The person must always
  be able to close their own check.
- Offsets are measured from the end of the grace window and must not decrease.
- Name responders by ROLE only: PRIMARY, BACKUP, TERTIARY. If they say "Maya", work out
  which role Maya holds from the circle you were given and use that role. Never put a
  name, a phone number or any other contact detail in the plan.
- contextPolicy defaults to NEVER for every signal. Only include a signal if the person
  explicitly asked for it to be shared, and only at the stage they asked for.
- Use the timezone you were given. Never guess one.

If the description is too vague to build a plan from, say so instead of inventing details.
"""


def compile_from_draft(
    draft: CompiledPlanDraft,
    *,
    plan_id: PlanId,
    version_number: int = 1,
    new_id: IdFactory = uuid_factory,
) -> CompilationResult:
    """Run a model draft through the same validation any other input gets.

    Nothing about this path is privileged because a model produced it. If anything, the
    opposite: this is the input most likely to be subtly wrong or deliberately steered.
    """
    document: dict[str, Any] = draft.model_dump(exclude_none=True)

    # Pydantic emits empty containers for absent optionals; the schema rejects an empty
    # daysOfWeek, and an empty contextPolicy means "everything NEVER" rather than a value.
    trigger = document.get("trigger", {})
    if not trigger.get("daysOfWeek"):
        trigger.pop("daysOfWeek", None)
    if not document.get("contextPolicy"):
        document.pop("contextPolicy", None)

    return compile_plan(document, plan_id=plan_id, version_number=version_number, new_id=new_id)


def guard_utterance(utterance: str) -> str:
    """Bound what reaches the model.

    Not a content filter — the tool surface is the defence against instructions hidden in
    text, and no wording can widen it. This only stops an unbounded input from becoming an
    unbounded prompt.
    """
    text = utterance.strip()
    if not text:
        raise PlanValidationError("nothing was said")
    if len(text) > MAX_UTTERANCE:
        raise PlanValidationError(
            f"that is longer than {MAX_UTTERANCE} characters; say it more briefly"
        )
    return text
