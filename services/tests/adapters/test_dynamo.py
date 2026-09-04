"""DynamoDB adapter tests.

The three conditional writes carry the invariants. Everything else here is round-tripping,
which matters because a persistence bug that drops a lease owner or a paused duration does
not fail loudly -- it makes escalation behave slightly wrong, later, unreproducibly.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from services.adapters.dynamo import (
    ConcurrentModification,
    DynamoActionLog,
    DynamoAlertRepository,
    DynamoAuditLog,
    DynamoCircleRepository,
    DynamoMomentRepository,
    DynamoPlanRepository,
)
from services.domain.alert import AlertState
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    MemberStatus,
)
from services.domain.clock import utc
from services.domain.idempotency import key_for
from services.domain.ids import (
    AlertId,
    CircleId,
    ConsentId,
    MembershipId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
    StepId,
)
from services.domain.moment import MomentStatus, moment_for
from services.domain.plan import Plan, ResponderRole
from services.tests.domain.conftest import DUE_AT, in_circle_escalation, make_alert, make_version

MONA = PersonId("person-mona")
MAYA = PersonId("person-maya")
OMAR = PersonId("person-omar")
PLAN = PlanId("plan-1")


# -- Invariant 1: one Moment produces at most one Alert -----------------------


def test_a_duplicate_scheduler_delivery_does_not_open_a_second_alert(table: Any) -> None:
    """The transaction's condition, not a prior read, is what makes this true."""
    repo = DynamoAlertRepository(table)
    first = repo.open_for_moment(make_alert())

    duplicate = replace(make_alert(), alert_id=AlertId("alert-2"))
    second = repo.open_for_moment(duplicate)

    assert second.alert_id == first.alert_id
    assert repo.get(AlertId("alert-2")) is None, "the losing Alert must not have been written"


def test_a_duplicate_delivery_returns_the_alert_as_it_now_stands(table: Any) -> None:
    """A replay arriving mid-escalation must not rewind anything."""
    repo = DynamoAlertRepository(table)
    opened = repo.open_for_moment(make_alert())
    repo.save(opened.mark_due(DUE_AT).enter_grace(DUE_AT))

    again = repo.open_for_moment(replace(make_alert(), alert_id=AlertId("alert-9")))
    assert again.state is AlertState.GRACE


def test_distinct_moments_open_distinct_alerts(table: Any) -> None:
    repo = DynamoAlertRepository(table)
    repo.open_for_moment(make_alert())
    other = replace(make_alert(), alert_id=AlertId("alert-2"), moment_id=MomentId("moment-2"))
    assert repo.open_for_moment(other).alert_id == AlertId("alert-2")


# -- Invariant 5: an external action dispatches at most once ------------------


def test_only_one_caller_wins_an_idempotency_key(table: Any) -> None:
    log = DynamoActionLog(table)
    key = key_for(AlertId("alert-1"), StepId("step-4"), attempt_number=1)

    assert log.claim_key(key) is True
    assert log.claim_key(key) is False
    assert log.was_dispatched(key)


def test_a_deliberate_retry_is_a_separate_action(table: Any) -> None:
    log = DynamoActionLog(table)
    alert, step = AlertId("alert-1"), StepId("step-4")
    assert log.claim_key(key_for(alert, step, 1)) is True
    assert log.claim_key(key_for(alert, step, 2)) is True
    assert log.claim_key(key_for(alert, step, 2)) is False


# -- optimistic locking -------------------------------------------------------


def test_a_stale_write_is_refused_rather_than_silently_winning(table: Any) -> None:
    """Two responders tapping 'I'm checking' in the same second.

    Both pass the domain's lease guard, because each read an Alert with no owner. The
    conditional write is what stops the second from overwriting the first.
    """
    alert = in_circle_escalation()
    writer = DynamoAlertRepository(table)
    writer.open_for_moment(alert)

    maya_view = DynamoAlertRepository(table)
    omar_view = DynamoAlertRepository(table)
    maya_read = maya_view.get(alert.alert_id)
    omar_read = omar_view.get(alert.alert_id)
    assert maya_read is not None and omar_read is not None

    maya_view.save(maya_read.claim(DUE_AT, MAYA))

    with pytest.raises(ConcurrentModification):
        omar_view.save(omar_read.claim(DUE_AT, OMAR))

    settled = writer.get(alert.alert_id)
    assert settled is not None and settled.lease is not None
    assert settled.lease.owner_person_id == MAYA, "the first writer must keep the Alert"


