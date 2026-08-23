"""EventBridge Scheduler target: a Moment has come due.

EventBridge owns every safety timer. This handler is what that timer wakes up, and its
whole job is to open exactly one Alert and hand escalation to Step Functions.

It must be safe to invoke twice with the same event. Scheduler guarantees at-least-once
delivery, so a duplicate is normal operation rather than an error, and the conditional
write in ``open_for_moment`` is what makes a second delivery harmless.
"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3

from services.domain.alert import Alert, AlertState
from services.domain.escalation import Ladder, LadderState
from services.domain.ids import AlertId, MomentId
from services.handlers import bootstrap


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    ctx = bootstrap.build()
    moment_id = MomentId(event["momentId"])
    now = ctx.clock.now()

    moment = ctx.moments.get(moment_id)
    if moment is None:
        # The Moment was cancelled between the schedule being created and firing. Nothing
        # to do, and nothing wrong.
        return {"status": "NO_SUCH_MOMENT", "momentId": moment_id}

    version = ctx.plans.get_version(moment.version_id)
    if version is None:
        raise RuntimeError(f"moment {moment_id} pins version {moment.version_id}, which is gone")

    candidate = Alert(
        alert_id=AlertId(event.get("alertId") or f"alert-{moment_id}"),
        moment_id=moment_id,
        plan_version_id=version.version_id,
        state=AlertState.SCHEDULED,
        opened_at=now,
        ladder=Ladder(version=version, state=LadderState(started_at=now, scale=ctx.scale)),
    )
    alert = ctx.alerts.open_for_moment(candidate)

    if alert.alert_id != candidate.alert_id:
        # A previous delivery already opened this Alert and escalation is under way.
        return {"status": "ALREADY_OPEN", "alertId": alert.alert_id}

    ctx.audit.append(
        alert_id=alert.alert_id,
        actor_type="SYSTEM",
        actor_id="scheduler",
        event_type="MOMENT_DUE",
        at=now,
    )

    _start_escalation(ctx, alert)
    return {"status": "OPENED", "alertId": alert.alert_id}


def _start_escalation(ctx: bootstrap.Context, alert: Alert) -> None:
    """Hand off to Step Functions.

    The execution name is derived from the Alert, so a duplicate delivery that somehow got
    past the conditional write still cannot start a second escalation for the same Alert:
    Step Functions rejects a duplicate execution name.
    """
    client = boto3.client("stepfunctions")
    try:
        client.start_execution(
            stateMachineArn=ctx.state_machine_arn,
            name=f"alert-{alert.alert_id}",
            input=json.dumps({"alertId": alert.alert_id}),
        )
    except client.exceptions.ExecutionAlreadyExists:
        return


def is_configured() -> bool:
    return bool(os.environ.get("ICO_TABLE_NAME"))
