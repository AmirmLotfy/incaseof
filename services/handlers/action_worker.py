"""SQS consumer: perform one external action.

The only place in the system that talks to a delivery provider. Everything upstream writes
intents; this turns an intent into a message, a push, or (in P1) a call.

Channel availability is explicit rather than assumed. ``CALL`` compiles, schedules and
dispatches like any other rung, and reports ``CHANNEL_UNAVAILABLE`` until Amazon Connect is
wired — so a plan written today keeps working unchanged when voice lands, and the gap is
visible in the timeline rather than silent.
"""

from __future__ import annotations

import json
from typing import Any

from services.domain.ids import AlertId
from services.domain.plan import Channel
from services.handlers import bootstrap

# Partial batch failure: SQS retries only the records named here, so one poison message
# does not drag its whole batch back onto the queue.
BatchResponse = dict[str, list[dict[str, str]]]


def handler(event: dict[str, Any], _context: Any = None) -> BatchResponse:
    ctx = bootstrap.build()
    failures: list[dict[str, str]] = []

    for record in event.get("Records", []):
        try:
            _deliver(ctx, json.loads(record["body"]))
        # Broad by intent: one malformed or failing record must not take the batch
        # down with it. SQS retries only what is reported below.
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def _deliver(ctx: bootstrap.Context, intent: dict[str, Any]) -> None:
    alert_id = AlertId(intent["alertId"])
    channel = Channel(intent["channel"])
    now = ctx.clock.now()

    alert = ctx.alerts.get(alert_id)
    if alert is None or alert.is_terminal:
        # Invariant 4. The Alert closed while this sat on the queue; sending now would
        # contact somebody about a situation that is already resolved.
        ctx.audit.append(
            alert_id=alert_id,
            actor_type="WORKER",
            actor_id="action",
            event_type="ACTION_SUPPRESSED",
            at=now,
            metadata={"reason": "ALERT_CLOSED", "sequence": str(intent.get("sequence"))},
        )
        return

    if not channel.is_available_in_p0:
        ctx.audit.append(
            alert_id=alert_id,
            actor_type="WORKER",
            actor_id="action",
            event_type="CHANNEL_UNAVAILABLE",
            at=now,
            metadata={"channel": channel.value, "sequence": str(intent.get("sequence"))},
        )
        return

    _send(ctx, alert_id, intent, channel)

    ctx.audit.append(
        alert_id=alert_id,
        actor_type="WORKER",
        actor_id="action",
        event_type="ACTION_SENT",
        at=now,
        metadata={"channel": channel.value, "sequence": str(intent.get("sequence"))},
    )


def _send(
    ctx: bootstrap.Context, alert_id: AlertId, intent: dict[str, Any], channel: Channel
) -> None:
    """Resolve the recipient and hand the message to a provider.

    Endpoint resolution happens **here**, at the last possible moment, from the encrypted
    contact store — never earlier, and never anywhere the model can reach. By this point
    the recipient has already been authorized by role upstream; this only turns that role
    into an address.

    Provider integration lands with the channels in Phase 3. The seam is deliberate: this
    is the single function that will ever hold a phone number.
    """
    raise NotImplementedError(
        f"channel {channel} has no provider bound yet; FCM and SMS land in Phase 3"
    )
