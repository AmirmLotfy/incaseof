"""The escalation ladder.

This module computes **when** each rung is due and **which** rung is next. It never fires
anything: dispatch belongs to the workflow, and the timers belong to EventBridge. Keeping
the arithmetic here and pure is what lets every timing rule be tested in milliseconds.

Two rules carry the weight:

*Progress is tracked by attempted step, not by elapsed time.* The next rung is the lowest
sequence not yet attempted. That is what makes invariant 6 true by construction -- a
resumed ladder cannot restart, because the rungs behind it are already marked attempted.

*Pause time shifts the whole remaining schedule forward.* While a responder holds a
checking lease, backup escalation is paused. On release, the rungs that have not fired yet
move out by exactly the paused duration, so a responder who checks for nine minutes does
not cause the backup contact to fire the instant they give up.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from .clock import REAL_TIME, TimeScale
from .plan import EscalationStep, PlanVersion


@dataclass(frozen=True, slots=True)
class LadderState:
    """Progress through one Alert's ladder.

    ``started_at`` is the end of the grace window, which is when escalation begins -- not
    the due time. Grace is the acceptable-uncertainty period that precedes contact.
    """

    started_at: datetime
    paused_seconds: float = 0.0
    attempted: frozenset[int] = field(default_factory=frozenset)
    scale: TimeScale = REAL_TIME

    def due_at(self, step: EscalationStep) -> datetime:
        """When this rung should fire, accounting for compression and paused time."""
        offset = self.scale.apply(step.offset_seconds)
        return self.started_at + timedelta(seconds=offset + self.paused_seconds)

    def is_attempted(self, step: EscalationStep) -> bool:
        return step.sequence in self.attempted

    def mark_attempted(self, step: EscalationStep) -> LadderState:
        return replace(self, attempted=self.attempted | {step.sequence})

    def add_pause(self, seconds: float) -> LadderState:
        """Shift every not-yet-fired rung forward by a completed pause."""
        if seconds < 0:
            raise ValueError(f"paused duration cannot be negative, got {seconds}")
        return replace(self, paused_seconds=self.paused_seconds + seconds)


@dataclass(frozen=True, slots=True)
class Ladder:
    """A PlanVersion's steps plus one Alert's progress through them."""

    version: PlanVersion
    state: LadderState

    # -- what is next -----------------------------------------------------

    def next_step(self) -> EscalationStep | None:
        """The lowest-sequence rung not yet attempted, or None when exhausted."""
        for step in self.version.steps:
            if not self.state.is_attempted(step):
                return step
        return None

    def next_due_at(self) -> datetime | None:
        """When the next rung fires. This is the instant to hand EventBridge."""
        step = self.next_step()
        return None if step is None else self.state.due_at(step)

    def due_steps(self, now: datetime) -> tuple[EscalationStep, ...]:
        """Rungs that are due and not yet attempted.

        Returned in sequence order so a delayed worker replays them in the order the
        subject would have experienced them.
        """
        return tuple(
            step
            for step in self.version.steps
            if not self.state.is_attempted(step) and self.state.due_at(step) <= now
        )

    # -- phase ------------------------------------------------------------

    def subject_ladder_exhausted(self) -> bool:
        """Every subject-directed rung has been attempted.

        This is what moves an Alert from SELF_CONTACT to CIRCLE_ESCALATION: we have tried
        the person themselves and the uncertainty is unresolved.
        """
        return all(self.state.is_attempted(step) for step in self.version.subject_steps)

    def circle_ladder_exhausted(self) -> bool:
        """Every rung has been attempted and nobody closed the loop."""
        return self.next_step() is None

    def remaining_responder_steps(self) -> tuple[EscalationStep, ...]:
        return tuple(
            step for step in self.version.responder_steps if not self.state.is_attempted(step)
        )

    # -- transitions ------------------------------------------------------

    def attempt(self, step: EscalationStep) -> Ladder:
        return replace(self, state=self.state.mark_attempted(step))

    def pause_for(self, seconds: float) -> Ladder:
        return replace(self, state=self.state.add_pause(seconds))
