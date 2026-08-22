"""The domain must stay pure.

`.claude/rules/backend.md`: "Domain logic has no AWS imports - keep it testable without
mocking the cloud." This asserts it, because the rule is one careless import from being
untrue, and the cost only shows up much later as tests that need credentials.

The same applies to the model: nothing in the safety core may depend on Gemini being
reachable, since escalation has to continue when it is not.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN = Path(__file__).resolve().parents[2] / "domain"

FORBIDDEN_PREFIXES = (
    "boto3",
    "botocore",
    "aws_lambda_powertools",
    "strands",
    "google",
    "google_genai",
    "requests",
    "httpx",
    "urllib3",
)

# datetime.now() and friends: time must arrive as an argument so lease expiry and grace
# windows are testable. See services/domain/clock.py.
AMBIENT_TIME_CALLS = {"now", "utcnow", "today", "time", "monotonic"}


def domain_modules() -> list[Path]:
    return sorted(p for p in DOMAIN.glob("*.py") if p.name != "__init__.py")


def test_there_are_domain_modules_to_check() -> None:
    """A glob that matches nothing would make every test below vacuously pass."""
    assert len(domain_modules()) >= 8


@pytest.mark.parametrize("module", domain_modules(), ids=lambda p: p.name)
def test_no_cloud_or_model_imports(module: Path) -> None:
    tree = ast.parse(module.read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.append(node.module)

    offenders = [
        name
        for name in imported
        if any(name == p or name.startswith(f"{p}.") for p in FORBIDDEN_PREFIXES)
    ]
    assert not offenders, (
        f"{module.name} imports {offenders}. The domain owns safety state and must run "
        f"without the cloud or the model being reachable."
    )


@pytest.mark.parametrize("module", domain_modules(), ids=lambda p: p.name)
def test_no_ambient_clock_reads(module: Path) -> None:
    """`clock.py` defines the only sanctioned clock reads."""
    if module.name == "clock.py":
        return

    tree = ast.parse(module.read_text())
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in AMBIENT_TIME_CALLS:
                value = node.func.value
                root = value.id if isinstance(value, ast.Name) else None
                if root in {"datetime", "date", "time"}:
                    offenders.append(f"{root}.{node.func.attr}() at line {node.lineno}")

    assert not offenders, (
        f"{module.name} reads the clock directly: {offenders}. Time must be passed in, "
        f"or lease expiry and grace windows become untestable."
    )
