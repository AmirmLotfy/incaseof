"""Atomic DynamoDB reservations for production monitoring capacity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from services.adapters import keys
from services.domain.capacity import (
    AccountPlanCapacityExhausted,
    GlobalPlanCapacityExhausted,
    PlanCapacityUsage,
)
from services.domain.ids import PersonId, PlanId

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_dynamodb.service_resource import Table
else:
    Table = Any


@dataclass
class DynamoPlanCapacityRepository:
    table: Table

    @staticmethod
    def _global_key() -> dict[str, str]:
        return {"pk": "CONTROL#PLAN_CAPACITY", "sk": "GLOBAL"}

    @staticmethod
    def _account_key(person_id: PersonId) -> dict[str, str]:
        return {"pk": keys.person(person_id), "sk": "PLAN_CAPACITY"}

    @staticmethod
    def _reservation_key(plan_id: PlanId) -> dict[str, str]:
        return {"pk": keys.plan(plan_id), "sk": "CAPACITY"}

    def usage(self, person_id: PersonId) -> PlanCapacityUsage:
        account = self.table.get_item(Key=self._account_key(person_id), ConsistentRead=True).get(
            "Item", {}
        )
        global_usage = self.table.get_item(Key=self._global_key(), ConsistentRead=True).get(
            "Item", {}
        )
        return PlanCapacityUsage(
            account_reserved=int(cast("int", account.get("reserved", 0))),
            global_reserved=int(cast("int", global_usage.get("reserved", 0))),
        )

    def reserve(
        self,
        *,
        person_id: PersonId,
        plan_id: PlanId,
        account_limit: int,
        global_limit: int,
        at: datetime,
    ) -> PlanCapacityUsage:
        if account_limit < 1:
            raise AccountPlanCapacityExhausted("account plan capacity is zero")
        if global_limit < 1:
            raise GlobalPlanCapacityExhausted("global plan capacity is zero")
        existing = self.table.get_item(Key=self._reservation_key(plan_id), ConsistentRead=True).get(
            "Item"
        )
        if existing is not None:
            if existing.get("personId") != str(person_id):
                raise ValueError("capacity reservation belongs to another account")
            return self.usage(person_id)

        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                **self._reservation_key(plan_id),
                                "entityType": "PlanCapacityReservation",
                                "personId": str(person_id),
                                "planId": str(plan_id),
                                "reservedAt": at.isoformat(),
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": self._account_key(person_id),
                            "UpdateExpression": (
                                "SET reserved = if_not_exists(reserved, :zero) + :one, "
                                "updatedAt = :at"
                            ),
                            "ConditionExpression": (
                                "attribute_not_exists(reserved) OR reserved < :maximum"
                            ),
                            "ExpressionAttributeValues": {
                                ":zero": 0,
                                ":one": 1,
                                ":maximum": account_limit,
                                ":at": at.isoformat(),
                            },
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": self._global_key(),
                            "UpdateExpression": (
                                "SET reserved = if_not_exists(reserved, :zero) + :one, "
                                "updatedAt = :at"
                            ),
                            "ConditionExpression": (
                                "attribute_not_exists(reserved) OR reserved < :maximum"
                            ),
                            "ExpressionAttributeValues": {
                                ":zero": 0,
                                ":one": 1,
                                ":maximum": global_limit,
                                ":at": at.isoformat(),
                            },
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException:
            # A concurrent retry of this plan is success. Different plans compete on the
            # conditional counters, so exactly one can consume the final slot.
            existing = self.table.get_item(
                Key=self._reservation_key(plan_id), ConsistentRead=True
            ).get("Item")
            if existing is not None and existing.get("personId") == str(person_id):
                return self.usage(person_id)
            usage = self.usage(person_id)
            if usage.account_reserved >= account_limit:
                raise AccountPlanCapacityExhausted("account plan capacity is exhausted") from None
            if usage.global_reserved >= global_limit:
                raise GlobalPlanCapacityExhausted("global plan capacity is exhausted") from None
            raise
        return self.usage(person_id)

    def release(self, *, person_id: PersonId, plan_id: PlanId, at: datetime) -> None:
        reservation = self.table.get_item(
            Key=self._reservation_key(plan_id), ConsistentRead=True
        ).get("Item")
        if reservation is None:
            return
        if reservation.get("personId") != str(person_id):
            raise ValueError("capacity reservation belongs to another account")
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": self.table.name,
                            "Key": self._reservation_key(plan_id),
                            "ConditionExpression": "personId = :person",
                            "ExpressionAttributeValues": {":person": str(person_id)},
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": self._account_key(person_id),
                            "UpdateExpression": "SET reserved = reserved - :one, updatedAt = :at",
                            "ConditionExpression": "reserved >= :one",
                            "ExpressionAttributeValues": {":one": 1, ":at": at.isoformat()},
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": self._global_key(),
                            "UpdateExpression": "SET reserved = reserved - :one, updatedAt = :at",
                            "ConditionExpression": "reserved >= :one",
                            "ExpressionAttributeValues": {":one": 1, ":at": at.isoformat()},
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException:
            if (
                self.table.get_item(Key=self._reservation_key(plan_id), ConsistentRead=True).get(
                    "Item"
                )
                is None
            ):
                return
            raise
