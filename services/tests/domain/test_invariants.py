"""The seven invariants from docs/PRODUCT-STATES.md section 6.

The document says "assert these in tests". This is that file. Each test names the
invariant it defends, so a failure here reads as a product-rule violation rather than a
unit-test failure.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest

from services.domain.alert import Alert, AlertState
from services.domain.errors import LeaseConflict, TerminalAlert
from services.domain.ids import PersonId

from .conftest import DUE_AT, escalating, in_circle_escalation, make_alert, make_version

MONA = PersonId("person-mona")
MAYA = PersonId("person-maya")


# -- Invariant 2: an Alert is pinned to one Plan Version for its whole life ----


def test_alert_stays_pinned_to_its_version_through_every_transition() -> None:
    v4 = make_version(version_number=4)
    alert = escalating(v4)

    # The user edits their plan mid-Alert; v5 becomes active elsewhere.
    v5 = make_version(version_number=5, lease_seconds=60)
    assert v5.version_id != v4.version_id

    alert = alert.record_attempt(v4.step(1)).escalate_to_circle(DUE_AT)
    alert = alert.claim(DUE_AT, MAYA)

    assert alert.plan_version_id == v4.version_id
    assert alert.version.version_number == 4
    # The lease used v4's window, not v5's - the live plan cannot reach into a live Alert.
    assert alert.lease is not None
    assert alert.lease.expires_at == DUE_AT + timedelta(seconds=600)


# -- Invariant 3: terminal states never transition out ------------------------


@pytest.mark.parametrize(
    "terminal",
    [AlertState.RESOLVED, AlertState.CANCELLED, AlertState.ESCALATION_EXHAUSTED],
)
def test_terminal_alerts_reject_every_event(terminal: AlertState) -> None:
    alert = make_alert(state=terminal)
    attempts: tuple[Callable[[Alert], Alert], ...] = (
        lambda a: a.mark_due(DUE_AT),
        lambda a: a.confirm_subject(DUE_AT, MONA),
        lambda a: a.claim(DUE_AT, MAYA),
        lambda a: a.escalate_to_circle(DUE_AT),
        lambda a: a.cancel(DUE_AT, MONA),
    )
    for attempt in attempts:
        with pytest.raises(TerminalAlert):
            attempt(alert)


def test_a_resolved_alert_cannot_be_reopened_by_a_late_responder() -> None:
    """The realistic version: an SMS reply lands after the subject already confirmed."""
    alert = in_circle_escalation().claim(DUE_AT, MAYA)
    resolved = alert.confirm_subject(DUE_AT + timedelta(minutes=1), MONA)

    with pytest.raises(TerminalAlert):
        resolved.responder_unable(DUE_AT + timedelta(minutes=2))


# -- Invariant 4: terminal state cancels all pending external actions ----------


def test_no_actions_are_due_once_an_alert_is_terminal() -> None:
    alert = escalating()
    later = DUE_AT + timedelta(hours=2)

    assert alert.due_steps(later), "precondition: rungs are pending before resolution"

    resolved = alert.confirm_subject(DUE_AT, MONA)
    assert resolved.due_steps(later) == ()
    assert resolved.next_action_due_at() is None


# -- Invariant 6: escalation resumes at the paused step, never from the top ----


def test_lease_expiry_resumes_at_the_next_rung_not_the_first() -> None:
    alert = in_circle_escalation()
    primary, backup = alert.version.responder_steps

    alert = alert.record_attempt(primary)
    assert alert.ladder.next_step() == backup

    claimed = alert.claim(DUE_AT + timedelta(minutes=25), MAYA)
    expiry = claimed.lease.expires_at  # type: ignore[union-attr]
    resumed = claimed.expire_lease(expiry)

    assert resumed.state is AlertState.CIRCLE_ESCALATION
    assert resumed.ladder.next_step() == backup, "the ladder restarted instead of resuming"
    assert primary.sequence in resumed.ladder.state.attempted


def test_paused_time_pushes_the_remaining_ladder_out_by_exactly_that_much() -> None:
    """A responder who checks for ten minutes must not cause the backup to fire instantly."""
    alert = in_circle_escalation()
    primary, backup = alert.version.responder_steps
    alert = alert.record_attempt(primary)

    before = alert.ladder.state.due_at(backup)

    claim_at = DUE_AT + timedelta(minutes=25)
    claimed = alert.claim(claim_at, MAYA)
    resumed = claimed.expire_lease(claim_at + timedelta(seconds=600))

    after = resumed.ladder.state.due_at(backup)
    assert after - before == timedelta(seconds=600)


# -- Acknowledged is not resolved ---------------------------------------------


def test_claiming_an_alert_does_not_resolve_it() -> None:
    """The single most important semantic in the product."""
    alert = in_circle_escalation().claim(DUE_AT, MAYA)

    assert alert.state is AlertState.CHECKING
    assert not alert.is_terminal
    assert alert.resolution is None
    assert alert.resolved_at is None


def test_a_claim_pauses_escalation_without_ending_it() -> None:
    alert = in_circle_escalation()
    later = DUE_AT + timedelta(hours=1)
    assert alert.due_steps(later), "precondition: the Circle ladder has pending rungs"

    claimed = alert.claim(DUE_AT, MAYA)
    assert claimed.due_steps(later) == (), "escalation must pause while someone is checking"
    assert claimed.next_action_due_at() is None
    assert claimed.is_open, "paused is not closed"


# -- Lease ownership ----------------------------------------------------------


def test_two_responders_cannot_both_hold_the_same_alert() -> None:
    omar = PersonId("person-omar")
    claimed = in_circle_escalation().claim(DUE_AT, MAYA)

    with pytest.raises(LeaseConflict):
        claimed.claim(DUE_AT + timedelta(minutes=1), omar)


def test_only_the_lease_holder_may_verify_contact() -> None:
    omar = PersonId("person-omar")
    claimed = in_circle_escalation().claim(DUE_AT, MAYA)

    with pytest.raises(LeaseConflict):
        claimed.resolve_by_responder(DUE_AT + timedelta(minutes=1), omar)


def test_a_lease_cannot_be_expired_early() -> None:
    """Expiry is a clock fact, not a decision someone can take on another's behalf."""
    claimed = in_circle_escalation().claim(DUE_AT, MAYA)

    with pytest.raises(LeaseConflict):
        claimed.expire_lease(DUE_AT + timedelta(minutes=1))


