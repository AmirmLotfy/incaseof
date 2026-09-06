"""Contact endpoints: the most sensitive thing this system stores.

A phone number here, joined to the Circle it belongs to, is a map of who is close to whom.
These check the properties that make that safe to hold at all.
"""

from __future__ import annotations

from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError

from services.adapters.contact import ChannelRouter, DeliveryStatus, PushSender, SmsSender
from services.adapters.endpoints import DynamoEndpointRepository
from services.domain.circle import CircleMember, MemberStatus
from services.domain.clock import utc
from services.domain.contact_endpoint import EndpointStatus, EndpointType, redact
from services.domain.ids import AlertId, CircleId, MembershipId, PersonId
from services.domain.plan import Channel, ResponderRole

MAYA = PersonId("person-maya")
OMAR = PersonId("person-omar")
# Ofcom's reserved drama range. Never a real number, even in a test.
NUMBER = "+447700900123"


@pytest.fixture
def endpoints(table: Any) -> DynamoEndpointRepository:
    kms = boto3.client("kms", region_name="us-east-1")
    key = kms.create_key(Description="test")["KeyMetadata"]["KeyId"]
    return DynamoEndpointRepository(table=table, kms=kms, key_id=key)


def a_member(person_id: PersonId = MAYA) -> CircleMember:
    return CircleMember(
        membership_id=MembershipId("m-1"),
        circle_id=CircleId("circle-1"),
        person_id=person_id,
        role=ResponderRole.PRIMARY,
        priority=1,
        status=MemberStatus.ACCEPTED,
        display_name="Maya",
    )


# -- at rest ------------------------------------------------------------------


def test_the_number_is_never_stored_in_plaintext(
    endpoints: DynamoEndpointRepository, table: Any
) -> None:
    endpoints.save(
        endpoint_id="e-1", person_id=MAYA, endpoint_type=EndpointType.PHONE, value=NUMBER
    )

    raw = str(table.scan()["Items"])
    assert NUMBER not in raw
    assert "447700900123" not in raw
    assert "900123" not in raw, "even a fragment is enough to narrow a search"


def test_it_round_trips_through_encryption(endpoints: DynamoEndpointRepository) -> None:
    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
        verified_at=utc(2026, 8, 1),
    )
    stored = endpoints.for_person(MAYA, EndpointType.PHONE)

    assert stored is not None
    assert endpoints.reveal(stored) == NUMBER


def test_a_ciphertext_cannot_be_moved_to_another_person(
    endpoints: DynamoEndpointRepository,
) -> None:
    """The encryption context is what makes this fail.

    Without it, a row copied from one person to another would decrypt happily and the
    system would message the wrong human being about somebody's safety.
    """
    from dataclasses import replace

    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    mayas = endpoints.for_person(MAYA, EndpointType.PHONE)
    assert mayas is not None

    stolen = replace(mayas, person_id=OMAR)
    with pytest.raises(ClientError):
        endpoints.reveal(stolen)


def test_an_unverified_endpoint_refuses_to_decrypt(
    endpoints: DynamoEndpointRepository,
) -> None:
    endpoints.save(
        endpoint_id="e-1", person_id=MAYA, endpoint_type=EndpointType.PHONE, value=NUMBER
    )
    stored = endpoints.for_person(MAYA, EndpointType.PHONE)
    assert stored is not None

    with pytest.raises(ValueError, match="only a verified endpoint"):
        endpoints.reveal(stored)


def test_phone_verification_can_reveal_then_conditionally_verify_and_revoke(
    endpoints: DynamoEndpointRepository,
) -> None:
    endpoints.save(
        endpoint_id="e-current",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    stored = endpoints.save_candidate(
        endpoint_id="e-verify",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
    )
    assert endpoints.reveal_for_verification(stored) == NUMBER
    current = endpoints.for_person(MAYA, EndpointType.PHONE)
    assert current is not None and current.endpoint_id == "e-current"
    assert endpoints.revoke_candidate(MAYA, EndpointType.PHONE, "e-verify")
    candidate = endpoints.candidate(MAYA, EndpointType.PHONE, "e-verify")
    assert candidate is not None and candidate.status is EndpointStatus.REVOKED
    current = endpoints.for_person(MAYA, EndpointType.PHONE)
    assert current is not None and current.endpoint_id == "e-current" and current.is_usable


def test_the_repr_never_shows_the_value(endpoints: DynamoEndpointRepository) -> None:
    """A repr ends up in tracebacks, logs and error trackers."""
    endpoint = endpoints.save(
        endpoint_id="e-1", person_id=MAYA, endpoint_type=EndpointType.PHONE, value=NUMBER
    )
    rendered = repr(endpoint)

    assert "<sealed>" in rendered
    assert NUMBER not in rendered
    assert "ciphertext" not in rendered


def test_redaction_shows_enough_to_identify_and_no_more() -> None:
    assert redact(NUMBER) == "•" * (len(NUMBER) - 4) + "0123"
    assert redact("12") == "••"


# -- sending ------------------------------------------------------------------


def test_a_verified_endpoint_sends(endpoints: DynamoEndpointRepository) -> None:
    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)

    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.SMS,
        body="Mona hasn't responded",
        link="https://incaof.com/r/token",
    )

    assert result.status is DeliveryStatus.ACCEPTED
    assert result.provider_reference


