"""What a responder can do.

Reached through a signed single-Alert link, by somebody with no account.

A valid signature is necessary and never sufficient. Every action re-checks, at the moment
it happens: is the Alert still open, is this person still an accepted member, is their
consent still active, and does the current escalation step still involve them. A token
minted twenty minutes ago says what was true then; consent withdrawn since must stop
contact immediately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.domain.alert import Alert
from services.domain.authorization import evaluate_responder_action
from services.domain.circle import CircleMember
from services.domain.errors import NotAuthorized
from services.domain.ids import AlertId, CircleId, PlanId
from services.domain.responder_token import (
    ResponderClaims,
    ResponderPermission,
    TokenError,
    verify,
)
from services.handlers import bootstrap


@dataclass(frozen=True, slots=True)
class IncidentView:
    """What a responder is shown. Deliberately little.

    Enough to decide whether to act: who, which check, when it was expected, what has
    already been tried. Nothing about the person's other plans, their Circle, or their
    history.
    """

    alert_id: AlertId
    subject_name: str
    plan_label: str
    expected_at: datetime
    state: str
    tried: list[dict[str, str]]
    owner_name: str | None
    lease_expires_at: datetime | None
    can_claim: bool
    can_resolve: bool


def _authorise(
    ctx: bootstrap.Context, token: str, permission: ResponderPermission
) -> tuple[Alert, CircleMember, ResponderClaims]:
    """Validate the link, then re-check everything it asserts against current state."""
    now = ctx.now()

    try:
        claims = verify(token, key=ctx.signing_key, now=now)
    except TokenError as error:
        ctx.audit.append(
            alert_id=AlertId("unknown"),
            actor_type="RESPONDER",
            actor_id="anonymous",
            event_type="TOKEN_REJECTED",
            at=now,
            metadata={"reason": error.reason},
        )
        raise NotAuthorized("invalid link") from error

    if not claims.allows(permission):
        raise NotAuthorized(f"link does not grant {permission}")

    alert = ctx.alerts.get(claims.alert_id)
    if alert is None:
        raise NotAuthorized("no such alert")

    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None
    if plan is None or circle is None:
        raise NotAuthorized("alert is not reachable")

    decision = evaluate_responder_action(
        alert=alert, circle=circle, responder_id=claims.responder_id, now=now
    )
    if not decision.allowed or decision.member is None:
        ctx.audit.append(
            alert_id=alert.alert_id,
            actor_type="POLICY",
            actor_id="authorization",
            event_type="RESPONDER_DENIED",
            at=now,
            metadata={"reason": str(decision.reason)},
        )
        raise NotAuthorized(str(decision.reason))

    # Consent is checked here too, not only when the message was sent. Somebody who
    # withdrew consent after the SMS went out must not be able to act on it.
    consent = ctx.circles.consents_for(PlanId(plan.plan_id)).get(claims.responder_id)
    if consent is None or not consent.is_active(now):
        raise NotAuthorized("consent is not active")

    return alert, decision.member, claims


def view(ctx: bootstrap.Context, token: str) -> IncidentView:
    """The Incident Room."""
    alert, member, _ = _authorise(ctx, token, ResponderPermission.VIEW_ALERT)
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None

    tried = [
        {"at": str(event.get("at")), "event": str(event.get("eventType"))}
        for event in ctx.audit.for_alert(alert.alert_id)
        if str(event.get("eventType"))
        in {"ACTION_QUEUED", "ACTION_ACCEPTED", "ACTION_DELIVERED", "CHANNEL_UNAVAILABLE"}
    ]

    return IncidentView(
        alert_id=alert.alert_id,
        subject_name=circle.owner_display_name
        if circle and circle.owner_display_name
        else "Someone",
        plan_label=alert.version.label or "Check-in",
        expected_at=alert.opened_at,
        state=str(alert.state),
        tried=tried,
        owner_name=_owner_name(ctx, alert),
        lease_expires_at=alert.lease.expires_at if alert.lease else None,
        can_claim=alert.lease is None,
        can_resolve=alert.lease is not None and alert.lease.owner_person_id == member.person_id,
    )


def _owner_name(ctx: bootstrap.Context, alert: Alert) -> str | None:
    if alert.lease is None:
        return None
    plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
    circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None
    holder = circle.member(alert.lease.owner_person_id) if circle else None
    return holder.display_name if holder else None


def claim(ctx: bootstrap.Context, token: str) -> Alert:
    """ "I'm checking."

    Pauses backup escalation for the lease. It does **not** mean the subject is safe, and
    the API says so explicitly in its response.
    """
    alert, member, _ = _authorise(ctx, token, ResponderPermission.CLAIM)
    now = ctx.now()

    claimed = alert.claim(now, member.person_id)
    ctx.alerts.save(claimed)
    ctx.audit.append(
        alert_id=alert.alert_id,
        actor_type="RESPONDER",
        actor_id=member.person_id,
        event_type="ALERT_CLAIMED",
        at=now,
    )
    return claimed


def extend(ctx: bootstrap.Context, token: str) -> Alert:
    """Yes, still checking."""
    alert, member, _ = _authorise(ctx, token, ResponderPermission.EXTEND)
    now = ctx.now()

    if alert.lease is None or alert.lease.owner_person_id != member.person_id:
        raise NotAuthorized("only the responder holding this alert may extend it")

    extended = alert.extend_lease(now)
    ctx.alerts.save(extended)
    ctx.audit.append(
        alert_id=alert.alert_id,
        actor_type="RESPONDER",
        actor_id=member.person_id,
        event_type="LEASE_EXTENDED",
        at=now,
    )
    return extended


def report_unable(ctx: bootstrap.Context, token: str) -> Alert:
    """ "I couldn't reach them." Escalation resumes immediately."""
    alert, member, _ = _authorise(ctx, token, ResponderPermission.REPORT_UNABLE)
    now = ctx.now()

    if alert.lease is None or alert.lease.owner_person_id != member.person_id:
        raise NotAuthorized("only the responder holding this alert may release it")

    released = alert.responder_unable(now)
    ctx.alerts.save(released)
    ctx.audit.append(
        alert_id=alert.alert_id,
        actor_type="RESPONDER",
        actor_id=member.person_id,
        event_type="RESPONDER_UNABLE",
        at=now,
    )
    return released


def resolve(ctx: bootstrap.Context, token: str) -> Alert:
    """ "I reached them, they're okay."

    The only responder path that closes an Alert, and only for the person holding the lease.
    """
    alert, member, _ = _authorise(ctx, token, ResponderPermission.RESOLVE)
    now = ctx.now()

    resolved = alert.resolve_by_responder(now, member.person_id)
    ctx.alerts.save(resolved)
    ctx.audit.append(
        alert_id=alert.alert_id,
        actor_type="RESPONDER",
        actor_id=member.person_id,
        event_type="RESPONDER_VERIFIED",
        at=now,
    )
    return resolved
