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
        assert row["utterance"].strip(), f"{row['id']}: empty utterance"
        assert row["expected"], f"{row['id']}: no expected intent"
        unknown = set(row["expected"]) - VALID_INTENTS
        assert not unknown, f"{row['id']}: unknown intent {unknown}"


def test_ambiguity_is_represented() -> None:
    """The most dangerous failure is treating a hedge as a confirmation.

    If the suite has no ambiguous cases, it cannot detect that regression.
    """
    rows = read_jsonl("intent.jsonl")
    ambiguous = [r for r in rows if "AMBIGUOUS" in r["expected"]]
    assert len(ambiguous) >= 3, "too few ambiguous cases to detect over-confident resolution"


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
    assert len(rows) >= 10, "adversarial suite is too small to be meaningful"