def test_sequential_writes_from_one_reader_succeed(table: Any) -> None:
    repo = DynamoAlertRepository(table)
    alert = repo.open_for_moment(in_circle_escalation())
    claimed = alert.claim(DUE_AT, MAYA)
    repo.save(claimed)
    repo.save(claimed.resolve_by_responder(DUE_AT + timedelta(minutes=2), MAYA))

    final = repo.get(alert.alert_id)
    assert final is not None and final.state is AlertState.RESOLVED


# -- round tripping -----------------------------------------------------------


def test_an_alert_survives_a_round_trip_with_its_ladder_intact(table: Any) -> None:
    repo = DynamoAlertRepository(table)
    alert = in_circle_escalation()
    primary = alert.version.responder_steps[0]
    alert = alert.record_attempt(primary).claim(DUE_AT, MAYA)
    resumed = alert.expire_lease(DUE_AT + timedelta(seconds=600))

    repo.open_for_moment(resumed)
    loaded = DynamoAlertRepository(table).get(resumed.alert_id)
    assert loaded is not None

    assert loaded.state is resumed.state
    assert loaded.ladder.state.attempted == resumed.ladder.state.attempted
    assert loaded.ladder.state.paused_seconds == pytest.approx(600.0)
    assert loaded.ladder.next_step() == resumed.ladder.next_step()
    assert loaded.plan_version_id == resumed.plan_version_id


def test_the_pinned_version_travels_with_the_alert(table: Any) -> None:
    """A reader must never need the live plan to interpret a running Alert."""
    repo = DynamoAlertRepository(table)
    alert = repo.open_for_moment(in_circle_escalation(make_version(version_number=4)))

    loaded = DynamoAlertRepository(table).get(alert.alert_id)
    assert loaded is not None
    assert loaded.version.version_number == 4
    assert len(loaded.version.steps) == 5


def test_a_resolution_round_trips_with_who_when_and_how(table: Any) -> None:
    repo = DynamoAlertRepository(table)
    alert = repo.open_for_moment(in_circle_escalation()).claim(DUE_AT, MAYA)
    repo.save(alert)
    repo.save(alert.resolve_by_responder(DUE_AT + timedelta(minutes=3), MAYA))

    loaded = DynamoAlertRepository(table).get(alert.alert_id)
    assert loaded is not None and loaded.resolution is not None
    assert loaded.resolution.resolved_by_person_id == MAYA
    assert loaded.resolution.created_at == DUE_AT + timedelta(minutes=3)


# -- plan versions ------------------------------------------------------------


def test_a_version_cannot_be_overwritten(table: Any) -> None:
    repo = DynamoPlanRepository(table)
    repo.save_version(make_version())

    with pytest.raises(ValueError, match="immutable"):
        repo.save_version(make_version(lease_seconds=60))


def test_a_version_round_trips_completely(table: Any) -> None:
    repo = DynamoPlanRepository(table)
    version = make_version()
    repo.save_version(version)

    loaded = DynamoPlanRepository(table).get_version(version.version_id)
    assert loaded == version, "a version must survive persistence byte for byte"


def test_activation_records_when_without_touching_the_ladder(table: Any) -> None:
    repo = DynamoPlanRepository(table)
    version = make_version()
    repo.save_version(version)
    repo.save_plan(
        Plan(
            plan_id=PLAN,
            subject_person_id=MONA,
            circle_id=CircleId("circle-1"),
            plan_type=version.plan_type,
        )
    )

    activated = repo.activate(PLAN, version.version_id, DUE_AT)
    assert activated.active_version_id == version.version_id

    stored = repo.get_version(version.version_id)
    assert stored is not None
    assert stored.activated_at == DUE_AT
    assert stored.steps == version.steps


# -- moments and the sparse index --------------------------------------------


def test_the_sweeper_finds_a_moment_whose_schedule_never_fired(table: Any) -> None:
    repo = DynamoMomentRepository(table)
    moment = moment_for(
        moment_id=MomentId("moment-1"),
        version_id=PlanVersionId("pv-4"),
        due_at=utc(2026, 8, 26, 21, 0),
        grace_seconds=0,
    )
    repo.save(moment)

    found = repo.due_before(utc(2026, 8, 26, 21, 30))
    assert [m.moment_id for m in found] == [moment.moment_id]


