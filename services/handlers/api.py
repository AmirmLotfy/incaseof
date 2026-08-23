"""HTTP API.

A translation layer: parse the event, call the domain, serialise the result. No rules live
here. A rule that exists only in an HTTP handler is a rule the workflow does not enforce,
and the workflow is what runs when nobody is looking.

Two authentication realms arrive here. ``/v1/*`` carries a Cognito principal. ``/r/*`` and
``/v1/r/*`` carry a signed single-Alert token, because a responder has no account.
"""

from __future__ import annotations

import json
from typing import Any

from services.domain.errors import (
    DomainError,
    LeaseConflict,
    NotAuthorized,
    TerminalAlert,
)
from services.domain.ids import AlertId, MomentId, PersonId, PlanId
from services.domain.resolution import ResolutionSource
from services.handlers import bootstrap, responding

JSON = "application/json"
PROBLEM = "application/problem+json"


def _response(status: int, body: dict[str, Any], content_type: str = JSON) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": content_type, "cache-control": "no-store"},
        "body": json.dumps(body, default=str),
    }


def _problem(status: int, title: str, reason_code: str) -> dict[str, Any]:
    """RFC 9457.

    The reason code is stable and machine-readable; the title is not for parsing.
    Authorization failures say little on purpose: a 403 that explains *why* can confirm
    that somebody else's Alert exists.
    """
    return _response(
        status,
        {"type": "about:blank", "title": title, "status": status, "reason_code": reason_code},
        PROBLEM,
    )


def _caller(event: dict[str, Any]) -> PersonId:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    subject = claims.get("sub")
    if not subject:
        raise NotAuthorized("no authenticated principal on this request")
    return PersonId(subject)


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    try:
        return _dispatch(event)
    except NotAuthorized:
        return _problem(403, "Not permitted", "NOT_AUTHORIZED")
    except TerminalAlert:
        return _problem(409, "This is already closed", "ALERT_CLOSED")
    except LeaseConflict:
        return _problem(409, "Someone else is already checking", "LEASE_HELD")
    except DomainError as error:
        return _problem(422, str(error), "INVALID_REQUEST")


def _dispatch(event: dict[str, Any]) -> dict[str, Any]:
    ctx = bootstrap.build()
    route = event.get("routeKey", "")
    params = event.get("pathParameters") or {}

    # -- responder, by signed token ---------------------------------------
    token = params.get("signedToken")
    if token:
        return _responder_route(ctx, route, token)

    # -- subject, by Cognito principal ------------------------------------
    if route == "GET /v1/moments/next":
        return _next_moment(ctx, _caller(event))
    if route == "POST /v1/moments/{momentId}/confirm":
        return _confirm(ctx, event, MomentId(params["momentId"]))
    if route == "POST /v1/moments/{momentId}/extend":
        return _extend(ctx, event, MomentId(params["momentId"]))
    if route == "GET /v1/plans":
        return _plans(ctx, _caller(event))
    if route == "GET /v1/plans/{planId}":
        return _plan(ctx, PlanId(params["planId"]))
    if route == "GET /v1/circle":
        return _circle(ctx, _caller(event))
    if route == "POST /v1/alerts/{alertId}/claim":
        return _claim(ctx, event, AlertId(params["alertId"]))
    if route == "POST /v1/alerts/{alertId}/resolve":
        return _resolve(ctx, event, AlertId(params["alertId"]))
    if route == "GET /v1/alerts/{alertId}/timeline":
        return _timeline(ctx, AlertId(params["alertId"]))

    return _problem(404, "No such route", "NOT_FOUND")


# -- responder ----------------------------------------------------------------


def _responder_route(ctx: bootstrap.Context, route: str, token: str) -> dict[str, Any]:
    if route == "GET /r/{signedToken}":
        view = responding.view(ctx, token)
        return _response(
            200,
            {
                "alertId": view.alert_id,
                "subjectName": view.subject_name,
                "planLabel": view.plan_label,
                "expectedAt": view.expected_at.isoformat(),
                "tried": view.tried,
                "ownerName": view.owner_name,
                "leaseExpiresAt": view.lease_expires_at.isoformat()
                if view.lease_expires_at
                else None,
                "canClaim": view.can_claim,
                "canResolve": view.can_resolve,
            },
        )

    if route == "POST /v1/r/{signedToken}/claim":
        alert = responding.claim(ctx, token)
        lease = alert.lease
        return _response(
            200,
            {
                "alertId": alert.alert_id,
                "state": alert.state.value,
                "leaseExpiresAt": lease.expires_at.isoformat() if lease else None,
                # Said out loud on the wire, because the whole product turns on it.
                "resolved": False,
            },
        )

    if route == "POST /v1/r/{signedToken}/extend":
        alert = responding.extend(ctx, token)
        lease = alert.lease
        return _response(
            200,
            {
                "alertId": alert.alert_id,
                "leaseExpiresAt": lease.expires_at.isoformat() if lease else None,
            },
        )

    if route == "POST /v1/r/{signedToken}/unable":
        alert = responding.report_unable(ctx, token)
        return _response(200, {"alertId": alert.alert_id, "state": alert.state.value})

    if route == "POST /v1/r/{signedToken}/resolve":
        alert = responding.resolve(ctx, token)
        return _response(200, {"alertId": alert.alert_id, "state": alert.state.value})

    return _problem(404, "No such route", "NOT_FOUND")


# -- subject ------------------------------------------------------------------


