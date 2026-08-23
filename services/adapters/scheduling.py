"""EventBridge Scheduler.

**Every safety timer lives here.** Not on the phone, not in WorkManager, not in a sleeping
Lambda, and not in a Step Functions Wait inside an execution that was already killed. A
device-owned timer does not fire when the device is off, which is exactly the case this
product exists for.

One one-shot schedule per Moment. Schedules delete themselves after firing, so the group
holds only outstanding expectations and does not accumulate a year of history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Any, Protocol

from botocore.exceptions import ClientError

from services.domain.ids import MomentId
from services.domain.moment import ExpectedMoment

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_scheduler.client import EventBridgeSchedulerClient
else:
    EventBridgeSchedulerClient = Any

CONFLICT = "ConflictException"
NOT_FOUND = "ResourceNotFoundException"


class MomentScheduler(Protocol):
    """The port. Phase 1 domain never touches this; workflows do."""

    def schedule(self, moment: ExpectedMoment) -> str: ...

    def cancel(self, moment_id: MomentId) -> None: ...


def schedule_name(moment_id: MomentId) -> str:
    """Derived, never generated.

    A derived name makes creation idempotent: re-scheduling the same Moment collides with
    itself rather than producing a second timer that would fire a duplicate.
    """
    return f"moment-{moment_id}"


@dataclass
class EventBridgeMomentScheduler:
    client: EventBridgeSchedulerClient
    group_name: str
    target_arn: str
    role_arn: str

    def schedule(self, moment: ExpectedMoment) -> str:
        """Create the timer for one Moment. Safe to call again.

        The schedule fires at the *due* time, not at the end of grace. Grace is a domain
        concept the workflow applies once it wakes up; encoding it in the timer would put
        a safety rule somewhere no test can reach it.
        """
        name = schedule_name(moment.moment_id)
        # Scheduler wants a naive local time plus an explicit timezone. Everything stored
        # is UTC, so it is passed as UTC rather than converted to the plan's zone.
        at = moment.due_at.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds")

        request: dict[str, Any] = {
            "Name": name,
            "GroupName": self.group_name,
            "ScheduleExpression": f"at({at})",
            "ScheduleExpressionTimezone": "UTC",
            "FlexibleTimeWindow": {"Mode": "OFF"},
            # Self-cleaning: a fired schedule is history, and history belongs in the audit
            # trail rather than in the scheduler.
            "ActionAfterCompletion": "DELETE",
            "Target": {
                "Arn": self.target_arn,
                "RoleArn": self.role_arn,
                "Input": json.dumps({"momentId": moment.moment_id}),
                "RetryPolicy": {
                    # A Moment that fails to open an Alert is the one failure this product
                    # cannot absorb, so retry hard and for a long time.
                    "MaximumRetryAttempts": 5,
                    "MaximumEventAgeInSeconds": 3600,
                },
            },
        }

        try:
            self.client.create_schedule(**request)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != CONFLICT:
                raise
            # Already scheduled. Update rather than leave a stale time in place: an
            # extension moves the Moment, and the timer has to move with it.
            self.client.update_schedule(**request)
        return name

    def cancel(self, moment_id: MomentId) -> None:
        """Remove a timer for a Moment that resolved or was cancelled.

        A missing schedule is success, not an error: it usually means the Moment already
        fired and the schedule deleted itself.
        """
        try:
            self.client.delete_schedule(Name=schedule_name(moment_id), GroupName=self.group_name)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != NOT_FOUND:
                raise
