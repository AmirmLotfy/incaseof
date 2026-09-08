"""What happens when the model is not there.

"All safety workflows continue if the model is unavailable" is a non-negotiable, and it is
the property most likely to be quietly lost: the model works during development, so the
path where it does not is the one nobody exercises.

Every failure mode here has the same correct answer — fall back to explicit choices and let
the person answer plainly. A safety product that resolves an Alert because a classifier was
confident-but-wrong is worse than one that asks a question.
"""

from __future__ import annotations

import pytest

from services.agent.agent import (
    FALLBACK_CHOICES,
    Intent,
    IntentReading,
    Reading,
    read,
)

from .conftest import StubAgent


def test_an_outage_degrades_to_explicit_choices() -> None:
    reading = read(StubAgent(error=ConnectionError("model unreachable")), "I'm okay")

    assert reading.degraded
    assert reading.choices == FALLBACK_CHOICES
    assert not reading.unambiguous


def test_a_timeout_degrades() -> None:
    reading = read(StubAgent(error=TimeoutError("deadline exceeded")), "I'm okay")
    assert reading.degraded


def test_malformed_output_degrades_rather_than_guessing() -> None:
    """A response that is not the shape we asked for tells us nothing."""
    reading = read(StubAgent(error=ValueError("invalid JSON")), "I'm okay")
    assert reading.degraded


def test_an_unrecognised_intent_degrades() -> None:
    """A model that invents an intent name must not have it silently accepted."""
    reading = read(
        StubAgent(result=IntentReading(intents=["DEFINITELY_FINE"], unambiguous=True)),
        "I'm okay",
    )
    assert reading.degraded


def test_an_empty_utterance_degrades() -> None:
    assert read(StubAgent(), "").degraded
    assert read(StubAgent(), "   ").degraded


def test_an_enormous_utterance_degrades_without_reaching_the_model() -> None:
    """Bounds the input rather than filtering it. The tool surface is the real defence."""
    agent = StubAgent(result=IntentReading(intents=["SAFE_CONFIRMED"], unambiguous=True))
    reading = read(agent, "x" * 5000)

    assert reading.degraded
    assert not agent.calls, "an oversized utterance still reached the model"


def test_degradation_never_looks_like_a_confirmation() -> None:
    """The failure mode that would actually hurt somebody."""
    for error in (ConnectionError(), TimeoutError(), ValueError(), RuntimeError()):
        reading = read(StubAgent(error=error), "I'm okay")
        assert not reading.wants(Intent.SAFE_CONFIRMED), (
            f"{type(error).__name__} was read as a confirmation"
        )


def test_the_fallback_choices_let_a_person_do_everything_that_matters() -> None:
    """Confirm, ask for someone, or buy time — without the model."""
    assert FALLBACK_CHOICES == ("I'M OKAY", "NEED SOMEONE", "GIVE ME MORE TIME")


def test_a_good_reading_is_passed_through() -> None:
    reading = read(
        StubAgent(result=IntentReading(intents=["SAFE_CONFIRMED"], unambiguous=True)),
        "I'm fine, just fell asleep",
    )

    assert not reading.degraded
    assert reading.wants(Intent.SAFE_CONFIRMED)
    assert reading.unambiguous
    assert reading.choices == ()


def test_a_hedge_is_carried_through_as_ambiguous() -> None:
    reading = read(
        StubAgent(result=IntentReading(intents=["AMBIGUOUS"], unambiguous=False)),
        "probably",
    )

    assert reading.wants(Intent.AMBIGUOUS)
    assert not reading.unambiguous


def test_two_intents_in_one_utterance_both_survive() -> None:
    """ "I'm okay but contact Maya anyway" must not lose half its meaning."""
    reading = read(
        StubAgent(
            result=IntentReading(
                intents=["SAFE_CONFIRMED", "CONTACT_REQUESTED"],
                unambiguous=True,
                role="PRIMARY",
            )
        ),
        "I'm okay but please contact Maya anyway",
    )

    assert reading.wants(Intent.SAFE_CONFIRMED)
    assert reading.wants(Intent.CONTACT_REQUESTED)
    assert reading.role == "PRIMARY"


@pytest.mark.parametrize("degraded", [True, False])
def test_the_domain_never_imports_the_model(degraded: bool) -> None:
    """The structural reason escalation survives an outage.

    Asserted in test_purity.py too; repeated here because this is the property the whole
    file is about, and it is the one that makes the rest of it true rather than hopeful.
    """
    del degraded
    import ast
    from pathlib import Path

    domain = Path(__file__).resolve().parents[2] / "domain"
    for module in domain.glob("*.py"):
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(("strands", "google")), (
                    f"{module.name} imports {node.module}"
                )


def test_a_degraded_reading_reports_itself_as_degraded() -> None:
    """Callers must be able to tell a fallback from an answer.

    A degraded reading that looked like a normal one would let the UI present a guess as a
    classification.
    """
    reading = read(StubAgent(error=ConnectionError()), "anything")
    assert isinstance(reading, Reading)
    assert reading.degraded
    assert reading.intents == (Intent.UNAVAILABLE,)
