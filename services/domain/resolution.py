"""Resolution records.

Every resolution records who, when, how, source, plan version and incident id, because
"why did this stop?" must always be answerable. See docs/PRODUCT-STATES.md section 5.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .ids import AlertId, PersonId, PlanVersionId
from .plan import StopCondition


class ResolutionSource(StrEnum):
    """Where the closing input physically came from.

    Recorded separately from the method because "the subject confirmed" and "someone
    holding the subject's unlocked phone tapped a button" are the same method from
    different sources, and an audit trail should be able to tell them apart later.
    """

    APP = "APP"
    NOTIFICATION_ACTION = "NOTIFICATION_ACTION"
    RESPONDER_WEB = "RESPONDER_WEB"
    SMS_REPLY = "SMS_REPLY"
    VOICE_IVR = "VOICE_IVR"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True, slots=True)
class Resolution:
    """An immutable record of how one Alert closed."""

    alert_id: AlertId
    resolved_by_person_id: PersonId | None
    method: StopCondition
    source: ResolutionSource
    plan_version_id: PlanVersionId
    created_at: datetime
    reason_code: str | None = None

    def __post_init__(self) -> None:
        # A cancellation has no resolver in the "someone confirmed" sense, but every other
        # method does: an Alert that closed with nobody attached is unauditable.
        needs_person = self.method in {
            StopCondition.SUBJECT_EXPLICIT_CONFIRMATION,
            StopCondition.RESPONDER_VERIFIED_CONTACT,
            StopCondition.VERIFIED_CALL_RESPONSE,
        }
        if needs_person and self.resolved_by_person_id is None:
            raise ValueError(f"{self.method} requires the person who resolved it")
