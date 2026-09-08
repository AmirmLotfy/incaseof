"""IAM-authenticated invocation of the ICO AgentCore Runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentCoreCompiler:
    client: Any
    runtime_arn: str
    qualifier: str = "DEFAULT"

    def compile(
        self,
        *,
        utterance: str,
        subject_person_id: str,
        timezone: str,
        circle_roles: list[dict[str, str]],
    ) -> dict[str, Any]:
        payload = json.dumps(
            {
                "operation": "compile_plan",
                "utterance": utterance,
                "timezone": timezone,
                "circleRoles": circle_roles,
            },
            separators=(",", ":"),
        ).encode()
        # Reuse one warm, stateless compiler session per authenticated subject. The hash
        # keeps the subject identifier out of AgentCore's infrastructure-level session ID,
        # and its 72-character value satisfies AgentCore's 33-character minimum. Creating
        # a fresh session on every retry can exhaust microVM capacity without adding any
        # isolation: runtimeUserId remains the actual AWS-enforced user boundary.
        runtime_session_id = f"compile-{sha256(str(subject_person_id).encode()).hexdigest()}"
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            qualifier=self.qualifier,
            runtimeSessionId=runtime_session_id,
            runtimeUserId=subject_person_id,
            contentType="application/json",
            accept="application/json",
            payload=payload,
        )
        stream = response["response"]
        raw = stream.read() if hasattr(stream, "read") else bytes(stream)
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("AgentCore returned a non-object response")
        decoded.setdefault("trace", {})
        if isinstance(decoded["trace"], dict):
            decoded["trace"].update(
                {
                    "runtimeSessionId": response.get("runtimeSessionId"),
                    "traceId": response.get("traceId"),
                }
            )
        return decoded
