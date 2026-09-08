"""The agent.

One agent, with a narrow tool surface. Not a planning agent plus a safety agent plus a
supervisor agent — that shape multiplies failure modes without improving any outcome, and
docs/AI-SAFETY.md section 2 says so plainly.

Two capabilities: understanding what somebody said, and turning a description into a plan.
Both go through the same gate as everything else, and both degrade to something usable when
the model is unreachable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from botocore.config import Config
from pydantic import BaseModel, Field

from services.agent.compilation import (
    COMPILER_INSTRUCTIONS,
    CompiledPlanDraft,
    Preview,
    compile_from_draft,
    guard_utterance,
)
from services.agent.config import MAX_OUTPUT_TOKENS, MODEL_ID, MODEL_TEMPERATURE
from services.agent.prompts import SYSTEM_PROMPT
from services.domain.agent_decision import hash_input
from services.domain.errors import PlanValidationError
from services.domain.ids import IdFactory, PlanId, uuid_factory

log = logging.getLogger(__name__)

DEFAULT_MODEL = MODEL_ID

if TYPE_CHECKING:
    from services.agent.gateway import Gateway


class Intent(StrEnum):
    """What somebody meant. Mirrors evals/datasets/intent.jsonl."""

    SAFE_CONFIRMED = "SAFE_CONFIRMED"
    AMBIGUOUS = "AMBIGUOUS"
    EXTENSION_REQUESTED = "EXTENSION_REQUESTED"
    PLAN_EXCEPTION_REQUESTED = "PLAN_EXCEPTION_REQUESTED"
    CONTACT_REQUESTED = "CONTACT_REQUESTED"
    UNAVAILABLE = "UNAVAILABLE"


class IntentReading(BaseModel):
    """The model's reading of one utterance."""

    intents: list[Any] = Field(
        description="One or more of SAFE_CONFIRMED, AMBIGUOUS, EXTENSION_REQUESTED, "
        "PLAN_EXCEPTION_REQUESTED, CONTACT_REQUESTED"
    )
    unambiguous: bool = Field(
        description="False for any hedge: probably, I think so, I guess, maybe"
    )
    extension_seconds: int | None = None
    role: str | None = Field(default=None, description="PRIMARY, BACKUP or TERTIARY only")


# What the person is offered when the model cannot be reached. Escalation is entirely
# unaffected either way, because the timers live in EventBridge.
FALLBACK_CHOICES = ("I'M OKAY", "NEED SOMEONE", "GIVE ME MORE TIME")


@dataclass(frozen=True, slots=True)
class Reading:
    """A classified utterance, or an honest admission that it was not classified."""

    intents: tuple[Intent, ...]
    unambiguous: bool
    extension_seconds: int | None = None
    role: str | None = None
    degraded: bool = False

    @property
    def choices(self) -> tuple[str, ...]:
        return FALLBACK_CHOICES if self.degraded else ()

    def wants(self, intent: Intent) -> bool:
        return intent in self.intents


DEGRADED = Reading(intents=(Intent.UNAVAILABLE,), unambiguous=False, degraded=True)


def _model(model_id: str = DEFAULT_MODEL) -> Any:
    """Build the model client.

    Amazon Bedrock uses ambient, temporary IAM credentials supplied by Lambda or
    AgentCore. No provider API key exists in the website, APK, runtime configuration or
    source tree.
    """
    from strands.models.bedrock import BedrockModel

    return BedrockModel(
        model_id=os.environ.get("AWS_BEDROCK_MODEL_ID", model_id),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=MODEL_TEMPERATURE,
        streaming=False,
        boto_client_config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
    )


def build_agent(gateway: Gateway, *, model_id: str = DEFAULT_MODEL, model: Any = None) -> Any:
    """Construct the agent for one authenticated subject."""
    from strands import Agent

    from services.agent.tools import build_tools

    return Agent(
        model=model if model is not None else _model(model_id),
        tools=build_tools(gateway),
        system_prompt=SYSTEM_PROMPT,
    )


def build_compile_agent(*, model_id: str = DEFAULT_MODEL, model: Any = None) -> Any:
    """Construct the side-effect-free plan compiler used by AgentCore Runtime.

    Compilation has no tools: the model can only produce typed data. The API facade then
    re-runs the deterministic schema, timezone, contact-role and safety validators before
    showing a preview. Keeping this separate from :func:`build_agent` also makes it
    impossible for a compiler prompt to reach a state-changing tool by accident.
    """
    from strands import Agent

    return Agent(
        model=model if model is not None else _model(model_id),
        tools=[],
        system_prompt=SYSTEM_PROMPT,
    )


# -- understanding ------------------------------------------------------------


def read(agent: Any, utterance: str) -> Reading:
    """Classify what somebody said.

    Any failure degrades to explicit choices rather than to a guess. A safety product that
    resolves an Alert because the classifier was confident-but-wrong is worse than one that
    asks a plain question.
    """
    try:
        text = guard_utterance(utterance)
    except PlanValidationError:
        return DEGRADED

    try:
        reading: IntentReading = agent.structured_output(
            IntentReading,
            f"Classify what this person said. Text: {text!r}",
        )
    # Broad on purpose: an outage, a timeout, a malformed response and a schema mismatch
    # all have the same correct answer — fall back and let the person answer explicitly.
    except Exception as error:
        log.warning("intent classification unavailable: %s", type(error).__name__)
        return DEGRADED

    intents = tuple(
        Intent(value)
        for value in reading.intents
        if isinstance(value, str) and value in Intent.__members__
    )
    if not intents:
        return DEGRADED

    return Reading(
        intents=intents,
        unambiguous=bool(reading.unambiguous),
        extension_seconds=reading.extension_seconds,
        role=reading.role,
    )


# -- compiling ----------------------------------------------------------------


def compile_plan_from_utterance(
    agent: Any,
    utterance: str,
    *,
    plan_id: PlanId,
    timezone: str,
    circle_roles: list[dict[str, str]] | None = None,
    model_id: str = DEFAULT_MODEL,
    new_id: IdFactory = uuid_factory,
) -> Preview:
    """Turn a description into a plan for somebody to look at.

    Raises PlanValidationError when the result cannot be made safe. Failing here is the
    correct outcome: the alternative is activating a plan whose ladder is wrong, and
    nobody would find out until the night it mattered.
    """
    text = guard_utterance(utterance)
    roles = circle_roles or []

    prompt = (
        f"{COMPILER_INSTRUCTIONS}\n"
        f"Timezone: {timezone}\n"
        f"Circle roles available: {roles}\n\n"
        f"The person said: {text!r}"
    )

    draft: CompiledPlanDraft = agent.structured_output(CompiledPlanDraft, prompt)

    # The model's own timezone is ignored. It is given one and must use it; a guessed zone
    # silently moves a safety deadline.
    draft = draft.model_copy(update={"timezone": timezone})

    result = compile_from_draft(draft, plan_id=plan_id, new_id=new_id)
    return Preview(result=result, utterance_hash=hash_input(text), model_id=model_id)
