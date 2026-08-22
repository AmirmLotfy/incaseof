"""Shared fixtures for contract tests.

These tests are the guard rail that keeps the three stacks (Python, Kotlin, TypeScript)
agreeing about what a plan is. They deliberately have no AWS or model dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "packages" / "domain-schemas"
FIXTURE_DIR = REPO_ROOT / "packages" / "test-fixtures"


def load_fixture(path: Path) -> dict[str, Any]:
    """Load a fixture, stripping the documentation-only root key.

    Invalid fixtures carry a root-level ``_why`` describing the single rule they exist to
    prove. The schema sets ``additionalProperties: false``, so leaving ``_why`` in place
    would make every negative test fail for that reason instead of the intended one --
    the tests would all pass while proving nothing.
    """
    data: dict[str, Any] = json.loads(path.read_text())
    data.pop("_why", None)
    return data


@pytest.fixture(scope="session")
def compiled_plan_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((SCHEMA_DIR / "compiled-plan.schema.json").read_text())
    return schema


@pytest.fixture(scope="session")
def alert_state_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((SCHEMA_DIR / "alert-state.schema.json").read_text())
    return schema


def valid_fixtures() -> list[Path]:
    return sorted((FIXTURE_DIR / "valid").glob("*.json"))


def invalid_fixtures() -> list[Path]:
    return sorted((FIXTURE_DIR / "invalid").glob("*.json"))
