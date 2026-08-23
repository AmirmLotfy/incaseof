"""HTTP API.

A thin translation layer: parse the event, call the domain, serialise the result. No rules
live here — a rule that exists only in an HTTP handler is a rule the workflow does not
enforce, and the workflow is what runs when nobody is looking.

Two authentication realms reach this module. ``/v1/*`` carries a Cognito principal.
``/v1/r/*`` carries a signed single-Alert responder token, because a friend must be able
to respond at 2am without creating an account.
"""

from __future__ import annotations

import json
from typing import Any

from services.domain.errors import DomainError, LeaseConflict, NotAuthorized, TerminalAlert
from services.domain.ids import AlertId, MomentId, PersonId
from services.domain.resolution import ResolutionSource
from services.handlers import bootstrap

JSON = "application/json"
PROBLEM = "application/problem+json"


def _response(status: int, body: dict[str, Any], content_type: str = JSON) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": content_type, "cache-control": "no-store"},
        "body": json.dumps(body),
    }


def _problem(status: int, title: str, reason_code: str) -> dict[str, Any]:
    """RFC 9457. The reason code is stable and machine-readable; the detail is not.

    Authorization failures deliberately say little: a 403 that explains *why* can confirm
    that another person's Alert exists.
    """
    return _response(
        status,
        {"type": "about:blank", "title": title, "status": status, "reason_code": reason_code},
        PROBLEM,
    )


def _caller(event: dict[str, Any]) -> PersonId:
    """The authenticated subject, from the JWT the API Gateway authorizer validated."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    subject = claims.get("sub")
    if not subject:
        raise NotAuthorized("no authenticated principal on this request")
    return PersonId(subject)


def _route(event: dict[str, Any]) -> tuple[str, str]:
    ctx = event.get("requestContext", {}).get("http", {})
    return ctx.get("method", ""), event.get("routeKey", "")


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    try:
        return _dispatch(event)
    except NotAuthorized:
        return _problem(403, "Not permitted", "NOT_AUTHORIZED")
    except TerminalAlert:
        return _problem(409, "This alert is already closed", "ALERT_CLOSED")
    except LeaseConflict:
        return _problem(409, "Someone else is already checking", "LEASE_HELD")
    except DomainError as error:
        return _problem(422, str(error), "INVALID_REQUEST")


def _dispatch(event: dict[str, Any]) -> dict[str, Any]:
    ctx = bootstrap.build()
    _, route = _route(event)
    params = event.get("pathParameters") or {}

    if route == "POST /v1/moments/{momentId}/confirm":
        return _confirm(ctx, event, MomentId(params["momentId"]))
    if route == "POST /v1/alerts/{alertId}/claim":
        return _claim(ctx, event, AlertId(params["alertId"]))
    if route == "POST /v1/alerts/{alertId}/resolve":
        return _resolve(ctx, event, AlertId(params["alertId"]))
    if route == "GET /v1/alerts/{alertId}/timeline":
        return _timeline(ctx, AlertId(params["alertId"]))

    return _problem(404, "No such route", "NOT_FOUND")


def _confirm(ctx: bootstrap.Context, event: dict[str, Any], moment_id: MomentId) -> dict[str, Any]:
    """ "I'm okay." The subject's confirmation always wins, from any non-terminal state."""
    person = _caller(event)
    alert = ctx.alerts.alert_for_moment(moment_id)
    if alert is None:
        return _problem(404, "No open alert for that moment", "NOT_FOUND")

    now = ctx.clock.now()
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


def _claim(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    """ "I'm checking." Pauses backup escalation. Does not resolve anything."""
    responder = _caller(event)
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return _problem(404, "No such alert", "NOT_FOUND")

    now = ctx.clock.now()
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
    assert lease is not None  # noqa: S101
    return _response(
        200,
        {
            "alertId": alert_id,
            "state": claimed.state.value,
            "leaseExpiresAt": lease.expires_at.isoformat(),
            # Said explicitly, because the whole product hinges on this distinction.
            "resolved": False,
        },
    )


def _resolve(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    """ "I reached them, they're okay." The only responder path that closes an Alert."""
    responder = _caller(event)
    alert = ctx.alerts.get(alert_id)
    if alert is None:
        return _problem(404, "No such alert", "NOT_FOUND")

    now = ctx.clock.now()
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
                    "at": str(e.get("at")),
                    "actor": str(e.get("actorType")),
                    "event": str(e.get("eventType")),
                    "metadata": e.get("metadata") or {},
                }
                for e in events
            ],
        },
    )
