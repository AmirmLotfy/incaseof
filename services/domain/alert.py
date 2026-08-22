"""The Alert lifecycle.

docs/PRODUCT-STATES.md is normative. ``test_doc_parity.py`` parses its transition table and
asserts TRANSITIONS below matches it in both directions, so the two cannot drift.

Transitions are functional: every method returns a new Alert rather than mutating one.
Safety state that can be changed in place is safety state that can be changed by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum

from .clock import require_aware
from .errors import InvalidTransition, LeaseConflict, TerminalAlert
from .escalation import Ladder, LadderState
from .ids import AlertId, MomentId, PersonId, PlanVersionId
from .plan import EscalationStep, PlanVersion, StopCondition
from .resolution import Resolution, ResolutionSource

LEASE_WARNING_SECONDS = 120


class AlertState(StrEnum):
    SCHEDULED = "SCHEDULED"
    DUE = "DUE"
    GRACE = "GRACE"
    SELF_CONTACT = "SELF_CONTACT"
    CIRCLE_ESCALATION = "CIRCLE_ESCALATION"
    CHECKING = "CHECKING"
    RESOLVED = "RESOLVED"
    ESCALATION_EXHAUSTED = "ESCALATION_EXHAUSTED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset(
    {AlertState.RESOLVED, AlertState.ESCALATION_EXHAUSTED, AlertState.CANCELLED}
)

NON_TERMINAL_STATES = frozenset(AlertState) - TERMINAL_STATES


class AlertEvent(StrEnum):
    DUE_TIME_REACHED = "DUE_TIME_REACHED"
    GRACE_CONFIGURED = "GRACE_CONFIGURED"
    GRACE_ELAPSED = "GRACE_ELAPSED"
    SUBJECT_CONFIRMED = "SUBJECT_CONFIRMED"
    USER_CANCELLED = "USER_CANCELLED"
    SUBJECT_LADDER_EXHAUSTED = "SUBJECT_LADDER_EXHAUSTED"
    RESPONDER_CLAIMED = "RESPONDER_CLAIMED"
    CIRCLE_LADDER_EXHAUSTED = "CIRCLE_LADDER_EXHAUSTED"
    RESPONDER_VERIFIED = "RESPONDER_VERIFIED"
    RESPONDER_UNABLE = "RESPONDER_UNABLE"
    LEASE_EXPIRED = "LEASE_EXPIRED"


def _build_transitions() -> dict[tuple[AlertState, AlertEvent], AlertState]:
    table: dict[tuple[AlertState, AlertEvent], AlertState] = {
        (AlertState.SCHEDULED, AlertEvent.DUE_TIME_REACHED): AlertState.DUE,
        (AlertState.DUE, AlertEvent.GRACE_CONFIGURED): AlertState.GRACE,
        (AlertState.DUE, AlertEvent.USER_CANCELLED): AlertState.CANCELLED,
        (AlertState.GRACE, AlertEvent.USER_CANCELLED): AlertState.CANCELLED,
        (AlertState.GRACE, AlertEvent.GRACE_ELAPSED): AlertState.SELF_CONTACT,
        (AlertState.SELF_CONTACT, AlertEvent.SUBJECT_LADDER_EXHAUSTED): (
            AlertState.CIRCLE_ESCALATION
        ),
        (AlertState.CIRCLE_ESCALATION, AlertEvent.RESPONDER_CLAIMED): AlertState.CHECKING,
        (AlertState.CIRCLE_ESCALATION, AlertEvent.CIRCLE_LADDER_EXHAUSTED): (
            AlertState.ESCALATION_EXHAUSTED
        ),
        (AlertState.CHECKING, AlertEvent.RESPONDER_VERIFIED): AlertState.RESOLVED,
        (AlertState.CHECKING, AlertEvent.RESPONDER_UNABLE): AlertState.CIRCLE_ESCALATION,
        (AlertState.CHECKING, AlertEvent.LEASE_EXPIRED): AlertState.CIRCLE_ESCALATION,
    }
    # "any non-terminal | subject confirms okay | RESOLVED".
    # The subject saying they are okay always wins, from wherever the Alert has reached.
    for state in NON_TERMINAL_STATES:
        table[(state, AlertEvent.SUBJECT_CONFIRMED)] = AlertState.RESOLVED
    return table


TRANSITIONS = _build_transitions()


def next_state(state: AlertState, event: AlertEvent) -> AlertState:
    if state in TERMINAL_STATES:
        raise TerminalAlert(
            f"{state} is terminal; {event} cannot apply. Invariant 3: terminal states "
            f"never transition out."
        )
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise InvalidTransition(state, event) from None


@dataclass(frozen=True, slots=True)
class CheckingLease:
    """Temporary ownership of an Alert by a responder.

    Holding a lease means "I am looking into this", which pauses backup escalation. It
    does not mean the subject is safe -- see docs/PRODUCT-STATES.md section 3.
    """

    owner_person_id: PersonId
    claimed_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def should_warn(self, now: datetime) -> bool:
        """Two minutes out: 'Are you still checking?'"""
        return not self.is_expired(now) and (
            self.expires_at - now <= timedelta(seconds=LEASE_WARNING_SECONDS)
        )

    def held_seconds(self, until: datetime) -> float:
        """How long escalation was actually paused. Never negative."""
        return max(0.0, (until - self.claimed_at).total_seconds())

    def extended_to(self, new_expiry: datetime) -> CheckingLease:
        return replace(self, expires_at=new_expiry)


@dataclass(frozen=True, slots=True)
class Alert:
    """One unresolved expectation, and everything done about it so far."""

    alert_id: AlertId
    moment_id: MomentId
    plan_version_id: PlanVersionId
    state: AlertState
    opened_at: datetime
    ladder: Ladder
    lease: CheckingLease | None = None
    resolution: Resolution | None = None
    resolved_at: datetime | None = None
    released_signals: frozenset[str] = field(default_factory=frozenset)

    # -- queries ----------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def is_open(self) -> bool:
        return not self.is_terminal

    @property
    def version(self) -> PlanVersion:
        """The pinned version. Never the live plan -- invariant 2."""
        return self.ladder.version

    @property
    def is_paused(self) -> bool:
        """Backup escalation is paused while somebody is checking."""
        return self.state is AlertState.CHECKING

    def next_action_due_at(self) -> datetime | None:
        """When the next rung fires, or None if paused, terminal or exhausted."""
        if self.is_terminal or self.is_paused:
            return None
        return self.ladder.next_due_at()

    def due_steps(self, now: datetime) -> tuple[EscalationStep, ...]:
        """Rungs to dispatch now.

        Empty while terminal or paused: invariant 4 means a closed Alert dispatches
        nothing, and a paused one waits for the responder holding it.
        """
        if self.is_terminal or self.is_paused:
            return ()
        return self.ladder.due_steps(now)

    # -- internals --------------------------------------------------------

    def _apply(self, event: AlertEvent) -> AlertState:
        return next_state(self.state, event)

    def _guard_open(self, action: str) -> None:
        """Refuse work on a closed Alert, and say so in those terms.

        Ordering matters here. A closed Alert has no lease, so a lease check placed first
        reports "no lease to release" for what is really "this alert is already closed" --
        a misleading error for the common case of a responder replying by SMS moments
        after the subject confirmed in the app.
        """
        if self.is_terminal:
            raise TerminalAlert(
                f"cannot {action}: alert {self.alert_id} is already {self.state}. "
                f"Invariant 3: terminal states never transition out."
            )

    # -- lifecycle --------------------------------------------------------

    def mark_due(self, now: datetime) -> Alert:
        return replace(self, state=self._apply(AlertEvent.DUE_TIME_REACHED))

    def enter_grace(self, now: datetime) -> Alert:
        return replace(self, state=self._apply(AlertEvent.GRACE_CONFIGURED))

    def begin_self_contact(self, now: datetime) -> Alert:
        """Grace has elapsed. Escalation starts now, so the ladder clock starts here."""
        require_aware(now, "now")
        state = self._apply(AlertEvent.GRACE_ELAPSED)
        started = LadderState(
            started_at=now,
            paused_seconds=self.ladder.state.paused_seconds,
            attempted=self.ladder.state.attempted,
            scale=self.ladder.state.scale,
        )
        return replace(self, state=state, ladder=replace(self.ladder, state=started))

    def record_attempt(self, step: EscalationStep) -> Alert:
        """Mark a rung as attempted.

        Attempted means dispatched, not delivered and certainly not answered. Delivery is
        not resolution.
        """
        return replace(self, ladder=self.ladder.attempt(step))

    def escalate_to_circle(self, now: datetime) -> Alert:
        return replace(self, state=self._apply(AlertEvent.SUBJECT_LADDER_EXHAUSTED))

    def exhaust(self, now: datetime) -> Alert:
        """Every rung tried, nobody closed the loop. Terminal, and not a success."""
        return replace(self, state=self._apply(AlertEvent.CIRCLE_LADDER_EXHAUSTED))

    # -- subject actions --------------------------------------------------

    def confirm_subject(
        self,
        now: datetime,
        person_id: PersonId,
        source: ResolutionSource = ResolutionSource.APP,
    ) -> Alert:
        """The subject said they are okay. This always wins, from any non-terminal state."""
        require_aware(now, "now")
        state = self._apply(AlertEvent.SUBJECT_CONFIRMED)
        resolution = Resolution(
            alert_id=self.alert_id,
            resolved_by_person_id=person_id,
            method=StopCondition.SUBJECT_EXPLICIT_CONFIRMATION,
            source=source,
            plan_version_id=self.plan_version_id,
            created_at=now,
        )
        return replace(self, state=state, resolution=resolution, resolved_at=now, lease=None)

    def cancel(self, now: datetime, person_id: PersonId) -> Alert:
        """Cancel before escalation. Valid only from DUE or GRACE."""
        require_aware(now, "now")
        state = self._apply(AlertEvent.USER_CANCELLED)
        resolution = Resolution(
            alert_id=self.alert_id,
            resolved_by_person_id=person_id,
            method=StopCondition.USER_CANCELLED_BEFORE_ESCALATION,
            source=ResolutionSource.APP,
            plan_version_id=self.plan_version_id,
            created_at=now,
        )
        return replace(self, state=state, resolution=resolution, resolved_at=now)

    # -- responder actions ------------------------------------------------

    def claim(self, now: datetime, responder_id: PersonId) -> Alert:
        """A responder takes the Alert. Backup escalation pauses for the lease duration.

        This is an acknowledgement, not a resolution.
        """
        require_aware(now, "now")
        self._guard_open("claim")
        if self.lease is not None and not self.lease.is_expired(now):
            if self.lease.owner_person_id != responder_id:
                raise LeaseConflict(
                    f"alert {self.alert_id} is already held by "
                    f"{self.lease.owner_person_id} until {self.lease.expires_at.isoformat()}"
                )
        state = self._apply(AlertEvent.RESPONDER_CLAIMED)
        lease = CheckingLease(
            owner_person_id=responder_id,
            claimed_at=now,
            expires_at=now + timedelta(seconds=self.version.lease_seconds),
        )
        return replace(self, state=state, lease=lease)

    def extend_lease(self, now: datetime, seconds: int | None = None) -> Alert:
        """ "Yes, still checking." Extends without changing ownership or state."""
        self._guard_open("extend a lease")
        if self.lease is None:
            raise LeaseConflict(f"alert {self.alert_id} has no lease to extend")
        window = seconds if seconds is not None else self.version.lease_seconds
        return replace(self, lease=self.lease.extended_to(now + timedelta(seconds=window)))

    def _release_lease(self, now: datetime, event: AlertEvent) -> Alert:
        """Give the ladder back its paused time and resume where it left off."""
        self._guard_open("release a lease")
        if self.lease is None:
            raise LeaseConflict(f"alert {self.alert_id} has no lease to release")
        state = self._apply(event)
        paused = self.lease.held_seconds(min(now, self.lease.expires_at))
        return replace(self, state=state, lease=None, ladder=self.ladder.pause_for(paused))

    def responder_unable(self, now: datetime) -> Alert:
        """ "I couldn't reach them." Escalation resumes immediately."""
        require_aware(now, "now")
        return self._release_lease(now, AlertEvent.RESPONDER_UNABLE)

    def expire_lease(self, now: datetime) -> Alert:
        """The responder went quiet. Normal and expected, not an error."""
        require_aware(now, "now")
        self._guard_open("expire a lease")
        if self.lease is not None and not self.lease.is_expired(now):
            raise LeaseConflict(
                f"lease on {self.alert_id} does not expire until "
                f"{self.lease.expires_at.isoformat()}"
            )
        return self._release_lease(now, AlertEvent.LEASE_EXPIRED)

    def resolve_by_responder(
        self,
        now: datetime,
        responder_id: PersonId,
        source: ResolutionSource = ResolutionSource.RESPONDER_WEB,
    ) -> Alert:
        """ "I reached them, they're okay." The only responder path that closes an Alert."""
        require_aware(now, "now")
        self._guard_open("verify contact")
        if self.lease is None or self.lease.owner_person_id != responder_id:
            raise LeaseConflict(
                f"{responder_id} does not hold the lease on {self.alert_id}; only the "
                f"responder who claimed it may verify contact"
            )
        state = self._apply(AlertEvent.RESPONDER_VERIFIED)
        resolution = Resolution(
            alert_id=self.alert_id,
            resolved_by_person_id=responder_id,
            method=StopCondition.RESPONDER_VERIFIED_CONTACT,
            source=source,
            plan_version_id=self.plan_version_id,
            created_at=now,
        )
        return replace(self, state=state, resolution=resolution, resolved_at=now, lease=None)
