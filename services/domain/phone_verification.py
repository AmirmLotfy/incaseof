"""Phone ownership verification without carrying phone numbers through the domain.

The provider reference and endpoint id are opaque identifiers.  The readable destination
exists only inside the endpoint adapter and the provider call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from .account import SupportedCountry
from .clock import require_aware
from .errors import DomainError
from .ids import PersonId

_EGYPT_MOBILE = re.compile(r"^\+20(?:10|11|12|15)\d{8}$")
_US_MOBILE = re.compile(r"^\+1[2-9]\d{2}[2-9]\d{6}$")


class PhoneVerificationStatus(StrEnum):
    RESERVED = "RESERVED"
    SENT = "SENT"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PhoneVerificationRateLimited(DomainError):
    """A start request exceeded the per-person cooldown or daily ceiling."""


class OtpProviderUnavailable(Exception):
    """The OTP provider is absent or temporarily cannot serve a request."""


class OtpSendRejected(Exception):
    """The provider definitely rejected an OTP send."""


@dataclass(frozen=True, slots=True)
class PhoneVerification:
    verification_id: str
    person_id: PersonId
    endpoint_id: str
    provider_reference: str
    country: SupportedCountry
    status: PhoneVerificationStatus
    attempts: int
    created_at: datetime
    expires_at: datetime
    sent_at: datetime | None = None
    verified_at: datetime | None = None
    previous_endpoint_id: str | None = None

    def __post_init__(self) -> None:
        if not self.verification_id or len(self.verification_id) > 64:
            raise DomainError("verification id is invalid")
        if not self.endpoint_id:
            raise DomainError("endpoint id is required")
        if not self.provider_reference or len(self.provider_reference) > 48:
            raise DomainError("provider reference is invalid")
        require_aware(self.created_at, "phone_verification.created_at")
        require_aware(self.expires_at, "phone_verification.expires_at")
        if self.expires_at <= self.created_at:
            raise DomainError("phone verification must expire after creation")
        if self.attempts < 0 or self.attempts > 5:
            raise DomainError("phone verification attempts are invalid")

    def sent(self, at: datetime) -> PhoneVerification:
        require_aware(at, "phone_verification.sent_at")
        return replace(self, status=PhoneVerificationStatus.SENT, sent_at=at)

    def verified(self, at: datetime) -> PhoneVerification:
        require_aware(at, "phone_verification.verified_at")
        if at > self.expires_at:
            raise DomainError("phone verification has expired")
        return replace(self, status=PhoneVerificationStatus.VERIFIED, verified_at=at)


def validate_phone_for_country(value: str, country: SupportedCountry) -> str:
    """Return canonical E.164 input only when it belongs to the selected launch market."""
    if value != value.strip() or len(value) > 16:
        raise DomainError("phone number must use E.164 format")
    pattern = _EGYPT_MOBILE if country is SupportedCountry.EGYPT else _US_MOBILE
    if not pattern.fullmatch(value):
        raise DomainError(f"phone number does not match country {country.value}")
    return value
