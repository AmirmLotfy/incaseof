"""Durable phone-verification challenges and the AWS OTP boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, NoReturn, Protocol, cast

from boto3.dynamodb.conditions import Attr
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from services.adapters import keys
from services.domain.account import SupportedCountry
from services.domain.contact_endpoint import ContactEndpoint
from services.domain.ids import PersonId
from services.domain.phone_verification import (
    OtpProviderUnavailable,
    OtpSendRejected,
    PhoneVerification,
    PhoneVerificationRateLimited,
    PhoneVerificationStatus,
)

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_pinpoint.client import PinpointClient
else:
    PinpointClient = Any
    Table = Any


class OtpProvider(Protocol):
    def send(self, *, destination: str, reference: str) -> str | None: ...

    def verify(self, *, destination: str, reference: str, otp: str) -> bool: ...


class PhoneVerificationRepository(Protocol):
    def reserve(self, challenge: PhoneVerification) -> None: ...

    def get(self, person_id: PersonId, verification_id: str) -> PhoneVerification | None: ...

    def mark_sent(self, challenge: PhoneVerification, at: datetime) -> PhoneVerification: ...

    def mark_failed(self, challenge: PhoneVerification) -> PhoneVerification: ...

    def record_invalid_attempt(
        self, challenge: PhoneVerification, at: datetime
    ) -> PhoneVerification: ...

    def mark_verified(
        self, challenge: PhoneVerification, endpoint: ContactEndpoint, at: datetime
    ) -> PhoneVerification | None: ...


@dataclass
class DynamoPhoneVerificationRepository:
    table: Table
    daily_limit: int = 5
    cooldown: timedelta = timedelta(seconds=60)
    max_attempts: int = 5

    @staticmethod
    def _key(person_id: PersonId, verification_id: str) -> dict[str, str]:
        return {
            "pk": keys.person(person_id),
            "sk": f"PHONE_VERIFICATION#{verification_id}",
        }

    def reserve(self, challenge: PhoneVerification) -> None:
        """Atomically reserve a challenge and one per-person rate-limit slot."""
        day = challenge.created_at.date().isoformat()
        cutoff = (challenge.created_at - self.cooldown).isoformat()
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": {
                                "pk": keys.person(challenge.person_id),
                                "sk": f"PHONE_VERIFICATION_RATE#{day}",
                            },
                            "UpdateExpression": (
                                "SET entityType = :kind, lastStartedAt = :now ADD startCount :one"
                            ),
                            "ConditionExpression": (
                                "(attribute_not_exists(startCount) OR startCount < :limit) AND "
                                "(attribute_not_exists(lastStartedAt) OR lastStartedAt <= :cutoff)"
                            ),
                            "ExpressionAttributeValues": {
                                ":kind": "PhoneVerificationRate",
                                ":now": challenge.created_at.isoformat(),
                                ":cutoff": cutoff,
                                ":one": 1,
                                ":limit": self.daily_limit,
                            },
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": self._to_item(challenge),
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException as error:
            raise PhoneVerificationRateLimited("phone verification is rate limited") from error

    def get(self, person_id: PersonId, verification_id: str) -> PhoneVerification | None:
        item = self.table.get_item(
            Key=self._key(person_id, verification_id), ConsistentRead=True
        ).get("Item")
        return self._from_item(item) if item else None

    def mark_sent(self, challenge: PhoneVerification, at: datetime) -> PhoneVerification:
        return self._transition(challenge, challenge.sent(at), {PhoneVerificationStatus.RESERVED})

    def mark_failed(self, challenge: PhoneVerification) -> PhoneVerification:
        failed = replace(challenge, status=PhoneVerificationStatus.FAILED)
        return self._transition(
            challenge,
            failed,
            {PhoneVerificationStatus.RESERVED, PhoneVerificationStatus.SENT},
        )

    def record_invalid_attempt(
        self, challenge: PhoneVerification, at: datetime
    ) -> PhoneVerification:
        attempts = challenge.attempts + 1
        status = (
            PhoneVerificationStatus.FAILED if attempts >= self.max_attempts else challenge.status
        )
        updated = replace(challenge, attempts=attempts, status=status)
        del at  # provider owns OTP expiry; this write owns only attempts/status
        return self._transition(
            challenge,
            updated,
            {PhoneVerificationStatus.RESERVED, PhoneVerificationStatus.SENT},
        )

    def mark_verified(
        self, challenge: PhoneVerification, endpoint: ContactEndpoint, at: datetime
    ) -> PhoneVerification | None:
        """Commit provider validation and endpoint usability in one transaction."""
        after = challenge.verified(at)
        active_put: dict[str, Any] = {
            "TableName": self.table.name,
            "Item": {
                "pk": keys.person(challenge.person_id),
                "sk": "ENDPOINT#PHONE",
                "endpointId": endpoint.endpoint_id,
                "endpointType": "PHONE",
                "status": "VERIFIED",
                "ciphertext": endpoint.ciphertext,
                "verifiedAt": at.isoformat(),
            },
        }
        if challenge.previous_endpoint_id is None:
            active_put["ConditionExpression"] = "attribute_not_exists(pk)"
        else:
            active_put["ConditionExpression"] = "endpointId = :previous"
            active_put["ExpressionAttributeValues"] = {":previous": challenge.previous_endpoint_id}
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": self._key(challenge.person_id, challenge.verification_id),
                            "UpdateExpression": "SET #status = :verified, verifiedAt = :at",
                            "ConditionExpression": (
                                "#status IN (:reserved, :sent) AND attempts = :attempts "
                                "AND endpointId = :endpoint"
                            ),
                            "ExpressionAttributeNames": {"#status": "status"},
                            "ExpressionAttributeValues": {
                                ":verified": PhoneVerificationStatus.VERIFIED.value,
                                ":reserved": PhoneVerificationStatus.RESERVED.value,
                                ":sent": PhoneVerificationStatus.SENT.value,
                                ":attempts": challenge.attempts,
                                ":endpoint": challenge.endpoint_id,
                                ":at": at.isoformat(),
                            },
                        }
                    },
                    {"Put": cast(Any, active_put)},
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": {
                                "pk": keys.person(challenge.person_id),
                                "sk": f"ENDPOINT_CANDIDATE#PHONE#{challenge.endpoint_id}",
                            },
                            "UpdateExpression": "SET #status = :verified, verifiedAt = :at",
                            "ConditionExpression": "endpointId = :endpoint AND #status = :pending",
                            "ExpressionAttributeNames": {"#status": "status"},
                            "ExpressionAttributeValues": {
                                ":verified": "VERIFIED",
                                ":pending": "UNVERIFIED",
                                ":endpoint": challenge.endpoint_id,
                                ":at": at.isoformat(),
                            },
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException:
            current = self.get(challenge.person_id, challenge.verification_id)
            if current is not None and current.status is PhoneVerificationStatus.VERIFIED:
                return current
            return None
        return after

    def _transition(
        self,
        before: PhoneVerification,
        after: PhoneVerification,
        allowed: set[PhoneVerificationStatus],
    ) -> PhoneVerification:
        try:
            self.table.put_item(
                Item=self._to_item(after),
                ConditionExpression=Attr("status").is_in([status.value for status in allowed])
                & Attr("attempts").eq(before.attempts)
                & Attr("endpointId").eq(before.endpoint_id),
            )
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            current = self.get(before.person_id, before.verification_id)
            if current == after:
                return current
            raise PhoneVerificationRateLimited("phone verification changed concurrently") from None
        return after

    @staticmethod
    def _to_item(challenge: PhoneVerification) -> dict[str, Any]:
        return {
            "pk": keys.person(challenge.person_id),
            "sk": f"PHONE_VERIFICATION#{challenge.verification_id}",
            "entityType": "PhoneVerification",
            "verificationId": challenge.verification_id,
            "endpointId": challenge.endpoint_id,
            "providerReference": challenge.provider_reference,
            "country": challenge.country.value,
            "status": challenge.status.value,
            "attempts": challenge.attempts,
            "createdAt": challenge.created_at.isoformat(),
            "expiresAt": challenge.expires_at.isoformat(),
            "sentAt": challenge.sent_at.isoformat() if challenge.sent_at else None,
            "verifiedAt": challenge.verified_at.isoformat() if challenge.verified_at else None,
            "previousEndpointId": challenge.previous_endpoint_id,
        }

    @staticmethod
    def _from_item(item: dict[str, Any]) -> PhoneVerification:
        return PhoneVerification(
            verification_id=str(item["verificationId"]),
            person_id=PersonId(str(item["pk"]).removeprefix("PERSON#")),
            endpoint_id=str(item["endpointId"]),
            provider_reference=str(item["providerReference"]),
            country=SupportedCountry(str(item["country"])),
            status=PhoneVerificationStatus(str(item["status"])),
            attempts=int(item["attempts"]),
            created_at=datetime.fromisoformat(str(item["createdAt"])),
            expires_at=datetime.fromisoformat(str(item["expiresAt"])),
            sent_at=datetime.fromisoformat(str(item["sentAt"])) if item.get("sentAt") else None,
            verified_at=datetime.fromisoformat(str(item["verifiedAt"]))
            if item.get("verifiedAt")
            else None,
            previous_endpoint_id=str(item["previousEndpointId"])
            if item.get("previousEndpointId")
            else None,
        )


@dataclass(frozen=True)
class PinpointOtpProvider:
    client: PinpointClient
    application_id: str
    origination_identity: str
    brand_name: str
    validity_minutes: int = 10
    allowed_attempts: int = 5

    def send(self, *, destination: str, reference: str) -> str | None:
        try:
            response = self.client.send_otp_message(
                ApplicationId=self.application_id,
                SendOTPMessageRequestParameters={
                    "AllowedAttempts": self.allowed_attempts,
                    "BrandName": self.brand_name,
                    "Channel": "SMS",
                    "CodeLength": 6,
                    "DestinationIdentity": destination,
                    "Language": "en-US",
                    "OriginationIdentity": self.origination_identity,
                    "ReferenceId": reference,
                    "ValidityPeriod": self.validity_minutes,
                },
            )
        except (BotoCoreError, ClientError) as error:
            self._raise_provider_error(error)
        message = response.get("MessageResponse", {})
        result = cast(dict[str, Any], message.get("Result", {}).get(destination, {}))
        if result.get("DeliveryStatus") != "SUCCESSFUL":
            raise OtpSendRejected("OTP send was rejected")
        provider_reference = result.get("MessageId") or message.get("RequestId")
        return str(provider_reference) if provider_reference else None

    def verify(self, *, destination: str, reference: str, otp: str) -> bool:
        try:
            response = self.client.verify_otp_message(
                ApplicationId=self.application_id,
                VerifyOTPMessageRequestParameters={
                    "DestinationIdentity": destination,
                    "Otp": otp,
                    "ReferenceId": reference,
                },
            )
        except (BotoCoreError, ClientError) as error:
            self._raise_provider_error(error)
        return response.get("VerificationResponse", {}).get("Valid") is True

    @staticmethod
    def _raise_provider_error(error: Exception) -> NoReturn:
        if isinstance(error, ClientError):
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"BadRequestException", "ForbiddenException", "NotFoundException"}:
                raise OtpSendRejected("OTP provider rejected the request") from error
        raise OtpProviderUnavailable("OTP provider is temporarily unavailable") from error


def pinpoint_client(boto3_module: Any) -> Any:
    """Create the client with bounded retries and timeouts for a synchronous API path."""
    return boto3_module.client(
        "pinpoint",
        config=Config(
            # A timed-out send has an unknown outcome. Retrying it here could generate
            # two valid codes, so this boundary makes exactly one provider call.
            retries={"total_max_attempts": 1, "mode": "standard"},
            connect_timeout=5,
            read_timeout=10,
        ),
    )
