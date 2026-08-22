"""Circles, membership and consent.

Nobody becomes a safety contact by accident. Membership requires an invitation the person
accepted, and contact requires a consent grant that is **active at the moment of contact**
-- not merely active when they were invited. Somebody who withdraws consent mid-Alert must
stop being contacted immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .ids import CircleId, ConsentId, MembershipId, PersonId, PlanId
from .plan import ResponderRole


class MemberStatus(StrEnum):
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    REMOVED = "REMOVED"


class ConsentStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ContactChannelPermission(StrEnum):
    """Which channels a member agreed to be reached on.

    Separate from technical capability: a person may own a phone that can receive calls
    and still only have agreed to messages.
    """

    PUSH = "PUSH"
    SMS = "SMS"
    CALL = "CALL"


@dataclass(frozen=True, slots=True)
class ConsentGrant:
    """One person's agreement to be a safety contact for one plan.

    Records the policy version so a later change to what consent *means* does not silently
    reinterpret an agreement somebody already gave.
    """

    consent_id: ConsentId
    subject_person_id: PersonId
    responder_person_id: PersonId
    plan_id: PlanId
    status: ConsentStatus
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    policy_version: str = "1.0"
    channels: frozenset[ContactChannelPermission] = frozenset(
        {ContactChannelPermission.PUSH, ContactChannelPermission.SMS}
    )

    def is_active(self, now: datetime) -> bool:
        """Active *right now*, which is the only question that matters at contact time."""
        if self.status is not ConsentStatus.ACTIVE:
            return False
        if self.revoked_at is not None and now >= self.revoked_at:
            return False
        if self.expires_at is not None and now >= self.expires_at:
            return False
        return True

    def permits_channel(self, channel: ContactChannelPermission) -> bool:
        return channel in self.channels

    def withdrawn_at(self, now: datetime) -> ConsentGrant:
        from dataclasses import replace

        return replace(self, status=ConsentStatus.WITHDRAWN, revoked_at=now)


@dataclass(frozen=True, slots=True)
class CircleMember:
    """One person's place in a Circle.

    ``person_id`` is an identifier, never an endpoint. Phone numbers live encrypted in the
    contact-endpoint store and are resolved server-side at dispatch time -- they are never
    carried on this object, and never reach the model.
    """

    membership_id: MembershipId
    circle_id: CircleId
    person_id: PersonId
    role: ResponderRole
    priority: int
    status: MemberStatus
    display_name: str
    relationship: str | None = None

    @property
    def is_accepted(self) -> bool:
        return self.status is MemberStatus.ACCEPTED


@dataclass(frozen=True, slots=True)
class Circle:
    """The people a subject chose, and the roles they hold."""

    circle_id: CircleId
    owner_person_id: PersonId
    members: tuple[CircleMember, ...] = ()

    def member_for_role(self, role: ResponderRole) -> CircleMember | None:
        """The accepted member holding this role, lowest priority number first.

        Returns None rather than falling back to another role: silently contacting the
        backup because the primary declined would violate the plan the subject approved.
        """
        candidates = [m for m in self.members if m.role is role and m.is_accepted]
        if not candidates:
            return None
        return min(candidates, key=lambda m: m.priority)

    def member(self, person_id: PersonId) -> CircleMember | None:
        for candidate in self.members:
            if candidate.person_id == person_id:
                return candidate
        return None

    @property
    def accepted_members(self) -> tuple[CircleMember, ...]:
        return tuple(m for m in self.members if m.is_accepted)

    @property
    def filled_roles(self) -> frozenset[ResponderRole]:
        return frozenset(m.role for m in self.accepted_members)
