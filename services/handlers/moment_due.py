"""A Moment has come due.

EventBridge Scheduler owns the timer; this is what that timer wakes up. Its whole job is
to open exactly one Alert and hand escalation to the workflow.

Safe to invoke twice. Scheduler delivers at least once, so a duplicate is normal operation
rather than an error, and the conditional write in ``open_for_moment`` is what makes the
second delivery harmless.
"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from services.domain.alert import Alert, AlertState
from services.domain.escalation import Ladder, LadderState
from services.domain.ids import AlertId, IdFactory, MomentId, uuid_factory
from services.handlers import bootstrap


def open_alert(
    ctx: bootstrap.Context,
    moment_id: MomentId,
    *,
    new_id: IdFactory = uuid_factory,
) -> tuple[Alert | None, bool]:
    """Open the Alert for a Moment.

    Returns the Alert and whether this call is the one that opened it. A duplicate
    delivery gets back the Alert that already exists, with ``opened`` false.
    """
    moment = ctx.moments.get(moment_id)
    if moment is None:
        # Cancelled between the schedule being created and firing. Nothing to do, and
        # nothing wrong.
        return None, False

    version = ctx.plans.get_version(moment.version_id)
    if version is None:
        raise RuntimeError(
            f"moment {moment_id} pins version {moment.version_id}, which no longer exists"
        )

    now = ctx.now()
    candidate = Alert(
        alert_id=AlertId(new_id()),
        moment_id=moment_id,
        plan_version_id=version.version_id,
        state=AlertState.SCHEDULED,
        opened_at=moment.due_at,
        ladder=Ladder(
            version=version,
            state=LadderState(started_at=moment.grace_until, scale=ctx.scale),
        ),
    )
    alert = ctx.alerts.open_for_moment(candidate)
    opened = alert.alert_id == candidate.alert_id

    if opened:
        ctx.audit.append(
            alert_id=alert.alert_id,
            actor_type="SYSTEM",
            actor_id="scheduler",
            event_type="MOMENT_DUE",
            at=now,
        )
    return alert, opened


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    ctx = bootstrap.build()
    alert, opened = open_alert(ctx, MomentId(event["momentId"]))

    if alert is None:
        return {"status": "NO_SUCH_MOMENT", "momentId": event["momentId"]}
    if not opened:
        return {"status": "ALREADY_OPEN", "alertId": alert.alert_id}

    _start_escalation(alert.alert_id)
    return {"status": "OPENED", "alertId": alert.alert_id}


def _start_escalation(alert_id: AlertId) -> None:
    """Hand off to Step Functions.

    The execution name is derived from the Alert, so even a duplicate that somehow got past
    the conditional write cannot start a second escalation — Step Functions rejects a
    repeated execution name.
    """
    arn = os.environ.get("ICO_STATE_MACHINE_ARN")
    if not arn:
        return
    client = boto3.client("stepfunctions")
    try:
        client.start_execution(
            stateMachineArn=arn,
            name=f"alert-{alert_id}",
            input=json.dumps({"alertId": alert_id}),
        )
    except client.exceptions.ExecutionAlreadyExists:
        return
