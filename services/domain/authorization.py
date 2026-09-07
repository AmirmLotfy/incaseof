"""The policy layer.

Every real-world action passes through here. This is deliberately deterministic code, not
a prompt: the model may *propose* contacting someone, but whether that happens is decided
by the rules below.

Two entry points per decision:

* ``evaluate_*`` returns a :class:`PolicyDecision` and never raises. This is what gets
  recorded as an AGENT_DECISION, including denials, so the developer trace and the audit
  timeline can show exactly what was refused and why.
* ``authorize_*`` enforces it and raises :class:`NotAuthorized`.

The distinction matters: a denial that is merely an exception disappears from the record,
and "nothing happened" is indistinguishable from "something was blocked".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .alert import Alert, AlertState
from .circle import Circle, CircleMember, ConsentGrant, ContactChannelPermission
from .errors import NotAuthorized, PlanValidationError
from .ids import PersonId, PlanId
from .plan import Channel, ContextSignal, EscalationStep, ReleaseLevel, ResponderRole


class Reason(StrEnum):
    """Stable machine codes. Safe to log and to show in a trace; they leak no user data."""

    ALLOWED = "ALLOWED"
    ALERT_NOT_OPEN = "ALERT_NOT_OPEN"
    STEP_NOT_IN_PLAN_VERSION = "STEP_NOT_IN_PLAN_VERSION"
    STEP_NOT_RESPONDER_DIRECTED = "STEP_NOT_RESPONDER_DIRECTED"
    ROLE_NOT_IN_PLAN_VERSION = "ROLE_NOT_IN_PLAN_VERSION"
    NO_MEMBER_FOR_ROLE = "NO_MEMBER_FOR_ROLE"
    MEMBER_NOT_ACCEPTED = "MEMBER_NOT_ACCEPTED"
    CONSENT_NOT_ACTIVE = "CONSENT_NOT_ACTIVE"
    CHANNEL_NOT_PERMITTED = "CHANNEL_NOT_PERMITTED"
    SIGNAL_NEVER_RELEASABLE = "SIGNAL_NEVER_RELEASABLE"
    ESCALATION_STAGE_TOO_EARLY = "ESCALATION_STAGE_TOO_EARLY"
    NOT_A_CIRCLE_MEMBER = "NOT_A_CIRCLE_MEMBER"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """A recordable ALLOW/DENY, with the reason and any resolved subject."""

    allowed: bool
    reason: Reason
    detail: str = ""
    member: CircleMember | None = None

    def __bool__(self) -> bool:
        return self.allowed


_ALLOW = PolicyDecision(allowed=True, reason=Reason.ALLOWED)


def _deny(reason: Reason, detail: str) -> PolicyDecision:
    return PolicyDecision(allowed=False, reason=reason, detail=detail)


_CHANNEL_PERMISSION: dict[Channel, ContactChannelPermission] = {
    Channel.PUSH: ContactChannelPermission.PUSH,
    Channel.SMS: ContactChannelPermission.SMS,
    Channel.CALL: ContactChannelPermission.CALL,
}


def evaluate_contact(
    *,
    alert: Alert,
    circle: Circle,
    consents: dict[PersonId, ConsentGrant],
    sequence: int,
    plan_id: PlanId,
    now: datetime,
) -> PolicyDecision:
    """May escalation rung ``sequence`` contact anybody, and if so, whom?

    Checks run in the order of docs/AI-SAFETY.md section 3.

    The caller passes a **sequence number**, not a step object, and never a person or an
    endpoint. The rung is resolved from the Alert's own pinned version here. That closes a
    real gap: EscalationStep compares by value, so a step taken from a *different* version
    with identical content would satisfy a naive ``step in version.steps`` check and drive
    an Alert with a ladder it was never pinned to. Resolving internally makes a foreign
    step impossible to express, the same way naming a role rather than a phone number makes
    an arbitrary contact impossible to express.
    """
    if not alert.is_open:
        return _deny(Reason.ALERT_NOT_OPEN, f"alert is {alert.state}")

    try:
        step: EscalationStep = alert.version.step(sequence)
    except PlanValidationError:
        return _deny(
            Reason.STEP_NOT_IN_PLAN_VERSION,
            f"pinned version {alert.plan_version_id} has no rung {sequence}",
        )

    if not step.action.is_responder_directed or step.target_role is None:
        return _deny(
            Reason.STEP_NOT_RESPONDER_DIRECTED,
            f"{step.action} does not contact a responder",
        )

    role: ResponderRole = step.target_role
    if role not in alert.version.responder_roles:
        return _deny(
            Reason.ROLE_NOT_IN_PLAN_VERSION,
            f"{role} is not a responder role in version {alert.plan_version_id}",
        )

    member = circle.member_for_role(role)
    if member is None:
        return _deny(Reason.NO_MEMBER_FOR_ROLE, f"no accepted member holds {role}")
    if alert.version.responder_bindings and (
        alert.version.responder_bindings.get(role.value) != str(member.person_id)
    ):
        return _deny(Reason.ROLE_NOT_IN_PLAN_VERSION, "role now belongs to a different person")
    if not member.is_accepted:
        return _deny(Reason.MEMBER_NOT_ACCEPTED, f"{role} membership is {member.status}")

    consent = consents.get(member.person_id)
    if consent is None or not consent.is_active(now):
        # Checked at contact time, not at invitation time: consent withdrawn mid-Alert
        # must stop contact immediately.
        status = "absent" if consent is None else str(consent.status)
        return _deny(Reason.CONSENT_NOT_ACTIVE, f"consent for {role} is {status}")
    if consent.plan_id != plan_id:
        return _deny(
            Reason.CONSENT_NOT_ACTIVE,
            f"consent for {role} covers a different plan",
        )

    permission = _CHANNEL_PERMISSION[step.action.channel]
    if not consent.permits_channel(permission):
        return _deny(
            Reason.CHANNEL_NOT_PERMITTED,
            f"{role} has not agreed to be reached by {permission}",
        )

    return PolicyDecision(allowed=True, reason=Reason.ALLOWED, member=member)


def authorize_contact(
    *,
    alert: Alert,
    circle: Circle,
    consents: dict[PersonId, ConsentGrant],
    sequence: int,
    plan_id: PlanId,
    now: datetime,
) -> CircleMember:
    """Enforcing form. Returns the member to contact, or raises."""
    decision = evaluate_contact(
        alert=alert,
        circle=circle,
        consents=consents,
        sequence=sequence,
        plan_id=plan_id,
        now=now,
    )
    if not decision.allowed or decision.member is None:
        raise NotAuthorized(f"{decision.reason}: {decision.detail}")
    return decision.member


def reached_stage(alert: Alert) -> ReleaseLevel:
    """How far escalation has got, expressed as a context-release stage."""
    if alert.state in {AlertState.CIRCLE_ESCALATION, AlertState.CHECKING}:
        return ReleaseLevel.CIRCLE_ESCALATION
    if alert.state is AlertState.SELF_CONTACT:
        # Only once the subject's own channels have been exhausted does this count as a
        # failed attempt to reach them.
        if alert.ladder.subject_ladder_exhausted():
            return ReleaseLevel.AFTER_SUBJECT_CALL_FAILED
        return ReleaseLevel.ON_ALERT_OPEN
    if alert.is_open:
        return ReleaseLevel.ON_ALERT_OPEN
    return ReleaseLevel.NEVER


def evaluate_context_release(
    *, alert: Alert, signal: ContextSignal, now: datetime
) -> PolicyDecision:
    """May this context signal be released yet?

    The default for every signal is NEVER, and the subject opts in per signal, in advance.
    Location is off unless a plan explicitly enables it.
    """
    del now  # Stage is derived from Alert state, not from wall-clock time.
    policy = alert.version.context_policy
    allowed_at = policy.level_for(signal)

    if allowed_at is ReleaseLevel.NEVER:
        return _deny(
            Reason.SIGNAL_NEVER_RELEASABLE,
            f"{signal} is never releasable under version {alert.plan_version_id}",
        )

    stage = reached_stage(alert)
    if not policy.permits(signal, stage):
        return _deny(
            Reason.ESCALATION_STAGE_TOO_EARLY,
            f"{signal} unlocks at {allowed_at}; escalation has only reached {stage}",
        )
    return _ALLOW


def authorize_context_release(*, alert: Alert, signal: ContextSignal, now: datetime) -> None:
    decision = evaluate_context_release(alert=alert, signal=signal, now=now)
    if not decision.allowed:
        raise NotAuthorized(f"{decision.reason}: {decision.detail}")


def evaluate_responder_action(
    *, alert: Alert, circle: Circle, responder_id: PersonId, now: datetime
) -> PolicyDecision:
    """May this person act on this Alert at all?

    Guards the responder web surface: holding a signed link is not the same as being on
    the plan, and a link that outlives a membership must stop working.
    """
    del now
    if not alert.is_open:
        return _deny(Reason.ALERT_NOT_OPEN, f"alert is {alert.state}")

    member = circle.member(responder_id)
    if member is None or not member.is_accepted:
        return _deny(Reason.NOT_A_CIRCLE_MEMBER, "not an accepted member of this Circle")

    if alert.version.responder_bindings and (
        alert.version.responder_bindings.get(member.role.value) != str(responder_id)
    ):
        return _deny(Reason.ROLE_NOT_IN_PLAN_VERSION, "responder is not pinned to this Alert")

    if member.role not in alert.version.responder_roles:
        return _deny(
            Reason.ROLE_NOT_IN_PLAN_VERSION,
            f"{member.role} is not a responder on version {alert.plan_version_id}",
        )
    return PolicyDecision(allowed=True, reason=Reason.ALLOWED, member=member)
