"""Where a person can actually be reached.

The most sensitive thing this system stores, and the reason for most of the architecture
around it. A phone number here, joined to the Circle it belongs to, is a map of who is
close to whom — which is a stalking risk, not merely a privacy one.

So the rules are absolute, and they are structural rather than procedural:

* The value is **KMS-encrypted at rest**. It is never stored in plaintext.
* It is **never returned to a client**, at any endpoint, in any shape.
* It is **never logged**, at any level, including DEBUG.
* It **never reaches the model** — there is no tool parameter that could carry it.
* It is resolved at the last possible moment, in the worker, and nowhere else.

This module deliberately holds no decryption. Decrypting is the adapter's job, at the point
of sending, so a domain object can never carry a readable number around.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .ids import PersonId


class EndpointType(StrEnum):
    PHONE = "PHONE"
    # S105: the *name* of a channel, not a secret. The value it identifies is sealed.
    PUSH_TOKEN = "PUSH_TOKEN"  # noqa: S105
    EMAIL = "EMAIL"


class EndpointStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class ContactEndpoint:
    """A way to reach somebody, with the value kept sealed.

    ``ciphertext`` is opaque here on purpose. Holding a decrypted number on a domain object
    would mean it could be passed, serialised, or logged by any code that touched it.
    """

    endpoint_id: str
    person_id: PersonId
    endpoint_type: EndpointType
    ciphertext: bytes
    status: EndpointStatus
    verified_at: datetime | None = None

    @property
    def is_usable(self) -> bool:
        """Only a verified endpoint may be contacted.

        An unverified number might belong to somebody else entirely — a typo, or a number
        that has since been reassigned. Messaging it would tell a stranger that a specific
        person has not come home.
        """
        return self.status is EndpointStatus.VERIFIED

    def __repr__(self) -> str:
        """Never render the ciphertext.

        A repr ends up in tracebacks, logs and error trackers. This one shows the shape and
        nothing else.
        """
        return (
            f"ContactEndpoint(id={self.endpoint_id!r}, person={self.person_id!r}, "
            f"type={self.endpoint_type}, status={self.status}, value=<sealed>)"
        )


def redact(value: str) -> str:
    """Render an endpoint for a human, without disclosing it.

    Used in the audit trail and in operator-facing views, where somebody needs to confirm
    *which* endpoint was used without being handed the endpoint itself.
    """
    if len(value) <= 4:
        return "•" * len(value)
    return f"{'•' * (len(value) - 4)}{value[-4:]}"
