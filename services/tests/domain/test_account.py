from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.clock import utc
from services.domain.errors import DomainError
from services.domain.ids import PersonId

NOW = utc(2026, 9, 6, 8, 0)


def _profile() -> Profile:
    return Profile(
        person_id=PersonId("person-1"),
        display_name="Mona",
        locale=SupportedLocale.ARABIC,
        timezone="Africa/Cairo",
        country=SupportedCountry.EGYPT,
        status=AccountStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_profile_accepts_both_launch_markets_and_locales() -> None:
    egypt = _profile()
    us = replace(
        egypt,
        locale=SupportedLocale.ENGLISH,
        timezone="America/New_York",
        country=SupportedCountry.UNITED_STATES,
    )
    assert (egypt.country, us.country) == (
        SupportedCountry.EGYPT,
        SupportedCountry.UNITED_STATES,
    )


@pytest.mark.parametrize("timezone", ["", "Cairo", "Mars/Olympus"])
def test_profile_rejects_an_invalid_timezone(timezone: str) -> None:
    with pytest.raises(DomainError, match="IANA timezone"):
        replace(_profile(), timezone=timezone)


def test_profile_update_keeps_creation_identity_and_rejects_deleting_accounts() -> None:
    updated = _profile().update(
        at=NOW + timedelta(minutes=1),
        display_name="Mona Lotfy",
        locale=SupportedLocale.ENGLISH,
    )
    assert updated.created_at == NOW
    assert updated.display_name == "Mona Lotfy"
    assert updated.locale is SupportedLocale.ENGLISH

    with pytest.raises(DomainError, match="pending deletion"):
        replace(updated, status=AccountStatus.DELETION_PENDING).update(
            at=NOW + timedelta(minutes=2), display_name="Changed"
        )
