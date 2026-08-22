"""Idempotency keys for external actions.

Target: **zero duplicate external actions** (docs/ARCHITECTURE.md section 6). The person on
the other end of a duplicate is not a log line -- they are someone being told twice, at
night, that a person they care about may not be okay.

The key is derived, never generated. Two callers computing it for the same attempt must
produce the same string, because that is what makes the conditional write a deduplicator
rather than a race.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ids import AlertId, StepId


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """``alert_id + escalation_step_id + attempt_number``.

    Attempt number is part of the key so a *deliberate* retry -- a second attempt after a
    provider failure -- is a distinct action, while an accidental replay of the same
    attempt is not.
    """

    alert_id: AlertId
    step_id: StepId
    attempt_number: int

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError(f"attempt numbers start at 1, got {self.attempt_number}")

    def __str__(self) -> str:
        return f"{self.alert_id}:{self.step_id}:{self.attempt_number}"

    @property
    def value(self) -> str:
        return str(self)


def key_for(alert_id: AlertId, step_id: StepId, attempt_number: int = 1) -> IdempotencyKey:
    return IdempotencyKey(alert_id=alert_id, step_id=step_id, attempt_number=attempt_number)
