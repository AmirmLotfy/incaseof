"""Drill Mode.

"Test this plan" and the hackathon demo are the same thing: the production workflow on a
compressed schedule. There is no demo code path, and these tests are what keeps it that way
— if a shortcut were ever added for the demo, the compressed run would stop matching the
real one and this file would fail.

Only the *schedule* is scaled. Timestamps stay real, so the audit trail never lies about
when something happened. See docs/DEMO.md.
"""

from __future__ import annotations

from services.domain.alert import AlertState
from services.domain.clock import REAL_TIME, TimeScale
from services.handlers import bootstrap, responding

from .conftest import MAYA, Slice


def _compress(a_slice: Slice, factor: float) -> Slice:
    a_slice.ctx = bootstrap.Context(**{**a_slice.ctx.__dict__, "scale": TimeScale(factor)})
    return a_slice


def test_a_drill_reaches_the_same_outcome_as_a_real_run(a_slice: Slice) -> None:
    """Same states, same contacts, same resolution — on a fiftieth of the clock."""
    _compress(a_slice, 0.02)

    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    assert a_slice.alert.state is AlertState.CIRCLE_ESCALATION
    subject_messages = [m for m in a_slice.sender.sent if m["recipient"] == "subject"]
    assert len(subject_messages) == 3, "the subject ladder was skipped under compression"

    token = a_slice.link_for(MAYA)
    responding.claim(a_slice.ctx, token)
    resolved = responding.resolve(a_slice.ctx, token)

    assert resolved.state is AlertState.RESOLVED
    assert resolved.resolution is not None


def test_compression_shortens_the_ladder_and_nothing_else(a_slice: Slice) -> None:
    """A twenty-five minute ladder finishes in thirty seconds."""
    _compress(a_slice, 0.02)

    activation = a_slice.create_plan()
    started = activation.moment.due_at
    a_slice.clock.instant = started
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    elapsed = (a_slice.clock.now() - started).total_seconds()

    # Grace is 600s and the primary rung sits at +1500s: 2100s at real speed.
    assert elapsed < 200, f"compression did not apply: {elapsed}s elapsed"
    assert elapsed > 0, "the ladder took no time at all, which means it did not run"


def test_a_drill_records_real_timestamps(a_slice: Slice) -> None:
    """The clock is never scaled, only the offsets.

    A scaled clock would put fictional times in the audit trail, and the trail is the thing
    that has to be trustworthy afterwards.
    """
    _compress(a_slice, 0.02)

    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.sent))

    events = a_slice.ctx.audit.for_alert(a_slice.alert_id)  # type: ignore[arg-type]
    stamps = [str(event["at"]) for event in events]
    assert stamps, "nothing was recorded"
    for stamp in stamps:
        assert stamp.startswith("2026-08-26"), f"a scaled clock leaked into the trail: {stamp}"


def test_a_drill_enforces_the_same_policy(a_slice: Slice) -> None:
    """Compression must not be a way around authorisation."""
    _compress(a_slice, 0.02)

    activation = a_slice.create_plan()
    assert a_slice.plan_id is not None
    grants = a_slice.ctx.circles.consents_for(a_slice.plan_id)
    a_slice.ctx.circles.save_consent(grants[MAYA].withdrawn_at(activation.moment.due_at))

    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.run_workflow()

    assert not a_slice.sender.to("Maya"), "compression bypassed a consent check"
    assert "CONTACT_DENIED" in a_slice.timeline()


def test_a_drill_still_suppresses_duplicates(a_slice: Slice) -> None:
    """Idempotency is not relaxed for a demo."""
    _compress(a_slice, 0.02)

    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    a_slice.fire_moment()
    a_slice.run_workflow(until=lambda: bool(a_slice.sender.to("Maya")))

    assert len(a_slice.sender.to("Maya")) == 1


def test_real_time_is_the_default(a_slice: Slice) -> None:
    """Nothing is compressed unless something asked for it."""
    assert a_slice.ctx.scale is REAL_TIME
    assert not a_slice.ctx.scale.is_compressed
