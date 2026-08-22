"""Adapter semantics.

The in-memory adapters exist so invariants can be proven without the cloud. That only
works if they behave like the real thing, so these tests target the two conditional
operations that Phase 2 will implement as DynamoDB conditional writes.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from services.adapters.memory import (
    InMemoryActionLog,
    InMemoryAlertRepository,
    InMemoryPlanRepository,
)
from services.domain.idempotency import key_for
from services.domain.ids import AlertId, MomentId, PlanId, StepId
from services.domain.plan import Plan

from .conftest import DUE_AT, make_alert, make_version

# -- Invariant 1: one Moment produces at most one Alert -----------------------


def test_a_duplicate_scheduler_delivery_does_not_open_a_second_alert() -> None:
    repo = InMemoryAlertRepository()
    first = repo.open_for_moment(make_alert())

    duplicate = replace(make_alert(), alert_id=AlertId("alert-2"))
    second = repo.open_for_moment(duplicate)

    assert second.alert_id == first.alert_id
    assert len(repo.alerts) == 1


def test_a_duplicate_delivery_returns_the_live_alert_rather_than_raising() -> None:
    """A replayed event is normal operation. The caller carries on with what exists."""
    repo = InMemoryAlertRepository()
    opened = repo.open_for_moment(make_alert())
    progressed = opened.mark_due(DUE_AT).enter_grace(DUE_AT)
    repo.save(progressed)

    again = repo.open_for_moment(replace(make_alert(), alert_id=AlertId("alert-9")))
    assert again.state == progressed.state, "should return current state, not a fresh Alert"


def test_different_moments_get_different_alerts() -> None:
    repo = InMemoryAlertRepository()
    repo.open_for_moment(make_alert())
    other = replace(make_alert(), alert_id=AlertId("alert-2"), moment_id=MomentId("moment-2"))
    repo.open_for_moment(other)

    assert len(repo.alerts) == 2


# -- Invariant 5: an action dispatches at most once per attempt ---------------


def test_only_the_first_caller_wins_an_idempotency_key() -> None:
    log = InMemoryActionLog()
    key = key_for(AlertId("alert-1"), StepId("step-4"), attempt_number=1)

    assert log.claim_key(key) is True, "first caller should dispatch"
    assert log.claim_key(key) is False, "replay must not dispatch again"
    assert log.was_dispatched(key)


def test_a_deliberate_retry_is_a_distinct_action() -> None:
    """Attempt number is in the key so a real retry is allowed, a replay is not."""
    log = InMemoryActionLog()
    alert, step = AlertId("alert-1"), StepId("step-4")

    assert log.claim_key(key_for(alert, step, 1)) is True
    assert log.claim_key(key_for(alert, step, 2)) is True
    assert log.claim_key(key_for(alert, step, 2)) is False


def test_keys_do_not_collide_across_alerts_or_steps() -> None:
    log = InMemoryActionLog()
    assert log.claim_key(key_for(AlertId("a-1"), StepId("s-1"), 1)) is True
    assert log.claim_key(key_for(AlertId("a-2"), StepId("s-1"), 1)) is True
    assert log.claim_key(key_for(AlertId("a-1"), StepId("s-2"), 1)) is True


def test_attempt_numbers_start_at_one() -> None:
    with pytest.raises(ValueError, match="attempt numbers start at 1"):
        key_for(AlertId("a-1"), StepId("s-1"), 0)


# -- Plan versions are immutable ----------------------------------------------


def test_a_version_cannot_be_overwritten() -> None:
    repo = InMemoryPlanRepository()
    version = make_version()
    repo.save_version(version)

    with pytest.raises(ValueError, match="immutable"):
        repo.save_version(make_version(lease_seconds=60))


def test_activating_records_when_without_disturbing_a_live_alert() -> None:
    repo = InMemoryPlanRepository()
    version = make_version()
    repo.save_version(version)
    repo.plans[PlanId("plan-1")] = Plan(
        plan_id=PlanId("plan-1"),
        subject_person_id="person-mona",
        circle_id="circle-1",
        plan_type=version.plan_type,
    )

    activated = repo.activate(PlanId("plan-1"), version.version_id, DUE_AT)
    assert activated.active_version_id == version.version_id
    assert activated.is_active
    stored = repo.get_version(version.version_id)
    assert stored is not None and stored.activated_at == DUE_AT
