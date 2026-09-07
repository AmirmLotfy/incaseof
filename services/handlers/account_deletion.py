"""Retry account erasure until every owned resource is gone.

The durable request is the source of truth. A worker crash leaves it on the pending
index, so the five-minute scheduler invokes this handler again. Cognito deletion is last:
until application cleanup succeeds, the disabled principal remains identifiable for a
safe retry but cannot sign in or start new monitoring work.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import boto3 as boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from services.adapters import keys
from services.adapters.account_deletion import (
    AccountDeletionLeaseHeld,
    DynamoAccountDeletionRepository,
)
from services.adapters.capacity import DynamoPlanCapacityRepository
from services.adapters.endpoints import DynamoEndpointRepository
from services.domain.account_deletion import AccountDeletion
from services.domain.contact_endpoint import EndpointType
from services.domain.ids import PersonId, PlanId

log = logging.getLogger(__name__)


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for account deletion")
    return value


def _error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def _delete_push_endpoint(table: Any, request: AccountDeletion) -> None:
    platform_arn = os.environ.get("ICO_PUSH_PLATFORM_ARN")
    if not platform_arn:
        return
    endpoints = DynamoEndpointRepository(
        table=table,
        kms=boto3.client("kms"),
        key_id=_required("ICO_KMS_KEY_ID"),
    )
    endpoint = endpoints.for_person(request.person_id, EndpointType.PUSH_TOKEN)
    if endpoint is None or not endpoint.is_usable:
        return
    endpoint_arn = endpoints.reveal(endpoint)
    try:
        boto3.client("sns").delete_endpoint(EndpointArn=endpoint_arn)
    except ClientError as error:
        if _error_code(error) not in {"NotFound", "NotFoundException"}:
            raise


def _discover_data(table: Any, person_id: PersonId) -> tuple[set[str], set[tuple[str, str]]]:
    """Strongly find owned roots plus responder membership and consent records."""
    roots: set[str] = set()
    associated: set[tuple[str, str]] = set()
    request: dict[str, Any] = {
        "ConsistentRead": True,
    }
    while True:
        response = table.scan(**request)
        for item in response.get("Items", []):
            pk, sk = str(item["pk"]), str(item["sk"])
            if item.get(keys.GSI2_PK) == keys.owner_partition(person_id):
                roots.add(pk)
            data = item.get("data")
            if not isinstance(data, dict):
                continue
            if sk.startswith("MEMBER#") and data.get("personId") == str(person_id):
                associated.add((pk, sk))
            elif sk.startswith("CONSENT#") and data.get("responderPersonId") == str(person_id):
                associated.add((pk, sk))
            elif pk.startswith("INVITATION#") and data.get("responderPersonId") == str(person_id):
                roots.add(pk)
        last = response.get("LastEvaluatedKey")
        if not last:
            return roots, associated
        request["ExclusiveStartKey"] = last


def _partition(table: Any, partition_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    request: dict[str, Any] = {
        "KeyConditionExpression": Key("pk").eq(partition_key),
        "ConsistentRead": True,
    }
    while True:
        response = table.query(**request)
        rows.extend(response.get("Items", []))
        last = response.get("LastEvaluatedKey")
        if not last:
            return rows
        request["ExclusiveStartKey"] = last


def _is_discovery_marker(
    row: dict[str, Any], root: str, person_id: PersonId, owner_partition: str
) -> bool:
    data = row.get("data")
    return bool(
        row.get(keys.GSI2_PK) == owner_partition
        or (root == keys.person(person_id) and row.get("sk") == "ACCOUNT_DELETION")
        or (
            root.startswith("INVITATION#")
            and isinstance(data, dict)
            and data.get("responderPersonId") == str(person_id)
        )
    )


def _cancel_timer(moment_partition: str) -> None:
    moment_id = moment_partition.removeprefix("MOMENT#")
    try:
        boto3.client("scheduler").delete_schedule(
            Name=f"moment-{moment_id}", GroupName=_required("ICO_SCHEDULE_GROUP")
        )
    except ClientError as error:
        if _error_code(error) != "ResourceNotFoundException":
            raise


def _stop_workflow(alert_partition: str) -> None:
    alert_id = alert_partition.removeprefix("ALERT#")
    state_machine = _required("ICO_STATE_MACHINE_ARN")
    execution = state_machine.replace(":stateMachine:", ":execution:") + f":alert-{alert_id}"
    try:
        boto3.client("stepfunctions").stop_execution(
            executionArn=execution, error="AccountDeletion", cause="Account deletion requested"
        )
    except ClientError as error:
        if _error_code(error) not in {"ExecutionDoesNotExist", "ValidationException"}:
            raise


def _purge_application_data(table: Any, person_id: PersonId, at: datetime) -> None:
    roots, associated = _discover_data(table, person_id)
    roots.add(keys.person(person_id))
    related: set[str] = set()

    capacity = DynamoPlanCapacityRepository(table)
    for root in sorted(roots):
        if root.startswith("PLAN#"):
            capacity.release(
                person_id=person_id,
                plan_id=PlanId(root.removeprefix("PLAN#")),
                at=at,
            )

    # Stop all future and in-progress safety work before deleting its records.
    for root in sorted(roots):
        if root.startswith("MOMENT#"):
            _cancel_timer(root)
        elif root.startswith("ALERT#"):
            _stop_workflow(root)

    rows_by_root: dict[str, list[dict[str, Any]]] = {}
    for root in sorted(roots):
        rows = _partition(table, root)
        rows_by_root[root] = rows
        for row in rows:
            sk = str(row.get("sk", ""))
            data = row.get("data")
            if root.startswith("PLAN#") and sk.startswith("VERSION#") and isinstance(data, dict):
                version_id = data.get("versionId")
                if version_id:
                    related.add(f"PLANVERSION#{version_id}")
            if root.startswith("ALERT#") and "#QUEUED#" in sk:
                related.add(f"IDEM#{sk.split('#QUEUED#', 1)[1]}")

    for root in sorted(related):
        rows_by_root[root] = _partition(table, root)

    # Related partitions are deleted before their owning alert/plan. If any idempotent
    # delete has an unknown outcome, the owner marker still lets the next run rediscover
    # the dependency. A batch cannot provide that ordering guarantee.
    for root in sorted(related):
        for row in rows_by_root[root]:
            table.delete_item(Key={"pk": row["pk"], "sk": row["sk"]})

    for pk, sk in sorted(associated):
        table.delete_item(Key={"pk": pk, "sk": sk})

    owner_partition = keys.owner_partition(person_id)
    for root in sorted(roots):
        rows = rows_by_root[root]

        # Every non-marker row is gone before the final discoverable row. Retrying after
        # any interruption therefore either finds the root again or finds it fully gone.
        for marker in (False, True):
            for row in rows:
                if _is_discovery_marker(row, root, person_id, owner_partition) == marker:
                    table.delete_item(Key={"pk": row["pk"], "sk": row["sk"]})


def process(table: Any, request: AccountDeletion, *, at: datetime | None = None) -> None:
    repository = DynamoAccountDeletionRepository(table)
    attempted_at = at or datetime.now(UTC)
    current = repository.record_attempt(request, attempted_at)
    cognito = boto3.client("cognito-idp")
    user_pool_id = _required("ICO_USER_POOL_ID")
    try:
        cognito.admin_disable_user(UserPoolId=user_pool_id, Username=current.cognito_username)
    except ClientError as error:
        if _error_code(error) != "UserNotFoundException":
            raise

    _delete_push_endpoint(table, current)
    _purge_application_data(table, current.person_id, attempted_at)

    try:
        cognito.admin_delete_user(UserPoolId=user_pool_id, Username=current.cognito_username)
    except ClientError as error:
        if _error_code(error) != "UserNotFoundException":
            raise
    repository.complete(current)


def handler(_event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    table = boto3.resource("dynamodb").Table(_required("ICO_TABLE_NAME"))
    repository = DynamoAccountDeletionRepository(table)
    failures: list[Exception] = []
    completed = 0
    for request in repository.pending(limit=5):
        try:
            process(table, request)
            completed += 1
        except AccountDeletionLeaseHeld:
            continue
        except Exception as error:  # each durable row stays indexed for the next invocation
            failures.append(error)
            log.exception("account deletion retry failed for request %s", request.request_id)
    if failures:
        raise RuntimeError(f"{len(failures)} account deletion request(s) require retry")
    return {"completed": completed}
