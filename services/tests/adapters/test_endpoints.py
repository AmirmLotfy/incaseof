"""Contact endpoints: the most sensitive thing this system stores.

A phone number here, joined to the Circle it belongs to, is a map of who is close to whom.
These check the properties that make that safe to hold at all.
"""

from __future__ import annotations

from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError

from services.adapters.contact import DeliveryStatus, SmsSender
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
