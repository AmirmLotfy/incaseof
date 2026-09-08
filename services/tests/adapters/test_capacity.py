from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import pytest

from services.adapters.capacity import DynamoPlanCapacityRepository
from services.adapters.memory import InMemoryPlanCapacityRepository
from services.domain.capacity import (
    AccountPlanCapacityExhausted,
    GlobalPlanCapacityExhausted,
)
from services.domain.ids import PersonId, PlanId

NOW = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)
MONA = PersonId("person-mona")


def test_dynamo_reservation_is_idempotent_and_updates_both_counters(table: Any) -> None:
    repository = DynamoPlanCapacityRepository(table)

    first = repository.reserve(
        person_id=MONA,
        plan_id=PlanId("plan-1"),
        account_limit=2,
        global_limit=3,
        at=NOW,
    )
    replay = repository.reserve(
        person_id=MONA,
        plan_id=PlanId("plan-1"),
        account_limit=2,
        global_limit=3,
        at=NOW,
    )

    assert first == replay
    assert replay.account_reserved == 1
    assert replay.global_reserved == 1
    reservation = table.get_item(Key={"pk": "PLAN#plan-1", "sk": "CAPACITY"})["Item"]
    assert reservation["personId"] == MONA


def test_dynamo_reservation_enforces_account_and_global_limits(table: Any) -> None:
    repository = DynamoPlanCapacityRepository(table)
    repository.reserve(
        person_id=MONA,
        plan_id=PlanId("mona-1"),
        account_limit=1,
        global_limit=2,
        at=NOW,
    )

    with pytest.raises(AccountPlanCapacityExhausted):
        repository.reserve(
            person_id=MONA,
            plan_id=PlanId("mona-2"),
            account_limit=1,
            global_limit=2,
            at=NOW,
        )

    repository.reserve(
        person_id=PersonId("person-maya"),
        plan_id=PlanId("maya-1"),
        account_limit=1,
        global_limit=2,
        at=NOW,
    )
    with pytest.raises(GlobalPlanCapacityExhausted):
        repository.reserve(
            person_id=PersonId("person-omar"),
            plan_id=PlanId("omar-1"),
            account_limit=1,
            global_limit=2,
            at=NOW,
        )


def test_concurrent_dynamo_reservations_cannot_overbook_the_last_global_slot(
    table: Any,
) -> None:
    people = tuple(PersonId(f"person-{index}") for index in range(8))

    def reserve(index: int) -> str:
        try:
            DynamoPlanCapacityRepository(table).reserve(
                person_id=people[index],
                plan_id=PlanId(f"plan-{index}"),
                account_limit=1,
                global_limit=1,
                at=NOW,
            )
        except GlobalPlanCapacityExhausted:
            return "FULL"
        return "RESERVED"

    with ThreadPoolExecutor(max_workers=len(people)) as pool:
        outcomes = tuple(pool.map(reserve, range(len(people))))

    assert outcomes.count("RESERVED") == 1
    assert outcomes.count("FULL") == len(people) - 1
    global_row = table.get_item(Key={"pk": "CONTROL#PLAN_CAPACITY", "sk": "GLOBAL"})["Item"]
    assert int(global_row["reserved"]) == 1


def test_release_is_idempotent_and_never_releases_another_accounts_slot(table: Any) -> None:
    repository = DynamoPlanCapacityRepository(table)
    plan_id = PlanId("plan-1")
    repository.reserve(
        person_id=MONA,
        plan_id=plan_id,
        account_limit=1,
        global_limit=1,
        at=NOW,
    )

    with pytest.raises(ValueError, match="another account"):
        repository.release(person_id=PersonId("person-maya"), plan_id=plan_id, at=NOW)

    repository.release(person_id=MONA, plan_id=plan_id, at=NOW)
    repository.release(person_id=MONA, plan_id=plan_id, at=NOW)

    assert repository.usage(MONA).account_reserved == 0
    assert repository.usage(MONA).global_reserved == 0
    assert table.get_item(Key={"pk": "PLAN#plan-1", "sk": "CAPACITY"}).get("Item") is None


def test_in_memory_adapter_serializes_concurrent_reservations() -> None:
    repository = InMemoryPlanCapacityRepository()

    def reserve(index: int) -> str:
        try:
            repository.reserve(
                person_id=PersonId(f"person-{index}"),
                plan_id=PlanId(f"plan-{index}"),
                account_limit=1,
                global_limit=1,
                at=NOW,
            )
        except GlobalPlanCapacityExhausted:
            return "FULL"
        return "RESERVED"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = tuple(pool.map(reserve, range(8)))

    assert outcomes.count("RESERVED") == 1
    assert outcomes.count("FULL") == 7
