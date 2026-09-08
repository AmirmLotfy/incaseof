"""Durable admission capacity for active monitoring plans."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import DomainError


@dataclass(frozen=True, slots=True)
class PlanCapacityUsage:
    account_reserved: int
    global_reserved: int


class AccountPlanCapacityExhausted(DomainError):
    """The account already reserved every plan slot it may use."""


class GlobalPlanCapacityExhausted(DomainError):
    """The launch budget has no unreserved monitoring slot."""