def test_responder_unable_resumes_immediately_without_waiting_for_expiry() -> None:
    claimed = in_circle_escalation().claim(DUE_AT, MAYA)
    gave_up_at = DUE_AT + timedelta(minutes=2)

    resumed = claimed.responder_unable(gave_up_at)

    assert resumed.state is AlertState.CIRCLE_ESCALATION
    assert resumed.lease is None
    # Only the two minutes actually spent count as paused, not the full ten-minute lease.
    assert resumed.ladder.state.paused_seconds == pytest.approx(120.0)


def test_an_abandoned_lease_pauses_only_until_it_expired() -> None:
    """A responder who vanishes pauses escalation for the lease, not for however long
    it took the system to notice."""
    claimed = in_circle_escalation().claim(DUE_AT, MAYA)
    noticed_late = DUE_AT + timedelta(minutes=45)

    resumed = claimed.expire_lease(noticed_late)

    assert resumed.ladder.state.paused_seconds == pytest.approx(600.0)


# -- Stop conditions ----------------------------------------------------------


def test_the_subject_can_close_their_own_alert_from_any_stage() -> None:
    stages: list[Alert] = [
        make_alert().mark_due(DUE_AT),
        make_alert().mark_due(DUE_AT).enter_grace(DUE_AT),
        escalating(),
        in_circle_escalation(),
        in_circle_escalation().claim(DUE_AT, MAYA),
    ]
    for alert in stages:
        resolved = alert.confirm_subject(DUE_AT + timedelta(minutes=1), MONA)
        assert resolved.state is AlertState.RESOLVED, f"blocked from {alert.state}"
        assert resolved.resolution is not None
        assert resolved.lease is None, "resolving must release any held lease"


def test_resolution_records_who_when_how_and_which_version() -> None:
    resolved = (
        in_circle_escalation()
        .claim(DUE_AT, MAYA)
        .resolve_by_responder(DUE_AT + timedelta(minutes=3), MAYA)
    )
    record = resolved.resolution
    assert record is not None
    assert record.resolved_by_person_id == MAYA
    assert record.created_at == DUE_AT + timedelta(minutes=3)
    assert record.plan_version_id == resolved.plan_version_id
    assert record.alert_id == resolved.alert_id
