"""Domain objects to DynamoDB items and back.

Kept separate from the repositories so the mapping can be round-trip tested on its own. A
persistence bug that silently drops a field -- a lease owner, a paused duration, an
attempted rung -- would not fail loudly; it would just make escalation behave slightly
wrong, later, in a way nobody could reproduce.

Two DynamoDB facts shape this module:

* The resource API refuses ``float`` and returns every number as ``Decimal``. Numbers are
  converted on the way in and back out, in one place.
* Empty sets are not storable. ``attempted`` and ``stop_conditions`` are written as lists.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from services.domain.alert import Alert, AlertState, CheckingLease
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    ContactChannelPermission,
    MemberStatus,
)
from services.domain.clock import REAL_TIME, TimeScale
from services.domain.escalation import Ladder, LadderState
from services.domain.ids import (
    AlertId,
    CircleId,
    ConsentId,
    InvitationId,
    MembershipId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
    StepId,
)
from services.domain.invitation import CircleInvitation, InvitationStatus
from services.domain.moment import ExpectedMoment, MomentStatus
from services.domain.plan import (
    ActionType,
    ContextPolicy,
    ContextSignal,
    EscalationStep,
    Plan,
    PlanType,
    PlanVersion,
    ReleaseLevel,
    ResponderRole,
    StopCondition,
    Trigger,
    TriggerKind,
)
from services.domain.resolution import Resolution, ResolutionSource

Item = dict[str, Any]


def invitation_to(invitation: CircleInvitation) -> Item:
    return {
        "invitationId": invitation.invitation_id,
        "circleId": invitation.circle_id,
        "ownerPersonId": invitation.owner_person_id,
        "responderPersonId": invitation.responder_person_id,
        "membershipId": invitation.membership_id,
        "planIds": list(invitation.plan_ids),
        "expiresAt": _iso(invitation.expires_at),
        "status": invitation.status.value,
    }


def invitation_from(item: Item) -> CircleInvitation:
    expires_at = _dt(item["expiresAt"])
    assert expires_at is not None  # noqa: S101
    return CircleInvitation(
        invitation_id=InvitationId(item["invitationId"]),
        circle_id=CircleId(item["circleId"]),
        owner_person_id=PersonId(item["ownerPersonId"]),
        responder_person_id=PersonId(item["responderPersonId"]),
        membership_id=MembershipId(item["membershipId"]),
        plan_ids=tuple(PlanId(value) for value in item.get("planIds", [])),
        expires_at=expires_at,
        status=InvitationStatus(item["status"]),
    )


def _num(value: float | int) -> Decimal:
    """DynamoDB stores numbers as Decimal; float is rejected outright."""
    return Decimal(str(value))


def _float(value: Any) -> float:
    return float(value)


def _int(value: Any) -> int:
    return int(value)


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


# -- plan version -------------------------------------------------------------


def trigger_to(trigger: Trigger) -> Item:
    return {
        "kind": trigger.kind.value,
        "dueAt": _iso(trigger.due_at),
        "timeOfDay": trigger.time_of_day,
        "daysOfWeek": list(trigger.days_of_week),
        "intervalSeconds": _num(trigger.interval_seconds) if trigger.interval_seconds else None,
        "offsetSeconds": _num(trigger.offset_seconds) if trigger.offset_seconds else None,
    }


def trigger_from(item: Item) -> Trigger:
    return Trigger(
        kind=TriggerKind(item["kind"]),
        due_at=_dt(item.get("dueAt")),
        time_of_day=item.get("timeOfDay"),
        days_of_week=tuple(item.get("daysOfWeek") or ()),
        interval_seconds=_int(item["intervalSeconds"]) if item.get("intervalSeconds") else None,
        offset_seconds=_int(item["offsetSeconds"]) if item.get("offsetSeconds") else None,
    )


def step_to(step: EscalationStep) -> Item:
    return {
        "stepId": step.step_id,
        "sequence": _num(step.sequence),
        "offsetSeconds": _num(step.offset_seconds),
        "action": step.action.value,
        "targetRole": step.target_role.value if step.target_role else None,
    }


def step_from(item: Item) -> EscalationStep:
    role = item.get("targetRole")
    return EscalationStep(
        step_id=StepId(item["stepId"]),
        sequence=_int(item["sequence"]),
        offset_seconds=_int(item["offsetSeconds"]),
        action=ActionType(item["action"]),
        target_role=ResponderRole(role) if role else None,
    )


def version_to(version: PlanVersion) -> Item:
    return {
        "versionId": version.version_id,
        "planId": version.plan_id,
        "versionNumber": _num(version.version_number),
        "planType": version.plan_type.value,
        "timezone": version.timezone,
        "trigger": trigger_to(version.trigger),
        "graceSeconds": _num(version.grace_seconds),
        "steps": [step_to(s) for s in version.steps],
        "stopConditions": [c.value for c in sorted(version.stop_conditions)],
        "contextPolicy": {
            signal.value: level.value for signal, level in version.context_policy.levels.items()
        },
        "leaseSeconds": _num(version.lease_seconds),
        "label": version.label,
        "activatedAt": _iso(version.activated_at),
    }


def version_from(item: Item) -> PlanVersion:
    return PlanVersion(
        version_id=PlanVersionId(item["versionId"]),
        plan_id=PlanId(item["planId"]),
        version_number=_int(item["versionNumber"]),
        plan_type=PlanType(item["planType"]),
        timezone=item["timezone"],
        trigger=trigger_from(item["trigger"]),
        grace_seconds=_int(item["graceSeconds"]),
        steps=tuple(step_from(s) for s in item["steps"]),
        stop_conditions=frozenset(StopCondition(c) for c in item["stopConditions"]),
        context_policy=ContextPolicy(
            {
                ContextSignal(signal): ReleaseLevel(level)
                for signal, level in (item.get("contextPolicy") or {}).items()
            }
        ),
        lease_seconds=_int(item["leaseSeconds"]),
        label=item.get("label"),
        activated_at=_dt(item.get("activatedAt")),
    )


def plan_to(plan: Plan) -> Item:
    return {
        "planId": plan.plan_id,
        "subjectPersonId": plan.subject_person_id,
        "circleId": plan.circle_id,
        "planType": plan.plan_type.value,
        "activeVersionId": plan.active_version_id,
        "paused": plan.paused,
    }


def plan_from(item: Item) -> Plan:
    active = item.get("activeVersionId")
    return Plan(
        plan_id=PlanId(item["planId"]),
        subject_person_id=PersonId(item["subjectPersonId"]),
        circle_id=CircleId(item["circleId"]),
        plan_type=PlanType(item["planType"]),
        active_version_id=PlanVersionId(active) if active else None,
        paused=bool(item.get("paused", False)),
    )


# -- moment -------------------------------------------------------------------


def moment_to(moment: ExpectedMoment) -> Item:
    return {
        "momentId": moment.moment_id,
        "versionId": moment.version_id,
        "dueAt": _iso(moment.due_at),
        "graceUntil": _iso(moment.grace_until),
        "status": moment.status.value,
        "isDrill": moment.is_drill,
        "timeScale": _num(moment.time_scale),
    }


def moment_from(item: Item) -> ExpectedMoment:
    due_at = _dt(item["dueAt"])
    grace_until = _dt(item["graceUntil"])
    assert due_at is not None and grace_until is not None  # noqa: S101
    return ExpectedMoment(
        moment_id=MomentId(item["momentId"]),
        version_id=PlanVersionId(item["versionId"]),
        due_at=due_at,
        grace_until=grace_until,
        status=MomentStatus(item["status"]),
        is_drill=bool(item.get("isDrill", False)),
        time_scale=_float(item.get("timeScale", 1.0)),
    )


# -- alert --------------------------------------------------------------------


def lease_to(lease: CheckingLease | None) -> Item | None:
    if lease is None:
        return None
    return {
        "ownerPersonId": lease.owner_person_id,
        "claimedAt": _iso(lease.claimed_at),
        "expiresAt": _iso(lease.expires_at),
    }


def lease_from(item: Item | None) -> CheckingLease | None:
    if not item:
        return None
    claimed = _dt(item["claimedAt"])
    expires = _dt(item["expiresAt"])
    assert claimed is not None and expires is not None  # noqa: S101
    return CheckingLease(
        owner_person_id=PersonId(item["ownerPersonId"]),
        claimed_at=claimed,
        expires_at=expires,
    )


def resolution_to(resolution: Resolution | None) -> Item | None:
    if resolution is None:
        return None
    return {
        "alertId": resolution.alert_id,
        "resolvedByPersonId": resolution.resolved_by_person_id,
        "method": resolution.method.value,
        "source": resolution.source.value,
        "planVersionId": resolution.plan_version_id,
        "createdAt": _iso(resolution.created_at),
        "reasonCode": resolution.reason_code,
    }


def resolution_from(item: Item | None) -> Resolution | None:
    if not item:
        return None
    created = _dt(item["createdAt"])
    assert created is not None  # noqa: S101
    by = item.get("resolvedByPersonId")
    return Resolution(
        alert_id=AlertId(item["alertId"]),
        resolved_by_person_id=PersonId(by) if by else None,
        method=StopCondition(item["method"]),
        source=ResolutionSource(item["source"]),
        plan_version_id=PlanVersionId(item["planVersionId"]),
        created_at=created,
        reason_code=item.get("reasonCode"),
    )


def ladder_to(ladder: Ladder) -> Item:
    return {
        "startedAt": _iso(ladder.state.started_at),
        "pausedSeconds": _num(ladder.state.paused_seconds),
        # A list, not a set: DynamoDB cannot store an empty set, and a fresh Alert has
        # attempted nothing.
        "attempted": sorted(_num(s) for s in ladder.state.attempted),
        "scale": _num(ladder.state.scale.factor),
    }


def ladder_from(item: Item, version: PlanVersion) -> Ladder:
    started = _dt(item["startedAt"])
    assert started is not None  # noqa: S101
    return Ladder(
        version=version,
        state=LadderState(
            started_at=started,
            paused_seconds=_float(item["pausedSeconds"]),
            attempted=frozenset(_int(s) for s in item.get("attempted") or ()),
            scale=TimeScale(_float(item["scale"])) if item.get("scale") else REAL_TIME,
        ),
    )


def alert_to(alert: Alert) -> Item:
    return {
        "alertId": alert.alert_id,
        "momentId": alert.moment_id,
        "planVersionId": alert.plan_version_id,
        "state": alert.state.value,
        "openedAt": _iso(alert.opened_at),
        "ladder": ladder_to(alert.ladder),
        "lease": lease_to(alert.lease),
        "resolution": resolution_to(alert.resolution),
        "resolvedAt": _iso(alert.resolved_at),
        "releasedSignals": sorted(alert.released_signals),
        # The pinned version travels with the Alert so a reader never has to consult the
        # live plan to interpret it.
        "version": version_to(alert.version),
    }


def alert_from(item: Item) -> Alert:
    version = version_from(item["version"])
    opened = _dt(item["openedAt"])
    assert opened is not None  # noqa: S101
    return Alert(
        alert_id=AlertId(item["alertId"]),
        moment_id=MomentId(item["momentId"]),
        plan_version_id=PlanVersionId(item["planVersionId"]),
        state=AlertState(item["state"]),
        opened_at=opened,
        ladder=ladder_from(item["ladder"], version),
        lease=lease_from(item.get("lease")),
        resolution=resolution_from(item.get("resolution")),
        resolved_at=_dt(item.get("resolvedAt")),
        released_signals=frozenset(item.get("releasedSignals") or ()),
    )


# -- circle and consent -------------------------------------------------------


def member_to(member: CircleMember) -> Item:
    return {
        "membershipId": member.membership_id,
        "circleId": member.circle_id,
        "personId": member.person_id,
        "role": member.role.value,
        "priority": _num(member.priority),
        "status": member.status.value,
        "displayName": member.display_name,
        "relationship": member.relationship,
    }


def member_from(item: Item) -> CircleMember:
    return CircleMember(
        membership_id=MembershipId(item["membershipId"]),
        circle_id=CircleId(item["circleId"]),
        person_id=PersonId(item["personId"]),
        role=ResponderRole(item["role"]),
        priority=_int(item["priority"]),
        status=MemberStatus(item["status"]),
        display_name=item["displayName"],
        relationship=item.get("relationship"),
    )


def consent_to(consent: ConsentGrant) -> Item:
    return {
        "consentId": consent.consent_id,
        "subjectPersonId": consent.subject_person_id,
        "responderPersonId": consent.responder_person_id,
        "planId": consent.plan_id,
        "status": consent.status.value,
        "acceptedAt": _iso(consent.accepted_at),
        "revokedAt": _iso(consent.revoked_at),
        "expiresAt": _iso(consent.expires_at),
        "policyVersion": consent.policy_version,
        "channels": sorted(c.value for c in consent.channels),
    }


def consent_from(item: Item) -> ConsentGrant:
    return ConsentGrant(
        consent_id=ConsentId(item["consentId"]),
        subject_person_id=PersonId(item["subjectPersonId"]),
        responder_person_id=PersonId(item["responderPersonId"]),
        plan_id=PlanId(item["planId"]),
        status=ConsentStatus(item["status"]),
        accepted_at=_dt(item.get("acceptedAt")),
        revoked_at=_dt(item.get("revokedAt")),
        expires_at=_dt(item.get("expiresAt")),
        policy_version=item.get("policyVersion", "1.0"),
        channels=frozenset(ContactChannelPermission(c) for c in (item.get("channels") or ())),
    )


def circle_to(circle: Circle) -> Item:
    return {
        "circleId": circle.circle_id,
        "ownerPersonId": circle.owner_person_id,
        "ownerDisplayName": circle.owner_display_name,
    }


def circle_from(item: Item, members: tuple[CircleMember, ...]) -> Circle:
    return Circle(
        circle_id=CircleId(item["circleId"]),
        owner_person_id=PersonId(item["ownerPersonId"]),
        members=members,
        owner_display_name=item.get("ownerDisplayName", ""),
    )
