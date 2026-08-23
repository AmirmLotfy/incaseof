"""Repository ports.

The domain depends on these Protocols, never on DynamoDB. Phase 2 supplies adapters; the
in-memory adapter in ``services/adapters/memory.py`` is not a mock -- it implements the
same conditional semantics, so a test that passes against it is testing the real rules.

Two operations are deliberately *conditional* rather than plain writes, because they are
the operations that enforce invariants under concurrency:

* :meth:`AlertRepository.open_for_moment` -- one Moment produces at most one Alert.
* :meth:`ActionLog.claim_key` -- an external action fires at most once per attempt.

Expressing these as "check, then write" would be a race. Expressing them as conditional
writes is what makes the invariant true when two schedulers deliver the same event.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .agent_decision import AgentDecision
from .alert import Alert
from .circle import Circle, ConsentGrant
from .idempotency import IdempotencyKey
from .ids import AlertId, CircleId, MomentId, PersonId, PlanId, PlanVersionId
from .moment import ExpectedMoment
from .plan import Plan, PlanVersion


class PlanRepository(Protocol):
    def get_plan(self, plan_id: PlanId) -> Plan | None: ...

    def get_version(self, version_id: PlanVersionId) -> PlanVersion | None: ...

    def save_plan(self, plan: Plan) -> None: ...

    def save_version(self, version: PlanVersion) -> None:
        """Persist a version. Versions are immutable; re-saving one is a programming error."""
        ...

    def activate(self, plan_id: PlanId, version_id: PlanVersionId, at: datetime) -> Plan: ...


class MomentRepository(Protocol):
    def get(self, moment_id: MomentId) -> ExpectedMoment | None: ...

    def save(self, moment: ExpectedMoment) -> None: ...

    def due_before(self, instant: datetime) -> tuple[ExpectedMoment, ...]:
        """Moments whose due time has passed and which are still unresolved."""
        ...


class AlertRepository(Protocol):
    def get(self, alert_id: AlertId) -> Alert | None: ...

    def save(self, alert: Alert) -> None: ...

    def alert_for_moment(self, moment_id: MomentId) -> Alert | None:
        """The Alert opened for this Moment, if one was."""
        ...

    def open_for_moment(self, alert: Alert) -> Alert:
        """Open an Alert for a Moment, conditional on none existing.

        Returns the *existing* Alert if one is already open for that Moment, rather than
        raising. A duplicate scheduler delivery is normal operation, not an error, and the
        caller's correct response is to carry on with the Alert that exists.
        """
        ...


class CircleRepository(Protocol):
    def get(self, circle_id: CircleId) -> Circle | None: ...

    def consents_for(self, plan_id: PlanId) -> dict[PersonId, ConsentGrant]:
        """Consent grants covering this plan, keyed by responder."""
        ...

    def save_circle(self, circle: Circle) -> None: ...

    def save_consent(self, consent: ConsentGrant) -> None: ...


class ActionLog(Protocol):
    def claim_key(self, key: IdempotencyKey) -> bool:
        """Reserve an idempotency key.

        Returns True if this caller won the race and should dispatch; False if the key was
        already taken, in which case the caller reports success and sends nothing. The
        person on the other end of a duplicate is being contacted twice about the same
        alert -- suppressing that is the whole point.
        """
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
