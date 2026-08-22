"""Plans, versions and the escalation ladder.

A **PlanVersion is immutable once activated**. Moments reference a version, and Alerts pin
to one for their entire life, so editing a plan mid-Alert cannot change what that Alert is
doing. See docs/ARCHITECTURE.md section 4.

The enums here mirror packages/domain-schemas/compiled-plan.schema.json exactly.
``test_schema_parity.py`` asserts they have not drifted apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .clock import require_aware
from .errors import PlanValidationError
from .ids import PlanId, PlanVersionId, StepId

MAX_STEPS = 12
DEFAULT_LEASE_SECONDS = 600


class PlanType(StrEnum):
    ROUTINE = "ROUTINE"
    JOURNEY = "JOURNEY"
    SOLO = "SOLO"
    RECOVERY = "RECOVERY"


class TriggerKind(StrEnum):
    RECURRING = "RECURRING"
    ONE_TIME = "ONE_TIME"
    RELATIVE = "RELATIVE"


class Channel(StrEnum):
    """Physical delivery channel.

    CALL is P0-declared but not P0-wired: Amazon Connect provisioning has multi-day lead
    time, so a CALL action dispatches and reports CHANNEL_UNAVAILABLE rather than being
    removed from the model. Adding Connect in P1 requires no domain change.
    """

    PUSH = "PUSH"
    SMS = "SMS"
    CALL = "CALL"

    @property
    def is_available_in_p0(self) -> bool:
        return self is not Channel.CALL


class ActionType(StrEnum):
    PUSH_SUBJECT = "PUSH_SUBJECT"
    SMS_SUBJECT = "SMS_SUBJECT"
    CALL_SUBJECT = "CALL_SUBJECT"
    MESSAGE_RESPONDER = "MESSAGE_RESPONDER"
    CALL_RESPONDER = "CALL_RESPONDER"

    @property
    def is_subject_directed(self) -> bool:
        return self in _SUBJECT_ACTIONS

    @property
    def is_responder_directed(self) -> bool:
        return self in _RESPONDER_ACTIONS

    @property
    def channel(self) -> Channel:
        return _ACTION_CHANNEL[self]


_SUBJECT_ACTIONS = frozenset(
    {ActionType.PUSH_SUBJECT, ActionType.SMS_SUBJECT, ActionType.CALL_SUBJECT}
)
_RESPONDER_ACTIONS = frozenset({ActionType.MESSAGE_RESPONDER, ActionType.CALL_RESPONDER})

_ACTION_CHANNEL: dict[ActionType, Channel] = {
    ActionType.PUSH_SUBJECT: Channel.PUSH,
    ActionType.SMS_SUBJECT: Channel.SMS,
    ActionType.CALL_SUBJECT: Channel.CALL,
    ActionType.MESSAGE_RESPONDER: Channel.SMS,
    ActionType.CALL_RESPONDER: Channel.CALL,
}


class ResponderRole(StrEnum):
    """The agent selects a ROLE. It never names a person and never names an endpoint.

    This is the structural prompt-injection defence: the vocabulary for "contact this
    arbitrary person" does not exist. See docs/AI-SAFETY.md section 3.
    """

    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"
    TERTIARY = "TERTIARY"


class StopCondition(StrEnum):
    """The only ways an Alert closes successfully.

    Deliberately absent, and must never be added: notification delivered, responder
    acknowledged, phone moved, model believes the subject is safe.
    """

    SUBJECT_EXPLICIT_CONFIRMATION = "SUBJECT_EXPLICIT_CONFIRMATION"
    RESPONDER_VERIFIED_CONTACT = "RESPONDER_VERIFIED_CONTACT"
    VERIFIED_CALL_RESPONSE = "VERIFIED_CALL_RESPONSE"
    USER_CANCELLED_BEFORE_ESCALATION = "USER_CANCELLED_BEFORE_ESCALATION"
    PLAN_COMPLETION_SIGNAL = "PLAN_COMPLETION_SIGNAL"


class ReleaseLevel(StrEnum):
    """The escalation stage at which a context signal becomes releasable.

    Read as "release this only once escalation has reached at least here". As a *policy*
    setting NEVER is the most private and ON_ALERT_OPEN the most permissive, but the
    comparison below ranks by *escalation stage*, which runs the other way: an Alert opens
    first, the subject's call fails second, the Circle is reached third. Conflating the two
    orderings inverts ON_ALERT_OPEN and leaks a signal the subject expected to be held back.
    """

    NEVER = "NEVER"
    AFTER_SUBJECT_CALL_FAILED = "AFTER_SUBJECT_CALL_FAILED"
    CIRCLE_ESCALATION = "CIRCLE_ESCALATION"
    ON_ALERT_OPEN = "ON_ALERT_OPEN"

    @property
    def rank(self) -> int:
        return _RELEASE_RANK[self]


# Ranked by escalation stage, earliest first. NEVER sits outside the ordering: it is
# not a stage, and no reached stage can satisfy it.
_RELEASE_RANK: dict[ReleaseLevel, int] = {
    ReleaseLevel.NEVER: 0,
    ReleaseLevel.ON_ALERT_OPEN: 1,
    ReleaseLevel.AFTER_SUBJECT_CALL_FAILED: 2,
    ReleaseLevel.CIRCLE_ESCALATION: 3,
}


class ContextSignal(StrEnum):
    LOCATION = "location"
    BATTERY = "battery"
    LAST_CONNECTION = "lastConnection"
    NETWORK_STATUS = "networkStatus"


@dataclass(frozen=True, slots=True)
class ContextPolicy:
    """Progressive context release. Everything is private until opted into, in advance."""

    levels: dict[ContextSignal, ReleaseLevel] = field(default_factory=dict)

    def level_for(self, signal: ContextSignal) -> ReleaseLevel:
        """Unlisted signals are NEVER. The default is always the private one."""
        return self.levels.get(signal, ReleaseLevel.NEVER)

    def permits(self, signal: ContextSignal, reached: ReleaseLevel) -> bool:
        """Whether ``signal`` may be released now that escalation has reached ``reached``."""
        allowed = self.level_for(signal)
        if allowed is ReleaseLevel.NEVER or reached is ReleaseLevel.NEVER:
            return False
        return reached.rank >= allowed.rank


@dataclass(frozen=True, slots=True)
class Trigger:
    """When a Moment is expected."""

    kind: TriggerKind
    due_at: datetime | None = None
    time_of_day: str | None = None
    days_of_week: tuple[str, ...] = ()
    interval_seconds: int | None = None
    offset_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.kind is TriggerKind.ONE_TIME:
            if self.due_at is None:
                raise PlanValidationError("ONE_TIME trigger requires due_at")
            require_aware(self.due_at, "trigger.due_at")
        elif self.kind is TriggerKind.RECURRING:
            if not self.time_of_day:
                raise PlanValidationError("RECURRING trigger requires time_of_day")
        elif self.kind is TriggerKind.RELATIVE and self.offset_seconds is None:
            raise PlanValidationError("RELATIVE trigger requires offset_seconds")


@dataclass(frozen=True, slots=True)
class EscalationStep:
    """One rung of the ladder.

    ``offset_seconds`` is measured from the end of the grace window, not from the due time:
    grace is the acceptable-uncertainty period, and escalation starts after it.
    """

    step_id: StepId
    sequence: int
    offset_seconds: int
    action: ActionType
    target_role: ResponderRole | None = None

    def __post_init__(self) -> None:
        if self.action.is_responder_directed and self.target_role is None:
            raise PlanValidationError(
                f"step {self.sequence}: {self.action} must name a target role"
            )
        if self.action.is_subject_directed and self.target_role is not None:
            raise PlanValidationError(
                f"step {self.sequence}: {self.action} is subject-directed and must not "
                f"address a responder"
            )


@dataclass(frozen=True, slots=True)
class PlanVersion:
    """An immutable snapshot of a plan's protection.

    Never mutate one. Editing a plan produces a new version; live Alerts keep the old.
    """

    version_id: PlanVersionId
    plan_id: PlanId
    version_number: int
    plan_type: PlanType
    timezone: str
    trigger: Trigger
    grace_seconds: int
    steps: tuple[EscalationStep, ...]
    stop_conditions: frozenset[StopCondition]
    context_policy: ContextPolicy
    lease_seconds: int = DEFAULT_LEASE_SECONDS
    label: str | None = None
    activated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.steps:
            raise PlanValidationError("a plan with no escalation steps never contacts anyone")
        if len(self.steps) > MAX_STEPS:
            raise PlanValidationError(
                f"at most {MAX_STEPS} escalation steps, got {len(self.steps)}"
            )
        if not self.stop_conditions:
            raise PlanValidationError("a plan with no stop condition would escalate forever")

        sequences = [s.sequence for s in self.steps]
        if sequences != list(range(1, len(sequences) + 1)):
            raise PlanValidationError(f"step sequences must be 1..n, got {sequences}")

        offsets = [s.offset_seconds for s in self.steps]
        if offsets != sorted(offsets):
            raise PlanValidationError(
                f"escalation offsets must be non-decreasing, got {offsets}: a ladder that "
                f"goes backwards would contact a backup before the primary"
            )

    @property
    def subject_steps(self) -> tuple[EscalationStep, ...]:
        return tuple(s for s in self.steps if s.action.is_subject_directed)

    @property
    def responder_steps(self) -> tuple[EscalationStep, ...]:
        return tuple(s for s in self.steps if s.action.is_responder_directed)

    @property
    def responder_roles(self) -> frozenset[ResponderRole]:
        """Roles this version may contact. Anything else is unauthorized."""
        return frozenset(s.target_role for s in self.responder_steps if s.target_role)

    def step(self, sequence: int) -> EscalationStep:
        for candidate in self.steps:
            if candidate.sequence == sequence:
                return candidate
        raise PlanValidationError(f"no step with sequence {sequence}")


@dataclass(frozen=True, slots=True)
class Plan:
    """The mutable container. Its protection lives in versions, not here."""

    plan_id: PlanId
    subject_person_id: str
    circle_id: str
    plan_type: PlanType
    active_version_id: PlanVersionId | None = None
    paused: bool = False

    @property
    def is_active(self) -> bool:
        return self.active_version_id is not None and not self.paused
