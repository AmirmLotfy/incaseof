from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

import boto3
import pytest
from botocore.stub import Stubber

from services.adapters.otp import DynamoPhoneVerificationRepository, PinpointOtpProvider
from services.domain.account import SupportedCountry
from services.domain.clock import utc
from services.domain.contact_endpoint import ContactEndpoint, EndpointStatus, EndpointType
from services.domain.ids import PersonId
from services.domain.phone_verification import (
    OtpSendRejected,
    PhoneVerification,
    PhoneVerificationRateLimited,
    PhoneVerificationStatus,
)

PERSON = PersonId("person-1")
NOW = utc(2026, 9, 7, 8, 0)


def _challenge(number: int = 1) -> PhoneVerification:
    return PhoneVerification(
        verification_id=f"verification-{number}",
        person_id=PERSON,
        endpoint_id=f"endpoint-{number}",
        provider_reference=f"reference-{number}",
        country=SupportedCountry.UNITED_STATES,
        status=PhoneVerificationStatus.RESERVED,
        attempts=0,
        created_at=NOW + timedelta(minutes=number - 1),
        expires_at=NOW + timedelta(minutes=number + 9),
    )


def test_challenge_reservation_is_atomic_and_enforces_cooldown(table: Any) -> None:
    repository = DynamoPhoneVerificationRepository(table)
    repository.reserve(_challenge())

    with pytest.raises(PhoneVerificationRateLimited):
        repository.reserve(replace(_challenge(2), created_at=NOW + timedelta(seconds=59)))

    assert repository.get(PERSON, "verification-1") == _challenge()
    assert repository.get(PERSON, "verification-2") is None


def test_challenge_enforces_daily_start_limit(table: Any) -> None:
    repository = DynamoPhoneVerificationRepository(table, cooldown=timedelta(0))
    for number in range(1, 6):
        repository.reserve(_challenge(number))

    with pytest.raises(PhoneVerificationRateLimited):
        repository.reserve(_challenge(6))


def test_invalid_attempts_fail_closed_at_five(table: Any) -> None:
    repository = DynamoPhoneVerificationRepository(table)
    challenge = _challenge()
    repository.reserve(challenge)
    challenge = repository.mark_sent(challenge, NOW)

    for _ in range(5):
        challenge = repository.record_invalid_attempt(challenge, NOW)

    assert challenge.attempts == 5
    assert challenge.status is PhoneVerificationStatus.FAILED


def test_correct_code_commit_atomically_requires_the_same_pending_endpoint(table: Any) -> None:
    repository = DynamoPhoneVerificationRepository(table)
    challenge = replace(_challenge(), previous_endpoint_id="previous")
    repository.reserve(challenge)
    challenge = repository.mark_sent(challenge, NOW)
    table.put_item(
        Item={
            "pk": "PERSON#person-1",
            "sk": "ENDPOINT#PHONE",
            "endpointId": "previous",
            "endpointType": "PHONE",
            "status": "VERIFIED",
            "ciphertext": b"old",
        }
    )
    endpoint = ContactEndpoint(
        endpoint_id=challenge.endpoint_id,
        person_id=PERSON,
        endpoint_type=EndpointType.PHONE,
        status=EndpointStatus.UNVERIFIED,
        ciphertext=b"sealed",
    )
    table.put_item(
        Item={
            "pk": "PERSON#person-1",
            "sk": f"ENDPOINT_CANDIDATE#PHONE#{challenge.endpoint_id}",
            "endpointId": challenge.endpoint_id,
            "endpointType": "PHONE",
            "status": "UNVERIFIED",
            "ciphertext": b"sealed",
        }
    )

    verified = repository.mark_verified(challenge, endpoint, NOW)

    assert verified is not None and verified.status is PhoneVerificationStatus.VERIFIED
    endpoint = table.get_item(
        Key={"pk": "PERSON#person-1", "sk": "ENDPOINT#PHONE"}, ConsistentRead=True
    )["Item"]
    assert endpoint["status"] == "VERIFIED"
    assert endpoint["verifiedAt"] == NOW.isoformat()


def test_correct_code_cannot_verify_a_replaced_endpoint(table: Any) -> None:
    repository = DynamoPhoneVerificationRepository(table)
    challenge = _challenge()
    repository.reserve(challenge)
    challenge = repository.mark_sent(challenge, NOW)
    endpoint = ContactEndpoint(
        endpoint_id=challenge.endpoint_id,
        person_id=PERSON,
        endpoint_type=EndpointType.PHONE,
        status=EndpointStatus.UNVERIFIED,
        ciphertext=b"sealed",
    )
    table.put_item(
        Item={
            "pk": "PERSON#person-1",
            "sk": f"ENDPOINT_CANDIDATE#PHONE#{challenge.endpoint_id}",
            "endpointId": challenge.endpoint_id,
            "endpointType": "PHONE",
            "status": "UNVERIFIED",
            "ciphertext": b"sealed",
        }
    )
    table.put_item(
        Item={
            "pk": "PERSON#person-1",
            "sk": "ENDPOINT#PHONE",
            "endpointId": "replacement",
            "endpointType": "PHONE",
            "status": "VERIFIED",
            "ciphertext": b"old",
        }
    )

    assert repository.mark_verified(challenge, endpoint, NOW) is None
    stored = repository.get(PERSON, challenge.verification_id)
    assert stored is not None and stored.status is PhoneVerificationStatus.SENT


def test_pinpoint_provider_sends_and_verifies() -> None:
    client = boto3.client("pinpoint", region_name="us-east-1")
    stubber = Stubber(client)
    destination = "+12025550123"
    request = {
        "ApplicationId": "app-1",
        "SendOTPMessageRequestParameters": {
            "AllowedAttempts": 5,
            "BrandName": "In Case Of",
            "Channel": "SMS",
            "CodeLength": 6,
            "DestinationIdentity": destination,
            "Language": "en-US",
            "OriginationIdentity": "+12025550199",
            "ReferenceId": "reference-1",
            "ValidityPeriod": 10,
        },
    }
    stubber.add_response(
        "send_otp_message",
        {
            "MessageResponse": {
                "ApplicationId": "app-1",
                "RequestId": "request-1",
                "Result": {
                    destination: {
                        "DeliveryStatus": "SUCCESSFUL",
                        "StatusCode": 200,
                        "MessageId": "message-1",
                    }
                },
            }
        },
        request,
    )
    stubber.add_response(
        "verify_otp_message",
        {"VerificationResponse": {"Valid": True}},
        {
            "ApplicationId": "app-1",
            "VerifyOTPMessageRequestParameters": {
                "DestinationIdentity": destination,
                "Otp": "123456",
                "ReferenceId": "reference-1",
            },
        },
    )
    provider = PinpointOtpProvider(client, "app-1", "+12025550199", "In Case Of")

    with stubber:
        assert provider.send(destination=destination, reference="reference-1") == "message-1"
        assert provider.verify(destination=destination, reference="reference-1", otp="123456")


def test_pinpoint_provider_rejects_a_non_success_delivery() -> None:
    client = boto3.client("pinpoint", region_name="us-east-1")
    stubber = Stubber(client)
    destination = "+12025550123"
    stubber.add_response(
        "send_otp_message",
        {
            "MessageResponse": {
                "ApplicationId": "app-1",
                "Result": {destination: {"DeliveryStatus": "PERMANENT_FAILURE", "StatusCode": 400}},
            }
        },
    )
    provider = PinpointOtpProvider(client, "app-1", "+12025550199", "In Case Of")

    with stubber, pytest.raises(OtpSendRejected):
        provider.send(destination=destination, reference="reference-1")
