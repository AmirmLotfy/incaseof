"""Performing one external action.

The only place that talks to a delivery provider, and the only place that turns an
authorised role into an address. Everything upstream deals in identifiers.
"""

from __future__ import annotations

import json
from typing import Any

from services.adapters.contact import (
    Delivery,
    DeliveryRecipient,
    DeliveryStatus,
    ProviderNotInvoked,
)
from services.adapters.queue import ActionIntent
from services.domain.authorization import evaluate_contact
from services.domain.circle import CircleMember
from services.domain.idempotency import key_for
from services.domain.ids import CircleId, PlanId
from services.handlers import bootstrap, escalation

BatchResponse = dict[str, list[dict[str, str]]]


class DeliveryDeferred(Exception):
    """No provider call happened; checking temporarily owns the Alert."""


def deliver(ctx: bootstrap.Context, intent: ActionIntent) -> Delivery:
    """Send one message, or explain in the timeline why it was not sent."""
    now = ctx.now()
    if ctx.outbox is None:
        raise RuntimeError("a durable worker ledger is required")
    row = ctx.outbox.get(intent.idempotency_key)
    if row is None or row.get("intent") != json.loads(intent.to_json()):
        # Legacy/untrusted queue payloads cannot authorize an external action.
        _record(ctx, intent, "ACTION_SUPPRESSED", now, reason="UNREGISTERED_INTENT")
        raise ValueError("unregistered intent requires DLQ reconciliation")
    if row["status"] != "PENDING":
        outcome = row.get("outcome", {})
        return Delivery(
            DeliveryStatus.UNKNOWN if row["status"] == "SENDING" else DeliveryStatus(row["status"]),
            provider_reference=outcome.get("provider_reference"),
            error_code=outcome.get("reason"),
        )
    alert = ctx.alerts.get(intent.alert_id)
    if alert is not None and alert.is_paused:
        # Keep PENDING. The durable relay retries after checking releases/expires.
        return Delivery(DeliveryStatus.FAILED, error_code="CHECKING")
    if not ctx.outbox.begin(intent, now):
        return Delivery(DeliveryStatus.UNKNOWN, error_code="ATTEMPT_ALREADY_OWNED")
    result = Delivery(DeliveryStatus.FAILED, error_code="ALERT_CLOSED")
    event = "ACTION_SUPPRESSED"
    provider_started = False
    try:
        # Fresh reads after taking ownership; authorization is checked at delivery time.
        alert = ctx.alerts.get(intent.alert_id)
        if alert is not None and not alert.is_terminal:
            if alert.is_paused:
                # Claim raced with taking worker ownership; do not contact the backup.
                ctx.outbox.defer(intent)
                return Delivery(DeliveryStatus.FAILED, error_code="CHECKING_RACE")
            else:
                recipient = _recipient(ctx, intent)
                if recipient is None:
                    result = Delivery(DeliveryStatus.FAILED, error_code="NOT_AUTHORIZED")
                    event = "CONTACT_DENIED"
                elif ctx.sender is None:
                    result = Delivery(DeliveryStatus.CHANNEL_UNAVAILABLE)
                    event = "CHANNEL_UNAVAILABLE"
                else:
                    body = (
                        escalation.responder_body(ctx, alert, _subject_name(ctx, intent))
                        if intent.action.is_responder_directed
                        else "Everything okay?"
                    )
                    link = (
                        escalation.responder_link(ctx, alert, recipient, now)
                        if isinstance(recipient, CircleMember)
                        else None
                    )
                    latest = ctx.alerts.get(intent.alert_id)
                    if latest is None or latest.is_terminal:
                        result = Delivery(DeliveryStatus.FAILED, error_code="ALERT_CLOSED")
                        event = "ACTION_SUPPRESSED"
                    elif latest.is_paused:
                        ctx.outbox.defer(intent)
                        return Delivery(DeliveryStatus.FAILED, error_code="CHECKING_RACE")
                    else:
                        provider_started = True
                        result = ctx.sender.send(
                            alert_id=intent.alert_id,
                            member=recipient,
                            channel=intent.channel,
                            body=body,
                            link=link,
                        )
                        event = _event_for(result)
    except DeliveryDeferred:
        ctx.outbox.defer(intent)
        return Delivery(DeliveryStatus.FAILED, error_code="CHECKING")
    except ProviderNotInvoked:
        ctx.outbox.defer(intent)
        raise
    except Exception as error:
        if not provider_started:
            ctx.outbox.defer(intent)
            raise
        # No exception from an attempted provider call proves it was not accepted.
        result = Delivery(
            DeliveryStatus.UNKNOWN if provider_started else DeliveryStatus.FAILED,
            error_code=type(error).__name__,
        )
        event = _event_for(result)
    ctx.outbox.finish(
        intent.idempotency_key,
        result.status.value,
        now,
        event_type=event,
        reason=result.error_code,
        provider_reference=result.provider_reference,
    )
    return result


