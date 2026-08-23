"""Delivering one message to one person.

The only place in the system that turns an authorised **role** into an actual address. By
the time anything reaches here, the recipient has already been checked against the pinned
Plan Version, active consent, and the current escalation step -- this performs delivery and
nothing else.

Endpoint resolution is deliberately last. The further down the call stack it happens, the
fewer places a phone number can be logged, cached, serialised into a workflow payload, or
handed to a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from services.domain.circle import CircleMember
from services.domain.ids import AlertId
from services.domain.plan import Channel


class DeliveryStatus(StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"
    CHANNEL_UNAVAILABLE = "CHANNEL_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Delivery:
    status: DeliveryStatus
    provider_reference: str | None = None
    error_code: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is DeliveryStatus.SENT


class ContactSender(Protocol):
    """Sends one message. Implementations bind to FCM, SMS, or voice."""

    def send(
        self,
        *,
        alert_id: AlertId,
        member: CircleMember | None,
        channel: Channel,
        body: str,
        link: str | None,
    ) -> Delivery: ...


@dataclass
class RecordingSender:
    """Records what would be sent, and sends nothing.

    Used by the end-to-end slice test and by local runs. It is not a stand-in for the
    product: everything upstream -- authorisation, idempotency, the ladder, the state
    machine -- is the real code. What is stubbed is the provider's wire call, which is the
    one thing that cannot be exercised without a phone and an account.
    """

    sent: list[dict[str, object]] = field(default_factory=list)
    fail_channels: set[Channel] = field(default_factory=set)

    def send(
        self,
        *,
        alert_id: AlertId,
        member: CircleMember | None,
        channel: Channel,
        body: str,
        link: str | None,
    ) -> Delivery:
        if not channel.is_available_in_p0:
            return Delivery(status=DeliveryStatus.CHANNEL_UNAVAILABLE)
        if channel in self.fail_channels:
            return Delivery(status=DeliveryStatus.FAILED, error_code="PROVIDER_ERROR")

        self.sent.append(
            {
                "alertId": alert_id,
                # The recipient is recorded by id and display name. Even here there is no
                # endpoint, because nothing upstream ever produced one.
                "recipient": member.display_name if member else "subject",
                "recipientId": member.person_id if member else None,
                "channel": channel.value,
                "body": body,
                "link": link,
            }
        )
        return Delivery(status=DeliveryStatus.SENT, provider_reference=f"rec-{len(self.sent)}")

    def to(self, name: str) -> list[dict[str, object]]:
        return [m for m in self.sent if m["recipient"] == name]

    def on(self, channel: Channel) -> list[dict[str, object]]:
        return [m for m in self.sent if m["channel"] == channel.value]


def compose_responder_message(
    *, subject_name: str, plan_label: str, expected_at: datetime, tried: list[str]
) -> str:
    """What a responder reads on a lock screen at 2am.

    Person, then fact, then what was already tried. No speculation: it says somebody has
    not responded, never that anything is wrong -- see docs/design/COPY.md section 3.
    """
    lines = [
        f"{subject_name} hasn't responded",
        "",
        f"{plan_label} · Expected {expected_at.strftime('%-I:%M %p')}",
    ]
    if tried:
        lines += ["", "In Case of tried:", *[f"  {item}" for item in tried]]
    return "\n".join(lines)
