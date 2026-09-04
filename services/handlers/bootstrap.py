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

from services.adapters.contact import (
    ChannelRouter,
    ContactSender,
    PushSender,
    SafeDemoSender,
    SmsSender,
)
from services.adapters.devices import DeviceRegistry, SnsDeviceRegistry
from services.adapters.dynamo import (
    DynamoActionLog,
    DynamoAlertRepository,
    DynamoAuditLog,
    DynamoCircleRepository,
    DynamoDecisionLog,
    DynamoInvitationRepository,
    DynamoMomentRepository,
    DynamoPlanRepository,
)
from services.adapters.endpoints import DynamoEndpointRepository
from services.adapters.queue import ActionQueue, SqsActionQueue
from services.adapters.scheduling import EventBridgeMomentScheduler, MomentScheduler
from services.domain.clock import REAL_TIME, Clock, SystemClock, TimeScale
from services.domain.plan import Channel
from services.domain.ports import (
    ActionLog,
    AlertRepository,
    AuditLog,
    CircleRepository,
    DecisionLog,
    InvitationRepository,
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
    invitations: InvitationRepository | None = None
    devices: DeviceRegistry | None = None

    def now(self) -> datetime:
        return self.clock.now()

    @property
    def action_queue_url(self) -> str:
        return _required("ICO_ACTION_QUEUE_URL")

    @property
    def state_machine_arn(self) -> str:
        return _required("ICO_STATE_MACHINE_ARN")


def build(*, schedule_target_arn: str | None = None) -> Context:
    """Fresh repositories per invocation, sharing one warm table resource.

    The Alert repository tracks the revision it last read in order to write conditionally,
    so it must not be reused across invocations — a stale revision from a previous request
    would either reject a valid write or, worse, be refreshed and hide a real conflict.
    """
    table = _table()
    scale_factor = float(os.environ.get("ICO_TIME_SCALE", "1.0"))
    endpoints = _endpoints(table)
    return Context(
        plans=DynamoPlanRepository(table),
        moments=DynamoMomentRepository(table),
        alerts=DynamoAlertRepository(table),
        circles=DynamoCircleRepository(table),
        actions=DynamoActionLog(table),
        audit=DynamoAuditLog(table),
        clock=SystemClock(),
        scale=TimeScale(scale_factor) if scale_factor != 1.0 else REAL_TIME,
        scheduler=_scheduler(schedule_target_arn),
        queue=_queue(),
        sender=_sender(table),
        signing_key=_signing_key(),
        decisions=DynamoDecisionLog(table),
        invitations=DynamoInvitationRepository(table),
        devices=_devices(endpoints),
    )


def _endpoints(table: Any) -> DynamoEndpointRepository | None:
    key_id = os.environ.get("ICO_KMS_KEY_ID")
    if not key_id:
        return None
    return DynamoEndpointRepository(table=table, kms=boto3.client("kms"), key_id=key_id)


def _devices(endpoints: DynamoEndpointRepository | None) -> DeviceRegistry | None:
    platform_arn = os.environ.get("ICO_PUSH_PLATFORM_ARN")
    if endpoints is None or not platform_arn:
        return None
    return SnsDeviceRegistry(
        sns=boto3.client("sns"),
        endpoints=endpoints,
        platform_application_arn=platform_arn,
    )


def _sender(table: Any) -> ContactSender | None:
    """Delivery, on whichever channels are actually configured.

    Absent altogether means the worker records CHANNEL_UNAVAILABLE rather than pretending
    to send — visible in the timeline instead of silent. A channel missing from the router
    reports the same way, so "push is not wired here" and "the text failed" stay distinct
    facts for whoever reads the timeline at 2am.
    """
    delivery_mode = os.environ.get("ICO_DELIVERY_MODE")
    if delivery_mode:
        if delivery_mode != "SAFE_SINK" or os.environ.get("ICO_ENV") != "demo":
            raise RuntimeError("ICO_DELIVERY_MODE is permitted only as SAFE_SINK in demo")
        return SafeDemoSender()

    endpoints = _endpoints(table)
    if endpoints is None:
        return None

    sns = boto3.client("sns")

    senders: dict[Channel, Any] = {
        Channel.SMS: SmsSender(
            sns=sns,
            endpoints=endpoints,
            sender_id=os.environ.get("ICO_SMS_SENDER_ID") or None,
        )
    }
    if os.environ.get("ICO_PUSH_PLATFORM_ARN"):
        # Push is bound only when a platform application exists. Without Firebase
        # credentials there is nothing to publish to, and claiming otherwise would put a
        # rung in the ladder that silently does nothing.
        senders[Channel.PUSH] = PushSender(sns=sns, endpoints=endpoints)

    return ChannelRouter(senders=senders)


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


def _scheduler(target_arn: str | None = None) -> MomentScheduler | None:
    """EventBridge Scheduler, when this environment has one.

    ``target_arn`` lets a caller supply the function to wake. MomentDue passes its own ARN
    from the Lambda context, because a function cannot be given its own ARN as an
    environment variable without creating a CloudFormation dependency cycle.
    """
    group = os.environ.get("ICO_SCHEDULE_GROUP")
    target = target_arn or os.environ.get("ICO_MOMENT_DUE_ARN")
    role = os.environ.get("ICO_SCHEDULER_ROLE_ARN")
    if not (group and target and role):
        return None
    return EventBridgeMomentScheduler(
        client=boto3.client("scheduler"),
        group_name=group,
        target_arn=target,
        role_arn=role,
    )
