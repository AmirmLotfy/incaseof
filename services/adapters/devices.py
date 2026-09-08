"""FCM device registration through Amazon SNS mobile push."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from services.adapters.endpoints import EndpointRepository
from services.domain.contact_endpoint import EndpointStatus, EndpointType
from services.domain.ids import DeviceId, PersonId


class DeviceRegistry(Protocol):
    def register(
        self,
        *,
        device_id: DeviceId,
        person_id: PersonId,
        registration_token: str,
        now: datetime,
    ) -> None: ...

    def remove(self, *, device_id: DeviceId, person_id: PersonId) -> bool: ...


@dataclass
class SnsDeviceRegistry:
    sns: Any
    endpoints: EndpointRepository
    platform_application_arn: str

    def register(
        self,
        *,
        device_id: DeviceId,
        person_id: PersonId,
        registration_token: str,
        now: datetime,
    ) -> None:
        result = self.sns.create_platform_endpoint(
            PlatformApplicationArn=self.platform_application_arn,
            Token=registration_token,
            CustomUserData=str(person_id),
        )
        endpoint_arn = str(result["EndpointArn"])
        self.endpoints.save(
            endpoint_id=str(device_id),
            person_id=person_id,
            endpoint_type=EndpointType.PUSH_TOKEN,
            value=endpoint_arn,
            status=EndpointStatus.VERIFIED,
            verified_at=now,
        )

    def remove(self, *, device_id: DeviceId, person_id: PersonId) -> bool:
        endpoint = self.endpoints.for_person(person_id, EndpointType.PUSH_TOKEN)
        if endpoint is None or endpoint.endpoint_id != device_id:
            return False
        endpoint_arn = self.endpoints.reveal(endpoint)
        self.sns.delete_endpoint(EndpointArn=endpoint_arn)
        return self.endpoints.delete(person_id, EndpointType.PUSH_TOKEN, str(device_id))
