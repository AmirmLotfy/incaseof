"""Moment scheduling, especially across DST.

"A plan without an explicit timezone is a bug: DST and travel silently move the deadline."
These tests use real European DST transitions (2026-03-29 and 2026-10-25) rather than
synthetic offsets, because the failure mode being guarded against is precisely the one
that only appears on real transition dates.
"""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from services.domain.clock import utc
from services.domain.errors import PlanValidationError
from services.domain.ids import MomentId, PlanVersionId
from services.domain.moment import moment_for, next_due_at
from services.domain.plan import Trigger, TriggerKind

AMS = ZoneInfo("Europe/Amsterdam")
CAIRO = "Africa/Cairo"


def daily(at: str, days: tuple[str, ...] = ()) -> Trigger:
    return Trigger(kind=TriggerKind.RECURRING, time_of_day=at, days_of_week=days)


# -- basics -------------------------------------------------------------------


def test_a_one_time_trigger_fires_once_and_then_never_again() -> None:
    due = utc(2026, 8, 26, 18, 0)
    trigger = Trigger(kind=TriggerKind.ONE_TIME, due_at=due)

    assert next_due_at(trigger, CAIRO, utc(2026, 8, 26, 12, 0)) == due
    assert next_due_at(trigger, CAIRO, utc(2026, 8, 26, 18, 0)) is None
    assert next_due_at(trigger, CAIRO, utc(2026, 8, 27, 0, 0)) is None


def test_a_relative_trigger_counts_from_activation() -> None:
    trigger = Trigger(kind=TriggerKind.RELATIVE, offset_seconds=5400)
    now = utc(2026, 8, 26, 12, 0)
    assert next_due_at(trigger, CAIRO, now) == now + timedelta(seconds=5400)


def test_a_daily_check_lands_at_the_local_wall_time() -> None:
    result = next_due_at(daily("21:00"), "Europe/Amsterdam", utc(2026, 8, 26, 12, 0))
    assert result is not None
    assert result.astimezone(AMS).hour == 21
    assert result.astimezone(AMS).minute == 0


def test_a_daily_check_already_passed_today_moves_to_tomorrow() -> None:
    after = utc(2026, 8, 26, 20, 0)  # 22:00 Amsterdam, past the 21:00 check
    result = next_due_at(daily("21:00"), "Europe/Amsterdam", after)
    assert result is not None
    local = result.astimezone(AMS)
    assert local.day == 27
    assert local.hour == 21


def test_weekday_restrictions_skip_the_days_not_listed() -> None:
    # 2026-08-26 is a Wednesday.
    result = next_due_at(daily("09:00", ("SAT", "SUN")), "Europe/Amsterdam", utc(2026, 8, 26, 6, 0))
    assert result is not None
    assert result.astimezone(AMS).weekday() == 5  # Saturday
    assert result.astimezone(AMS).day == 29


def test_an_unknown_timezone_is_rejected_rather_than_defaulted() -> None:
    with pytest.raises(PlanValidationError):
        next_due_at(daily("21:00"), "Mars/Olympus_Mons", utc(2026, 8, 26, 12, 0))


def test_an_unknown_weekday_is_rejected() -> None:
    with pytest.raises(PlanValidationError):
        next_due_at(daily("21:00", ("FUNDAY",)), CAIRO, utc(2026, 8, 26, 12, 0))


# -- DST ----------------------------------------------------------------------


def test_a_daily_check_keeps_its_local_time_across_a_dst_change() -> None:
    """The point of storing an IANA zone.

    21:00 Amsterdam is 20:00 UTC in winter and 19:00 UTC in summer. If this were computed
    in UTC the check would silently move by an hour, which for a safety deadline is a real
    change in when somebody gets contacted.
    """
    before = next_due_at(daily("21:00"), "Europe/Amsterdam", utc(2026, 3, 27, 12, 0))
    after = next_due_at(daily("21:00"), "Europe/Amsterdam", utc(2026, 3, 30, 12, 0))
    assert before is not None and after is not None

    assert before.astimezone(AMS).hour == 21
    assert after.astimezone(AMS).hour == 21
    # Compare offsets in the plan's zone: both results are normalised to UTC, where every
    # offset is zero by construction.
    assert before.astimezone(AMS).utcoffset() != after.astimezone(AMS).utcoffset(), (
        "expected the local offset to change across DST"
    )


