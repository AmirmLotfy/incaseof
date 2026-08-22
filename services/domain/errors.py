"""Domain errors.

Each error names a rule from the product contract, so a failure message points at the
decision it violated rather than at a stack frame.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base for every rule this domain enforces."""


class InvalidTransition(DomainError):
    """A transition that does not appear in docs/PRODUCT-STATES.md section 2."""

    def __init__(self, state: str, event: str) -> None:
        super().__init__(
            f"{event} is not a valid event in state {state}. "
            f"See docs/PRODUCT-STATES.md section 2 - it is normative."
        )
        self.state = state
        self.event = event


class TerminalAlert(DomainError):
    """An attempt to move an Alert that has already reached a terminal state.

    Invariant 3: terminal states never transition out.
    """


class PlanValidationError(DomainError):
    """A compiled plan that cannot safely become a PlanVersion."""


class NotAuthorized(DomainError):
    """An action the actor is not permitted to take.

    Raised for consent that is absent, withdrawn or expired; for a responder who is not
    on the Alert's pinned PlanVersion; and for a contact the current escalation step does
    not permit.
    """


class LeaseConflict(DomainError):
    """Two responders cannot both believe they own an Alert."""


class DuplicateAction(DomainError):
    """An external action with this idempotency key was already dispatched.

    Callers treat this as success and do not resend: the target of a duplicate is a real
    person being contacted twice about the same alert.
    """
