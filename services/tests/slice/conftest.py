"""A driver for the whole vertical slice.

Everything here except the driver itself is production code. The domain, the adapters, the
handlers, the policy layer and the state machine are the same objects a deployed Lambda
uses. What the driver replaces is the three AWS services that only exist to move time and
messages around:

* **EventBridge Scheduler** -> ``fire_moment`` calls the same handler the timer would.
* **Step Functions** -> ``run_workflow`` loops decide/dispatch and advances the clock on a
  WAIT, which is exactly what the state machine does.
* **SQS** -> an in-memory queue the driver drains into the real worker, with the ability to
  replay a message so at-least-once delivery can be reproduced.

DynamoDB is not replaced at all -- moto speaks its real semantics, including the conditional
writes the invariants depend on.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import boto3
import pytest
from moto import mock_aws

from services.adapters import keys
from services.adapters.contact import RecordingSender
from services.adapters.dynamo import (
    DynamoActionLog,
    DynamoAlertRepository,
    DynamoAuditLog,
    DynamoCircleRepository,
    DynamoMomentRepository,
    DynamoPlanRepository,
)
from services.adapters.queue import InMemoryActionQueue
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    ContactChannelPermission,
    MemberStatus,
)
from services.domain.clock import REAL_TIME, FixedClock, TimeScale, utc
from services.domain.ids import (
    AlertId,
    CircleId,
    ConsentId,
    MembershipId,
    MomentId,
    PersonId,
    PlanId,
    SequentialIds,
)
from services.domain.plan import ResponderRole
from services.handlers import action_worker, bootstrap, escalation, moment_due, planning

SIGNING_KEY = b"slice-test-signing-key-not-a-real-secret"
START = utc(2026, 8, 26, 18, 0)

MONA = PersonId("person-mona")
MAYA = PersonId("person-maya")
OMAR = PersonId("person-omar")
CIRCLE = CircleId("circle-1")

# The evening ladder from the build contract §60, in P0 channels only.
EVENING_PLAN: dict[str, Any] = {
    "type": "ROUTINE",
    "label": "Evening check",
    "timezone": "Europe/Amsterdam",
    "trigger": {"kind": "RECURRING", "timeOfDay": "21:00"},
    "grace": {"seconds": 600},
    "steps": [
        {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
        {"sequence": 2, "offsetSeconds": 600, "action": "PUSH_SUBJECT"},
        {"sequence": 3, "offsetSeconds": 1200, "action": "SMS_SUBJECT"},
        {
            "sequence": 4,
            "offsetSeconds": 1500,
            "action": "MESSAGE_RESPONDER",
            "targetRole": "PRIMARY",
        },
        {
            "sequence": 5,
            "offsetSeconds": 2700,
            "action": "MESSAGE_RESPONDER",
            "targetRole": "BACKUP",
        },
    ],
    "stopConditions": ["SUBJECT_EXPLICIT_CONFIRMATION", "RESPONDER_VERIFIED_CONTACT"],
    "contextPolicy": {"location": "NEVER", "battery": "AFTER_SUBJECT_CALL_FAILED"},
    "leaseSeconds": 600,
}


@dataclass
class Slice:
    """The system, driven end to end."""

    ctx: bootstrap.Context
    clock: FixedClock
    queue: InMemoryActionQueue
    sender: RecordingSender
    ids: SequentialIds
    plan_id: PlanId | None = None
    moment_id: MomentId | None = None
    alert_id: AlertId | None = None
    workflow_steps: int = field(default=0)

    # -- time -------------------------------------------------------------

    def advance(self, seconds: float) -> datetime:
        return self.clock.advance(seconds)

    # -- setting up -------------------------------------------------------

    def given_a_circle(self, *, consent_for: tuple[PersonId, ...] = (MAYA, OMAR)) -> Circle:
        circle = Circle(
            circle_id=CIRCLE,
            owner_person_id=MONA,
            owner_display_name="Mona",
            members=(
                CircleMember(
                    membership_id=MembershipId("m-maya"),
                    circle_id=CIRCLE,
                    person_id=MAYA,
                    role=ResponderRole.PRIMARY,
                    priority=1,
                    status=MemberStatus.ACCEPTED,
                    display_name="Maya",
                    relationship="Sister",
                ),
                CircleMember(
                    membership_id=MembershipId("m-omar"),
                    circle_id=CIRCLE,
                    person_id=OMAR,
                    role=ResponderRole.BACKUP,
                    priority=1,
                    status=MemberStatus.ACCEPTED,
                    display_name="Omar",
                    relationship="Friend",
                ),
            ),
        )
        self.ctx.circles.save_circle(circle)
        return circle

    def given_consent(self, plan_id: PlanId, *people: PersonId) -> None:
        for person in people:
            self.ctx.circles.save_consent(
                ConsentGrant(
                    consent_id=ConsentId(f"c-{person}"),
                    subject_person_id=MONA,
                    responder_person_id=person,
                    plan_id=plan_id,
                    status=ConsentStatus.ACTIVE,
                    accepted_at=START - timedelta(days=30),
                    channels=frozenset(
                        {ContactChannelPermission.PUSH, ContactChannelPermission.SMS}
                    ),
                )
            )

    def create_plan(self, document: dict[str, Any] | None = None) -> planning.Activation:
        """Create, then activate. Two steps, because that is how the product works."""
        circle = self.given_a_circle()
        plan, result = planning.create_plan(
            self.ctx,
            document or EVENING_PLAN,
            subject_person_id=MONA,
            circle_id=circle.circle_id,
            new_id=self.ids,
        )
        self.plan_id = plan.plan_id
        self.given_consent(plan.plan_id, MAYA, OMAR)

        activation = planning.activate_plan(
            self.ctx,
            plan.plan_id,
            result.version.version_id,
            now=self.clock.now(),
            new_id=self.ids,
        )
        self.moment_id = activation.moment.moment_id
        return activation

    # -- playing AWS ------------------------------------------------------

    def fire_moment(self) -> AlertId | None:
        """What EventBridge Scheduler does when the timer goes off."""
        assert self.moment_id is not None
        alert, _ = moment_due.open_alert(self.ctx, self.moment_id, new_id=self.ids)
        if alert is not None:
            self.alert_id = alert.alert_id
        return self.alert_id

    def run_workflow(
        self,
        *,
        max_steps: int = 40,
        stop_after_wait: bool = False,
        until: Callable[[], bool] | None = None,
    ) -> str:
        """What Step Functions does: decide, act or wait, decide again.

        A WAIT advances the clock by exactly the seconds the domain asked for, which is the
        behaviour that makes ladder timing testable in milliseconds instead of in minutes.
        """
        assert self.alert_id is not None
        for _ in range(max_steps):
            if until is not None and until():
                return "REACHED"
            self.workflow_steps += 1
            decision = escalation.decide(self.ctx, self.alert_id)

            if decision["decision"] == escalation.TERMINAL:
                return str(decision.get("reason", "TERMINAL"))

            if decision["decision"] == escalation.DISPATCH:
                escalation.dispatch(self.ctx, self.alert_id, decision["sequences"])
                self.deliver_queued()
                continue

            if stop_after_wait:
                return "WAITING"
            self.advance(float(decision["seconds"]))

        raise AssertionError(f"workflow did not settle within {max_steps} steps")

    def deliver_queued(self, *, replay: bool = False) -> None:
        """What SQS does: hand each message to the worker.

        ``replay`` re-delivers everything a second time, reproducing at-least-once delivery.
        """
        pending = self.queue.drain()
        for intent in pending:
            action_worker.deliver(self.ctx, intent)
        if replay:
            for intent in pending:
                action_worker.deliver(self.ctx, intent)

    # -- inspecting -------------------------------------------------------

    @property
    def alert(self) -> Any:
        assert self.alert_id is not None
        return self.ctx.alerts.get(self.alert_id)

    def timeline(self) -> list[str]:
        assert self.alert_id is not None
        return [str(event.get("eventType")) for event in self.ctx.audit.for_alert(self.alert_id)]

    def link_for(self, person: PersonId) -> str:
        """The responder link that was actually sent to this person."""
        name = {MAYA: "Maya", OMAR: "Omar"}[person]
        messages = self.sender.to(name)
        assert messages, f"nothing was sent to {name}"
        link = messages[-1]["link"]
        assert isinstance(link, str), f"no link in the message to {name}"
        return link.rsplit("/r/", 1)[1]


@pytest.fixture
def a_slice() -> Iterator[Slice]:
    previous = dict(os.environ)
    os.environ.update(
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SESSION_TOKEN": "testing",
            "AWS_DEFAULT_REGION": "us-east-1",
        }
    )
    try:
        with mock_aws():
            resource = boto3.resource("dynamodb", region_name="us-east-1")
            table = resource.create_table(
                TableName="ico-slice",
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": keys.GSI1_PK, "AttributeType": "S"},
                    {"AttributeName": keys.GSI1_SK, "AttributeType": "S"},
                    {"AttributeName": keys.GSI2_PK, "AttributeType": "S"},
                    {"AttributeName": keys.GSI2_SK, "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": keys.GSI1,
                        "KeySchema": [
                            {"AttributeName": keys.GSI1_PK, "KeyType": "HASH"},
                            {"AttributeName": keys.GSI1_SK, "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": keys.GSI2,
                        "KeySchema": [
                            {"AttributeName": keys.GSI2_PK, "KeyType": "HASH"},
                            {"AttributeName": keys.GSI2_SK, "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            clock = FixedClock(START)
            queue = InMemoryActionQueue()
            sender = RecordingSender()
            ctx = bootstrap.Context(
                plans=DynamoPlanRepository(table),
                moments=DynamoMomentRepository(table),
                alerts=DynamoAlertRepository(table),
                circles=DynamoCircleRepository(table),
                actions=DynamoActionLog(table),
                audit=DynamoAuditLog(table),
                clock=clock,
                scale=REAL_TIME,
                scheduler=None,
                queue=queue,
                sender=sender,
                signing_key=SIGNING_KEY,
            )
            yield Slice(
                ctx=ctx,
                clock=clock,
                queue=queue,
                sender=sender,
                ids=SequentialIds("x"),
            )
    finally:
        os.environ.clear()
        os.environ.update(previous)


@pytest.fixture
def compressed_slice(a_slice: Slice) -> Slice:
    """The same system on a demo clock. See docs/DEMO.md."""
    a_slice.ctx = bootstrap.Context(**{**a_slice.ctx.__dict__, "scale": TimeScale(0.02)})
    return a_slice
