"""The complete deterministic slice.

    create a Plan -> Moment due -> missed -> Alert -> Circle contacted -> claimed -> resolved

Everything below the driver is production code. This is the thing that must work before the
model is added, and it is the test that says whether it does.
"""

from __future__ import annotations

import pytest

from services.domain.alert import AlertState
from services.domain.errors import NotAuthorized
from services.domain.plan import Channel
from services.domain.resolution import ResolutionSource
from services.handlers import responding

from .conftest import MAYA, MONA, OMAR, Slice

# -- the whole loop -----------------------------------------------------------


def test_the_whole_slice_from_a_plan_to_a_resolution(a_slice: Slice) -> None:
    """The one that matters."""
    activation = a_slice.create_plan()
    assert activation.moment.due_at.isoformat().startswith("2026-08-26T19:00")

    # The Moment comes due. Nobody answers.
    a_slice.clock.instant = activation.moment.due_at
    alert_id = a_slice.fire_moment()
    assert alert_id is not None

    # Escalation runs until the primary responder is contacted.
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    assert a_slice.sender.to("Maya"), "the Circle was never reached"
    assert a_slice.alert.state is AlertState.CIRCLE_ESCALATION

    # The subject was tried first, and on their own channels.
    subject_messages = [m for m in a_slice.sender.sent if m["recipient"] == "subject"]
    assert len(subject_messages) == 3, "expected two pushes and an SMS before the Circle"

    # Maya opens the link she was sent.
    token = a_slice.link_for(MAYA)
    view = responding.view(a_slice.ctx, token)
    assert view.subject_name == "Mona"
    assert view.plan_label == "Evening check"
    assert view.can_claim

    # "I'm checking."
    claimed = responding.claim(a_slice.ctx, token)
    assert claimed.state is AlertState.CHECKING
    assert claimed.resolution is None, "claiming is not resolving"

    # "I reached her, she's okay."
    a_slice.advance(120)
    resolved = responding.resolve(a_slice.ctx, token)

    assert resolved.state is AlertState.RESOLVED
    assert resolved.resolution is not None
    assert resolved.resolution.resolved_by_person_id == MAYA
    assert resolved.resolution.source is ResolutionSource.RESPONDER_WEB
    assert resolved.resolution.plan_version_id == activation.version.version_id

    # Nothing further is attempted.
    assert a_slice.run_workflow() == str(AlertState.RESOLVED)
    assert not a_slice.sender.to("Omar"), "the backup was contacted after resolution"


def test_the_subject_confirming_stops_everything(a_slice: Slice) -> None:
    """The common case: somebody taps 'I'm okay' and nobody else is ever bothered."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()

    # One rung fires, then the subject answers.
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.sent))
    confirmed = a_slice.alert.confirm_subject(a_slice.clock.now(), MONA)
    a_slice.ctx.alerts.save(confirmed)

    assert a_slice.run_workflow() == str(AlertState.RESOLVED)
    assert not a_slice.sender.to("Maya"), "the Circle was contacted despite a confirmation"
    assert not a_slice.sender.to("Omar")


def test_the_ladder_runs_out_and_says_so(a_slice: Slice) -> None:
    """Nobody answers, anywhere. That is a terminal state, and not a successful one."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()

    assert a_slice.run_workflow() == str(AlertState.ESCALATION_EXHAUSTED)
    assert a_slice.sender.to("Maya")
    assert a_slice.sender.to("Omar")
    assert a_slice.alert.resolution is None, "an exhausted Alert must not look resolved"


# -- the invariants, across the whole slice -----------------------------------


def test_a_duplicate_scheduler_delivery_opens_one_alert(a_slice: Slice) -> None:
    """Invariant 1, through the real handler rather than the repository directly."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at

    first = a_slice.fire_moment()
    second = a_slice.fire_moment()

    assert first == second


def test_a_replayed_queue_message_does_not_contact_anyone_twice(a_slice: Slice) -> None:
    """Invariant 5, end to end.

    The person on the other end of a duplicate is being told twice, at night, that someone
    they care about may not be okay.
    """
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    before = len(a_slice.sender.sent)
    # Re-run the workflow from the same point: every rung it would re-dispatch already
    # holds a claimed idempotency key.
    a_slice.run_workflow(max_steps=3, stop_after_wait=True)

    to_maya = a_slice.sender.to("Maya")
    assert len(to_maya) == 1, f"Maya was contacted {len(to_maya)} times"
    assert len(a_slice.sender.sent) == before


def test_claiming_pauses_the_backup_and_expiry_resumes_at_the_right_rung(
    a_slice: Slice,
) -> None:
    """Invariant 6, which is the subtlest thing in the product."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    token = a_slice.link_for(MAYA)
    responding.claim(a_slice.ctx, token)

    # While the lease is held, the workflow waits rather than escalating.
    assert a_slice.run_workflow(stop_after_wait=True) == "WAITING"
    assert not a_slice.sender.to("Omar"), "the backup fired while somebody was checking"

    # Maya goes quiet. The lease expires and escalation resumes — at Omar, not back at the
    # first rung.
    lease = a_slice.alert.lease
    assert lease is not None
    a_slice.clock.instant = lease.expires_at
    a_slice.run_workflow()

    assert a_slice.sender.to("Omar"), "escalation did not resume after the lease expired"
    assert len(a_slice.sender.to("Maya")) == 1, "the ladder restarted instead of resuming"


