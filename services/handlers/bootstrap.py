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
from functools import lru_cache
from typing import Any

import boto3

from services.adapters.dynamo import (
    DynamoActionLog,
    DynamoAlertRepository,
    DynamoAuditLog,
    DynamoCircleRepository,
    DynamoMomentRepository,
    DynamoPlanRepository,
)
from services.domain.clock import REAL_TIME, SystemClock, TimeScale


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

    plans: DynamoPlanRepository
    moments: DynamoMomentRepository
    alerts: DynamoAlertRepository
    circles: DynamoCircleRepository
    actions: DynamoActionLog
    audit: DynamoAuditLog
    clock: SystemClock
    scale: TimeScale

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
    )
