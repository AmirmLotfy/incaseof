"""Builders for domain tests.

Named, realistic defaults so a test body shows only what it is actually varying.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from services.domain.alert import Alert, AlertState
from services.domain.clock import REAL_TIME, FixedClock, TimeScale, utc
from services.domain.escalation import Ladder, LadderState
from services.domain.ids import AlertId, MomentId, PlanId, PlanVersionId, StepId
from services.domain.plan import (
    ActionType,
    ContextPolicy,
    ContextSignal,
    EscalationStep,
    PlanType,
    PlanVersion,
    ReleaseLevel,
    ResponderRole,
    StopCondition,
    Trigger,
    TriggerKind,
)

DUE_AT = utc(2026, 8, 26, 21, 0)

# The P0 evening ladder: push, push, SMS, then the Circle. No CALL rungs, because
# Amazon Connect is P1 - see docs/PRD.md section 12.
EVENING_STEPS = (
    (1, 0, ActionType.PUSH_SUBJECT, None),
    (2, 600, ActionType.PUSH_SUBJECT, None),
    (3, 1200, ActionType.SMS_SUBJECT, None),
    (4, 1500, ActionType.MESSAGE_RESPONDER, ResponderRole.PRIMARY),
    (5, 2700, ActionType.MESSAGE_RESPONDER, ResponderRole.BACKUP),
)


def make_version(
    *,
    steps: tuple[tuple[int, int, ActionType, ResponderRole | None], ...] = EVENING_STEPS,
    grace_seconds: int = 0,
    lease_seconds: int = 600,
    location: ReleaseLevel = ReleaseLevel.NEVER,
    version_number: int = 4,
) -> PlanVersion:
    return PlanVersion(
        version_id=PlanVersionId(f"pv-{version_number}"),
        plan_id=PlanId("plan-1"),
        version_number=version_number,
        plan_type=PlanType.ROUTINE,
        timezone="Africa/Cairo",
        trigger=Trigger(kind=TriggerKind.ONE_TIME, due_at=DUE_AT),
        grace_seconds=grace_seconds,
        steps=tuple(
            EscalationStep(
                step_id=StepId(f"step-{seq}"),
                sequence=seq,
                offset_seconds=offset,
                action=action,
                target_role=role,
            )
            for seq, offset, action, role in steps
        ),
        stop_conditions=frozenset(
            {
                StopCondition.SUBJECT_EXPLICIT_CONFIRMATION,
                StopCondition.RESPONDER_VERIFIED_CONTACT,
            }
        ),
        context_policy=ContextPolicy({ContextSignal.LOCATION: location}),
        lease_seconds=lease_seconds,
        label="Evening check",
    )


def make_alert(
    *,
    version: PlanVersion | None = None,
    state: AlertState = AlertState.SCHEDULED,
    opened_at: datetime = DUE_AT,
    scale: TimeScale = REAL_TIME,
) -> Alert:
    version = version or make_version()
    return Alert(
        alert_id=AlertId("alert-1"),
        moment_id=MomentId("moment-1"),
        plan_version_id=version.version_id,
        state=state,
        opened_at=opened_at,
        ladder=Ladder(version=version, state=LadderState(started_at=opened_at, scale=scale)),
    )


def escalating(version: PlanVersion | None = None, at: datetime = DUE_AT) -> Alert:
    """An Alert driven to SELF_CONTACT, where the ladder actually starts."""
    return (
        make_alert(version=version, opened_at=at)
        .mark_due(at)
        .enter_grace(at)
        .begin_self_contact(at)
    )


def in_circle_escalation(version: PlanVersion | None = None, at: datetime = DUE_AT) -> Alert:
    """An Alert whose subject rungs are all spent, now reaching the Circle."""
    alert = escalating(version, at)
    for step in alert.version.subject_steps:
        alert = alert.record_attempt(step)
    return alert.escalate_to_circle(at)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(DUE_AT)
