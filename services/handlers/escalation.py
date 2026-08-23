"""Step Functions tasks.

The state machine is a loop: ask what is due, dispatch it, wait until the next rung, ask
again. All of the deciding happens here in the domain; the state machine only sequences
and waits.

Every task is safe to retry. Step Functions retries on its own, and a task that is not
idempotent turns a transient error into a person being contacted twice.
"""

from __future__ import annotations

import json
from typing import Any

import boto3

from services.domain.alert import Alert, AlertState
from services.domain.authorization import evaluate_contact
from services.domain.idempotency import key_for
from services.domain.ids import AlertId, CircleId, PlanId
from services.handlers import bootstrap

TERMINAL = "TERMINAL"


def next_action(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    """What should happen next for this Alert, and when.

    Returns a decision the state machine can act on without interpreting anything:
    ``DISPATCH`` with rungs to send, ``WAIT`` with seconds, or ``TERMINAL``.
    """
    ctx = bootstrap.build()
    alert_id = AlertId(event["alertId"])
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return {"decision": TERMINAL, "reason": "NO_SUCH_ALERT"}

    now = ctx.clock.now()
    alert = _advance_phase(ctx, alert, now)

    if alert.is_terminal:
        return {"decision": TERMINAL, "reason": str(alert.state), "alertId": alert_id}

    if alert.is_paused:
        lease = alert.lease
        assert lease is not None  # noqa: S101 - CHECKING always carries a lease
        return {
            "decision": "WAIT",
            "seconds": max(1, int((lease.expires_at - now).total_seconds())),
            "reason": "LEASE_HELD",
            "alertId": alert_id,
        }

    due = alert.due_steps(now)
    if due:
        return {
            "decision": "DISPATCH",
            "alertId": alert_id,
            "sequences": [step.sequence for step in due],
        }

    upcoming = alert.next_action_due_at()
    if upcoming is None:
        return {"decision": TERMINAL, "reason": "LADDER_EXHAUSTED", "alertId": alert_id}

    return {
        "decision": "WAIT",
        "seconds": max(1, int((upcoming - now).total_seconds())),
        "reason": "NEXT_RUNG",
        "alertId": alert_id,
    }


def _advance_phase(ctx: bootstrap.Context, alert: Alert, now: Any) -> Alert:
    """Move the Alert through the phases whose trigger is the passage of time.

    Grace elapsing, the subject ladder running out, and a lease expiring are all things
    that simply become true — nobody performs them — so the workflow discovers them here.
    """
    moved = alert

    if moved.state is AlertState.SCHEDULED:
        moved = moved.mark_due(now)
    if moved.state is AlertState.DUE:
        moved = moved.enter_grace(now)
    if moved.state is AlertState.GRACE:
        moment = ctx.moments.get(moved.moment_id)
        if moment is not None and moment.grace_elapsed(now):
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


def dispatch(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    """Turn due rungs into queued actions.

    Nothing is sent from here. Each rung becomes an ActionIntent on the queue, guarded by
    an idempotency key, and a worker performs the actual delivery. That split is what
    makes a Step Functions retry harmless.
    """
    ctx = bootstrap.build()
    alert_id = AlertId(event["alertId"])
    alert = ctx.alerts.get(alert_id)
    if alert is None or alert.is_terminal:
        # Invariant 4: reaching a terminal state cancels pending external actions.
        return {"dispatched": [], "suppressed": "ALERT_CLOSED"}

    now = ctx.clock.now()
    sqs = boto3.client("sqs")
    dispatched: list[int] = []
    denied: list[dict[str, str]] = []

    for sequence in event.get("sequences", []):
        step = alert.version.step(int(sequence))

        if step.action.is_responder_directed:
            plan_id = PlanId(alert.version.plan_id)
            plan = ctx.plans.get_plan(plan_id)
            circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None
            decision = (
                evaluate_contact(
                    alert=alert,
                    circle=circle,
                    consents=ctx.circles.consents_for(plan_id),
                    sequence=step.sequence,
                    plan_id=plan_id,
                    now=now,
                )
                if circle is not None
                else None
            )
            if decision is None or not decision.allowed:
                reason = decision.reason if decision else "NO_CIRCLE"
                # A denial is recorded, never merely dropped. "Nothing happened" and
                # "something was blocked" must be distinguishable in the timeline.
                ctx.audit.append(
                    alert_id=alert_id,
                    actor_type="POLICY",
                    actor_id="authorization",
                    event_type="CONTACT_DENIED",
                    at=now,
                    metadata={"sequence": str(sequence), "reason": str(reason)},
                )
                denied.append({"sequence": str(sequence), "reason": str(reason)})
                alert = alert.record_attempt(step)
                continue

        key = key_for(alert_id, step.step_id, attempt_number=1)
        if not ctx.actions.claim_key(key):
            # Somebody already queued this exact attempt. Report success, send nothing.
            alert = alert.record_attempt(step)
            continue

        sqs.send_message(
            QueueUrl=ctx.action_queue_url,
            MessageBody=json.dumps(
                {
                    "alertId": alert_id,
                    "stepId": step.step_id,
                    "sequence": step.sequence,
                    "action": step.action.value,
                    "channel": step.action.channel.value,
                    "targetRole": step.target_role.value if step.target_role else None,
                    "idempotencyKey": key.value,
                }
            ),
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
