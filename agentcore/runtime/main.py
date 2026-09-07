"""ICO's side-effect-free Strands compiler on Amazon Bedrock AgentCore Runtime."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from services.agent.agent import build_compile_agent, compile_plan_from_utterance
from services.agent.config import MODEL_ID, PROMPT_SCHEMA_VERSION
from services.domain.compiler import document_from_version
from services.domain.errors import PlanValidationError
from services.domain.ids import PlanId, uuid_factory

log = logging.getLogger(__name__)
app = BedrockAgentCoreApp(debug=False)
_agent: Any | None = None


def _compiler() -> Any:
    global _agent
    if _agent is None:
        _agent = build_compile_agent()
    return _agent


def _roles(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 10:
        raise PlanValidationError("circleRoles must be an array with at most 10 roles")
    allowed_roles = {"PRIMARY", "BACKUP", "TERTIARY"}
    allowed_states = {"INVITED", "ACCEPTED", "DECLINED", "REMOVED"}
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise PlanValidationError("each Circle role must be an object")
        role = str(item.get("role") or "")
        status = str(item.get("status") or "")
        if role not in allowed_roles or status not in allowed_states:
            raise PlanValidationError("Circle role or status is invalid")
        result.append({"role": role, "status": status})
    return result


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile language to typed data; never create, activate, schedule or contact."""
    started = time.monotonic()
    if not isinstance(payload, dict) or payload.get("operation") != "compile_plan":
        raise PlanValidationError("unsupported operation")
    utterance = str(payload.get("utterance") or "")
    timezone = str(payload.get("timezone") or "UTC")
    roles = _roles(payload.get("circleRoles") or [])

    preview = compile_plan_from_utterance(
        _compiler(),
        utterance,
        plan_id=PlanId(uuid_factory()),
        timezone=timezone,
        circle_roles=roles,
    )
    elapsed_ms = round((time.monotonic() - started) * 1000)
    # Never log or return raw private text. The hash lets operators correlate retries and
    # evaluation cases without turning CloudWatch into a second copy of personal plans.
    input_hash = hashlib.sha256(utterance.encode()).hexdigest()
    log.info(
        json.dumps(
            {
                "event": "compile_completed",
                "model_id": MODEL_ID,
                "schema_version": PROMPT_SCHEMA_VERSION,
                "input_hash": input_hash,
                "latency_ms": elapsed_ms,
            },
            separators=(",", ":"),
        )
    )
    return {
        "compiledPlan": document_from_version(preview.result.version),
        "warnings": list(preview.warnings),
        "trace": {
            "modelId": MODEL_ID,
            "schemaVersion": PROMPT_SCHEMA_VERSION,
            "inputHash": input_hash,
            "latencyMs": elapsed_ms,
            "runtime": "AMAZON_BEDROCK_AGENTCORE",
            "authorization": "IAM_SIGV4",
        },
    }


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "8080")))
