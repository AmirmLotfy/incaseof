"""Time.

The domain never calls ``datetime.now()``. Time arrives as an argument, because lease
expiry, grace windows and escalation offsets are the behaviour most worth testing and the
least testable if the clock is ambient.

Demo compression scales *offsets*, never the clock. A scaled clock would make timestamps
lie in the audit trail; scaled offsets keep every recorded time real while letting a
ten-minute ladder run in twelve seconds. See docs/DEMO.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Source of the current instant, always timezone-aware UTC."""

    def now(self) -> datetime: ...


class SystemClock:
    """Real time. Used in production; never in a unit test."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass
class FixedClock:
    """Controllable time for tests.

    Mutable by design: a test advances it to drive a lease to expiry rather than sleeping.
    """

    instant: datetime

    def now(self) -> datetime:
        return self.instant

    def advance(self, seconds: float) -> datetime:
        self.instant += timedelta(seconds=seconds)
        return self.instant


@dataclass(frozen=True)
class TimeScale:
    """Schedule compression factor.

    ``1.0`` is real time. ``0.02`` turns ten minutes into twelve seconds for a demo, using
    the same state machine, the same workflow and the same policy checks.
    """

    factor: float = 1.0

    def __post_init__(self) -> None:
        if not 0 < self.factor <= 1.0:
            raise ValueError(f"time scale must be in (0, 1], got {self.factor}")

    @property
    def is_compressed(self) -> bool:
        """Whether a surface using this scale must display the demo banner."""
        return self.factor != 1.0

    def apply(self, seconds: int) -> float:
        """Compress an offset. Never applied to a timestamp."""
        return seconds * self.factor


REAL_TIME = TimeScale(1.0)


def utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    """Construct an aware UTC instant. Convenience for tests and fixtures."""
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def require_aware(moment: datetime, label: str) -> datetime:
    """Reject naive datetimes at the boundary.

    A naive timestamp in a safety deadline is a silent bug: it reads as correct locally
    and drifts by hours in another zone.
    """
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware; got naive {moment!r}")
    return moment
