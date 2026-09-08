from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from services.handlers.agent_tool_target import handler


@dataclass
class ClientContext:
    custom: dict[str, str]


@dataclass
class Context:
    tool: str
    aws_request_id: str = "request-1"

    @property
    def client_context(self) -> ClientContext:
        return ClientContext({"bedrockAgentCoreToolName": f"IcoSafetyTools___{self.tool}"})


def call(tool: str, event: dict[str, Any]) -> dict[str, Any]:
    return handler(event, Context(tool))


def test_contact_tool_accepts_only_an_abstract_role() -> None:
    result = call("propose_contact_role", {"role": "PRIMARY"})
    assert result == {
        "allowed": True,
        "role": "PRIMARY",
        "performed": False,
        "requiresDeterministicAuthorization": True,
    }


@pytest.mark.parametrize("role", ["Maya", "+12025550137", "maya@example.com", "https://x.test"])
def test_contact_tool_rejects_names_and_endpoints(role: str) -> None:
    with pytest.raises(ValueError, match="role must be"):
        call("propose_contact_role", {"role": role})


def test_tool_rejects_smuggled_arguments() -> None:
    with pytest.raises(ValueError, match="only role"):
        call("propose_contact_role", {"role": "PRIMARY", "phone": "+12025550137"})


def test_contract_tool_is_read_only() -> None:
    result = call("read_safety_contract", {})
    assert result["principle"] == "Monitor the plan, not the person"
    assert "endpoint" not in result
