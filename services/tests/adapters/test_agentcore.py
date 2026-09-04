from __future__ import annotations

from io import BytesIO
from typing import Any

from services.adapters.agentcore import AgentCoreCompiler


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def invoke_agent_runtime(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "response": BytesIO(b'{"compiledPlan":{},"trace":{}}'),
            "runtimeSessionId": kwargs["runtimeSessionId"],
            "traceId": "trace-1",
        }


def test_compiler_reuses_a_redacted_subject_session() -> None:
    client = RecordingClient()
    compiler = AgentCoreCompiler(client=client, runtime_arn="arn:runtime")

    for _ in range(2):
        compiler.compile(
            utterance="Check on me at nine",
            subject_person_id="person-sensitive-123",
            timezone="Africa/Cairo",
            circle_roles=[],
        )

    first = client.calls[0]
    second = client.calls[1]
    assert first["runtimeSessionId"] == second["runtimeSessionId"]
    assert first["runtimeSessionId"].startswith("compile-")
    assert len(first["runtimeSessionId"]) == 72
    assert "person-sensitive-123" not in first["runtimeSessionId"]
    assert first["runtimeUserId"] == "person-sensitive-123"
