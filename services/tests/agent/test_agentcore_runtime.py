from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from agentcore.runtime import main
from services.agent.compilation import CompiledPlanDraft
from services.domain.errors import PlanValidationError

from .conftest import StubAgent


def test_runtime_import_does_not_reach_stateful_handlers() -> None:
    """The AgentCore ZIP intentionally excludes services.handlers and adapters."""
    repository = Path(__file__).resolve().parents[3]
    script = """
import importlib.abc
import sys

class BlockStatefulRuntimeImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'services.handlers' or fullname.startswith('services.handlers.'):
            raise ImportError(f'forbidden runtime import: {fullname}')
        return None

sys.meta_path.insert(0, BlockStatefulRuntimeImports())
import agentcore.runtime.main
"""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned script
        [sys.executable, "-c", script],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def _draft() -> CompiledPlanDraft:
    return CompiledPlanDraft.model_validate(
        {
            "type": "ROUTINE",
            "label": "Evening check",
            "timezone": "Africa/Cairo",
            "trigger": {"kind": "RECURRING", "timeOfDay": "21:00"},
            "grace": {"seconds": 300},
            "steps": [
                {"sequence": 1, "offsetSeconds": 0, "action": "PUSH_SUBJECT"},
                {
                    "sequence": 2,
                    "offsetSeconds": 300,
                    "action": "MESSAGE_RESPONDER",
                    "targetRole": "PRIMARY",
                },
            ],
            "stopConditions": [
                "SUBJECT_EXPLICIT_CONFIRMATION",
                "RESPONDER_VERIFIED_CONTACT",
            ],
            "contextPolicy": {"location": "NEVER"},
        }
    )


def test_runtime_compiles_without_exposing_the_utterance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "_agent", StubAgent(result=_draft()))
    utterance = "check on me every evening at nine"

    result = main.invoke(
        {
            "operation": "compile_plan",
            "utterance": utterance,
            "timezone": "Africa/Cairo",
            "circleRoles": [{"role": "PRIMARY", "status": "ACCEPTED"}],
        }
    )

    assert result["compiledPlan"]["timezone"] == "Africa/Cairo"
    assert result["trace"]["runtime"] == "AMAZON_BEDROCK_AGENTCORE"
    assert result["trace"]["modelId"] == "us.anthropic.claude-sonnet-4-6"
    assert len(result["trace"]["inputHash"]) == 64
    assert utterance not in str(result)


def test_runtime_rejects_model_controlled_contact_identity() -> None:
    with pytest.raises(PlanValidationError, match="role or status"):
        main.invoke(
            {
                "operation": "compile_plan",
                "utterance": "contact Maya",
                "timezone": "UTC",
                "circleRoles": [{"role": "+12025550137", "status": "ACCEPTED"}],
            }
        )
