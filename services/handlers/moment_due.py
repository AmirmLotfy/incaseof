"""A Moment has come due.

EventBridge Scheduler owns the timer; this is what that timer wakes up. Its whole job is
to open exactly one Alert and hand escalation to the workflow.

Safe to invoke twice. Scheduler delivers at least once, so a duplicate is normal operation
rather than an error, and the conditional write in ``open_for_moment`` is what makes the
second delivery harmless.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

from services.domain.alert import Alert, AlertState
from services.domain.escalation import Ladder, LadderState
from services.domain.ids import AlertId, IdFactory, MomentId, uuid_factory
from services.handlers import bootstrap

log = logging.getLogger(__name__)


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


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    # Its own ARN comes from the invocation context. It cannot be an environment variable:
    # a function referencing its own ARN is a CloudFormation dependency cycle.
    own_arn = getattr(context, "invoked_function_arn", None)
    ctx = bootstrap.build(schedule_target_arn=own_arn)

    moment_id = MomentId(event["momentId"])
    alert, opened = open_alert(ctx, moment_id)

    if alert is None:
        return {"status": "NO_SUCH_MOMENT", "momentId": moment_id}
    if not opened:
        return {"status": "ALREADY_OPEN", "alertId": alert.alert_id}

    # Queue the next occurrence before escalating. A recurring plan that only ever fires
    # once is indistinguishable from a working one until the second night, and by then the
    # person believes they are covered.
    following = _queue_next_occurrence(ctx, moment_id)

    _start_escalation(ctx, alert.alert_id)
    return {
        "status": "OPENED",
        "alertId": alert.alert_id,
        "nextMomentId": following.moment_id if following else None,
    }


def _queue_next_occurrence(ctx: bootstrap.Context, moment_id: MomentId) -> Any:
    """Schedule the next Moment for a recurring plan.

    A one-time plan has no next Moment, which is the plan finishing rather than an error.
    A failure here must not take down the Alert that just opened: the person in front of us
    matters more than tomorrow's check, and the reconciliation sweeper catches a Moment
    that was never scheduled.
    """
    try:
        # Imported inside the guard on purpose. An import error is precisely the failure
        # this protects against: planning pulls in the compiler, which reads a schema file
        # at import time, and a packaging mistake there would otherwise take down the Alert
        # that just opened.
        from services.handlers import planning

        moment = ctx.moments.get(moment_id)
        if moment is None:
            return None
        version = ctx.plans.get_version(moment.version_id)
        if version is None:
            return None

        return planning.schedule_following_moment(ctx, version, after=moment.due_at)
    except Exception:
        log.warning("could not queue the next occurrence for %s", moment_id, exc_info=True)
        return None


def _start_escalation(ctx: bootstrap.Context, alert_id: AlertId) -> None:
    """Hand off to Step Functions.

    ``ctx`` is unused today but kept in the signature: the state-machine ARN belongs on the
    context alongside every other piece of configuration, and reading it from the
    environment here is the outlier.

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
