"""Compiling a CompiledPlan document into a PlanVersion.

This is the boundary between language and action. Everything the agent produces passes
through here before anything real can happen, so the validation is layered rather than
single-shot -- each layer catches a different class of mistake, and a document must clear
all of them:

1. **Schema** -- shape, types, enums, closed objects. Rejects anything the contract does
   not describe, including a smuggled contact endpoint.
2. **Semantic** -- rules JSON Schema cannot express: ordered offsets, a reachable
   termination, a resolvable timezone.
3. **Safety** -- rules about what a plan may *do*: the subject must always be able to
   close their own Alert, and somebody must actually be contacted.

Only then does a PlanVersion exist. Activation is still a separate, explicit human step --
see docs/AI-SAFETY.md section 5. Compiling is not activating.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import PlanValidationError
from .ids import IdFactory, PlanId, PlanVersionId, StepId, uuid_factory
from .moment import resolve_zone
from .plan import (
    DEFAULT_LEASE_SECONDS,
    ActionType,
    ContextPolicy,
    ContextSignal,
    EscalationStep,
    PlanType,
    PlanVersion,
    ReleaseLevel,
    ResponderRole,
    StopCondition,
    Trigger,
    TriggerKind,
)

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "domain-schemas"
    / "compiled-plan.schema.json"
)


@dataclass(frozen=True, slots=True)
class CompilationResult:
    """A compiled version plus the human-readable preview that must be confirmed."""

    version: PlanVersion
    warnings: tuple[str, ...] = ()


def _load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text())
    return schema


_VALIDATOR = Draft202012Validator(_load_schema())


def validate_schema(document: dict[str, Any]) -> None:
    """Layer 1. Reports every violation at once rather than only the first.

    A caller fixing one problem per round trip is a caller who gives up and disables the
    check.
    """
    errors = sorted(_VALIDATOR.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise PlanValidationError(f"schema: {detail}")


def _trigger_from(document: dict[str, Any]) -> Trigger:
    raw = document["trigger"]
    kind = TriggerKind(raw["kind"])
    due_at = datetime.fromisoformat(raw["dueAt"]) if raw.get("dueAt") else None
    return Trigger(
        kind=kind,
        due_at=due_at,
        time_of_day=raw.get("timeOfDay"),
        days_of_week=tuple(raw.get("daysOfWeek", ())),
        interval_seconds=raw.get("intervalSeconds"),
        offset_seconds=raw.get("offsetSeconds"),
    )


def _context_policy_from(document: dict[str, Any]) -> ContextPolicy:
    raw = document.get("contextPolicy", {})
    levels: dict[ContextSignal, ReleaseLevel] = {}
    for signal in ContextSignal:
        if signal.value in raw:
            levels[signal] = ReleaseLevel(raw[signal.value])
    return ContextPolicy(levels)


def _steps_from(document: dict[str, Any], new_id: IdFactory) -> tuple[EscalationStep, ...]:
    steps = []
    for raw in document["steps"]:
        role = ResponderRole(raw["targetRole"]) if raw.get("targetRole") else None
        steps.append(
            EscalationStep(
                step_id=StepId(new_id()),
                sequence=raw["sequence"],
                offset_seconds=raw["offsetSeconds"],
                action=ActionType(raw["action"]),
                target_role=role,
            )
        )
    return tuple(steps)


def validate_semantics(version: PlanVersion) -> tuple[str, ...]:
    """Layer 2. Rules the schema cannot express, plus non-blocking warnings."""
    resolve_zone(version.timezone)  # raises PlanValidationError on an unknown zone

    warnings: list[str] = []

    if not version.responder_steps:
        warnings.append(
            "this plan never contacts anyone else: if the subject does not respond, "
            "escalation simply ends"
        )

    unavailable = {
        step.sequence for step in version.steps if not step.action.channel.is_available_in_p0
    }
    if unavailable:
        warnings.append(
            f"steps {sorted(unavailable)} use voice, which is not yet connected; they will "
            f"report CHANNEL_UNAVAILABLE until Amazon Connect lands"
        )

    if version.grace_seconds == 0 and version.steps[0].offset_seconds == 0:
        warnings.append("the first contact fires the instant the moment is due, with no grace")

    return tuple(warnings)


def validate_safety(version: PlanVersion) -> None:
    """Layer 3. What a plan is permitted to *do*."""
    if StopCondition.SUBJECT_EXPLICIT_CONFIRMATION not in version.stop_conditions:
        raise PlanValidationError(
            "safety: the subject must always be able to close their own Alert; "
            "SUBJECT_EXPLICIT_CONFIRMATION is required"
        )

    if not version.subject_steps:
        raise PlanValidationError(
            "safety: escalation must start with the subject. A plan that contacts the "
            "Circle without first asking the person defeats the point of the product."
        )

    first = version.steps[0]
    if not first.action.is_subject_directed:
        raise PlanValidationError(
            f"safety: step 1 is {first.action}; the first contact must go to the subject"
        )


def compile_plan(
    document: dict[str, Any],
    *,
    plan_id: PlanId,
    version_number: int,
    new_id: IdFactory = uuid_factory,
) -> CompilationResult:
    """Run every layer and produce an immutable PlanVersion.

    Never activates. The caller shows the result to a human and takes an explicit
    confirmation before anything becomes live.
    """
    validate_schema(document)

    version = PlanVersion(
        version_id=PlanVersionId(new_id()),
        plan_id=plan_id,
        version_number=version_number,
        plan_type=PlanType(document["type"]),
        timezone=document["timezone"],
        trigger=_trigger_from(document),
        grace_seconds=document["grace"]["seconds"],
        steps=_steps_from(document, new_id),
        stop_conditions=frozenset(StopCondition(value) for value in document["stopConditions"]),
        context_policy=_context_policy_from(document),
        lease_seconds=document.get("leaseSeconds", DEFAULT_LEASE_SECONDS),
        label=document.get("label"),
    )

    warnings = validate_semantics(version)
    validate_safety(version)
    return CompilationResult(version=version, warnings=warnings)
