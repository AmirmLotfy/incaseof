"""AgentCore Gateway Lambda target for ICO's role-only proposal tools.

This target deliberately has no repository, Scheduler, queue or messaging client. A tool
call can describe a proposed contact role or read the public safety contract; it cannot
resolve a contact endpoint or perform an action. Product Lambdas repeat ownership,
consent, plan-version and state checks before any later deterministic transition.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

TARGET_PREFIX = "IcoSafetyTools___"
ROLE_TOOL = "propose_contact_role"
CONTRACT_TOOL = "read_safety_contract"
ALLOWED_ROLES = frozenset({"PRIMARY", "BACKUP", "TERTIARY"})


def _tool_name(context: Any) -> str:
    client_context = getattr(context, "client_context", None)
    custom = getattr(client_context, "custom", None) if client_context else None
    full_name = custom.get("bedrockAgentCoreToolName", "") if isinstance(custom, dict) else ""
    if not full_name.startswith(TARGET_PREFIX):
        raise ValueError("unknown AgentCore Gateway target")
    return full_name.removeprefix(TARGET_PREFIX)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    tool = _tool_name(context)
    request_id = getattr(context, "aws_request_id", "unknown")
    result: dict[str, Any]

    if tool == CONTRACT_TOOL:
        if event:
            raise ValueError("read_safety_contract accepts no arguments")
        result = {
            "principle": "Monitor the plan, not the person",
            "resolutionRule": "Explicit confirmation is required",
            "contactRule": "Roles only; endpoints are resolved below the policy boundary",
        }
    elif tool == ROLE_TOOL:
        if set(event) != {"role"}:
            raise ValueError("propose_contact_role accepts only role")
        role = str(event.get("role") or "")
        if role not in ALLOWED_ROLES:
            # Cedar should deny before Lambda for the same invalid input. Repeating this
            # check makes policy defense-in-depth, never the sole safety boundary.
            raise ValueError("role must be PRIMARY, BACKUP or TERTIARY")
        result = {
            "allowed": True,
            "role": role,
            "performed": False,
            "requiresDeterministicAuthorization": True,
        }
    else:
        raise ValueError("unknown tool")

    log.info("gateway_tool_completed request_id=%s tool=%s", request_id, tool)
    return result
