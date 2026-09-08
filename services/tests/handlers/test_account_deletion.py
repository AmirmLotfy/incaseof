from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from services.adapters import keys
from services.adapters.account_deletion import DynamoAccountDeletionRepository
from services.adapters.capacity import DynamoPlanCapacityRepository
from services.domain.ids import PersonId, PlanId
from services.handlers import account_deletion
from services.tests.adapters.conftest import table as table

NOW = datetime(2026, 9, 8, 1, 0, tzinfo=UTC)
MONA = PersonId("person-mona")


class Cognito:
    def __init__(self, fail_delete_once: bool = False) -> None:
        self.disabled: list[str] = []
        self.deleted: list[str] = []
        self.fail_delete_once = fail_delete_once

    def admin_disable_user(self, **request: str) -> None:
        self.disabled.append(request["Username"])

    def admin_delete_user(self, **request: str) -> None:
        if self.fail_delete_once:
            self.fail_delete_once = False
            raise ClientError(
                {"Error": {"Code": "InternalErrorException", "Message": "retry"}},
                "AdminDeleteUser",
            )
        self.deleted.append(request["Username"])


class Scheduler:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def delete_schedule(self, **request: str) -> None:
        self.deleted.append(request["Name"])


class StepFunctions:
    def __init__(self) -> None:
        self.stopped: list[str] = []

    def stop_execution(self, **request: str) -> None:
        self.stopped.append(request["executionArn"])


def _seed(table: Any) -> Any:
    repository = DynamoAccountDeletionRepository(table)
    request = repository.request(
        person_id=MONA,
        cognito_username="mona-user",
        request_id="request-1",
        at=NOW,
    )
    owner = keys.owner_partition(MONA)
    rows = [
        {
            "pk": "PLAN#plan-1",
            "sk": "META",
            keys.GSI2_PK: owner,
            keys.GSI2_SK: "PLAN#plan-1",
        },
        {
            "pk": "PLAN#plan-1",
            "sk": "VERSION#0001",
            "data": {"versionId": "version-1"},
        },
        {"pk": "PLANVERSION#version-1", "sk": "META"},
        {
            "pk": "MOMENT#moment-1",
            "sk": "META",
            keys.GSI2_PK: owner,
            keys.GSI2_SK: "MOMENT#2026-09-08#moment-1",
        },
        {
            "pk": "ALERT#alert-1",
            "sk": "META",
            keys.GSI2_PK: owner,
            keys.GSI2_SK: "ALERT#2026-09-08#alert-1",
        },
        {"pk": "ALERT#alert-1", "sk": "AUDIT#now#QUEUED#delivery-1"},
        {"pk": "IDEM#delivery-1", "sk": "OUTBOX"},
        {
            "pk": "CIRCLE#another-person",
            "sk": "MEMBER#membership-1",
            "data": {"personId": str(MONA)},
        },
        {
            "pk": "PLAN#another-person",
            "sk": "CONSENT#person-mona",
            "data": {"responderPersonId": str(MONA)},
        },
        {
            "pk": "INVITATION#invitation-1",
            "sk": "META",
            "data": {"responderPersonId": str(MONA)},
        },
        {"pk": "UNRELATED#keep", "sk": "META", "value": "must survive"},
    ]
    for row in rows:
        table.put_item(Item=row)
    return request


def _configure(
    monkeypatch: pytest.MonkeyPatch,
    cognito: Cognito,
    scheduler: Scheduler,
    step_functions: StepFunctions,
) -> None:
    monkeypatch.setenv("ICO_USER_POOL_ID", "pool-1")
    monkeypatch.setenv("ICO_SCHEDULE_GROUP", "moments-test")
    monkeypatch.setenv(
        "ICO_STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123456789012:stateMachine:ico"
    )
    clients = {
        "cognito-idp": cognito,
        "scheduler": scheduler,
        "stepfunctions": step_functions,
    }
    monkeypatch.setattr(account_deletion.boto3, "client", lambda service: clients[service])


def test_cleanup_stops_runtime_work_purges_every_partition_then_deletes_identity(
    table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _seed(table)
    cognito, scheduler, step_functions = Cognito(), Scheduler(), StepFunctions()
    _configure(monkeypatch, cognito, scheduler, step_functions)

    account_deletion.process(table, request, at=NOW)

    assert cognito.disabled == ["mona-user"]
    assert cognito.deleted == ["mona-user"]
    assert scheduler.deleted == ["moment-moment-1"]
    assert step_functions.stopped and step_functions.stopped[0].endswith(":alert-alert-1")
    assert table.scan()["Items"] == [
        {"pk": "UNRELATED#keep", "sk": "META", "value": "must survive"}
    ]


def test_cleanup_releases_the_accounts_global_capacity_reservations(
    table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _seed(table)
    capacity = DynamoPlanCapacityRepository(table)
    capacity.reserve(
        person_id=MONA,
        plan_id=PlanId("plan-1"),
        account_limit=1,
        global_limit=1,
        at=NOW,
    )
    cognito, scheduler, step_functions = Cognito(), Scheduler(), StepFunctions()
    _configure(monkeypatch, cognito, scheduler, step_functions)

    account_deletion.process(table, request, at=NOW)

    assert capacity.usage(MONA).account_reserved == 0
    assert capacity.usage(MONA).global_reserved == 0
    assert table.get_item(Key={"pk": "PLAN#plan-1", "sk": "CAPACITY"}).get("Item") is None


def test_a_failure_after_data_purge_retries_identity_deletion_without_restoring_data(
    table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _seed(table)
    cognito, scheduler, step_functions = (
        Cognito(fail_delete_once=True),
        Scheduler(),
        StepFunctions(),
    )
    _configure(monkeypatch, cognito, scheduler, step_functions)

    with pytest.raises(ClientError):
        account_deletion.process(table, request, at=NOW)
    pending = DynamoAccountDeletionRepository(table).pending()
    assert len(pending) == 1

    account_deletion.process(table, pending[0], at=NOW + timedelta(minutes=5))

    assert cognito.deleted == ["mona-user"]
    assert table.scan()["Items"] == [
        {"pk": "UNRELATED#keep", "sk": "META", "value": "must survive"}
    ]


def test_a_failure_mid_purge_keeps_owner_markers_for_a_complete_retry(
    table: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _seed(table)
    cognito, scheduler, step_functions = Cognito(), Scheduler(), StepFunctions()
    _configure(monkeypatch, cognito, scheduler, step_functions)
    real_delete = table.delete_item
    calls = 0

    def fail_third_delete(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("interrupted purge")
        return real_delete(**kwargs)

    monkeypatch.setattr(table, "delete_item", fail_third_delete)
    with pytest.raises(RuntimeError, match="interrupted purge"):
        account_deletion.process(table, request, at=NOW)

    monkeypatch.setattr(table, "delete_item", real_delete)
    pending = DynamoAccountDeletionRepository(table).pending()
    account_deletion.process(table, pending[0], at=NOW + timedelta(minutes=5))

    assert cognito.deleted == ["mona-user"]
    assert table.scan()["Items"] == [
        {"pk": "UNRELATED#keep", "sk": "META", "value": "must survive"}
    ]
