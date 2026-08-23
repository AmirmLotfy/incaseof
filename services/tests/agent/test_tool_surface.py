"""The tool surface is the security boundary.

The question these ask is not "is this validated?" but the stronger one:

    could a completely compromised model cause harm through this signature?

A validation check can be forgotten in a refactor. A parameter that does not exist cannot.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from services.agent.tools import TOOL_NAMES, build_tools
from services.tests.agent.conftest import gateway_for


def tool_functions() -> list[Any]:
    return build_tools(gateway_for())


def test_the_tool_set_is_exactly_what_was_reviewed() -> None:
    """A new tool must be added deliberately, and considered against the rules below."""
    names = {t.tool_name for t in tool_functions()}
    assert names == TOOL_NAMES, f"tool surface changed: {names ^ TOOL_NAMES}"


@pytest.mark.parametrize("fn", tool_functions(), ids=lambda t: t.tool_name)
def test_no_tool_accepts_a_contact_endpoint(fn) -> None:  # type: ignore[no-untyped-def]
    """The rule that makes prompt injection structurally uninteresting.

    There is no parameter anywhere that can carry a phone number, an address or a URL, so
    "contact this person instead" is not a thing the model can say — regardless of what any
    text tells it to do.
    """
    forbidden = {
        "phone",
        "phone_number",
        "phonenumber",
        "number",
        "msisdn",
        "tel",
        "email",
        "address",
        "endpoint",
        "url",
        "link",
        "webhook",
        "to",
        "recipient",
        "destination",
        "contact",
    }
    signature = inspect.signature(fn._tool_func if hasattr(fn, "_tool_func") else fn)
    offenders = [p for p in signature.parameters if p.lower() in forbidden]
    assert not offenders, f"{fn.tool_name} accepts {offenders}"


@pytest.mark.parametrize("fn", tool_functions(), ids=lambda t: t.tool_name)
def test_no_tool_names_a_person(fn) -> None:  # type: ignore[no-untyped-def]
    """The model names a ROLE, never a person.

    A member id would technically be re-authorised server-side, but the stated rule is
    stricter and worth keeping: roles are a closed vocabulary the plan already defined,
    while an id is an open one.
    """
    signature = inspect.signature(fn._tool_func if hasattr(fn, "_tool_func") else fn)
    for name, param in signature.parameters.items():
        if name in {"person_id", "member_id", "circle_member_id", "responder_id"}:
            pytest.fail(f"{fn.tool_name} addresses a person directly via {name}")
        if name == "role":
            annotation = param.annotation
            assert annotation is str or annotation == "str", (
                f"{fn.tool_name}.role should be a plain string validated against the "
                f"plan's roles, got {annotation}"
            )


@pytest.mark.parametrize("fn", tool_functions(), ids=lambda t: t.tool_name)
def test_every_tool_is_documented_for_the_model(fn) -> None:  # type: ignore[no-untyped-def]
    """The description is what the model reasons about. A vague one produces vague use."""
    spec = fn.tool_spec
    description = spec.get("description", "")
    assert len(description) > 60, f"{fn.tool_name} is under-described"


def test_no_tool_can_send_anything() -> None:
    """There is no send, call, message or notify tool, and there must never be.

    Escalation dispatches through the workflow, which the model does not drive.
    """
    for name in TOOL_NAMES:
        for verb in ("send", "call_", "message_", "notify", "dial", "sms", "email"):
            assert verb not in name.lower(), f"{name} looks like a delivery tool"


def test_tools_hold_no_reference_to_storage() -> None:
    """Tools call the gateway and nothing else.

    A tool holding a repository would be one refactor away from skipping policy.
    """
    for fn in tool_functions():
        closure = getattr(fn._tool_func if hasattr(fn, "_tool_func") else fn, "__closure__", None)
        if not closure:
            continue
        captured = [type(cell.cell_contents).__name__ for cell in closure]
        for name in captured:
            assert "Repository" not in name, f"a tool captured {name} directly"
            assert "Table" not in name, f"a tool captured {name} directly"
