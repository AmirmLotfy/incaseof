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
from typing import Any, Protocol

from services.domain.circle import CircleMember
from services.domain.contact_endpoint import EndpointType
from services.domain.ids import AlertId
from services.domain.plan import Channel


class DeliveryStatus(StrEnum):
    """What we actually know about one message.

    `ACCEPTED` is deliberately not called `SENT`. A carrier returning a message id means it
    took custody of the message, not that it reached a handset — and the two genuinely come
    apart. On an SNS account still in the SMS sandbox, publishing to an unverified number
    returns a perfectly ordinary MessageId and delivers nothing at all.

    That distinction is not pedantry here. A responder reads the timeline to decide whether
    somebody has already been reached; if it says the sister was contacted when no text
    arrived, the product has closed the loop falsely, which is the worst thing it can do.
    `DELIVERED` is therefore reserved for a carrier receipt and is never inferred.
    """

    ACCEPTED = "ACCEPTED"
    DELIVERED = "DELIVERED"
    UNDELIVERED = "UNDELIVERED"
    FAILED = "FAILED"
    CHANNEL_UNAVAILABLE = "CHANNEL_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Delivery:
    status: DeliveryStatus
    provider_reference: str | None = None
    error_code: str | None = None

    @property
    def succeeded(self) -> bool:
        """The handoff worked. Says nothing about arrival — see `confirmed`."""
        return self.status in (DeliveryStatus.ACCEPTED, DeliveryStatus.DELIVERED)

    @property
    def confirmed(self) -> bool:
        """A carrier receipt says it arrived. Only ever set from a real receipt."""
        return self.status is DeliveryStatus.DELIVERED


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
        return Delivery(status=DeliveryStatus.ACCEPTED, provider_reference=f"rec-{len(self.sent)}")

    def to(self, name: str) -> list[dict[str, object]]:
        return [m for m in self.sent if m["recipient"] == name]

    def on(self, channel: Channel) -> list[dict[str, object]]:
        return [m for m in self.sent if m["channel"] == channel.value]


@dataclass
class SmsSender:
    """Delivers over SMS, resolving the endpoint at the moment of sending.

    This is the last link in the chain and the only code that ever holds a readable phone
    number. It holds one for the duration of a single `publish` call and does not log it,
    return it, or put it anywhere it could be read again — the audit trail records a
    redacted form so an operator can confirm *which* endpoint was used without being handed
    it.
    """

    sns: Any
    endpoints: Any
    sender_id: str | None = None

    def send(
        self,
        *,
        alert_id: AlertId,
        member: CircleMember | None,
        channel: Channel,
        body: str,
        link: str | None,
    ) -> Delivery:
        if channel is not Channel.SMS:
            # Push and voice bind to their own providers. Reporting rather than pretending
            # keeps the gap visible in the timeline.
            return Delivery(status=DeliveryStatus.CHANNEL_UNAVAILABLE)

        if member is None:
            return Delivery(status=DeliveryStatus.FAILED, error_code="NO_RECIPIENT")

        endpoint = self.endpoints.for_person(member.person_id, EndpointType.PHONE)
        if endpoint is None:
            return Delivery(status=DeliveryStatus.FAILED, error_code="NO_ENDPOINT")
        if not endpoint.is_usable:
            # An unverified number may belong to somebody else entirely — a typo, or a
            # number since reassigned. Messaging it would tell a stranger that a specific
            # person has not come home.
            return Delivery(status=DeliveryStatus.FAILED, error_code="ENDPOINT_UNVERIFIED")

        text = f"{body}\n\n{link}" if link else body

        try:
            number = self.endpoints.reveal(endpoint)
            attributes: dict[str, Any] = {
                # Transactional, not promotional: a safety message must not be dropped for
                # cost optimisation, and must not be subject to marketing opt-out lists.
                "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"},
            }
            if self.sender_id:
                attributes["AWS.SNS.SMS.SenderID"] = {
                    "DataType": "String",
                    "StringValue": self.sender_id,
                }

            response = self.sns.publish(
                PhoneNumber=number,
                Message=text,
                MessageAttributes=attributes,
            )
        except Exception as error:
            # The number must not appear in the message, and provider exceptions have been
            # known to echo their input.
            return Delivery(status=DeliveryStatus.FAILED, error_code=type(error).__name__)

        # ACCEPTED, not SENT. SNS has taken the message; whether a handset ever sees it is
        # a separate fact that arrives later on the delivery-receipt path, if at all.
        return Delivery(
            status=DeliveryStatus.ACCEPTED,
            provider_reference=str(response.get("MessageId", "")),
        )


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
