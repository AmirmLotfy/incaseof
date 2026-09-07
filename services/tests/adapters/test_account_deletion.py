from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from services.adapters.account_deletion import (
    AccountDeletionLeaseHeld,
    DynamoAccountDeletionRepository,
)
from services.adapters.profile import DynamoProfileRepository
from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.errors import DomainError
from services.domain.ids import PersonId

NOW = datetime(2026, 9, 8, 1, 0, tzinfo=UTC)
MONA = PersonId("person-mona")


def _profile() -> Profile:
    return Profile(
        person_id=MONA,
        display_name="Mona",
        locale=SupportedLocale.ARABIC,
        timezone="Africa/Cairo",
        country=SupportedCountry.EGYPT,
        status=AccountStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_request_closes_profile_and_persists_one_retryable_control_row(table: Any) -> None:
    DynamoProfileRepository(table).save(_profile())
    repository = DynamoAccountDeletionRepository(table)

    first = repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )
    replay = repository.request(
        person_id=MONA,
        cognito_username="ignored-replay",
        request_id="request-2",
        at=NOW,
    )

    assert first == replay
    assert repository.is_pending(MONA)
    assert repository.pending() == (first,)
    profile = DynamoProfileRepository(table).get(MONA)
    assert profile is not None
    assert profile.status is AccountStatus.DELETION_PENDING


def test_an_account_without_a_profile_can_still_be_deleted(table: Any) -> None:
    repository = DynamoAccountDeletionRepository(table)
    request = repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )

    assert repository.for_person(MONA) == request
    assert repository.for_person(PersonId("person-other")) is None


def test_completion_erases_the_retry_control_row(table: Any) -> None:
    repository = DynamoAccountDeletionRepository(table)
    request = repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )
    processing = repository.record_attempt(request, NOW)
    repository.complete(processing)

    assert repository.pending() == ()
    assert not repository.is_pending(MONA)


def test_a_second_worker_cannot_take_an_unexpired_cleanup_lease(table: Any) -> None:
    repository = DynamoAccountDeletionRepository(table)
    request = repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )
    repository.record_attempt(request, NOW)

    with pytest.raises(AccountDeletionLeaseHeld):
        repository.record_attempt(request, NOW)


def test_profile_cannot_be_recreated_after_the_deletion_lock_is_written(table: Any) -> None:
    repository = DynamoAccountDeletionRepository(table)
    repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )

    with pytest.raises(DomainError, match="deletion is in progress"):
        DynamoProfileRepository(table).save(_profile())
