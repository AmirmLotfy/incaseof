"""POST /v1/plans/compile.

Natural language in, a plan to look at out. **Creates nothing and activates nothing** — the
person sees what would happen and confirms it separately, which is the step the whole safety
model rests on (docs/AI-SAFETY.md section 5).

Degrades honestly. When the model is unreachable this returns 503 with the four plan
templates, so somebody can still build a plan by choosing one. It never returns a guess.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from services.agent.agent import DEFAULT_MODEL, build_agent, compile_plan_from_utterance
from services.agent.gateway import Gateway
from services.domain.errors import PlanValidationError
from services.domain.ids import CircleId, PersonId, PlanId, uuid_factory
from services.handlers import bootstrap

log = logging.getLogger(__name__)

TEMPLATES = [
    {"type": "ROUTINE", "label": "Routine", "example": "Check on me every evening."},
    {"type": "JOURNEY", "label": "Journey", "example": "I should arrive before midnight."},
    {"type": "SOLO", "label": "Solo", "example": "I'm hiking until six."},
    {"type": "RECOVERY", "label": "Recovery", "example": "I'm alone tonight. Check periodically."},
]


def compile_for(
    ctx: bootstrap.Context,
    *,
    utterance: str,
    subject_person_id: PersonId,
    circle_id: CircleId | None,
    timezone: str,
    agent: Any = None,
) -> dict[str, Any]:
    """Compile, or explain why not. Never raises past this boundary."""
    gateway = Gateway(
        ctx=ctx,
        subject_person_id=subject_person_id,
        circle_id=circle_id,
        model_id=DEFAULT_MODEL,
    )
    roles = gateway.circle_roles().data.get("roles", [])

    try:
        built = agent if agent is not None else build_agent(gateway)
    except RuntimeError as error:
        # No key configured. Say so plainly rather than pretending the feature exists.
        log.warning("agent unavailable: %s", error)
        return _unavailable("The assistant isn't available. Choose a template instead.")

    try:
        preview = compile_plan_from_utterance(
            built,
            utterance,
            plan_id=PlanId(uuid_factory()),
            timezone=timezone,
            circle_roles=roles,
        )
    except PlanValidationError as error:
        # The description could not be turned into something safe. Failing here is correct:
        # the alternative is a plan whose ladder is wrong, discovered on the night it counts.
        return {
            "status": 422,
            "body": {
                "title": "That description couldn't be turned into a plan",
                "detail": str(error),
                "templates": TEMPLATES,
            },
        }
    except Exception as error:
        log.warning("compilation failed: %s", type(error).__name__)
        return _unavailable("Couldn't build your plan just now. Choose a template instead.")

    version = preview.result.version
    return {
        "status": 200,
        "body": {
            # Said out loud on the wire. Nothing here is live.
            "active": False,
            "requiresConfirmation": True,
            "plan": {
                "label": version.label,
                "type": version.plan_type.value,
                "timezone": version.timezone,
                "graceSeconds": version.grace_seconds,
                "steps": [
                    {
                        "sequence": step.sequence,
                        "offsetSeconds": step.offset_seconds,
                        "action": step.action.value,
                        "targetRole": step.target_role.value if step.target_role else None,
                    }
                    for step in version.steps
                ],
                "contextPolicy": {
                    signal.value: level.value
                    for signal, level in version.context_policy.levels.items()
                },
            },
            "warnings": list(preview.warnings),
        },
    }


def _unavailable(message: str) -> dict[str, Any]:
    """503 with the templates.

    Plan creation must not depend on the model being reachable — the four templates in
    docs/PRD.md section 7 exist precisely so it does not.
    """
    return {
        "status": 503,
        "body": {"title": message, "templates": TEMPLATES},
    }


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    ctx = bootstrap.build()
    body = json.loads(event.get("body") or "{}")

    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    subject = claims.get("sub")
    if not subject:
        return {
            "statusCode": 403,
            "headers": {"content-type": "application/problem+json"},
            "body": json.dumps({"title": "Not permitted", "reason_code": "NOT_AUTHORIZED"}),
        }

    result = compile_for(
        ctx,
        utterance=body.get("utterance", ""),
        subject_person_id=PersonId(subject),
        circle_id=CircleId(body["circleId"]) if body.get("circleId") else None,
        timezone=body.get("timezone", "UTC"),
    )
    return {
        "statusCode": result["status"],
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(result["body"], default=str),
    }
