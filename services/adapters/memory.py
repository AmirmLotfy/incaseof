"""In-memory adapters.

Not mocks. These implement the same conditional semantics as the DynamoDB adapters in
Phase 2, so an invariant proven here is proven about the rules rather than about a stub.
Used by tests and by the local vertical slice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from services.domain.alert import Alert
from services.domain.circle import Circle, ConsentGrant
from services.domain.idempotency import IdempotencyKey
from services.domain.ids import (
    AlertId,
    CircleId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
)
from services.domain.moment import ExpectedMoment, MomentStatus
from services.domain.plan import Plan, PlanVersion


@dataclass
class InMemoryPlanRepository:
    plans: dict[PlanId, Plan] = field(default_factory=dict)
    versions: dict[PlanVersionId, PlanVersion] = field(default_factory=dict)

    def get_plan(self, plan_id: PlanId) -> Plan | None:
        return self.plans.get(plan_id)

    def get_version(self, version_id: PlanVersionId) -> PlanVersion | None:
        return self.versions.get(version_id)

    def save_version(self, version: PlanVersion) -> None:
        if version.version_id in self.versions:
            raise ValueError(
                f"version {version.version_id} already exists; versions are immutable. "
                f"Editing a plan creates a new version so live Alerts keep the old one."
            )
        self.versions[version.version_id] = version

    def activate(self, plan_id: PlanId, version_id: PlanVersionId, at: datetime) -> Plan:
        plan = self.plans[plan_id]
        version = self.versions[version_id]
        self.versions[version_id] = replace(version, activated_at=at)
        activated = replace(plan, active_version_id=version_id, paused=False)
        self.plans[plan_id] = activated
        return activated


@dataclass
class InMemoryMomentRepository:
    moments: dict[MomentId, ExpectedMoment] = field(default_factory=dict)

    def get(self, moment_id: MomentId) -> ExpectedMoment | None:
        return self.moments.get(moment_id)

    def save(self, moment: ExpectedMoment) -> None:
        self.moments[moment.moment_id] = moment

    def due_before(self, instant: datetime) -> tuple[ExpectedMoment, ...]:
        return tuple(
            m
            for m in sorted(self.moments.values(), key=lambda m: m.due_at)
            if m.due_at <= instant and m.status in {MomentStatus.SCHEDULED, MomentStatus.DUE}
        )


@dataclass
class InMemoryAlertRepository:
    alerts: dict[AlertId, Alert] = field(default_factory=dict)
    _by_moment: dict[MomentId, AlertId] = field(default_factory=dict)

    def get(self, alert_id: AlertId) -> Alert | None:
        return self.alerts.get(alert_id)

    def save(self, alert: Alert) -> None:
        self.alerts[alert.alert_id] = alert

    def alert_for_moment(self, moment_id: MomentId) -> Alert | None:
        existing_id = self._by_moment.get(moment_id)
        return self.alerts.get(existing_id) if existing_id else None

    def open_for_moment(self, alert: Alert) -> Alert:
        """Conditional insert keyed on the Moment. Invariant 1."""
        existing_id = self._by_moment.get(alert.moment_id)
        if existing_id is not None:
            return self.alerts[existing_id]
        self._by_moment[alert.moment_id] = alert.alert_id
        self.alerts[alert.alert_id] = alert
        return alert


@dataclass
class InMemoryCircleRepository:
    circles: dict[CircleId, Circle] = field(default_factory=dict)
    consents: dict[PlanId, dict[PersonId, ConsentGrant]] = field(default_factory=dict)

    def get(self, circle_id: CircleId) -> Circle | None:
        return self.circles.get(circle_id)

    def consents_for(self, plan_id: PlanId) -> dict[PersonId, ConsentGrant]:
        return dict(self.consents.get(plan_id, {}))


@dataclass
class InMemoryActionLog:
    """Reserved idempotency keys.

    ``claim_key`` is atomic here because the interpreter is; in DynamoDB it is a
    conditional write. Both answer the same question: did I win the right to send this?
    """

    claimed: set[str] = field(default_factory=set)

    def claim_key(self, key: IdempotencyKey) -> bool:
        if key.value in self.claimed:
            return False
        self.claimed.add(key.value)
        return True

    def was_dispatched(self, key: IdempotencyKey) -> bool:
        return key.value in self.claimed


@dataclass
class InMemoryAuditLog:
    events: list[dict[str, object]] = field(default_factory=list)

    def append(
        self,
        *,
        alert_id: AlertId,
        actor_type: str,
        actor_id: str,
        event_type: str,
        at: datetime,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.events.append(
            {
                "alert_id": alert_id,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "event_type": event_type,
                "at": at,
                "metadata": metadata or {},
            }
        )

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]:
        return tuple(e for e in self.events if e["alert_id"] == alert_id)