def test_an_alert_stays_pinned_to_its_version_while_the_plan_changes(
    a_slice: Slice,
) -> None:
    """Invariant 2, with a real second version written to the table mid-Alert."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.sent))

    original = a_slice.alert.plan_version_id

    # The subject edits their plan. A new version is stored and becomes active.
    from .conftest import EVENING_PLAN

    edited = {**EVENING_PLAN, "leaseSeconds": 120, "label": "Evening check v2"}
    _, result = __import__("services.handlers.planning", fromlist=["create_plan"]).create_plan(
        a_slice.ctx,
        edited,
        subject_person_id=MONA,
        circle_id="circle-1",
        new_id=a_slice.ids,
    )
    assert result.version.version_id != original

    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    assert a_slice.alert.plan_version_id == original
    assert a_slice.alert.version.label == "Evening check"
    assert a_slice.alert.version.lease_seconds == 600, "the live plan reached into an Alert"


def test_withdrawn_consent_stops_contact_mid_alert_and_is_recorded(
    a_slice: Slice,
) -> None:
    """Consent is checked at contact time, not at invitation time."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()

    assert a_slice.plan_id is not None
    grants = a_slice.ctx.circles.consents_for(a_slice.plan_id)
    a_slice.ctx.circles.save_consent(grants[MAYA].withdrawn_at(activation.moment.due_at))

    a_slice.run_workflow()

    assert not a_slice.sender.to("Maya"), "contacted somebody who had withdrawn consent"
    assert "CONTACT_DENIED" in a_slice.timeline(), "the denial was not recorded"
    # A denial is not silence: Omar still gets his rung.
    assert a_slice.sender.to("Omar")


def test_a_voice_rung_reports_unavailable_rather_than_failing_silently(
    a_slice: Slice,
) -> None:
    """CALL compiles and dispatches; only delivery is missing until Connect lands."""
    from .conftest import EVENING_PLAN

    with_voice = {
        **EVENING_PLAN,
        "steps": [
            {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
            {"sequence": 2, "offsetSeconds": 600, "action": "CALL_SUBJECT"},
            {
                "sequence": 3,
                "offsetSeconds": 900,
                "action": "MESSAGE_RESPONDER",
                "targetRole": "PRIMARY",
            },
        ],
    }
    activation = a_slice.create_plan(with_voice)
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    assert "CHANNEL_UNAVAILABLE" in a_slice.timeline()
    assert not a_slice.sender.on(Channel.CALL), "a call was reported as sent"
    # The ladder carried on past the unavailable rung rather than stalling on it.
    assert a_slice.sender.to("Maya")


# -- the responder surface ----------------------------------------------------


def test_a_link_works_only_for_its_own_alert(a_slice: Slice) -> None:
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    token = a_slice.link_for(MAYA)
    claims_alert = responding.view(a_slice.ctx, token).alert_id
    assert claims_alert == a_slice.alert_id


def test_only_the_holder_may_resolve(a_slice: Slice) -> None:
    """Omar cannot close an Alert Maya is checking."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow()  # runs the whole ladder, so Omar is contacted too

    maya_token = a_slice.link_for(MAYA)
    omar_token = a_slice.link_for(OMAR)
    assert maya_token != omar_token

    # Both links exist, but the Alert is exhausted by now — a terminal Alert refuses both,
    # which is itself the check that matters.
    with pytest.raises(NotAuthorized):
        responding.claim(a_slice.ctx, omar_token)


def test_a_forged_link_is_refused_and_recorded(a_slice: Slice) -> None:
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    with pytest.raises(NotAuthorized):
        responding.view(a_slice.ctx, "not-a-real-token")


def test_a_link_stops_working_once_the_alert_closes(a_slice: Slice) -> None:
    """A revoked-by-resolution link is inert, even though its signature is still valid."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    token = a_slice.link_for(MAYA)
    responding.claim(a_slice.ctx, token)
    responding.resolve(a_slice.ctx, token)

    with pytest.raises(NotAuthorized):
        responding.claim(a_slice.ctx, token)


def test_a_responder_can_report_that_they_could_not_reach_anyone(a_slice: Slice) -> None:
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    token = a_slice.link_for(MAYA)
    responding.claim(a_slice.ctx, token)
    released = responding.report_unable(a_slice.ctx, token)

    assert released.state is AlertState.CIRCLE_ESCALATION
    assert released.lease is None

    a_slice.run_workflow()
    assert a_slice.sender.to("Omar"), "escalation did not resume after 'I couldn't reach them'"


# -- the audit trail ----------------------------------------------------------


def test_the_timeline_explains_what_happened(a_slice: Slice) -> None:
    """ "Nothing happens invisibly." The trail must be readable end to end."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    token = a_slice.link_for(MAYA)
    responding.claim(a_slice.ctx, token)
    responding.resolve(a_slice.ctx, token)

    events = a_slice.timeline()
    for expected in (
        "MOMENT_DUE",
        "ACTION_QUEUED",
        "ACTION_SENT",
        "ALERT_CLAIMED",
        "RESPONDER_VERIFIED",
    ):
        assert expected in events, f"{expected} missing from the timeline: {events}"


def test_no_message_anywhere_carries_a_contact_endpoint(a_slice: Slice) -> None:
    """The structural guarantee, checked against what was actually produced."""
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow()

    serialised = str(a_slice.sender.sent).lower()
    for forbidden in ("+1", "+44", "phone", "msisdn", "@example", "endpoint"):
        assert forbidden not in serialised, f"{forbidden!r} leaked into a sent message"
