"""Signed Circle invitations and their persisted, replay-safe state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from .ids import CircleId, InvitationId, MembershipId, PersonId, PlanId


class InvitationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class CircleInvitation:
    invitation_id: InvitationId
    circle_id: CircleId
    owner_person_id: PersonId
    responder_person_id: PersonId
    membership_id: MembershipId
    plan_ids: tuple[PlanId, ...]
    expires_at: datetime
    status: InvitationStatus = InvitationStatus.PENDING

    def accept(self) -> CircleInvitation:
        return replace(self, status=InvitationStatus.ACCEPTED)

    def decline(self) -> CircleInvitation:
        return replace(self, status=InvitationStatus.DECLINED)
