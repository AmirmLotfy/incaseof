from __future__ import annotations

from typing import Any

from services.adapters.profile import DynamoProfileRepository
from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.clock import utc
from services.domain.ids import PersonId


def test_profile_round_trips_in_the_person_partition(table: Any) -> None:
    profile = Profile(
        person_id=PersonId("person-1"),
        display_name="Mona",
        locale=SupportedLocale.ARABIC,
        timezone="Africa/Cairo",
        country=SupportedCountry.EGYPT,
        status=AccountStatus.ACTIVE,
        created_at=utc(2026, 9, 6, 8, 0),
        updated_at=utc(2026, 9, 6, 8, 1),
    )
    repository = DynamoProfileRepository(table)

    repository.save(profile)

    assert repository.get(profile.person_id) == profile
    raw = table.get_item(Key={"pk": "PERSON#person-1", "sk": "PROFILE"})["Item"]
    assert raw["entityType"] == "Profile"
    assert not any("phone" in key.lower() or "endpoint" in key.lower() for key in raw)


def test_missing_profile_is_none(table: Any) -> None:
    assert DynamoProfileRepository(table).get(PersonId("missing")) is None
