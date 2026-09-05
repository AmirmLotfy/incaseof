"""Storing and using contact endpoints.

The only module that ever holds a readable phone number, and only for the duration of one
send. Everything above it deals in person ids and roles.

Encryption uses KMS with an **encryption context** binding the ciphertext to the person it
belongs to. Without that, a ciphertext lifted from one row and pasted into another would
decrypt happily, and the system would message the wrong person about somebody's safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from services.adapters import keys
from services.domain.contact_endpoint import (
    ContactEndpoint,
    EndpointStatus,
    EndpointType,
)
from services.domain.ids import PersonId

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_kms.client import KMSClient
else:
    KMSClient = Any
    Table = Any


class EndpointRepository(Protocol):
    def save(
        self,
        *,
        endpoint_id: str,
        person_id: PersonId,
        endpoint_type: EndpointType,
        value: str,
        status: EndpointStatus = EndpointStatus.UNVERIFIED,
        verified_at: datetime | None = None,
    ) -> ContactEndpoint: ...

    def for_person(
        self, person_id: PersonId, endpoint_type: EndpointType
    ) -> ContactEndpoint | None: ...

    def reveal(self, endpoint: ContactEndpoint) -> str:
        """Decrypt, for the single purpose of sending. Never log the result."""
        ...

    def delete(
        self, person_id: PersonId, endpoint_type: EndpointType, endpoint_id: str
    ) -> bool: ...


@dataclass
class DynamoEndpointRepository:
    table: Table
    kms: KMSClient
    key_id: str

    def save(
        self,
        *,
        endpoint_id: str,
        person_id: PersonId,
        endpoint_type: EndpointType,
        value: str,
        status: EndpointStatus = EndpointStatus.UNVERIFIED,
        verified_at: datetime | None = None,
    ) -> ContactEndpoint:
        """Encrypt and store. The plaintext never touches the table."""
        sealed = self.kms.encrypt(
            KeyId=self.key_id,
            Plaintext=value.encode(),
            # Binds the ciphertext to this person. A row copied to another person fails to
            # decrypt rather than silently messaging the wrong human being.
            EncryptionContext=self._context(person_id, endpoint_type),
        )["CiphertextBlob"]

        endpoint = ContactEndpoint(
            endpoint_id=endpoint_id,
            person_id=person_id,
            endpoint_type=endpoint_type,
            ciphertext=sealed,
            status=status,
            verified_at=verified_at,
        )
        self.table.put_item(
            Item={
                "pk": keys.person(person_id),
                "sk": f"ENDPOINT#{endpoint_type.value}",
                "endpointId": endpoint_id,
                "endpointType": endpoint_type.value,
                "status": status.value,
                "ciphertext": sealed,
                "verifiedAt": verified_at.isoformat() if verified_at else None,
            }
        )
        return endpoint

    def for_person(
        self, person_id: PersonId, endpoint_type: EndpointType
    ) -> ContactEndpoint | None:
        item = self.table.get_item(
            ConsistentRead=True,
            Key={"pk": keys.person(person_id), "sk": f"ENDPOINT#{endpoint_type.value}"},
        ).get("Item")
        if not item:
            return None

        verified = item.get("verifiedAt")
        return ContactEndpoint(
            endpoint_id=str(item["endpointId"]),
            person_id=person_id,
            endpoint_type=EndpointType(str(item["endpointType"])),
            ciphertext=bytes(item["ciphertext"].value)  # type: ignore[union-attr]
            if hasattr(item["ciphertext"], "value")
            else bytes(item["ciphertext"]),  # type: ignore[arg-type]
            status=EndpointStatus(str(item["status"])),
            verified_at=datetime.fromisoformat(str(verified)) if verified else None,
        )

    def reveal(self, endpoint: ContactEndpoint) -> str:
        """Decrypt for one send.

        The return value must not be logged, stored, put in a workflow payload, or returned
        from any API. It exists between here and the provider call, and nowhere else.
        """
        if not endpoint.is_usable:
            raise ValueError(
                f"endpoint {endpoint.endpoint_id} is {endpoint.status}; only a verified "
                f"endpoint may be contacted"
            )
        result = self.kms.decrypt(
            CiphertextBlob=endpoint.ciphertext,
            EncryptionContext=self._context(endpoint.person_id, endpoint.endpoint_type),
        )
        return str(result["Plaintext"].decode())

    def delete(self, person_id: PersonId, endpoint_type: EndpointType, endpoint_id: str) -> bool:
        current = self.for_person(person_id, endpoint_type)
        if current is None or current.endpoint_id != endpoint_id:
            return False
        self.table.delete_item(
            Key={"pk": keys.person(person_id), "sk": f"ENDPOINT#{endpoint_type.value}"}
        )
        return True

    @staticmethod
    def _context(person_id: PersonId, endpoint_type: EndpointType) -> dict[str, str]:
        return {"personId": str(person_id), "endpointType": endpoint_type.value}