def _event_for(result: Delivery) -> str:
    """Name what happened, at the resolution the timeline needs.

    A channel with no provider bound is not a failed send, and flattening the two into
    ACTION_FAILED reads as "we tried and it broke" — inviting somebody to wait for a retry
    that is never coming. `CHANNEL_UNAVAILABLE` says the honest thing instead: nothing was
    attempted on this channel, so do not wait on it.
    """
    if result.status is DeliveryStatus.UNKNOWN:
        return "ACTION_OUTCOME_UNKNOWN"
    if result.status is DeliveryStatus.CHANNEL_UNAVAILABLE:
        return "CHANNEL_UNAVAILABLE"
    # ACCEPTED, not SENT: the provider has custody. Delivery is a separate event that only
    # ever arrives from a carrier receipt, because a message id is not an arrival.
    return "ACTION_ACCEPTED" if result.succeeded else "ACTION_FAILED"


def _recipient(
    ctx: bootstrap.Context, intent: ActionIntent
) -> CircleMember | DeliveryRecipient | None:
    """Revalidate the pinned intent, current consent and recipient at the send boundary."""
    alert = ctx.alerts.get(intent.alert_id)
    if alert is not None and alert.is_paused:
        raise DeliveryDeferred()
    if alert is None or alert.is_terminal:
        return None
    step = alert.version.step(intent.sequence)
    if (
        step.step_id != intent.step_id
        or step.action != intent.action
        or step.action.channel != intent.channel
        or step.target_role != intent.target_role
        or key_for(intent.alert_id, step.step_id).value != intent.idempotency_key
    ):
        return None
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    if plan is None:
        return None
    if step.action.is_subject_directed:
        if intent.recipient_id != plan.subject_person_id:
            return None
        return DeliveryRecipient(plan.subject_person_id, "subject", is_subject=True)
    circle = ctx.circles.get(CircleId(plan.circle_id))
    if circle is None:
        return None
    decision = evaluate_contact(
        alert=alert,
        circle=circle,
        consents=ctx.circles.consents_for(plan.plan_id),
        sequence=step.sequence,
        plan_id=plan.plan_id,
        now=ctx.now(),
    )
    member = decision.member
    if (
        not decision.allowed
        or member is None
        or member.person_id != intent.recipient_id
        or str(member.membership_id) != intent.membership_id
    ):
        return None
    return member


def _subject_name(ctx: bootstrap.Context, intent: ActionIntent) -> str:
    alert = ctx.alerts.get(intent.alert_id)
    if alert is None:
        return "Someone"
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None
    return circle.owner_display_name if circle and circle.owner_display_name else "Someone"


def _record(
    ctx: bootstrap.Context,
    intent: ActionIntent,
    event: str,
    at: Any,
    reason: str | None = None,
    provider_reference: str | None = None,
) -> None:
    metadata = {"sequence": str(intent.sequence), "channel": intent.channel.value}
    if reason:
        metadata["reason"] = reason
    if provider_reference:
        # The carrier's own id for this message. Recorded so that "we handed it over" can
        # be checked against the provider later — an unverifiable claim of contact is worth
        # very little to somebody deciding whether to drive over.
        metadata["providerReference"] = provider_reference
    ctx.audit.append(
        alert_id=intent.alert_id,
        actor_type="WORKER",
        actor_id="action",
        event_type=event,
        at=at,
        metadata=metadata,
    )


def handler(event: dict[str, Any], _context: Any = None) -> BatchResponse:
    """SQS entry point.

    Failures are reported per message so one poison record does not drag its whole batch
    back onto the queue behind it.
    """
    ctx = bootstrap.build()
    failures: list[dict[str, str]] = []

    for record in event.get("Records", []):
        try:
            deliver(ctx, ActionIntent.from_dict(json.loads(record["body"])))
        # Broad by intent: one malformed or failing record must not take the batch down.
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}
