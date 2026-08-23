"""What the model proposed, and what happened to it.

Every proposal is recorded -- **including the ones that were refused**. A denial that only
raises an exception disappears, and "nothing happened" then becomes indistinguishable from
"something was blocked", which is precisely the distinction an audit trail exists to make.

This is also what the developer trace renders. It is the difference between claiming the
policy layer works and being able to show it refusing something.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from .ids import AlertId


class PolicyResult(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True, slots=True)
class AgentDecision:
    """One model proposal and its outcome."""

    decision_id: str
    alert_id: AlertId | None
    model_id: str
    proposed_tool: str
    policy_result: PolicyResult
    reason_code: str
    created_at: datetime
    input_hash: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    @property
    def was_denied(self) -> bool:
        return self.policy_result is PolicyResult.DENY


def hash_input(text: str) -> str:
    """Fingerprint an utterance without storing it.

    The trace needs to correlate a decision with what prompted it. It does not need the
    sentence itself, and utterances are the most sensitive text this system sees -- someone
    describing where they are going and who they are afraid of.
    """
    return sha256(text.encode()).hexdigest()[:16]