def test_a_resolved_moment_drops_out_of_the_index(table: Any) -> None:
    """Sparse by design: the index holds outstanding work, not history."""
    repo = DynamoMomentRepository(table)
    moment = moment_for(
        moment_id=MomentId("moment-1"),
        version_id=PlanVersionId("pv-4"),
        due_at=utc(2026, 8, 26, 21, 0),
        grace_seconds=0,
    )
    repo.save(moment)
    repo.save(replace(moment, status=MomentStatus.RESOLVED))

    assert repo.due_before(utc(2026, 8, 26, 22, 0)) == ()


def test_a_moment_not_yet_due_is_not_swept(table: Any) -> None:
    repo = DynamoMomentRepository(table)
    repo.save(
        moment_for(
            moment_id=MomentId("moment-1"),
            version_id=PlanVersionId("pv-4"),
            due_at=utc(2026, 8, 26, 23, 0),
            grace_seconds=0,
        )
    )
    assert repo.due_before(utc(2026, 8, 26, 21, 0)) == ()


# -- circle and consent -------------------------------------------------------


def test_a_circle_round_trips_with_its_members(table: Any) -> None:
    repo = DynamoCircleRepository(table)
    circle = Circle(
        circle_id=CircleId("circle-1"),
        owner_person_id=MONA,
        members=(
            CircleMember(
                membership_id=MembershipId("m-1"),
                circle_id=CircleId("circle-1"),
                person_id=MAYA,
                role=ResponderRole.PRIMARY,
                priority=1,
                status=MemberStatus.ACCEPTED,
                display_name="Maya",
                relationship="Sister",
            ),
        ),
    )
    repo.save_circle(circle)

    loaded = DynamoCircleRepository(table).get(CircleId("circle-1"))
    assert loaded is not None
    assert loaded.member_for_role(ResponderRole.PRIMARY) is not None
    assert loaded.members[0].display_name == "Maya"


def test_consent_is_stored_per_plan_and_read_back_by_responder(table: Any) -> None:
    repo = DynamoCircleRepository(table)
    repo.save_consent(
        ConsentGrant(
            consent_id=ConsentId("c-1"),
            subject_person_id=MONA,
            responder_person_id=MAYA,
            plan_id=PLAN,
            status=ConsentStatus.ACTIVE,
            accepted_at=DUE_AT,
        )
    )

    grants = DynamoCircleRepository(table).consents_for(PLAN)
    assert MAYA in grants
    assert grants[MAYA].is_active(DUE_AT)


def test_a_circle_member_item_never_stores_a_contact_endpoint(table: Any) -> None:
    """Phone numbers live encrypted elsewhere and are resolved at dispatch time.

    Asserted against the raw item, because the guarantee is about what is written to the
    table, not about what the domain object happens to expose.
    """
    repo = DynamoCircleRepository(table)
    repo.save_circle(
        Circle(
            circle_id=CircleId("circle-1"),
            owner_person_id=MONA,
            members=(
                CircleMember(
                    membership_id=MembershipId("m-1"),
                    circle_id=CircleId("circle-1"),
                    person_id=MAYA,
                    role=ResponderRole.PRIMARY,
                    priority=1,
                    status=MemberStatus.ACCEPTED,
                    display_name="Maya",
                ),
            ),
        )
    )
    raw = str(table.scan()["Items"])
    for forbidden in ("phone", "msisdn", "email", "+1", "+44"):
        assert forbidden not in raw.lower(), f"{forbidden!r} leaked into the member item"


# -- audit --------------------------------------------------------------------


def test_the_audit_trail_reads_back_in_chronological_order(table: Any) -> None:
    log = DynamoAuditLog(table)
    alert_id = AlertId("alert-1")
    for minute, event in enumerate(["CHECK_REQUESTED", "REMINDER_SENT", "CIRCLE_NOTIFIED"]):
        log.append(
            alert_id=alert_id,
            actor_type="SYSTEM",
            actor_id="workflow",
            event_type=event,
            at=DUE_AT + timedelta(minutes=minute * 10),
        )

    events = DynamoAuditLog(table).for_alert(alert_id)
    assert [e["eventType"] for e in events] == [
        "CHECK_REQUESTED",
        "REMINDER_SENT",
        "CIRCLE_NOTIFIED",
    ]
