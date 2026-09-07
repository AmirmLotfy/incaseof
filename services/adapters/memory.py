"""In-memory adapters.

Not mocks. These implement the same conditional semantics as the DynamoDB adapters in
Phase 2, so an invariant proven here is proven about the rules rather than about a stub.
Used by tests and by the local vertical slice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from services.domain.account import Profile
from services.domain.agent_decision import AgentDecision
from services.domain.alert import Alert
from services.domain.circle import Circle, ConsentGrant
from services.domain.idempotency import IdempotencyKey
from services.domain.ids import (
    AlertId,
    CircleId,
    InvitationId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
)
from services.domain.invitation import CircleInvitation
from services.domain.moment import ExpectedMoment, MomentStatus
from services.domain.plan import Plan, PlanVersion


@dataclass
class InMemoryProfileRepository:
    profiles: dict[PersonId, Profile] = field(default_factory=dict)

    def get(self, person_id: PersonId) -> Profile | None:
        return self.profiles.get(person_id)

    def save(self, profile: Profile) -> None:
        self.profiles[profile.person_id] = profile


@dataclass
class InMemoryPlanRepository:
    plans: dict[PlanId, Plan] = field(default_factory=dict)
    versions: dict[PlanVersionId, PlanVersion] = field(default_factory=dict)

    def get_plan(self, plan_id: PlanId) -> Plan | None:
        return self.plans.get(plan_id)

    def save_plan(self, plan: Plan) -> None:
        self.plans[plan.plan_id] = plan

    def get_version(self, version_id: PlanVersionId) -> PlanVersion | None:
        return self.versions.get(version_id)

    def latest_version(self, plan_id: PlanId) -> PlanVersion | None:
        candidates = (version for version in self.versions.values() if version.plan_id == plan_id)
        return max(candidates, key=lambda version: version.version_number, default=None)

    def save_version(self, version: PlanVersion) -> None:
        if version.version_id in self.versions:
            raise ValueError(
                f"version {version.version_id} already exists; versions are immutable. "
                f"Editing a plan creates a new version so live Alerts keep the old one."
            )
        self.versions[version.version_id] = version

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Plan, ...]:
        return tuple(
            sorted(
                (p for p in self.plans.values() if p.subject_person_id == subject_person_id),
                key=lambda p: str(p.plan_id),
            )
        )

    def activate(
        self,
        plan_id: PlanId,
        version_id: PlanVersionId,
        at: datetime,
        bindings: dict[str, str] | None = None,
    ) -> Plan:
        plan = self.plans[plan_id]
        version = self.versions[version_id]
        self.versions[version_id] = replace(
            version,
            activated_at=version.activated_at or at,
            responder_bindings=version.responder_bindings
            if version.activated_at
            else (bindings or {}),
        )
        activated = replace(plan, active_version_id=version_id, paused=False)
        self.plans[plan_id] = activated
        return activated


@dataclass
class InMemoryMomentRepository:
    moments: dict[MomentId, ExpectedMoment] = field(default_factory=dict)
    owners: dict[MomentId, PersonId] = field(default_factory=dict)

    def get(self, moment_id: MomentId) -> ExpectedMoment | None:
        return self.moments.get(moment_id)

    def save(
        self,
        moment: ExpectedMoment,
        *,
        subject_person_id: PersonId | None = None,
    ) -> None:
        self.moments[moment.moment_id] = moment
        if subject_person_id is not None:
            self.owners[moment.moment_id] = subject_person_id

    def next_for_subject(
        self, subject_person_id: PersonId, instant: datetime
    ) -> ExpectedMoment | None:
        del instant  # overdue moments intentionally remain eligible
        outstanding = (
            moment
            for moment_id, moment in self.moments.items()
            if self.owners.get(moment_id) == subject_person_id
            and moment.status in {MomentStatus.SCHEDULED, MomentStatus.DUE}
        )
        return min(outstanding, key=lambda moment: moment.due_at, default=None)

    def outstanding_for_subject(self, subject_person_id: PersonId) -> tuple[ExpectedMoment, ...]:
        return tuple(
            sorted(
                (
                    moment
                    for moment_id, moment in self.moments.items()
                    if self.owners.get(moment_id) == subject_person_id
                    and moment.status in {MomentStatus.SCHEDULED, MomentStatus.DUE}
                ),
                key=lambda moment: moment.due_at,
            )
        )

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
    owners: dict[AlertId, PersonId] = field(default_factory=dict)

    def get(self, alert_id: AlertId) -> Alert | None:
        return self.alerts.get(alert_id)

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Alert, ...]:
        return tuple(
            sorted(
                (
                    alert
                    for alert_id, alert in self.alerts.items()
                    if self.owners.get(alert_id) == subject_person_id
                ),
                key=lambda alert: alert.opened_at,
                reverse=True,
            )
        )

    def save(self, alert: Alert) -> None:
        self.alerts[alert.alert_id] = alert

    def alert_for_moment(self, moment_id: MomentId) -> Alert | None:
        existing_id = self._by_moment.get(moment_id)
        return self.alerts.get(existing_id) if existing_id else None

    def open_for_moment(
        self,
        alert: Alert,
        *,
        subject_person_id: PersonId | None = None,
    ) -> Alert:
        """Conditional insert keyed on the Moment. Invariant 1."""
        existing_id = self._by_moment.get(alert.moment_id)
        if existing_id is not None:
            return self.alerts[existing_id]
        self._by_moment[alert.moment_id] = alert.alert_id
        self.alerts[alert.alert_id] = alert
        if subject_person_id is not None:
            self.owners[alert.alert_id] = subject_person_id
        return alert


@dataclass
class InMemoryCircleRepository:
    circles: dict[CircleId, Circle] = field(default_factory=dict)
    consents: dict[PlanId, dict[PersonId, ConsentGrant]] = field(default_factory=dict)

    def get(self, circle_id: CircleId) -> Circle | None:
        return self.circles.get(circle_id)

    def for_owner(self, owner_person_id: PersonId) -> Circle | None:
        return next(
            (
                circle
                for circle in self.circles.values()
                if circle.owner_person_id == owner_person_id
            ),
            None,
        )

    def consents_for(self, plan_id: PlanId) -> dict[PersonId, ConsentGrant]:
        return dict(self.consents.get(plan_id, {}))

    def save_circle(self, circle: Circle) -> None:
        self.circles[circle.circle_id] = circle

    def save_consent(self, consent: ConsentGrant) -> None:
        self.consents.setdefault(consent.plan_id, {})[consent.responder_person_id] = consent


@dataclass
class InMemoryInvitationRepository:
    invitations: dict[InvitationId, CircleInvitation] = field(default_factory=dict)

    def get(self, invitation_id: InvitationId) -> CircleInvitation | None:
        return self.invitations.get(invitation_id)

    def save(self, invitation: CircleInvitation) -> None:
        self.invitations[invitation.invitation_id] = invitation


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
class InMemoryDecisionLog:
    decisions: list[AgentDecision] = field(default_factory=list)

    def append(self, decision: AgentDecision) -> None:
        self.decisions.append(decision)

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "decisionId": d.decision_id,
                "proposedTool": d.proposed_tool,
                "policyResult": d.policy_result.value,
                "reasonCode": d.reason_code,
            }
            for d in self.decisions
            if d.alert_id == alert_id
        )

    @property
    def denied(self) -> list[AgentDecision]:
        return [d for d in self.decisions if d.was_denied]


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
        # Keys mirror DynamoAuditLog exactly. The in-memory adapter exists so invariants
        # can be proven without the cloud, and that only works if a caller cannot tell the
        # two apart — a different key here would make a test pass against one adapter and
        # fail against the other.
        self.events.append(
            {
                "pk": f"ALERT#{alert_id}",
                "alertId": alert_id,
                "actorType": actor_type,
                "actorId": actor_id,
                "eventType": event_type,
                "at": at.isoformat(),
                "metadata": metadata or {},
            }
        )

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]:
        return tuple(e for e in self.events if e["alertId"] == alert_id)
