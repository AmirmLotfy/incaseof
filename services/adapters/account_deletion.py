"""DynamoDB lifecycle for retryable account deletion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from boto3.dynamodb.conditions import Key

from services.adapters import keys
from services.domain.account_deletion import AccountDeletion, AccountDeletionStatus
from services.domain.ids import PersonId


class AccountDeletionRepository(Protocol):
    def request(
        self,
        *,
        person_id: PersonId,
        cognito_username: str,
        request_id: str,
        at: datetime,
    ) -> AccountDeletion: ...

    def for_person(self, person_id: PersonId) -> AccountDeletion | None: ...

    def is_pending(self, person_id: PersonId) -> bool: ...

    def pending(self, limit: int = 10) -> tuple[AccountDeletion, ...]: ...

    def record_attempt(self, request: AccountDeletion, at: datetime) -> AccountDeletion: ...

    def complete(self, request: AccountDeletion) -> None: ...


class AccountDeletionLeaseHeld(RuntimeError):
    """Another worker owns this deletion attempt until its bounded lease expires."""


@dataclass
class DynamoAccountDeletionRepository:
    table: Any

    @staticmethod
    def _control_key(request_id: str) -> dict[str, str]:
        return {"pk": f"ACCOUNT_DELETION#{request_id}", "sk": keys.META}

    @staticmethod
    def _pointer_key(person_id: PersonId) -> dict[str, str]:
        return {"pk": keys.person(person_id), "sk": "ACCOUNT_DELETION"}

    def request(
        self,
        *,
        person_id: PersonId,
        cognito_username: str,
        request_id: str,
        at: datetime,
    ) -> AccountDeletion:
        existing = self.for_person(person_id)
        if existing is not None:
            return existing
        request = AccountDeletion(
            request_id=request_id,
            person_id=person_id,
            cognito_username=cognito_username,
            status=AccountDeletionStatus.PENDING,
            requested_at=at,
        )
        profile_key = {"pk": keys.person(person_id), "sk": "PROFILE"}
        profile = self.table.get_item(Key=profile_key, ConsistentRead=True).get("Item")
        writes: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self.table.name,
                    "Item": {
                        **self._control_key(request_id),
                        "entityType": "AccountDeletion",
                        "requestId": request_id,
                        "personId": str(person_id),
                        "cognitoUsername": cognito_username,
                        "status": request.status.value,
                        "requestedAt": at.isoformat(),
                        "attempts": 0,
                        keys.GSI1_PK: "ACCOUNT_DELETION#PENDING",
                        keys.GSI1_SK: f"{at.isoformat()}#{request_id}",
                    },
                    "ConditionExpression": "attribute_not_exists(pk)",
                }
            },
            {
                "Put": {
                    "TableName": self.table.name,
                    "Item": {
                        **self._pointer_key(person_id),
                        "entityType": "AccountDeletionPointer",
                        "requestId": request_id,
                        "requestedAt": at.isoformat(),
                    },
                    "ConditionExpression": "attribute_not_exists(pk)",
                }
            },
        ]
        if profile is not None:
            writes.append(
                {
                    "Update": {
                        "TableName": self.table.name,
                        "Key": profile_key,
                        "UpdateExpression": "SET #status = :pending, updatedAt = :at",
                        "ConditionExpression": "#status = :active",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":active": "ACTIVE",
                            ":pending": "DELETION_PENDING",
                            ":at": at.isoformat(),
                        },
                    }
                }
            )
        else:
            writes.append(
                {
                    "ConditionCheck": {
                        "TableName": self.table.name,
                        "Key": profile_key,
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                }
            )
        try:
            self.table.meta.client.transact_write_items(TransactItems=writes)
        except self.table.meta.client.exceptions.TransactionCanceledException:
            current = self.for_person(person_id)
            if current is not None:
                return current
            raise
        return request

    def for_person(self, person_id: PersonId) -> AccountDeletion | None:
        pointer = self.table.get_item(Key=self._pointer_key(person_id), ConsistentRead=True).get(
            "Item"
        )
        if pointer is None:
            return None
        control = self.table.get_item(
            Key=self._control_key(str(pointer["requestId"])), ConsistentRead=True
        ).get("Item")
        return self._from_item(control) if control else None

    def is_pending(self, person_id: PersonId) -> bool:
        return (
            self.table.get_item(Key=self._pointer_key(person_id), ConsistentRead=True).get("Item")
            is not None
        )

    def pending(self, limit: int = 10) -> tuple[AccountDeletion, ...]:
        response = self.table.query(
            IndexName=keys.GSI1,
            KeyConditionExpression=Key(keys.GSI1_PK).eq("ACCOUNT_DELETION#PENDING"),
            ScanIndexForward=True,
            Limit=limit,
        )
        return tuple(self._from_item(item) for item in response.get("Items", []))

    def record_attempt(self, request: AccountDeletion, at: datetime) -> AccountDeletion:
        try:
            self.table.update_item(
                Key=self._control_key(request.request_id),
                UpdateExpression=(
                    "SET #status = :processing, leaseUntil = :lease ADD attempts :one"
                ),
                ConditionExpression=(
                    "personId = :person AND (#status = :pending OR "
                    "(#status = :processing AND leaseUntil < :now))"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":person": str(request.person_id),
                    ":pending": AccountDeletionStatus.PENDING.value,
                    ":processing": AccountDeletionStatus.PROCESSING.value,
                    ":now": at.isoformat(),
                    ":lease": (at + timedelta(minutes=4)).isoformat(),
                    ":one": 1,
                },
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException as error:
            raise AccountDeletionLeaseHeld(request.request_id) from error
        return AccountDeletion(
            request_id=request.request_id,
            person_id=request.person_id,
            cognito_username=request.cognito_username,
            status=AccountDeletionStatus.PROCESSING,
            requested_at=request.requested_at,
            attempts=request.attempts + 1,
        )

    def complete(self, request: AccountDeletion) -> None:
        self.table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "TableName": self.table.name,
                        "Key": self._control_key(request.request_id),
                        "ConditionExpression": "personId = :person",
                        "ExpressionAttributeValues": {":person": str(request.person_id)},
                    }
                },
                {
                    "Delete": {
                        "TableName": self.table.name,
                        "Key": self._pointer_key(request.person_id),
                    }
                },
            ]
        )

    @staticmethod
    def _from_item(item: dict[str, Any]) -> AccountDeletion:
        return AccountDeletion(
            request_id=str(item["requestId"]),
            person_id=PersonId(str(item["personId"])),
            cognito_username=str(item["cognitoUsername"]),
            status=AccountDeletionStatus(str(item["status"])),
            requested_at=datetime.fromisoformat(str(item["requestedAt"])),
            attempts=int(item.get("attempts", 0)),
        )