def _next_moment(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    """The next thing expected of this person.

    404 when there is nothing outstanding, which is the normal, good state — the client
    reads it as "all clear" rather than as a failure.
    """
    pending = ctx.moments.due_before(ctx.now())
    if not pending:
        return _problem(404, "Nothing expected right now", "NO_PENDING_MOMENT")

    moment = pending[0]
    alert = ctx.alerts.alert_for_moment(moment.moment_id)
    version = ctx.plans.get_version(moment.version_id)
    return _response(
        200,
        {
            "momentId": moment.moment_id,
            "planLabel": (version.label if version else None) or "Check-in",
            "dueAt": moment.due_at.isoformat(),
            "graceUntil": moment.grace_until.isoformat(),
            "alertState": alert.state.value if alert else None,
            "alertId": alert.alert_id if alert else None,
        },
    )


def _confirm(ctx: bootstrap.Context, event: dict[str, Any], moment_id: MomentId) -> dict[str, Any]:
    """ "I'm okay." Always wins, from any non-terminal state."""
    person = _caller(event)
    alert = ctx.alerts.alert_for_moment(moment_id)
    if alert is None:
        return _problem(404, "No open alert for that moment", "NOT_FOUND")

    now = ctx.now()
    source = (
        ResolutionSource.NOTIFICATION_ACTION
        if (event.get("headers") or {}).get("x-ico-source") == "notification"
        else ResolutionSource.APP
    )
    resolved = alert.confirm_subject(now, person, source=source)
    ctx.alerts.save(resolved)
    ctx.audit.append(
        alert_id=resolved.alert_id,
        actor_type="SUBJECT",
        actor_id=person,
        event_type="SUBJECT_CONFIRMED",
        at=now,
    )
    return _response(200, {"alertId": resolved.alert_id, "state": resolved.state.value})


def _extend(ctx: bootstrap.Context, event: dict[str, Any], moment_id: MomentId) -> dict[str, Any]:
    """ "Give me another thirty minutes." Moves this Moment only, never the plan."""
    _caller(event)
    moment = ctx.moments.get(moment_id)
    if moment is None:
        return _problem(404, "No such moment", "NOT_FOUND")

    body = json.loads(event.get("body") or "{}")
    seconds = int(body.get("seconds", 1800))

    from dataclasses import replace

    extended = replace(
        moment,
        due_at=moment.due_at.fromtimestamp(
            moment.due_at.timestamp() + seconds, tz=moment.due_at.tzinfo
        ),
        grace_until=moment.grace_until.fromtimestamp(
            moment.grace_until.timestamp() + seconds, tz=moment.grace_until.tzinfo
        ),
    )
    ctx.moments.save(extended)
    if ctx.scheduler is not None:
        ctx.scheduler.schedule(extended)

    return _response(
        200,
        {
            "momentId": extended.moment_id,
            "planLabel": "",
            "dueAt": extended.due_at.isoformat(),
            "graceUntil": extended.grace_until.isoformat(),
        },
    )


def _plans(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    del ctx, person
    # Listing a person's plans needs an owner index, which no query has demonstrated yet.
    # Returning an empty list is honest; the screen says so rather than inventing content.
    return _response(200, [])  # type: ignore[arg-type]


def _plan(ctx: bootstrap.Context, plan_id: PlanId) -> dict[str, Any]:
    plan = ctx.plans.get_plan(plan_id)
    if plan is None:
        return _problem(404, "No such plan", "NOT_FOUND")
    version = ctx.plans.get_version(plan.active_version_id) if plan.active_version_id else None
    return _response(
        200,
        {
            "planId": plan.plan_id,
            "label": (version.label if version else None) or "Plan",
            "type": plan.plan_type.value,
            "cadence": version.trigger.kind.value if version else "",
            "timeOfDay": (version.trigger.time_of_day if version else None) or "",
            "active": plan.is_active,
            "steps": [
                {
                    "sequence": step.sequence,
                    "offsetSeconds": step.offset_seconds,
                    "action": step.action.value,
                    "targetRole": step.target_role.value if step.target_role else None,
                }
                for step in (version.steps if version else ())
            ],
        },
    )


def _circle(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    del ctx, person
    # Same: a person-to-circle index has not been demonstrated by a query yet.
    return _response(200, [])  # type: ignore[arg-type]


def _claim(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    responder = _caller(event)
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return _problem(404, "No such alert", "NOT_FOUND")

    now = ctx.now()
    claimed = alert.claim(now, responder)
    ctx.alerts.save(claimed)
    ctx.audit.append(
        alert_id=alert_id,
        actor_type="RESPONDER",
        actor_id=responder,
        event_type="ALERT_CLAIMED",
        at=now,
    )
    lease = claimed.lease
    return _response(
        200,
        {
            "alertId": alert_id,
            "state": claimed.state.value,
            "leaseExpiresAt": lease.expires_at.isoformat() if lease else None,
            "resolved": False,
        },
    )


def _resolve(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    responder = _caller(event)
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return _problem(404, "No such alert", "NOT_FOUND")

    now = ctx.now()
    resolved = alert.resolve_by_responder(now, responder)
    ctx.alerts.save(resolved)
    ctx.audit.append(
        alert_id=alert_id,
        actor_type="RESPONDER",
        actor_id=responder,
        event_type="RESPONDER_VERIFIED",
        at=now,
    )
    return _response(200, {"alertId": alert_id, "state": resolved.state.value})


def _timeline(ctx: bootstrap.Context, alert_id: AlertId) -> dict[str, Any]:
    """What happened, in order. Nothing happens invisibly."""
    events = ctx.audit.for_alert(alert_id)
    return _response(
        200,
        {
            "alertId": alert_id,
            "events": [
                {
                    "at": str(event.get("at")),
                    "actor": str(event.get("actorType")),
                    "event": str(event.get("eventType")),
                    "metadata": event.get("metadata") or {},
                }
                for event in events
            ],
        },
    )
