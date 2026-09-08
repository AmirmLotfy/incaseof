"""Account settings that determine how a plan may be scheduled and communicated."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .clock import require_aware
from .errors import DomainError
from .ids import PersonId


class SupportedCountry(StrEnum):
    EGYPT = "EG"
    UNITED_STATES = "US"


class SupportedLocale(StrEnum):
    ENGLISH = "en"
    ARABIC = "ar"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DELETION_PENDING = "DELETION_PENDING"
    DELETED = "DELETED"


@dataclass(frozen=True, slots=True)
class Profile:
    person_id: PersonId
    display_name: str
    locale: SupportedLocale
    timezone: str
    country: SupportedCountry
    status: AccountStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.display_name or self.display_name != self.display_name.strip():
            raise DomainError("display_name must contain visible text without outer whitespace")
        if len(self.display_name) > 60:
            raise DomainError("display_name must be 60 characters or fewer")
        if not self.timezone or self.timezone != self.timezone.strip() or len(self.timezone) > 64:
            raise DomainError("timezone must be a valid IANA timezone")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise DomainError("timezone must be a valid IANA timezone") from error
        require_aware(self.created_at, "profile.created_at")
        require_aware(self.updated_at, "profile.updated_at")
        if self.updated_at < self.created_at:
            raise DomainError("profile.updated_at cannot precede profile.created_at")

    def update(
        self,
        *,
        at: datetime,
        display_name: str | None = None,
        locale: SupportedLocale | None = None,
        timezone: str | None = None,
        country: SupportedCountry | None = None,
    ) -> Profile:
        require_aware(at, "profile.updated_at")
        if self.status is not AccountStatus.ACTIVE:
            raise DomainError("an account pending deletion cannot be updated")
        return replace(
            self,
            display_name=display_name if display_name is not None else self.display_name,
            locale=locale if locale is not None else self.locale,
            timezone=timezone if timezone is not None else self.timezone,
            country=country if country is not None else self.country,
            updated_at=at,
        )
