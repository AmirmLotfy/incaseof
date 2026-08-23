"""Wiring.

Handlers get their repositories from here so that a Lambda's entry point stays a thin
translation between an AWS event and a domain call. Nothing in this module makes a
decision; it only constructs.

Resources are built once per container and reused across invocations, which is the
difference between a warm handler doing one DynamoDB call and doing three.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any

import boto3

from services.adapters.contact import ContactSender
from services.adapters.dynamo import (
    DynamoActionLog,
    DynamoAlertRepository,
    DynamoAuditLog,
    DynamoCircleRepository,
    DynamoDecisionLog,
    DynamoMomentRepository,
    DynamoPlanRepository,
)
from services.adapters.queue import ActionQueue, SqsActionQueue
from services.adapters.scheduling import EventBridgeMomentScheduler, MomentScheduler
from services.domain.clock import REAL_TIME, Clock, SystemClock, TimeScale
from services.domain.ports import (
    ActionLog,
    AlertRepository,
    AuditLog,
    CircleRepository,
    DecisionLog,
    MomentRepository,
    PlanRepository,
)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Handlers fail fast on missing configuration rather than "
            f"defaulting, because a safety workflow silently pointed at the wrong table is "
            f"worse than one that does not start."
        )
    return value


@lru_cache(maxsize=1)
def _table() -> Any:
    return boto3.resource("dynamodb").Table(_required("ICO_TABLE_NAME"))


@dataclass(frozen=True)
class Context:
    """Everything a handler needs, constructed once."""

    # Declared as ports, never as the DynamoDB adapters. Naming the concrete type here
    # would make the in-memory adapters unusable by anything type-checked, which is the
    # opposite of why the ports exist — an invariant proven against one implementation is
    # only meaningful if both satisfy the same contract.
    plans: PlanRepository
    moments: MomentRepository
    alerts: AlertRepository
    circles: CircleRepository
    actions: ActionLog
    audit: AuditLog
    clock: Clock
    scale: TimeScale
    # Optional so the slice can be driven without AWS. When absent, the caller supplies
    # the equivalent — which is exactly what the end-to-end test does, playing the parts
    # of EventBridge, SQS and Step Functions while every other line of code is the real one.
    scheduler: MomentScheduler | None = None
    queue: ActionQueue | None = None
    sender: ContactSender | None = None
    decisions: DecisionLog | None = None
    signing_key: bytes = b""

    def now(self) -> datetime:
        return self.clock.now()

    @property
    def action_queue_url(self) -> str:
        return _required("ICO_ACTION_QUEUE_URL")

    @property
    def state_machine_arn(self) -> str:
        return _required("ICO_STATE_MACHINE_ARN")


def build() -> Context:
    """Fresh repositories per invocation, sharing one warm table resource.

    The Alert repository tracks the revision it last read in order to write conditionally,
    so it must not be reused across invocations — a stale revision from a previous request
    would either reject a valid write or, worse, be refreshed and hide a real conflict.
    """
    table = _table()
    scale_factor = float(os.environ.get("ICO_TIME_SCALE", "1.0"))
    return Context(
        plans=DynamoPlanRepository(table),
        moments=DynamoMomentRepository(table),
        alerts=DynamoAlertRepository(table),
        circles=DynamoCircleRepository(table),
        actions=DynamoActionLog(table),
        audit=DynamoAuditLog(table),
        clock=SystemClock(),
        scale=TimeScale(scale_factor) if scale_factor != 1.0 else REAL_TIME,
        scheduler=_scheduler(),
        queue=_queue(),
        signing_key=_signing_key(),
        decisions=DynamoDecisionLog(table),
    )


def _queue() -> ActionQueue | None:
    """The action queue, when this function is one that dispatches.

    The API handler never enqueues, so requiring the queue URL everywhere made it fail to
    start on a variable it does not use. Absent here is fine; ``escalation.dispatch``
    refuses to run without one rather than silently marking rungs attempted.
    """
    url = os.environ.get("ICO_ACTION_QUEUE_URL")
    return SqsActionQueue(client=boto3.client("sqs"), queue_url=url) if url else None


@lru_cache(maxsize=1)
def _signing_key() -> bytes:
    """The responder-token signing key, from Secrets Manager.

    Cached per container: this is on the path of every responder link open, and fetching
    a secret per request would add a round trip to somebody's 2am tap.

    Returning empty is safe here only because the token module refuses to sign or verify
    with a short key — an empty HMAC key produces perfectly valid-looking signatures that
    anybody could forge.
    """
    arn = os.environ.get("ICO_RESPONDER_KEY_SECRET_ARN")
    if not arn:
        return b""
    value = boto3.client("secretsmanager").get_secret_value(SecretId=arn)
    secret = value.get("SecretString") or ""
    return secret.encode()


def _scheduler() -> MomentScheduler | None:
    """EventBridge Scheduler, when this environment has one."""
    group = os.environ.get("ICO_SCHEDULE_GROUP")
    target = os.environ.get("ICO_MOMENT_DUE_ARN")
    role = os.environ.get("ICO_SCHEDULER_ROLE_ARN")
    if not (group and target and role):
        return None
    return EventBridgeMomentScheduler(
        client=boto3.client("scheduler"),
        group_name=group,
        target_arn=target,
        role_arn=role,
    )
