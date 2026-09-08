"""DynamoDB persistence for account profile and launch-market preferences."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from services.adapters import keys
from services.domain.account import AccountStatus, Profile, SupportedCountry, SupportedLocale
from services.domain.errors import DomainError
from services.domain.ids import PersonId

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_dynamodb.service_resource import Table
else:
    Table = Any


@dataclass
class DynamoProfileRepository:
    table: Table

    def get(self, person_id: PersonId) -> Profile | None:
        item = self.table.get_item(
            ConsistentRead=True,
            Key={"pk": keys.person(person_id), "sk": "PROFILE"},
        ).get("Item")
        if item is None:
            return None
        return Profile(
            person_id=person_id,
            display_name=str(item["displayName"]),
            locale=SupportedLocale(str(item["locale"])),
            timezone=str(item["timezone"]),
            country=SupportedCountry(str(item["country"])),
            status=AccountStatus(str(item["status"])),
            created_at=datetime.fromisoformat(str(item["createdAt"])),
            updated_at=datetime.fromisoformat(str(item["updatedAt"])),
        )

    def save(self, profile: Profile) -> None:
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "ConditionCheck": {
                            "TableName": self.table.name,
                            "Key": {
                                "pk": keys.person(profile.person_id),
                                "sk": "ACCOUNT_DELETION",
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": keys.person(profile.person_id),
                                "sk": "PROFILE",
                                "entityType": "Profile",
                                "displayName": profile.display_name,
                                "locale": profile.locale.value,
                                "timezone": profile.timezone,
                                "country": profile.country.value,
                                "status": profile.status.value,
                                "createdAt": profile.created_at.isoformat(),
                                "updatedAt": profile.updated_at.isoformat(),
                            },
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException as error:
            raise DomainError("account deletion is in progress") from error
