"""Expected Moments.

An Expected Moment is *something that should reasonably happen by a particular time*. It
is the product's central abstraction: everything else derives from it.

Scheduling is done in the plan's IANA timezone, not in UTC and not in the device's zone.
A plan that says "check on me at nine every evening" means nine in the subject's evening,
which is a different UTC instant before and after a DST change. Computing this in UTC
silently moves a safety deadline by an hour twice a year -- in the wrong direction half
the time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from .clock import require_aware
from .errors import PlanValidationError
from .ids import MomentId, PlanVersionId
from .plan import Trigger, TriggerKind

WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")


class MomentStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    DUE = "DUE"
    RESOLVED = "RESOLVED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class ExpectedMoment:
    """One expectation, and the window of acceptable uncertainty after it."""

    moment_id: MomentId
    version_id: PlanVersionId
    due_at: datetime
    grace_until: datetime
    status: MomentStatus = MomentStatus.SCHEDULED
    is_drill: bool = False
    time_scale: float = 1.0

    def __post_init__(self) -> None:
        require_aware(self.due_at, "due_at")
        require_aware(self.grace_until, "grace_until")
        if self.grace_until < self.due_at:
            raise PlanValidationError("grace cannot end before the moment is due")
        if not 0 < self.time_scale <= 1.0:
            raise PlanValidationError("moment time_scale must be in (0, 1]")

    def is_due(self, now: datetime) -> bool:
        return now >= self.due_at

    def grace_elapsed(self, now: datetime) -> bool:
        """Whether the acceptable-uncertainty window has passed and contact should begin."""
        return now >= self.grace_until


def resolve_zone(timezone: str) -> ZoneInfo:
    """Resolve an IANA zone name, or fail as a domain error.

    Shared with the compiler: an unknown zone must be rejected at compile time, not
    discovered at 21:00 when a Moment fails to schedule.
    """
    try:
        return ZoneInfo(timezone)
    except Exception as exc:
        raise PlanValidationError(f"unknown timezone {timezone!r}") from exc


def _parse_time_of_day(value: str) -> time:
    try:
        hour, minute = (int(part) for part in value.split(":"))
        return time(hour=hour, minute=minute)
    except (ValueError, TypeError) as exc:
        raise PlanValidationError(f"invalid time_of_day {value!r}, expected HH:MM") from exc


def _localise(day: datetime, at: time, zone: ZoneInfo) -> datetime:
    """Attach a local wall-clock time to a date, resolving DST edges explicitly.

    Spring forward: the wall time may not exist. We take the first valid instant after the
    gap rather than silently skipping the day -- a check that does not happen is far worse
    than a check that happens an hour late.

    Fall back: the wall time happens twice. We take the *first* occurrence (``fold=0``),
    which is the earlier instant, so protection starts sooner rather than later.
    """
    naive = datetime.combine(day.date(), at)
    candidate = naive.replace(tzinfo=zone, fold=0)

    # A non-existent local time does not survive a UTC round trip unchanged.
    round_tripped = candidate.astimezone(UTC).astimezone(zone)
    if round_tripped.hour != at.hour or round_tripped.minute != at.minute:
        return round_tripped
    return candidate


def next_due_at(trigger: Trigger, timezone: str, after: datetime) -> datetime | None:
    candidate = _next_unbounded(trigger, timezone, after)
    if candidate is not None and trigger.until_at is not None and candidate > trigger.until_at:
        return None
    return candidate


def _next_unbounded(trigger: Trigger, timezone: str, after: datetime) -> datetime | None:
    """The next instant this trigger expects something to happen, strictly after ``after``.

    Always returned in **UTC**, even though the arithmetic happens in the plan's zone.

    That normalisation is not cosmetic. CPython subtracts two aware datetimes that share a
    ``tzinfo`` object by taking the naive difference, without consulting ``utcoffset()``.
    Two zone-local datetimes spanning a DST change therefore subtract to 24 hours when the
    real elapsed time is 23 -- silently, with no error. Handing UTC to every caller means
    no downstream duration (a lease, a grace window, a paused ladder) can inherit that.

    Returns None when a one-time trigger has already passed.
    """
    require_aware(after, "after")

    if trigger.kind is TriggerKind.ONE_TIME:
        assert trigger.due_at is not None  # noqa: S101 - guaranteed by Trigger.__post_init__
        return trigger.due_at.astimezone(UTC) if trigger.due_at > after else None

    if trigger.kind is TriggerKind.RELATIVE:
        assert trigger.offset_seconds is not None  # noqa: S101
        return (after + timedelta(seconds=trigger.offset_seconds)).astimezone(UTC)

    zone = resolve_zone(timezone)
    assert trigger.time_of_day is not None  # noqa: S101
    at = _parse_time_of_day(trigger.time_of_day)
    local_after = after.astimezone(zone)

    allowed = set(trigger.days_of_week) if trigger.days_of_week else set(WEEKDAYS)
    unknown = allowed - set(WEEKDAYS)
    if unknown:
        raise PlanValidationError(f"unknown days_of_week {sorted(unknown)}")

    forward = _next_anchor(local_after, at, zone, allowed)
    if forward is None:
        return None

    if not trigger.interval_seconds:
        return forward.astimezone(UTC)

    # Interval semantics, stated explicitly because the schema leaves them open:
    # ``time_of_day`` anchors a chain, the chain repeats every ``interval_seconds``, and
    # each day's anchor re-syncs it. So "22:00 every three hours" yields 22:00, 01:00,
    # 04:00 ... and lands back exactly on 22:00 the next day rather than drifting.
    #
    # The caller applies the explicit until_at bound to this candidate.
    previous = _previous_anchor(local_after, at, zone, allowed)
    if previous is None:
        return forward.astimezone(UTC)

    stepped = _step_interval(previous, trigger.interval_seconds, after)
    return min(stepped, forward).astimezone(UTC)


def _next_anchor(
    local_after: datetime, at: time, zone: ZoneInfo, allowed: set[str]
) -> datetime | None:
    """The first allowed day's wall time strictly after ``local_after``.

    Nine days of lookahead covers any weekday pattern plus a day of slack for a DST shift
    that moves an occurrence across a boundary.
    """
    for offset in range(0, 9):
        day = local_after + timedelta(days=offset)
        if WEEKDAYS[day.weekday()] not in allowed:
            continue
        candidate = _localise(day, at, zone)
        if candidate > local_after:
            return candidate
    return None


def _previous_anchor(
    local_after: datetime, at: time, zone: ZoneInfo, allowed: set[str]
) -> datetime | None:
    """The most recent allowed day's wall time at or before ``local_after``."""
    for offset in range(0, 9):
        day = local_after - timedelta(days=offset)
        if WEEKDAYS[day.weekday()] not in allowed:
            continue
        candidate = _localise(day, at, zone)
        if candidate <= local_after:
            return candidate
    return None


def _step_interval(anchor: datetime, interval_seconds: int, after: datetime) -> datetime:
    """Walk an intra-day repeat forward from a passed anchor."""
    elapsed = (after.astimezone(UTC) - anchor.astimezone(UTC)).total_seconds()
    steps = int(elapsed // interval_seconds) + 1
    return anchor + timedelta(seconds=interval_seconds * steps)


def moment_for(
    *,
    moment_id: MomentId,
    version_id: PlanVersionId,
    due_at: datetime,
    grace_seconds: int,
    is_drill: bool = False,
    time_scale: float = 1.0,
) -> ExpectedMoment:
    return ExpectedMoment(
        moment_id=moment_id,
        version_id=version_id,
        due_at=due_at,
        grace_until=due_at + timedelta(seconds=grace_seconds),
        is_drill=is_drill,
        time_scale=time_scale,
    )
