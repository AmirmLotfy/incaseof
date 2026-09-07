"""Repository ports.

The domain depends on these Protocols, never on DynamoDB. Phase 2 supplies adapters; the
in-memory adapter in ``services/adapters/memory.py`` is not a mock -- it implements the
same conditional semantics, so a test that passes against it is testing the real rules.

Two operations are deliberately *conditional* rather than plain writes, because they are
the operations that enforce invariants under concurrency:

* :meth:`AlertRepository.open_for_moment` -- one Moment produces at most one Alert.
* :meth:`ActionLog.claim_key` -- compatibility detection for pre-outbox deployments.

Expressing these as "check, then write" would be a race. Expressing them as conditional
writes is what makes the invariant true when two schedulers deliver the same event.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .account import Profile
from .agent_decision import AgentDecision
from .alert import Alert
from .circle import Circle, ConsentGrant
from .idempotency import IdempotencyKey
from .ids import AlertId, CircleId, InvitationId, MomentId, PersonId, PlanId, PlanVersionId
from .invitation import CircleInvitation
from .moment import ExpectedMoment
from .plan import Plan, PlanVersion


class ProfileRepository(Protocol):
    def get(self, person_id: PersonId) -> Profile | None: ...

    def save(self, profile: Profile) -> None: ...


class PlanRepository(Protocol):
    def get_plan(self, plan_id: PlanId) -> Plan | None: ...

    def get_version(self, version_id: PlanVersionId) -> PlanVersion | None: ...

    def latest_version(self, plan_id: PlanId) -> PlanVersion | None: ...

    def save_plan(self, plan: Plan) -> None: ...

    def save_version(self, version: PlanVersion) -> None:
        """Persist a version. Versions are immutable; re-saving one is a programming error."""
        ...

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Plan, ...]:
        """Plans owned by a subject, ordered deterministically."""
        ...

    def activate(
        self,
        plan_id: PlanId,
        version_id: PlanVersionId,
        at: datetime,
        bindings: dict[str, str] | None = None,
    ) -> Plan: ...


class MomentRepository(Protocol):
    def get(self, moment_id: MomentId) -> ExpectedMoment | None: ...

    def save(
        self,
        moment: ExpectedMoment,
        *,
        subject_person_id: PersonId | None = None,
    ) -> None: ...

    def next_for_subject(
        self, subject_person_id: PersonId, instant: datetime
    ) -> ExpectedMoment | None:
        """The subject's next outstanding Moment, including overdue work."""
        ...

    def outstanding_for_subject(
        self, subject_person_id: PersonId
    ) -> tuple[ExpectedMoment, ...]: ...

    def due_before(self, instant: datetime) -> tuple[ExpectedMoment, ...]:
        """Moments whose due time has passed and which are still unresolved."""
        ...


class AlertRepository(Protocol):
    def get(self, alert_id: AlertId) -> Alert | None: ...

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Alert, ...]: ...

    def save(self, alert: Alert) -> None: ...

    def alert_for_moment(self, moment_id: MomentId) -> Alert | None:
        """The Alert opened for this Moment, if one was."""
        ...

    def open_for_moment(
        self,
        alert: Alert,
        *,
        subject_person_id: PersonId | None = None,
    ) -> Alert:
        """Open an Alert for a Moment, conditional on none existing.

        Returns the *existing* Alert if one is already open for that Moment, rather than
        raising. A duplicate scheduler delivery is normal operation, not an error, and the
        caller's correct response is to carry on with the Alert that exists.
        """
        ...


class CircleRepository(Protocol):
    def get(self, circle_id: CircleId) -> Circle | None: ...

    def for_owner(self, owner_person_id: PersonId) -> Circle | None:
        """The Circle owned by this person, if one exists."""
        ...

    def consents_for(self, plan_id: PlanId) -> dict[PersonId, ConsentGrant]:
        """Consent grants covering this plan, keyed by responder."""
        ...

    def save_circle(self, circle: Circle) -> None: ...

    def save_consent(self, consent: ConsentGrant) -> None: ...


class InvitationRepository(Protocol):
    def get(self, invitation_id: InvitationId) -> CircleInvitation | None: ...

    def save(self, invitation: CircleInvitation) -> None: ...


class ActionLog(Protocol):
    """Legacy action locks retained only to reconcile pre-outbox attempts safely."""

    def claim_key(self, key: IdempotencyKey) -> bool:
        """Reserve a legacy key. New delivery uses the durable outbox instead."""
        ...

    def was_dispatched(self, key: IdempotencyKey) -> bool: ...


class DecisionLog(Protocol):
    """Agent proposals and their outcomes.

    Separate from the audit log because these answer a different question: not "what
    happened to this Alert" but "what did the model ask for, and what did policy say".
    """

    def append(self, decision: AgentDecision) -> None: ...

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]: ...


class AuditLog(Protocol):
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
        """Append-only by convention. Nothing in the product ever edits an audit event."""
        ...

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]: ...
