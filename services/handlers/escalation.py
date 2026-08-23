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

    now = ctx.now()
    dispatched: list[int] = []
    denied: list[dict[str, str]] = []

    for sequence in sequences:
        step = alert.version.step(int(sequence))

        if step.action.is_responder_directed:
            decision = _authorise(ctx, alert, step, now)
            if decision is None:
                denied.append({"sequence": str(sequence), "reason": "NOT_AUTHORIZED"})
                alert = alert.record_attempt(step)
                continue

        key = key_for(alert_id, step.step_id, attempt_number=1)
        if not ctx.actions.claim_key(key):
            # Somebody already queued this exact attempt. Report success, send nothing.
            alert = alert.record_attempt(step)
            continue

        if ctx.queue is None:
            # Never silently. Skipping the enqueue here would mark the rung attempted and
            # contact nobody — the ladder would advance past a person who was never reached,
            # and nothing would look wrong.
            raise RuntimeError(
                "no action queue is configured; refusing to mark rungs attempted without "
                "dispatching them"
            )

        ctx.queue.enqueue(
            ActionIntent(
                alert_id=alert_id,
                step_id=step.step_id,
                sequence=step.sequence,
                action=step.action,
                channel=step.action.channel,
                target_role=step.target_role,
                idempotency_key=key.value,
            )
        )

        alert = alert.record_attempt(step)
        dispatched.append(step.sequence)
        ctx.audit.append(
            alert_id=alert_id,
            actor_type="SYSTEM",
            actor_id="workflow",
            event_type="ACTION_QUEUED",
            at=now,
            metadata={"sequence": str(step.sequence), "action": step.action.value},
        )

    ctx.alerts.save(alert)
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
        if str(event.get("eventType")) in {"ACTION_QUEUED", "ACTION_SENT"}
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