def test_the_day_a_clock_springs_forward_is_still_only_23_hours() -> None:
    """Consecutive daily checks across the gap are 23 hours apart, not 24."""
    saturday = next_due_at(daily("21:00"), "Europe/Amsterdam", utc(2026, 3, 28, 12, 0))
    assert saturday is not None
    sunday = next_due_at(daily("21:00"), "Europe/Amsterdam", saturday)
    assert sunday is not None

    assert sunday - saturday == timedelta(hours=23)


def test_a_check_scheduled_inside_the_spring_forward_gap_still_happens() -> None:
    """02:30 does not exist on 2026-03-29 in Amsterdam.

    A check that silently does not happen is the worst possible outcome for this product,
    so the moment moves to the first valid instant after the gap instead of vanishing.
    """
    result = next_due_at(daily("02:30"), "Europe/Amsterdam", utc(2026, 3, 28, 12, 0))
    assert result is not None

    local = result.astimezone(AMS)
    assert local.day == 29
    assert (local.hour, local.minute) == (3, 30), f"expected the post-gap instant, got {local}"


def test_an_ambiguous_autumn_time_takes_the_earlier_instant() -> None:
    """02:30 happens twice on 2026-10-25. Protection starts at the first one."""
    result = next_due_at(daily("02:30"), "Europe/Amsterdam", utc(2026, 10, 24, 12, 0))
    assert result is not None

    local = result.astimezone(AMS)
    assert local.day == 25
    assert (local.hour, local.minute) == (2, 30)
    assert local.utcoffset() == timedelta(hours=2), "expected the pre-fallback (summer) offset"


# -- intervals ----------------------------------------------------------------


INTERVAL = Trigger(kind=TriggerKind.RECURRING, time_of_day="22:00", interval_seconds=10800)


def test_an_interval_chain_repeats_from_its_anchor() -> None:
    """22:00 every three hours yields 22:00, 01:00, 04:00 ... continuously.

    The chain runs on rather than stopping at dawn: the schema has no end bound, so a plan
    meant to cover a single night is expressed as RELATIVE or ONE_TIME instead. Asserting
    the real behaviour rather than the hoped-for one keeps that gap visible.
    """
    just_after_anchor = utc(2026, 8, 26, 20, 30)  # 22:30 Amsterdam
    first = next_due_at(INTERVAL, "Europe/Amsterdam", just_after_anchor)
    assert first is not None
    assert first.astimezone(AMS).hour == 1, "expected the 01:00 rung"

    second = next_due_at(INTERVAL, "Europe/Amsterdam", first)
    assert second is not None
    assert second - first == timedelta(seconds=10800)


def test_an_interval_chain_stays_locked_to_its_anchor() -> None:
    """Stepping repeatedly must land back on 22:00 rather than drifting off it."""
    moment = utc(2026, 8, 26, 20, 30)
    seen: list[str] = []
    for _ in range(9):
        nxt = next_due_at(INTERVAL, "Europe/Amsterdam", moment)
        assert nxt is not None
        seen.append(nxt.astimezone(AMS).strftime("%H:%M"))
        moment = nxt

    assert "22:00" in seen, f"chain drifted off its anchor: {seen}"


def test_every_interval_moment_sits_on_the_chain() -> None:
    """Mid-afternoon still falls on the chain that began at 22:00 the previous evening."""
    result = next_due_at(INTERVAL, "Europe/Amsterdam", utc(2026, 8, 26, 12, 0))
    assert result is not None
    local = result.astimezone(AMS)
    assert (local.hour - 22) % 3 == 0, f"{local:%H:%M} is not on the 22:00 three-hour chain"


# -- grace --------------------------------------------------------------------


def test_grace_defines_the_window_before_contact_begins() -> None:
    due = utc(2026, 8, 26, 18, 0)
    moment = moment_for(
        moment_id=MomentId("m-1"),
        version_id=PlanVersionId("pv-4"),
        due_at=due,
        grace_seconds=1800,
    )

    assert moment.is_due(due)
    assert not moment.grace_elapsed(due)
    assert not moment.grace_elapsed(due + timedelta(minutes=29))
    assert moment.grace_elapsed(due + timedelta(minutes=30))


def test_a_moment_cannot_have_grace_ending_before_it_is_due() -> None:
    with pytest.raises(PlanValidationError):
        moment_for(
            moment_id=MomentId("m-1"),
            version_id=PlanVersionId("pv-4"),
            due_at=utc(2026, 8, 26, 18, 0),
            grace_seconds=-60,
        )
