"""Creating and activating a Plan.

The first step of the vertical slice, and the one place where a description of what should
happen becomes something that will actually wake a system up at 21:00.

Kept as plain functions over a Context rather than inside the HTTP handler, so the whole
sequence can be driven directly from a test without an API Gateway event.

Compiling and activating are separate on purpose. Compiling produces a PlanVersion for a
human to look at; activating is what schedules a real timer. Collapsing them would remove
the confirmation step the safety model depends on -- see docs/AI-SAFETY.md section 5.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from services.domain.clock import REAL_TIME, TimeScale
from services.domain.compiler import CompilationResult, compile_plan
from services.domain.ids import (
    CircleId,
    IdFactory,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
    uuid_factory,
)
from services.domain.moment import ExpectedMoment, moment_for, next_due_at
from services.domain.plan import Plan, PlanVersion, TriggerKind
from services.handlers import bootstrap


@dataclass(frozen=True, slots=True)
class Activation:
    """What activating produced: the live version and the first Moment it expects."""

    plan: Plan
    version: PlanVersion
    moment: ExpectedMoment
    schedule_name: str | None


def compile_only(
    document: dict[str, Any],
    *,
    plan_id: PlanId,
    version_number: int,
    new_id: IdFactory = uuid_factory,
) -> CompilationResult:
    """Validate and preview. Creates nothing, schedules nothing, activates nothing."""
    return compile_plan(document, plan_id=plan_id, version_number=version_number, new_id=new_id)


def create_plan(
    ctx: bootstrap.Context,
    document: dict[str, Any],
    *,
    subject_person_id: PersonId,
    circle_id: CircleId,
    new_id: IdFactory = uuid_factory,
) -> tuple[Plan, CompilationResult]:
    """Compile a document into a stored, inactive Plan.

    Inactive on purpose. A plan that started protecting somebody the moment it was
    described would be a plan nobody confirmed.
    """
    plan_id = PlanId(new_id())
    result = compile_only(document, plan_id=plan_id, version_number=1, new_id=new_id)

    plan = Plan(
        plan_id=plan_id,
        subject_person_id=subject_person_id,
        circle_id=circle_id,
        plan_type=result.version.plan_type,
        active_version_id=None,
    )
    ctx.plans.save_plan(plan)
    ctx.plans.save_version(result.version)
    return plan, result


def activate_plan(
    ctx: bootstrap.Context,
    plan_id: PlanId,
    version_id: PlanVersionId,
    *,
    now: datetime,
    new_id: IdFactory = uuid_factory,
) -> Activation:
    """Make a Plan live: pin the version, create the first Moment, and set its timer.

    The order matters. The Moment is written **before** the schedule is created, so a
    failure between the two leaves a Moment with no timer -- which the reconciliation
    sweeper finds -- rather than a timer pointing at a Moment that does not exist, which
    would fire into nothing and be invisible.
    """
    version = ctx.plans.get_version(version_id)
    if version is None:
        raise ValueError(f"no such version {version_id}")

    owner_plan = ctx.plans.get_plan(plan_id)
    if owner_plan is None or version.plan_id != plan_id:
        raise ValueError("version does not belong to the requested plan")
    circle = ctx.circles.get(owner_plan.circle_id)
    bindings = {
        role.value: str(member.person_id)
        for role in version.responder_roles
        if circle is not None and (member := circle.member_for_role(role)) is not None
    }
    plan = ctx.plans.activate(plan_id, version_id, now, bindings)
    version = ctx.plans.get_version(version_id) or version
    moment = _next_moment(version, now=now, new_id=new_id, scale=ctx.scale)
    ctx.moments.save(moment, subject_person_id=plan.subject_person_id)

    schedule_name = None
    if ctx.scheduler is not None:
        schedule_name = ctx.scheduler.schedule(moment)

    return Activation(
        plan=plan,
        version=replace(version, activated_at=now),
        moment=moment,
        schedule_name=schedule_name,
    )


def schedule_following_moment(
    ctx: bootstrap.Context,
    version: PlanVersion,
    *,
    after: datetime,
    new_id: IdFactory = uuid_factory,
) -> ExpectedMoment | None:
    """Queue the next occurrence of a recurring Plan.

    Called once a Moment resolves. A one-time Plan simply has no next Moment, which is not
    an error -- it is the plan finishing.
    """
    if version.trigger.kind is not TriggerKind.RECURRING:
        return None
    plan = ctx.plans.get_plan(version.plan_id)
    if plan is None or not plan.is_active or plan.active_version_id != version.version_id:
        return None
    if next_due_at(version.trigger, version.timezone, after) is None:
        return None
    moment = _next_moment(version, now=after, new_id=new_id, scale=ctx.scale)
    ctx.moments.save(moment, subject_person_id=plan.subject_person_id)
    if ctx.scheduler is not None:
        ctx.scheduler.schedule(moment)
    return moment


def _next_moment(
    version: PlanVersion,
    *,
    now: datetime,
    new_id: IdFactory,
    scale: TimeScale = REAL_TIME,
) -> ExpectedMoment:
    due_at = next_due_at(version.trigger, version.timezone, now)
    if due_at is None:
        raise ValueError(
            f"version {version.version_id} expects nothing after {now.isoformat()}; "
            f"a one-time plan whose moment has passed cannot be activated"
        )

    # Grace compresses along with the ladder. It is part of the schedule, not part of the
    # logic, and leaving it at full length would make a demo sit for ten real minutes
    # before anything happened — which is precisely the pressure that leads somebody to
    # build a separate demo path.
    #
    # The due time itself is never scaled: it comes from the plan's trigger and is a real
    # instant. A demo brings the moment closer by creating a plan due soon, not by
    # distorting when it falls.
    return moment_for(
        moment_id=MomentId(new_id()),
        version_id=version.version_id,
        due_at=due_at,
        grace_seconds=int(scale.apply(version.grace_seconds)),
        time_scale=scale.factor,
    )
