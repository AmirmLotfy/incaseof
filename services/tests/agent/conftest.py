"""Fixtures for agent tests.

The gateway is built over the same in-memory adapters the slice uses, so a denial proven
here is a denial the real policy layer produces.
"""

from __future__ import annotations

from typing import Any

import pytest

from services.adapters.memory import (
    InMemoryActionLog,
    InMemoryAlertRepository,
    InMemoryAuditLog,
    InMemoryCircleRepository,
    InMemoryDecisionLog,
    InMemoryMomentRepository,
    InMemoryPlanRepository,
)
from services.agent.gateway import Gateway
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    MemberStatus,
)
from services.domain.clock import REAL_TIME, FixedClock, utc
from services.domain.ids import (
    CircleId,
    ConsentId,
    MembershipId,
    PersonId,
    PlanId,
    SequentialIds,
)
from services.domain.plan import Plan, ResponderRole
from services.handlers import bootstrap
from services.tests.domain.conftest import DUE_AT, in_circle_escalation, make_version

MONA = PersonId("person-mona")
MAYA = PersonId("person-maya")
CIRCLE = CircleId("circle-1")
PLAN = PlanId("plan-1")


def gateway_for(
    *,
    subject: PersonId = MONA,
    with_alert: bool = False,
    consent: bool = True,
) -> Gateway:
    clock = FixedClock(DUE_AT)
    plans = InMemoryPlanRepository()
    circles = InMemoryCircleRepository()
    alerts = InMemoryAlertRepository()

    version = make_version()
    plans.save_version(version)
    plans.save_plan(
        Plan(
            plan_id=PLAN,
            subject_person_id=MONA,
            circle_id=CIRCLE,
            plan_type=version.plan_type,
            active_version_id=version.version_id,
        )
    )

    circles.save_circle(
        Circle(
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
            ),
        )
    )
    if consent:
        circles.save_consent(
            ConsentGrant(
                consent_id=ConsentId("c-maya"),
                subject_person_id=MONA,
                responder_person_id=MAYA,
                plan_id=PLAN,
                status=ConsentStatus.ACTIVE,
                accepted_at=utc(2026, 7, 1),
            )
        )

    if with_alert:
        alerts.open_for_moment(in_circle_escalation(version))

    ctx = bootstrap.Context(
        plans=plans,
        moments=InMemoryMomentRepository(),
        alerts=alerts,
        circles=circles,
        actions=InMemoryActionLog(),
        audit=InMemoryAuditLog(),
        clock=clock,
        scale=REAL_TIME,
        decisions=InMemoryDecisionLog(),
    )
    return Gateway(
        ctx=ctx,
        subject_person_id=subject,
        circle_id=CIRCLE,
        new_id=SequentialIds("d"),
    )


@pytest.fixture
def gateway() -> Gateway:
    return gateway_for(with_alert=True)


class StubAgent:
    """An agent whose model returns whatever a test says, or raises."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[type, str]] = []

    def structured_output(self, output_model: type, prompt: Any = None) -> Any:
        self.calls.append((output_model, str(prompt)))
        if self.error is not None:
            raise self.error
        return self.result