def test_a_provider_message_id_is_never_treated_as_arrival(
    endpoints: DynamoEndpointRepository,
) -> None:
    """A message id means the carrier took it, not that a phone received it.

    This is not hypothetical. On an SNS account in the SMS sandbox, publishing to an
    unverified number returns an ordinary MessageId and delivers nothing — which is exactly
    what this project's own dev account does today. If `succeeded` were allowed to mean
    "arrived", the Incident Room would tell a responder their sister had been contacted
    when no text was ever sent, and they would reasonably decide not to go round.
    """
    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)

    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.SMS,
        body="Mona hasn't responded",
        link=None,
    )

    assert result.succeeded, "the handoff did work"
    assert not result.confirmed, "but nothing has confirmed arrival"
    assert result.status is not DeliveryStatus.DELIVERED


def test_an_unverified_endpoint_is_not_messaged(
    endpoints: DynamoEndpointRepository,
) -> None:
    """It may belong to somebody else entirely — a typo, or a reassigned number."""
    endpoints.save(
        endpoint_id="e-1", person_id=MAYA, endpoint_type=EndpointType.PHONE, value=NUMBER
    )
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)

    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.SMS,
        body="x",
        link=None,
    )
    assert result.status is DeliveryStatus.FAILED
    assert result.error_code == "ENDPOINT_UNVERIFIED"


def test_a_missing_endpoint_fails_rather_than_crashes(
    endpoints: DynamoEndpointRepository,
) -> None:
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)
    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(OMAR),
        channel=Channel.SMS,
        body="x",
        link=None,
    )
    assert result.error_code == "NO_ENDPOINT"


def test_a_voice_rung_reports_unavailable_rather_than_pretending(
    endpoints: DynamoEndpointRepository,
) -> None:
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)
    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.CALL,
        body="x",
        link=None,
    )
    assert result.status is DeliveryStatus.CHANNEL_UNAVAILABLE


def test_the_delivery_result_never_carries_the_number(
    endpoints: DynamoEndpointRepository,
) -> None:
    """The result is recorded in the audit trail. It must be safe to store."""
    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    sender = SmsSender(sns=boto3.client("sns", region_name="us-east-1"), endpoints=endpoints)
    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.SMS,
        body="x",
        link=None,
    )

    assert NUMBER not in str(result)
    assert "900123" not in str(result)


class _CapturingSns:
    """Records what would be published, so the payload itself can be asserted on."""

    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []

    def publish(self, **kwargs: Any) -> dict[str, str]:
        self.published.append(kwargs)
        return {"MessageId": "push-1"}


def _push_endpoint(endpoints: DynamoEndpointRepository) -> None:
    endpoints.save(
        endpoint_id="p-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PUSH_TOKEN,
        value="arn:aws:sns:us-east-1:111122223333:endpoint/GCM/ico/abc",
        status=EndpointStatus.VERIFIED,
    )


def test_a_push_says_nothing_on_the_lock_screen(
    endpoints: DynamoEndpointRepository,
) -> None:
    """A notification is readable without unlocking, by whoever holds the phone.

    In the situation this product exists for, that is not reliably its owner. So the push
    says a check is waiting and nothing else — no name, no plan, no statement that somebody
    has not come home. The app renders the real copy after unlock.
    """
    _push_endpoint(endpoints)
    sns = _CapturingSns()
    sender = PushSender(sns=sns, endpoints=endpoints)

    result = sender.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.PUSH,
        body="Mona hasn't responded — Evening walk, expected 9:30 PM",
        link="https://incaof.com/r/token",
    )

    assert result.status is DeliveryStatus.ACCEPTED
    payload = str(sns.published[0]["Message"])
    assert "Mona" not in payload, "the subject's name reached a lock screen"
    assert "hasn't responded" not in payload
    assert "token" not in payload, "a responder link reached a lock screen"
    assert "A check is waiting for you" in payload


def test_the_router_keeps_unbound_channels_distinct_from_failures() -> None:
    """ "Nothing is wired to this" and "we tried and it broke" are different facts.

    Flattening them tells somebody to wait for a retry that is never coming.
    """
    router = ChannelRouter(senders={})

    result = router.send(
        alert_id=AlertId("alert-1"),
        member=a_member(),
        channel=Channel.PUSH,
        body="anything",
        link=None,
    )

    assert result.status is DeliveryStatus.CHANNEL_UNAVAILABLE
    assert not result.succeeded


def test_the_router_sends_each_rung_on_its_own_channel(
    endpoints: DynamoEndpointRepository,
) -> None:
    endpoints.save(
        endpoint_id="e-1",
        person_id=MAYA,
        endpoint_type=EndpointType.PHONE,
        value=NUMBER,
        status=EndpointStatus.VERIFIED,
    )
    _push_endpoint(endpoints)
    push_sns, sms = _CapturingSns(), boto3.client("sns", region_name="us-east-1")
    router = ChannelRouter(
        senders={
            Channel.SMS: SmsSender(sns=sms, endpoints=endpoints),
            Channel.PUSH: PushSender(sns=push_sns, endpoints=endpoints),
        }
    )

    for channel in (Channel.SMS, Channel.PUSH):
        assert router.send(
            alert_id=AlertId("alert-1"),
            member=a_member(),
            channel=channel,
            body="Mona hasn't responded",
            link=None,
        ).succeeded

    assert len(push_sns.published) == 1, "the SMS rung was published as a push"
    assert "TargetArn" in push_sns.published[0]
