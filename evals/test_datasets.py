"""Dataset integrity checks.

These run in normal CI: they need no model and no network, and they catch the failure
mode where an eval suite quietly stops covering what it claims to cover.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATASET_DIR = Path(__file__).parent / "datasets"

VALID_INTENTS = {
    "SAFE_CONFIRMED",
    "AMBIGUOUS",
    "EXTENSION_REQUESTED",
    "PLAN_EXCEPTION_REQUESTED",
    "CONTACT_REQUESTED",
}

REQUIRED_ATTACKS = {
    "arbitrary_number",
    "arbitrary_url",
    "fake_admin",
    "cross_tenant_read",
    "unauthorized_context_release",
    "delivery_as_resolution",
    "endpoint_injection",
    "silent_protection_change",
    "prompt_extraction",
    "hearsay_resolution",
    "replayed_token",
    "medical_assessment",
    "risk_prediction",
    "injection_via_plan_label",
    "injection_via_responder_message",
}


def read_jsonl(name: str) -> list[dict[str, Any]]:
    path = DATASET_DIR / name
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_intent_dataset_is_well_formed() -> None:
    rows = read_jsonl("intent.jsonl")
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for row in rows:
        # Empty and whitespace-only inputs are deliberately absent: guard_utterance rejects
        # them before the model is ever called, so they test the guard rather than the
        # model. They are covered in services/tests/agent/test_degradation.py.
        assert row["utterance"].strip(), f"{row['id']}: empty utterance"
        assert row["expected"], f"{row['id']}: no expected intent"
        unknown = set(row["expected"]) - VALID_INTENTS
        assert not unknown, f"{row['id']}: unknown intent {unknown}"


def test_the_suite_is_large_enough_to_mean_something() -> None:
    """The build contract asks for 100+ curated utterances."""
    rows = read_jsonl("intent.jsonl")
    assert len(rows) >= 100, f"only {len(rows)} intent cases"


def test_ambiguity_is_well_represented() -> None:
    """The most dangerous failure is treating a hedge as a confirmation.

    A suite with a handful of ambiguous cases cannot detect that regression, and hedges are
    exactly where a confident model goes wrong. A fifth of the suite is a floor, not a
    target.
    """
    rows = read_jsonl("intent.jsonl")
    ambiguous = [r for r in rows if "AMBIGUOUS" in r["expected"]]
    assert len(ambiguous) >= len(rows) // 5, (
        f"only {len(ambiguous)} of {len(rows)} cases are ambiguous"
    )


def test_every_intent_class_is_exercised() -> None:
    rows = read_jsonl("intent.jsonl")
    seen = {intent for row in rows for intent in row["expected"]}
    assert seen == VALID_INTENTS, f"never exercised: {sorted(VALID_INTENTS - seen)}"


def test_multi_intent_utterances_are_covered() -> None:
    """ "I'm okay but contact Maya anyway" must not lose half its meaning."""
    rows = read_jsonl("intent.jsonl")
    combined = [r for r in rows if len(r["expected"]) > 1]
    assert len(combined) >= 5, f"only {len(combined)} multi-intent cases"


def test_adversarial_dataset_covers_every_required_attack() -> None:
    rows = read_jsonl("adversarial.jsonl")
    covered = {r["attack"] for r in rows}
    missing = REQUIRED_ATTACKS - covered
    assert not missing, f"adversarial suite has no coverage for: {sorted(missing)}"
    for row in rows:
        assert row["expect_rejected"] is True, f"{row['id']}: adversarial cases must be rejected"


def test_adversarial_utterances_are_not_silently_dropped() -> None:
    rows = read_jsonl("adversarial.jsonl")
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate ids"
    assert len(rows) >= 30, f"adversarial suite is too small: {len(rows)} cases"


def test_the_adversarial_suite_covers_many_distinct_attacks() -> None:
    """Thirty variations on one attack would prove far less than thirty attacks."""
    rows = read_jsonl("adversarial.jsonl")
    classes = {row["attack"] for row in rows}
    assert len(classes) >= 20, f"only {len(classes)} distinct attack classes"
