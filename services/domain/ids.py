"""Typed identifiers.

Distinct types for each entity so a PersonId cannot be passed where an AlertId belongs.
mypy enforces this at no runtime cost.
"""

from __future__ import annotations

import uuid
from typing import NewType, Protocol

PersonId = NewType("PersonId", str)
CircleId = NewType("CircleId", str)
MembershipId = NewType("MembershipId", str)
PlanId = NewType("PlanId", str)
PlanVersionId = NewType("PlanVersionId", str)
StepId = NewType("StepId", str)
MomentId = NewType("MomentId", str)
AlertId = NewType("AlertId", str)
ActionId = NewType("ActionId", str)
ConsentId = NewType("ConsentId", str)
InvitationId = NewType("InvitationId", str)
DeviceId = NewType("DeviceId", str)


class IdFactory(Protocol):
    """Injected so tests can produce stable, readable identifiers."""

    def __call__(self) -> str: ...


def uuid_factory() -> str:
    return str(uuid.uuid4())


class SequentialIds:
    """Deterministic ids for tests: ``alert-1``, ``alert-2``.

    A failing assertion that names ``alert-2`` is diagnosable; one that names a UUID is not.
    """

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n}"
