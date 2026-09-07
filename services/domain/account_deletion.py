"""Durable account-erasure requests.

Deletion begins by closing the account to new work. A separate worker then removes
provider resources, timers, workflows, application data, and finally the Cognito user.
Keeping that work asynchronous lets every step be retried after a worker crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .clock import require_aware
from .ids import PersonId


class AccountDeletionStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"


@dataclass(frozen=True, slots=True)
class AccountDeletion:
    request_id: str
    person_id: PersonId
    cognito_username: str
    status: AccountDeletionStatus
    requested_at: datetime
    attempts: int = 0

    def __post_init__(self) -> None:
        if not self.request_id or not self.cognito_username:
            raise ValueError("deletion identity is required")
        require_aware(self.requested_at, "account_deletion.requested_at")
        if self.attempts < 0:
            raise ValueError("deletion attempts cannot be negative")
