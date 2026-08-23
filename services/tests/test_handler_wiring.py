"""Every Lambda handler string in the CDK must resolve to a real entry point.

This exists because it did not. A refactor renamed `escalation.dispatch` to
`dispatch_handler` and left the template pointing at the old name; the internal function
still existed with a different signature, so nothing failed to import, nothing failed to
synth, and 337 tests passed. It failed in production, mid-escalation, with
"dispatch() missing 1 required positional argument".

Neither side alone can catch that: the Python tests never read the template, and the
template assertions never import the code. This reads both.
"""

from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path

import pytest

CONSTRUCTS = Path(__file__).resolve().parents[2] / "infra" / "cdk" / "lib" / "constructs"


def handler_strings() -> list[str]:
    found: set[str] = set()
    for source in CONSTRUCTS.glob("*.ts"):
        found |= set(re.findall(r'handler:\s*"(services\.[a-zA-Z0-9_.]+)"', source.read_text()))
    return sorted(found)


def test_the_templates_declare_handlers_at_all() -> None:
    """A regex that silently matches nothing would make every test below vacuous."""
    assert len(handler_strings()) >= 5, f"only found {handler_strings()}"


@pytest.mark.parametrize("reference", handler_strings())
def test_the_handler_exists(reference: str) -> None:
    module_name, _, function_name = reference.rpartition(".")
    module = importlib.import_module(module_name)
    assert hasattr(module, function_name), (
        f"the template points at {reference}, which does not exist. A renamed handler "
        f"fails at invocation, not at synth."
    )


@pytest.mark.parametrize("reference", handler_strings())
def test_the_handler_takes_a_lambda_signature(reference: str) -> None:
    """(event, context) — anything else fails the moment AWS invokes it.

    An internal helper with the same name is the dangerous case: it imports fine and looks
    right, and only the argument count gives it away.
    """
    module_name, _, function_name = reference.rpartition(".")
    target = getattr(importlib.import_module(module_name), function_name)
    params = list(inspect.signature(target).parameters.values())

    assert len(params) >= 2, (
        f"{reference} takes {[p.name for p in params]}; AWS calls it with (event, context)"
    )
    assert params[1].default is not inspect.Parameter.empty, (
        f"{reference}'s second parameter must default, so the handler can also be called "
        f"directly in a test"
    )
