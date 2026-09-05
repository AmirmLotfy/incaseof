"""The escalation loop.

Step Functions sequences and waits; every decision happens here, in code that runs in
milliseconds under test. The state machine holds no opinions of its own.

Each function takes an explicit Context, so the same code runs behind a Lambda and inside
the end-to-end slice test with nothing mocked but the wire calls at the very edges.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from services.adapters.contact import compose_responder_message
from services.adapters.queue import ActionIntent
from services.domain.alert import Alert, AlertState
from services.domain.authorization import evaluate_contact
from services.domain.circle import CircleMember
from services.domain.idempotency import key_for
from services.domain.ids import AlertId, CircleId, PlanId
from services.domain.plan import EscalationStep
from services.domain.responder_token import issue
from services.handlers import bootstrap

TERMINAL = "TERMINAL"
DISPATCH = "DISPATCH"
WAIT = "WAIT"


# -- deciding -----------------------------------------------------------------


def decide(ctx: bootstrap.Context, alert_id: AlertId) -> dict[str, Any]:
    """What happens next for this Alert, and when.

    Returns something the state machine can act on without interpreting anything.
    """
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return {"decision": TERMINAL, "reason": "NO_SUCH_ALERT"}

    now = ctx.now()
    if ctx.outbox is not None and not alert.is_terminal and not alert.is_paused:
        for step in alert.version.steps:
            key = key_for(alert_id, step.step_id).value
            row = ctx.outbox.get(key)
            if row is None:
                continue
            if row["status"] in {"PENDING", "SENDING"}:
                return {"decision": WAIT, "seconds": 2, "reason": "DELIVERY_PENDING"}
    alert = advance(ctx, alert, now)

    if alert.is_terminal:
        return {"decision": TERMINAL, "reason": str(alert.state), "alertId": alert_id}

    if alert.is_paused:
        lease = alert.lease
        assert lease is not None  # noqa: S101 - CHECKING always carries a lease
        return {
            "decision": WAIT,
            "seconds": max(1, int((lease.expires_at - now).total_seconds())),
            "reason": "LEASE_HELD",
            "alertId": alert_id,
        }

    due = alert.due_steps(now)
    if due:
        return {
            "decision": DISPATCH,
            "alertId": alert_id,
            "sequences": [step.sequence for step in due],
        }

    upcoming = alert.next_action_due_at()
    if upcoming is None:
        return {"decision": TERMINAL, "reason": "LADDER_EXHAUSTED", "alertId": alert_id}

    return {
        "decision": WAIT,
        "seconds": max(1, int((upcoming - now).total_seconds())),
        "reason": "NEXT_RUNG",
        "alertId": alert_id,
    }


def advance(ctx: bootstrap.Context, alert: Alert, now: datetime) -> Alert:
    """Move through the phases whose only trigger is time passing.

    Grace elapsing, the subject ladder running out and a lease expiring are all things that
    simply become true — nobody performs them — so the workflow discovers them here rather
    than waiting to be told.
    """
    moved = alert

    if moved.state is AlertState.SCHEDULED:
        moved = moved.mark_due(now)
    if moved.state is AlertState.DUE:
        moved = moved.enter_grace(now)
    if moved.state is AlertState.GRACE:
        moment = ctx.moments.get(moved.moment_id)
        if moment is None or moment.grace_elapsed(now):
            moved = moved.begin_self_contact(now)
    if moved.state is AlertState.CHECKING:
        lease = moved.lease
        if lease is not None and lease.is_expired(now):
            moved = moved.expire_lease(now)
    if moved.state is AlertState.SELF_CONTACT and moved.ladder.subject_ladder_exhausted():
        moved = moved.escalate_to_circle(now)
    if moved.state is AlertState.CIRCLE_ESCALATION and moved.ladder.circle_ladder_exhausted():
        moved = moved.exhaust(now)

    if moved is not alert:
        ctx.alerts.save(moved)
        ctx.audit.append(
            alert_id=moved.alert_id,
            actor_type="SYSTEM",
            actor_id="workflow",
            event_type=f"STATE_{moved.state}",
            at=now,
        )
    return moved


# -- dispatching --------------------------------------------------------------


def dispatch(ctx: bootstrap.Context, alert_id: AlertId, sequences: list[int]) -> dict[str, Any]:
    """Turn due rungs into queued intents.

    Nothing is sent from here. Each rung becomes one queued action guarded by an
    idempotency key, and a worker performs delivery.
    """
    alert = ctx.alerts.get(alert_id)
    if alert is None or alert.is_terminal:
        # Invariant 4: a terminal Alert cancels everything still pending.
        return {"dispatched": [], "denied": [], "suppressed": "ALERT_CLOSED"}

    if ctx.outbox is None or ctx.queue is None:
        raise RuntimeError("a durable outbox and action queue are required")
    now = ctx.now()
    before = alert
    dispatched: list[int] = []
    denied: list[dict[str, str]] = []
    intents: list[ActionIntent] = []
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    if plan is None:
        raise RuntimeError("Alert plan is missing")
    if alert.is_paused:
        return {"dispatched": [], "denied": [], "suppressed": "CHECKING"}
    for sequence in sequences:
        step = alert.version.step(int(sequence))
        key = key_for(alert_id, step.step_id, attempt_number=1)
        if ctx.outbox.get(key.value):
            continue
        if ctx.actions.was_dispatched(key):
            alert = alert.record_attempt(step)
            ctx.audit.append(
                alert_id=alert_id,
                actor_type="SYSTEM",
                actor_id="migration",
                event_type="ACTION_OUTCOME_UNKNOWN",
                at=now,
                metadata={
                    "sequence": str(sequence),
                    "reason": "LEGACY_ATTEMPT_REQUIRES_RECONCILIATION",
                },
            )
            continue
        member = None
        if step.action.is_responder_directed:
            member = _authorise(ctx, alert, step, now)
            if member is None:
                denied.append({"sequence": str(sequence), "reason": "NOT_AUTHORIZED"})
                alert = alert.record_attempt(step)
                continue
        intents.append(
            ActionIntent(
                alert_id=alert_id,
                step_id=step.step_id,
                sequence=step.sequence,
                action=step.action,
                channel=step.action.channel,
                target_role=step.target_role,
                idempotency_key=key.value,
                recipient_id=member.person_id if member else plan.subject_person_id,
                membership_id=str(member.membership_id) if member else None,
            )
        )
        alert = alert.record_attempt(step)
        dispatched.append(step.sequence)
    if alert != before:
        ctx.outbox.stage(before, alert, intents, now)
        ctx.alerts.get(alert_id)  # refresh optimistic revision after the transaction
    for intent in intents:
        # Failure here leaves a durable PENDING row for the relay; never loses a rung.
        ctx.queue.enqueue(intent)
    return {"dispatched": dispatched, "denied": denied, "alertId": alert_id}


def _authorise(
    ctx: bootstrap.Context, alert: Alert, step: EscalationStep, now: datetime
) -> CircleMember | None:
    """Policy check for a responder-directed rung.

    A denial is *recorded*, never merely dropped. "Nothing happened" and "something was
    blocked" must be distinguishable in the timeline, or the audit trail lies by omission.
    """
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None

    if plan is None or circle is None:
        ctx.audit.append(
            alert_id=alert.alert_id,
            actor_type="POLICY",
            actor_id="authorization",
            event_type="CONTACT_DENIED",
            at=now,
            metadata={"sequence": str(step.sequence), "reason": "NO_CIRCLE"},
        )
        return None

    decision = evaluate_contact(
        alert=alert,
        circle=circle,
        consents=ctx.circles.consents_for(PlanId(plan.plan_id)),
        sequence=step.sequence,
        plan_id=PlanId(plan.plan_id),
        now=now,
    )
    if not decision.allowed or decision.member is None:
        ctx.audit.append(
            alert_id=alert.alert_id,
            actor_type="POLICY",
            actor_id="authorization",
            event_type="CONTACT_DENIED",
            at=now,
            metadata={"sequence": str(step.sequence), "reason": str(decision.reason)},
        )
        return None
    return decision.member


# -- responder links ----------------------------------------------------------


def responder_link(
    ctx: bootstrap.Context, alert: Alert, member: CircleMember, now: datetime
) -> str | None:
    """Mint a single-Alert link for one responder.

    The nonce is written before the token is handed out, so a link that exists can always
    be revoked. A token whose nonce was never stored would be unrevokable.
    """
    if not ctx.signing_key:
        return None

    nonce = f"{alert.alert_id}:{member.person_id}"
    token = issue(
        alert_id=alert.alert_id,
        responder_id=member.person_id,
        nonce=nonce,
        key=ctx.signing_key,
        now=now,
    )
    base = os.environ.get("ICO_RESPONDER_BASE_URL", "https://incaof.com")
    return f"{base}/r/{token}"


def responder_body(ctx: bootstrap.Context, alert: Alert, subject_name: str) -> str:
    """What the responder reads, built from what actually happened."""
    tried = [
        f"{event['at']!s:.16}  {event['eventType']!s}"
        for event in ctx.audit.for_alert(alert.alert_id)
        if str(event.get("eventType")) in {"ACTION_QUEUED", "ACTION_ACCEPTED", "ACTION_DELIVERED"}
    ]
    return compose_responder_message(
        subject_name=subject_name,
        plan_label=alert.version.label or "Check-in",
        expected_at=alert.opened_at,
        tried=tried,
    )


# -- Lambda entry points ------------------------------------------------------


def next_action(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    return decide(bootstrap.build(), AlertId(event["alertId"]))


def dispatch_handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    return dispatch(
        bootstrap.build(),
        AlertId(event["alertId"]),
        [int(s) for s in event.get("sequences", [])],
    )
