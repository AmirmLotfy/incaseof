"""The action outbox.

Workflows never call a provider. They enqueue an intent here, and a worker performs
delivery. That indirection is what makes a Step Functions retry harmless: the retry
re-enqueues an intent whose idempotency key is already claimed, so nothing is sent twice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from services.domain.ids import AlertId, StepId
from services.domain.plan import ActionType, Channel, ResponderRole

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_sqs.client import SQSClient
else:
    SQSClient = Any


@dataclass(frozen=True, slots=True)
class ActionIntent:
    """One thing to do, once.

    Carries identifiers and a role. Never a phone number: the recipient is resolved at
    delivery time, which keeps endpoints out of the queue, out of its logs, and out of any
    dead-letter message somebody later inspects.
    """

    alert_id: AlertId
    step_id: StepId
    sequence: int
    action: ActionType
    channel: Channel
    target_role: ResponderRole | None
    idempotency_key: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "alertId": self.alert_id,
                "stepId": self.step_id,
                "sequence": self.sequence,
                "action": self.action.value,
                "channel": self.channel.value,
                "targetRole": self.target_role.value if self.target_role else None,
                "idempotencyKey": self.idempotency_key,
            }
        )

    @staticmethod
    def from_dict(body: dict[str, Any]) -> ActionIntent:
        role = body.get("targetRole")
        return ActionIntent(
            alert_id=AlertId(body["alertId"]),
            step_id=StepId(body["stepId"]),
            sequence=int(body["sequence"]),
            action=ActionType(body["action"]),
            channel=Channel(body["channel"]),
            target_role=ResponderRole(role) if role else None,
            idempotency_key=body["idempotencyKey"],
        )


class ActionQueue(Protocol):
    def enqueue(self, intent: ActionIntent) -> None: ...


@dataclass
class SqsActionQueue:
    client: SQSClient
    queue_url: str

    def enqueue(self, intent: ActionIntent) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=intent.to_json())


@dataclass
class InMemoryActionQueue:
    """An in-process queue, so the slice can be driven without SQS.

    Delivery semantics are preserved where they matter: the driver can replay a message to
    reproduce at-least-once delivery, which is the property the idempotency guard exists
    to survive.
    """

    messages: list[ActionIntent] = field(default_factory=list)

    def enqueue(self, intent: ActionIntent) -> None:
        self.messages.append(intent)

    def drain(self) -> list[ActionIntent]:
        pending, self.messages = self.messages, []
        return pending
