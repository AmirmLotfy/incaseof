"""Durable intents, atomic ladder progress, and at-most-once provider attempts.

SQS is a transport, not the source of truth. A SENDING attempt is never reclaimed:
the process may have died after provider acceptance. Such attempts require reconciliation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from boto3.dynamodb.conditions import Attr

from services.adapters import codec, keys
from services.adapters.dynamo import ConcurrentModification
from services.adapters.queue import ActionIntent
from services.domain.alert import Alert


@dataclass
class DynamoOutbox:
    table: Any

    def stage(self, before: Alert, after: Alert, intents: list[ActionIntent], at: datetime) -> None:
        """Either persist every intent with ladder progress, or persist neither."""
        writes: list[dict[str, Any]] = [
            {
                "Update": {
                    "TableName": self.table.name,
                    "Key": {"pk": keys.alert(before.alert_id), "sk": keys.META},
                    "UpdateExpression": "SET #data = :after ADD revision :one",
                    "ConditionExpression": "#data = :before",
                    "ExpressionAttributeNames": {"#data": "data"},
                    "ExpressionAttributeValues": {
                        ":before": codec.alert_to(before),
                        ":after": codec.alert_to(after),
                        ":one": 1,
                    },
                }
            }
        ]
        for intent in intents:
            writes.append(
                {
                    "Put": {
                        "TableName": self.table.name,
                        "Item": {
                            **self._key(intent.idempotency_key),
                            "intent": json.loads(intent.to_json()),
                            "status": "PENDING",
                            keys.GSI1_PK: "OUTBOX#PENDING",
                            keys.GSI1_SK: intent.idempotency_key,
                        },
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                }
            )
            # Old deployment locks cannot safely be interpreted as unsent messages.
            writes.append(
                {
                    "ConditionCheck": {
                        "TableName": self.table.name,
                        "Key": {"pk": keys.idempotency(intent.idempotency_key), "sk": keys.LOCK},
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                }
            )
            writes.append(
                {
                    "Put": {
                        "TableName": self.table.name,
                        "Item": {
                            "pk": keys.alert(intent.alert_id),
                            "sk": f"AUDIT#{at.isoformat()}#QUEUED#{intent.idempotency_key}",
                            "alertId": intent.alert_id,
                            "actorType": "SYSTEM",
                            "actorId": "workflow",
                            "eventType": "ACTION_QUEUED",
                            "at": at.isoformat(),
                            "metadata": {
                                "sequence": str(intent.sequence),
                                "action": intent.action.value,
                            },
                        },
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                }
            )
        try:
            self.table.meta.client.transact_write_items(TransactItems=writes)
        except self.table.meta.client.exceptions.TransactionCanceledException as error:
            raise ConcurrentModification(
                "outbox or Alert changed; re-read before dispatch"
            ) from error

    @staticmethod
    def _key(key: str) -> dict[str, str]:
        return {"pk": keys.idempotency(key), "sk": "OUTBOX"}

    def get(self, key: str) -> dict[str, Any] | None:
        item: dict[str, Any] | None = self.table.get_item(
            Key=self._key(key),
            ConsistentRead=True,
        ).get("Item")
        return item

    def pending(self, limit: int = 100) -> list[ActionIntent]:
        pages = self.table.meta.client.get_paginator("query").paginate(
            TableName=self.table.name,
            IndexName=keys.GSI1,
            KeyConditionExpression="gsi1pk = :pending",
            ExpressionAttributeValues={":pending": "OUTBOX#PENDING"},
            PaginationConfig={"PageSize": limit},
        )
        return [
            ActionIntent.from_dict(row["intent"]) for page in pages for row in page.get("Items", [])
        ]

    def begin(self, intent: ActionIntent, at: datetime) -> bool:
        try:
            self.table.update_item(
                Key=self._key(intent.idempotency_key),
                UpdateExpression=(
                    "SET #status = :sending, startedAt = :at, gsi1pk = :index, gsi1sk = :sort"
                ),
                ConditionExpression=Attr("status").eq("PENDING")
                & Attr("intent").eq(json.loads(intent.to_json())),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":sending": "SENDING",
                    ":at": at.isoformat(),
                    ":index": "OUTBOX#SENDING",
                    ":sort": at.isoformat() + "#" + intent.idempotency_key,
                },
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True

    def finish(
        self,
        key: str,
        status: str,
        at: datetime,
        event_type: str | None = None,
        **details: str | None,
    ) -> None:
        row = self.get(key)
        if row is None:
            raise RuntimeError("missing durable attempt")
        intent = row["intent"]
        event = event_type or {
            "ACCEPTED": "ACTION_ACCEPTED",
            "UNKNOWN": "ACTION_OUTCOME_UNKNOWN",
            "CHANNEL_UNAVAILABLE": "CHANNEL_UNAVAILABLE",
        }.get(status, "ACTION_FAILED")
        outcome = {k: v for k, v in details.items() if v is not None}
        metadata = {"sequence": str(intent["sequence"]), "channel": intent["channel"]}
        if details.get("reason"):
            metadata["reason"] = str(details["reason"])
        if details.get("provider_reference"):
            metadata["providerReference"] = str(details["provider_reference"])
        self.table.meta.client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": self.table.name,
                        "Key": self._key(key),
                        "UpdateExpression": (
                            "SET #status = :status, finishedAt = :at, "
                            "outcome = :outcome REMOVE gsi1pk, gsi1sk"
                        ),
                        "ConditionExpression": "#status = :sending",
                        "ExpressionAttributeNames": {"#status": "status"},
                        "ExpressionAttributeValues": {
                            ":status": status,
                            ":sending": "SENDING",
                            ":at": at.isoformat(),
                            ":outcome": outcome,
                        },
                    }
                },
                {
                    "Put": {
                        "TableName": self.table.name,
                        "Item": {
                            "pk": keys.alert(intent["alertId"]),
                            "sk": f"AUDIT#{at.isoformat()}#OUTCOME#{key}",
                            "alertId": intent["alertId"],
                            "actorType": "WORKER",
                            "actorId": "action",
                            "eventType": event,
                            "at": at.isoformat(),
                            "metadata": metadata,
                        },
                        "ConditionExpression": "attribute_not_exists(pk)",
                    }
                },
            ]
        )

    def reconcile_stale(self, at: datetime) -> int:
        cutoff = (at - timedelta(seconds=90)).isoformat() + "#~"
        pages = self.table.meta.client.get_paginator("query").paginate(
            TableName=self.table.name,
            IndexName=keys.GSI1,
            KeyConditionExpression="gsi1pk = :sending AND gsi1sk <= :cutoff",
            ExpressionAttributeValues={":sending": "OUTBOX#SENDING", ":cutoff": cutoff},
        )
        count = 0
        for page in pages:
            for row in page.get("Items", []):
                key = row["intent"]["idempotencyKey"]
                current = self.get(key)
                if current is None or current["status"] != "SENDING":
                    continue
                try:
                    self.finish(key, "UNKNOWN", at, reason="WORKER_OUTCOME_MISSING")
                    count += 1
                except self.table.meta.client.exceptions.TransactionCanceledException:
                    # Another reconciler or the original worker persisted the outcome.
                    latest = self.get(key)
                    if latest is not None and latest["status"] == "SENDING":
                        raise
        return count

    def defer(self, intent: ActionIntent) -> None:
        """Release ownership only when authorization prevented any provider invocation."""
        self.table.update_item(
            Key=self._key(intent.idempotency_key),
            UpdateExpression="SET #status = :pending, gsi1pk = :pk, gsi1sk = :sk",
            ConditionExpression=Attr("status").eq("SENDING"),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":pending": "PENDING",
                ":pk": "OUTBOX#PENDING",
                ":sk": intent.idempotency_key,
            },
        )
