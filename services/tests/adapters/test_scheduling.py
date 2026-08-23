"""Scheduler adapter tests.

The timer is the single most important piece of infrastructure in this product: if it does
not fire, nobody notices that nobody noticed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import boto3
import pytest
from moto import mock_aws

from services.adapters.scheduling import EventBridgeMomentScheduler, schedule_name
from services.domain.clock import utc
from services.domain.ids import MomentId, PlanVersionId
from services.domain.moment import moment_for

GROUP = "ico-moments-test"
TARGET = "arn:aws:lambda:us-east-1:123456789012:function:MomentDue"
ROLE = "arn:aws:iam::123456789012:role/SchedulerRole"


@pytest.fixture
def scheduler() -> Iterator[EventBridgeMomentScheduler]:
    with mock_aws():
        client: Any = boto3.client("scheduler", region_name="us-east-1")
        client.create_schedule_group(Name=GROUP)
        yield EventBridgeMomentScheduler(
            client=client, group_name=GROUP, target_arn=TARGET, role_arn=ROLE
        )


def moment(moment_id: str = "moment-1") -> Any:
    return moment_for(
        moment_id=MomentId(moment_id),
        version_id=PlanVersionId("pv-4"),
        due_at=utc(2026, 8, 26, 21, 0),
        grace_seconds=600,
    )


def test_scheduling_a_moment_creates_a_one_shot_timer(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    name = scheduler.schedule(moment())

    described = scheduler.client.get_schedule(Name=name, GroupName=GROUP)
    assert described["ScheduleExpression"] == "at(2026-08-26T21:00:00)"
    assert described["ScheduleExpressionTimezone"] == "UTC"
    assert described["Target"]["Arn"] == TARGET


def test_the_timer_fires_at_the_due_time_not_the_end_of_grace(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    """Grace is a domain rule the workflow applies on waking.

    Baking it into the timer would move a safety rule somewhere no unit test can reach.
    """
    name = scheduler.schedule(moment())
    described = scheduler.client.get_schedule(Name=name, GroupName=GROUP)
    assert "21:00:00" in described["ScheduleExpression"], "should be due_at, not grace_until"


def test_rescheduling_the_same_moment_does_not_create_a_second_timer(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    """Two timers for one Moment would contact somebody twice."""
    scheduler.schedule(moment())
    scheduler.schedule(moment())

    listed = scheduler.client.list_schedules(GroupName=GROUP)["Schedules"]
    assert len(listed) == 1


def test_rescheduling_moves_the_timer_when_a_moment_is_extended(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    """ "Give me another 30 minutes" has to move the timer, not just the record."""
    scheduler.schedule(moment())

    extended = moment_for(
        moment_id=MomentId("moment-1"),
        version_id=PlanVersionId("pv-4"),
        due_at=utc(2026, 8, 26, 21, 30),
        grace_seconds=600,
    )
    name = scheduler.schedule(extended)

    described = scheduler.client.get_schedule(Name=name, GroupName=GROUP)
    assert described["ScheduleExpression"] == "at(2026-08-26T21:30:00)"


def test_cancelling_removes_the_timer(scheduler: EventBridgeMomentScheduler) -> None:
    scheduler.schedule(moment())
    scheduler.cancel(MomentId("moment-1"))

    assert scheduler.client.list_schedules(GroupName=GROUP)["Schedules"] == []


def test_cancelling_a_timer_that_already_fired_is_not_an_error(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    """Schedules delete themselves after firing, so cancel routinely finds nothing."""
    scheduler.cancel(MomentId("moment-never-existed"))


def test_the_schedule_name_is_derived_from_the_moment(
    scheduler: EventBridgeMomentScheduler,
) -> None:
    """Derived rather than generated: that is what makes creation idempotent."""
    assert schedule_name(MomentId("moment-1")) == "moment-moment-1"
    assert schedule_name(MomentId("moment-1")) == schedule_name(MomentId("moment-1"))


def test_the_timer_carries_only_a_moment_id(scheduler: EventBridgeMomentScheduler) -> None:
    """No contact endpoint, no plan detail, nothing about who is alone.

    Scheduler payloads are visible to anyone who can describe a schedule.
    """
    import json

    name = scheduler.schedule(moment())
    described = scheduler.client.get_schedule(Name=name, GroupName=GROUP)
    payload = json.loads(described["Target"]["Input"])

    assert payload == {"momentId": "moment-1"}


def test_a_failed_delivery_is_retried_hard(scheduler: EventBridgeMomentScheduler) -> None:
    """A Moment that never opens an Alert is the one failure the product cannot absorb."""
    name = scheduler.schedule(moment())
    retry = scheduler.client.get_schedule(Name=name, GroupName=GROUP)["Target"]["RetryPolicy"]

    assert retry["MaximumRetryAttempts"] >= 3
    assert retry["MaximumEventAgeInSeconds"] >= 900
