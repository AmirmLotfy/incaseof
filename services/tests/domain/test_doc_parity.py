"""The normative document is executable.

docs/PRODUCT-STATES.md declares itself the source of truth for the Alert lifecycle. That
claim is worth nothing unless something checks it, so this parses the transition table out
of the markdown and asserts the code agrees -- in *both* directions.

A transition added to the code but not the document fails here. A row added to the
document but not implemented fails here too. That is what "the documents win" means when
it is mechanical rather than aspirational.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from services.domain.alert import (
    NON_TERMINAL_STATES,
    TRANSITIONS,
    AlertEvent,
    AlertState,
)

DOC = Path(__file__).resolve().parents[3] / "docs" / "PRODUCT-STATES.md"

# Prose in the document -> the event the code names. Explicit rather than fuzzy-matched:
# a mapping that guesses would quietly skip a row it failed to understand, and a silently
# skipped row is exactly the drift this test exists to catch.
EVENT_PROSE: dict[str, AlertEvent] = {
    "due time reached": AlertEvent.DUE_TIME_REACHED,
    "grace configured": AlertEvent.GRACE_CONFIGURED,
    "grace elapsed": AlertEvent.GRACE_ELAPSED,
    "subject confirms": AlertEvent.SUBJECT_CONFIRMED,
    "subject confirms okay": AlertEvent.SUBJECT_CONFIRMED,
    "user cancels": AlertEvent.USER_CANCELLED,
    "ladder exhausted for subject": AlertEvent.SUBJECT_LADDER_EXHAUSTED,
    "responder claims": AlertEvent.RESPONDER_CLAIMED,
    "ladder exhausted": AlertEvent.CIRCLE_LADDER_EXHAUSTED,
    "responder verifies contact": AlertEvent.RESPONDER_VERIFIED,
    "responder reports unable": AlertEvent.RESPONDER_UNABLE,
    "lease expires": AlertEvent.LEASE_EXPIRED,
}

ANY_NON_TERMINAL = "any non-terminal"


def _clean(cell: str) -> str:
    """Strip the markdown a table cell carries: backticks and bold markers."""
    return cell.replace("`", "").replace("**", "").strip()


def _documented_transitions() -> set[tuple[AlertState, AlertEvent, AlertState]]:
    text = DOC.read_text()

    section = re.search(r"^## 2\. Transition table\s*(.*?)^---", text, re.MULTILINE | re.DOTALL)
    assert section, "docs/PRODUCT-STATES.md has no '## 2. Transition table' section"

    rows: set[tuple[AlertState, AlertEvent, AlertState]] = set()
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [_clean(c) for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() == "from":
            continue

        from_cell, event_cell, to_cell = cells[0], cells[1], cells[2]

        event = EVENT_PROSE.get(event_cell.lower())
        assert event is not None, (
            f"table row uses event prose {event_cell!r} that EVENT_PROSE does not map. "
            f"Add it, or the row is silently untested."
        )
        target = AlertState(to_cell)

        if from_cell.lower() == ANY_NON_TERMINAL:
            sources = list(NON_TERMINAL_STATES)
        else:
            sources = [AlertState(_clean(part)) for part in from_cell.split("/")]

        for source in sources:
            rows.add((source, event, target))

    assert rows, "parsed no transitions -- the table format changed and this test went blind"
    return rows


DOCUMENTED = _documented_transitions()


def test_the_table_was_actually_parsed() -> None:
    """Guards the guard: a regex that silently matches nothing proves nothing."""
    assert len(DOCUMENTED) >= 14, f"only parsed {len(DOCUMENTED)} transitions, expected 14+"


@pytest.mark.parametrize(
    ("source", "event", "target"),
    sorted(DOCUMENTED),
    ids=lambda v: str(v),
)
def test_every_documented_transition_is_implemented(
    source: AlertState, event: AlertEvent, target: AlertState
) -> None:
    assert (source, event) in TRANSITIONS, (
        f"docs/PRODUCT-STATES.md documents {source} + {event} -> {target}, "
        f"but the code has no such transition"
    )
    assert TRANSITIONS[(source, event)] == target, (
        f"docs say {source} + {event} -> {target}, code says -> {TRANSITIONS[(source, event)]}"
    )


def test_every_implemented_transition_is_documented() -> None:
    """The reverse direction: no undocumented behaviour may exist in safety state."""
    implemented = {(s, e, t) for (s, e), t in TRANSITIONS.items()}
    undocumented = implemented - DOCUMENTED
    assert not undocumented, (
        f"these transitions exist in code but not in docs/PRODUCT-STATES.md: "
        f"{sorted(undocumented)}. Document them deliberately, or remove them."
    )


def test_terminal_states_have_no_outbound_transitions() -> None:
    """Invariant 3, checked against the table rather than trusted."""
    terminal = set(AlertState) - NON_TERMINAL_STATES
    for state, event in TRANSITIONS:
        assert state not in terminal, f"{state} is terminal but has an outbound {event}"


def test_subject_confirmation_wins_from_every_non_terminal_state() -> None:
    """The subject saying they are okay must never be blocked by where escalation got to."""
    for state in NON_TERMINAL_STATES:
        assert TRANSITIONS.get((state, AlertEvent.SUBJECT_CONFIRMED)) == AlertState.RESOLVED, (
            f"subject confirmation does not resolve from {state}"
        )
