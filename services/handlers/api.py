"""HTTP API.

A translation layer: parse the event, call the domain, serialise the result. No rules live
here. A rule that exists only in an HTTP handler is a rule the workflow does not enforce,
and the workflow is what runs when nobody is looking.

Two authentication realms arrive here. ``/v1/*`` carries a Cognito principal. ``/r/*`` and
``/v1/r/*`` carry a signed single-Alert token, because a responder has no account.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import timedelta
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    ContactChannelPermission,
    MemberStatus,
)
from services.domain.contact_endpoint import EndpointType
from services.domain.demo_token import issue as issue_demo_token
from services.domain.demo_token import verify as verify_demo_token
from services.domain.errors import (
    DomainError,
    LeaseConflict,
    NotAuthorized,
    TerminalAlert,
)
from services.domain.ids import (
    AlertId,
    CircleId,
    ConsentId,
    DeviceId,
    InvitationId,
    MembershipId,
    MomentId,
    PersonId,
    PlanId,
    uuid_factory,
)
from services.domain.invitation import CircleInvitation, InvitationStatus
from services.domain.invitation_token import issue as issue_invitation_token
from services.domain.invitation_token import verify as verify_invitation_token
from services.domain.moment import ExpectedMoment, MomentStatus
from services.domain.plan import Channel, Plan, PlanVersion, ResponderRole
from services.domain.resolution import ResolutionSource
from services.domain.responder_token import TokenError
from services.handlers import bootstrap, planning, responding

JSON = "application/json"
PROBLEM = "application/problem+json"

DEMO_ROUTE_MAP = {
    "POST /v1/demo/plans/compile": "POST /v1/plans/compile",
    "POST /v1/demo/plans": "POST /v1/plans",
    "GET /v1/demo/plans": "GET /v1/plans",
    "GET /v1/demo/plans/{planId}": "GET /v1/plans/{planId}",
    "POST /v1/demo/plans/{planId}/activate": "POST /v1/plans/{planId}/activate",
    "POST /v1/demo/plans/{planId}/pause": "POST /v1/plans/{planId}/pause",
    "POST /v1/demo/plans/{planId}/resume": "POST /v1/plans/{planId}/resume",
    "POST /v1/demo/plans/{planId}/test": "POST /v1/plans/{planId}/test",
    "GET /v1/demo/moments/next": "GET /v1/moments/next",
    "POST /v1/demo/moments/{momentId}/confirm": "POST /v1/moments/{momentId}/confirm",
    "POST /v1/demo/moments/{momentId}/extend": "POST /v1/moments/{momentId}/extend",
    "GET /v1/demo/circle": "GET /v1/circle",
    "POST /v1/demo/circle/invitations": "POST /v1/circle/invitations",
    "GET /v1/demo/history": "GET /v1/history",
    "GET /v1/demo/alerts/{alertId}": "GET /v1/alerts/{alertId}",
    "POST /v1/demo/alerts/{alertId}/claim": "POST /v1/alerts/{alertId}/claim",
    "GET /v1/demo/alerts/{alertId}/timeline": "GET /v1/alerts/{alertId}/timeline",
}


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
    except TokenError:
        return _problem(403, "Not permitted", "NOT_AUTHORIZED")
    except TerminalAlert:
        return _problem(409, "This is already closed", "ALERT_CLOSED")
    except LeaseConflict:
        return _problem(409, "Someone else is already checking", "LEASE_HELD")
    except DomainError as error:
        return _problem(422, str(error), "INVALID_REQUEST")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _problem(400, "The request is malformed", "INVALID_REQUEST")


def _dispatch(event: dict[str, Any]) -> dict[str, Any]:
    route = event.get("routeKey", "")
    if route == "GET /":
        return _response(
            200,
            {
                "service": "In Case Of API",
                "status": "ok",
                "productBoundary": "Monitors expected moments, not people.",
            },
        )

    ctx = bootstrap.build()
    params = event.get("pathParameters") or {}

    if (
        route == "POST /v1/demo/session"
        or route == "GET /v1/demo/alerts/{alertId}/responder-link"
        or route in DEMO_ROUTE_MAP
    ):
        return _demo_route(ctx, event, route)

    # -- responder, by signed token ---------------------------------------
    token = params.get("signedToken")
    if token and (route == "GET /i/{signedToken}" or route.startswith("POST /v1/i/")):
        return _invitation_route(ctx, route, token)
    if token:
        return _responder_route(ctx, route, token)

    # -- subject, by Cognito principal ------------------------------------
    if route == "GET /v1/profile":
        return _profile(ctx, _caller(event))
    if route == "PATCH /v1/profile":
        return _update_profile(ctx, event, _caller(event))
    if route == "GET /v1/readiness":
        return _readiness_response(ctx, _caller(event))
    if route == "POST /v1/plans/compile":
        return _compile(ctx, event)
    if route == "POST /v1/plans":
        return _create_plan(ctx, event, _caller(event))
    if route == "GET /v1/moments/next":
        return _next_moment(ctx, _caller(event))
    if route == "POST /v1/moments/{momentId}/confirm":
        return _confirm(ctx, event, MomentId(params["momentId"]))
    if route == "POST /v1/moments/{momentId}/extend":
        return _extend(ctx, event, MomentId(params["momentId"]))
    if route == "GET /v1/moments/{momentId}":
        return _moment(ctx, MomentId(params["momentId"]), _caller(event))
    if route == "POST /v1/moments/{momentId}/cancel":
        return _cancel_moment(ctx, event, MomentId(params["momentId"]), _caller(event))
    if route == "GET /v1/plans":
        return _plans(ctx, _caller(event))
    if route == "GET /v1/history":
        return _history(ctx, _caller(event))
    if route == "GET /v1/plans/{planId}":
        return _plan(ctx, PlanId(params["planId"]), _caller(event))
    if route == "POST /v1/plans/{planId}/activate":
        return _activate_plan(ctx, event, PlanId(params["planId"]), _caller(event))
    if route == "POST /v1/plans/{planId}/pause":
        return _pause_plan(ctx, event, PlanId(params["planId"]), _caller(event))
    if route == "POST /v1/plans/{planId}/resume":
        return _resume_plan(ctx, event, PlanId(params["planId"]), _caller(event))
    if route == "POST /v1/plans/{planId}/test":
        return _test_plan(ctx, event, PlanId(params["planId"]))
    if route == "GET /v1/circle":
        return _circle(ctx, _caller(event))
    if route == "POST /v1/circle/invitations":
        return _invite(ctx, event, _caller(event))
    if route == "POST /v1/circle/invitations/{invitationId}/resend":
        return _resend_invitation(
            ctx,
            event,
            InvitationId(params["invitationId"]),
            _caller(event),
        )
    if route == "DELETE /v1/circle/members/{memberId}":
        return _remove_member(ctx, event, MembershipId(params["memberId"]), _caller(event))
    if route == "POST /v1/devices":
        return _register_device(ctx, event, _caller(event))
    if route == "DELETE /v1/devices/{deviceId}":
        return _remove_device(ctx, DeviceId(params["deviceId"]), _caller(event))
    if route == "GET /v1/alerts/{alertId}":
        return _alert(ctx, AlertId(params["alertId"]), _caller(event))
    if route == "POST /v1/alerts/{alertId}/claim":
        return _claim(ctx, event, AlertId(params["alertId"]))
    if route == "POST /v1/alerts/{alertId}/resolve":
        return _resolve(ctx, event, AlertId(params["alertId"]))
    if route == "POST /v1/alerts/{alertId}/release":
        return _release(ctx, event, AlertId(params["alertId"]))
    if route == "GET /v1/alerts/{alertId}/timeline":
        return _timeline(ctx, AlertId(params["alertId"]), _caller(event))

    return _problem(404, "No such route", "NOT_FOUND")


def _demo_route(ctx: bootstrap.Context, event: dict[str, Any], route: str) -> dict[str, Any]:
    """Run a synthetic, isolated judge tenant through the real product handlers.

    This realm exists only in the demo stack. Sessions are short lived and each gets a
    distinct subject identifier, so two judges cannot mutate one another's walkthrough.
    It has no delivery endpoints; the normal worker records safe sink/unavailable results.
    """
    if os.environ.get("ICO_ENV") != "demo":
        return _problem(404, "No such route", "NOT_FOUND")

    if route == "POST /v1/demo/session":
        person = PersonId(f"demo-{uuid5(NAMESPACE_URL, str(uuid_factory()))}")
        _ensure_demo_circle(ctx, person)
        value = issue_demo_token(person, key=ctx.signing_key, now=ctx.now())
        return _response(
            201,
            {
                "sessionToken": value,
                "expiresInSeconds": 1800,
                "subjectDisplayName": "Mona",
                "synthetic": True,
            },
        )

    authorization = str((event.get("headers") or {}).get("authorization") or "")
    if not authorization.startswith("Bearer "):
        raise NotAuthorized("demo session missing")
    claims = verify_demo_token(
        authorization.removeprefix("Bearer ").strip(),
        key=ctx.signing_key,
        now=ctx.now(),
    )
    _ensure_demo_circle(ctx, claims.person_id)

    if route == "GET /v1/demo/alerts/{alertId}/responder-link":
        from services.handlers.escalation import responder_link

        params = event.get("pathParameters") or {}
        alert, plan, _ = _authorized_alert(ctx, AlertId(params["alertId"]), claims.person_id)
        circle = ctx.circles.get(CircleId(plan.circle_id))
        member = circle.member_for_role(ResponderRole.PRIMARY) if circle else None
        if member is None:
            return _problem(409, "No demo responder is available", "NO_RESPONDER")
        link = responder_link(ctx, alert, member, ctx.now())
        if not link:
            return _problem(503, "The responder link is unavailable", "LINK_UNAVAILABLE")
        return _response(200, {"responderUrl": link, "synthetic": True})

    mapped = dict(event)
    mapped["routeKey"] = DEMO_ROUTE_MAP[route]
    request_context = dict(mapped.get("requestContext") or {})
    request_context["authorizer"] = {"jwt": {"claims": {"sub": str(claims.person_id)}}}
    mapped["requestContext"] = request_context

    if mapped["routeKey"] == "POST /v1/plans/compile":
        body = _body(mapped)
        body["circleId"] = str(_demo_circle_id(claims.person_id))
        mapped["body"] = json.dumps(body)

    response = _dispatch(mapped)
    if mapped["routeKey"] == "POST /v1/plans" and response.get("statusCode") == 201:
        document = json.loads(response["body"])
        _grant_demo_consents(ctx, claims.person_id, PlanId(document["planId"]))
    return response


def _demo_circle_id(person: PersonId) -> CircleId:
    return CircleId(_stable_id("circles", str(person)))


def _ensure_demo_circle(ctx: bootstrap.Context, person: PersonId) -> Circle:
    existing = ctx.circles.for_owner(person)
    if existing is not None:
        return existing
    circle_id = _demo_circle_id(person)
    members = tuple(
        CircleMember(
            membership_id=MembershipId(_stable_id(f"demo/{person}", role.value)),
            circle_id=circle_id,
            person_id=PersonId(_stable_id(f"demo/{person}/responders", role.value)),
            role=role,
            priority=priority,
            status=MemberStatus.ACCEPTED,
            display_name=name,
            relationship="Judge demo fixture",
        )
        for role, priority, name in (
            (ResponderRole.PRIMARY, 1, "Maya"),
            (ResponderRole.BACKUP, 2, "Omar"),
        )
    )
    circle = Circle(
        circle_id=circle_id,
        owner_person_id=person,
        members=members,
        owner_display_name="Mona",
    )
    ctx.circles.save_circle(circle)
    return circle


def _grant_demo_consents(ctx: bootstrap.Context, person: PersonId, plan_id: PlanId) -> None:
    circle = _ensure_demo_circle(ctx, person)
    for member in circle.members:
        ctx.circles.save_consent(
            ConsentGrant(
                consent_id=ConsentId(_stable_id(f"demo/{plan_id}/consents", str(member.person_id))),
                subject_person_id=person,
                responder_person_id=member.person_id,
                plan_id=plan_id,
                status=ConsentStatus.ACTIVE,
                accepted_at=ctx.now(),
                policy_version="judge-demo-v1",
            )
        )


def _compile(ctx: bootstrap.Context, event: dict[str, Any]) -> dict[str, Any]:
    """Natural language to a plan preview.

    Creates nothing. The person confirms separately, and the response says so on the wire.
    """
    from services.handlers.compile_plan import compile_for

    body = json.loads(event.get("body") or "{}")
    result = compile_for(
        ctx,
        utterance=body.get("utterance", ""),
        subject_person_id=_caller(event),
        circle_id=CircleId(body["circleId"]) if body.get("circleId") else None,
        timezone=body.get("timezone", "UTC"),
    )
    return _response(result["status"], result["body"])


def _body(event: dict[str, Any]) -> dict[str, Any]:
    parsed = json.loads(event.get("body") or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("JSON body must be an object")
    return parsed


def _idempotency_key(event: dict[str, Any]) -> str:
    headers = {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}
    key = headers.get("idempotency-key", "").strip()
    if not key or len(key) > 200:
        raise ValueError("Idempotency-Key is required")
    return key


def _stable_id(namespace: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"https://incaof.com/{namespace}/{key}"))


def _owned_plan(ctx: bootstrap.Context, plan_id: PlanId, person: PersonId) -> Plan:
    plan = ctx.plans.get_plan(plan_id)
    if plan is None or plan.subject_person_id != person:
        raise NotAuthorized("plan is not reachable")
    return plan


def _version_for(ctx: bootstrap.Context, plan: Plan) -> PlanVersion | None:
    if plan.active_version_id:
        return ctx.plans.get_version(plan.active_version_id)
    return ctx.plans.latest_version(plan.plan_id)


def _moment_belongs_to_plan(
    ctx: bootstrap.Context, moment: ExpectedMoment, plan_id: PlanId
) -> bool:
    version = ctx.plans.get_version(moment.version_id)
    return version is not None and version.plan_id == plan_id


def _owned_moment(
    ctx: bootstrap.Context, moment_id: MomentId, person: PersonId
) -> tuple[ExpectedMoment, Plan, PlanVersion]:
    moment = ctx.moments.get(moment_id)
    if moment is None:
        raise NotAuthorized("moment is not reachable")
    version = ctx.plans.get_version(moment.version_id)
    plan = ctx.plans.get_plan(version.plan_id) if version else None
    if version is None or plan is None or plan.subject_person_id != person:
        raise NotAuthorized("moment is not reachable")
    return moment, plan, version


def _authorized_alert(
    ctx: bootstrap.Context, alert_id: AlertId, person: PersonId
) -> tuple[Any, Plan, PlanVersion]:
    alert = ctx.alerts.get(alert_id)
    version = ctx.plans.get_version(alert.plan_version_id) if alert else None
    plan = ctx.plans.get_plan(version.plan_id) if version else None
    if alert is None or version is None or plan is None:
        raise NotAuthorized("alert is not reachable")
    if plan.subject_person_id == person:
        return alert, plan, version
    circle = ctx.circles.get(CircleId(plan.circle_id))
    member = circle.member(person) if circle else None
    consent = ctx.circles.consents_for(plan.plan_id).get(person)
    if (
        member is None
        or not member.is_accepted
        or consent is None
        or not consent.is_active(ctx.now())
    ):
        raise NotAuthorized("alert is not reachable")
    return alert, plan, version


def _plan_view(ctx: bootstrap.Context, plan: Plan) -> dict[str, Any]:
    version = _version_for(ctx, plan)
    return {
        "planId": plan.plan_id,
        "versionId": version.version_id if version else None,
        "label": (version.label if version else None) or "Plan",
        "type": plan.plan_type.value,
        "cadence": version.trigger.kind.value if version else "",
        "timeOfDay": (version.trigger.time_of_day if version else None) or "",
        "active": plan.is_active,
        "paused": plan.paused,
        "steps": [
            {
                "sequence": step.sequence,
                "offsetSeconds": step.offset_seconds,
                "action": step.action.value,
                "targetRole": step.target_role.value if step.target_role else None,
            }
            for step in (version.steps if version else ())
        ],
    }


def _moment_view(
    ctx: bootstrap.Context, moment: ExpectedMoment, version: PlanVersion
) -> dict[str, Any]:
    alert = ctx.alerts.alert_for_moment(moment.moment_id)
    return {
        "momentId": moment.moment_id,
        "planId": version.plan_id,
        "planLabel": version.label or "Check-in",
        "dueAt": moment.due_at.isoformat(),
        "graceUntil": moment.grace_until.isoformat(),
        "status": moment.status.value,
        "isDrill": moment.is_drill,
        "timeScale": moment.time_scale,
        "alertState": alert.state.value if alert else None,
        "alertId": alert.alert_id if alert else None,
    }


def _alert_view(alert: Any) -> dict[str, Any]:
    return {
        "alertId": alert.alert_id,
        "momentId": alert.moment_id,
        "planId": alert.version.plan_id,
        "planLabel": alert.version.label or "Check-in",
        "state": alert.state.value,
        "openedAt": alert.opened_at.isoformat(),
        "leaseOwner": alert.lease.owner_person_id if alert.lease else None,
        "leaseExpiresAt": alert.lease.expires_at.isoformat() if alert.lease else None,
        "resolvedAt": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "resolved": alert.is_terminal,
    }


def _finish_moment(ctx: bootstrap.Context, alert: Any) -> None:
    """Close the timer and materialize the next recurring Moment exactly once."""
    moment = ctx.moments.get(alert.moment_id)
    if moment is None or moment.status not in {MomentStatus.SCHEDULED, MomentStatus.DUE}:
        return
    ctx.moments.save(replace(moment, status=MomentStatus.RESOLVED))
    if ctx.scheduler is not None:
        ctx.scheduler.cancel(moment.moment_id)
    if moment.is_drill:
        return
    version = ctx.plans.get_version(moment.version_id)
    plan = ctx.plans.get_plan(version.plan_id) if version else None
    if version and plan and plan.is_active and plan.active_version_id == version.version_id:
        planning.schedule_following_moment(ctx, version, after=ctx.now())


def _invitation_repository(ctx: bootstrap.Context) -> Any:
    if ctx.invitations is None:
        raise RuntimeError("invitation repository is not configured")
    return ctx.invitations


def _invitation_token(ctx: bootstrap.Context, invitation: CircleInvitation) -> str:
    remaining = invitation.expires_at - ctx.now()
    return issue_invitation_token(
        invitation.invitation_id,
        key=ctx.signing_key,
        now=ctx.now(),
        lifetime=remaining,
    )


def _invitation_view(ctx: bootstrap.Context, invitation: CircleInvitation) -> dict[str, Any]:
    circle = ctx.circles.get(invitation.circle_id)
    member = circle.member(invitation.responder_person_id) if circle else None
    return {
        "invitationId": invitation.invitation_id,
        "ownerDisplayName": circle.owner_display_name if circle else "Someone",
        "displayName": member.display_name if member else "You",
        "relationship": member.relationship if member else None,
        "role": member.role.value if member else None,
        "status": invitation.status.value,
        "expiresAt": invitation.expires_at.isoformat(),
        "planCount": len(invitation.plan_ids),
    }


def _invitation_route(ctx: bootstrap.Context, route: str, token: str) -> dict[str, Any]:
    try:
        claims = verify_invitation_token(token, key=ctx.signing_key, now=ctx.now())
    except TokenError as error:
        raise NotAuthorized("invalid invitation") from error
    invitation = _invitation_repository(ctx).get(claims.invitation_id)
    if invitation is None or int(invitation.expires_at.timestamp()) != int(
        claims.expires_at.timestamp()
    ):
        raise NotAuthorized("invalid invitation")

    if route == "GET /i/{signedToken}":
        return _response(200, _invitation_view(ctx, invitation))
    if route == "POST /v1/i/{signedToken}/accept":
        return _accept_invitation(ctx, invitation)
    if route == "POST /v1/i/{signedToken}/decline":
        return _decline_invitation(ctx, invitation)
    return _problem(404, "No such route", "NOT_FOUND")


def _accept_invitation(ctx: bootstrap.Context, invitation: CircleInvitation) -> dict[str, Any]:
    if invitation.status is InvitationStatus.DECLINED:
        return _problem(409, "This invitation was declined", "INVITATION_CLOSED")
    if invitation.status is InvitationStatus.REVOKED:
        raise NotAuthorized("invalid invitation")
    circle = ctx.circles.get(invitation.circle_id)
    if circle is None:
        raise NotAuthorized("invalid invitation")
    member = circle.member(invitation.responder_person_id)
    if member is None or member.membership_id != invitation.membership_id:
        raise NotAuthorized("invalid invitation")
    accepted_member = replace(member, status=MemberStatus.ACCEPTED)
    ctx.circles.save_circle(
        replace(
            circle,
            members=tuple(
                accepted_member if candidate.membership_id == member.membership_id else candidate
                for candidate in circle.members
            ),
        )
    )
    for plan_id in invitation.plan_ids:
        plan = ctx.plans.get_plan(plan_id)
        if plan is None or plan.subject_person_id != invitation.owner_person_id:
            continue
        ctx.circles.save_consent(
            ConsentGrant(
                consent_id=ConsentId(
                    _stable_id(f"plans/{plan_id}/consents", str(invitation.responder_person_id))
                ),
                subject_person_id=invitation.owner_person_id,
                responder_person_id=invitation.responder_person_id,
                plan_id=plan_id,
                status=ConsentStatus.ACTIVE,
                accepted_at=ctx.now(),
            )
        )
    accepted = invitation.accept()
    _invitation_repository(ctx).save(accepted)
    return _response(200, {**_invitation_view(ctx, accepted), "consentActive": True})


def _decline_invitation(ctx: bootstrap.Context, invitation: CircleInvitation) -> dict[str, Any]:
    if invitation.status is InvitationStatus.ACCEPTED:
        return _problem(409, "This invitation was already accepted", "INVITATION_CLOSED")
    circle = ctx.circles.get(invitation.circle_id)
    member = circle.member(invitation.responder_person_id) if circle else None
    if circle and member:
        ctx.circles.save_circle(
            replace(
                circle,
                members=tuple(
                    replace(candidate, status=MemberStatus.DECLINED)
                    if candidate.membership_id == member.membership_id
                    else candidate
                    for candidate in circle.members
                ),
            )
        )
    declined = invitation.decline()
    _invitation_repository(ctx).save(declined)
    return _response(200, {**_invitation_view(ctx, declined), "consentActive": False})


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
                "state": view.state,
                "tried": view.tried,
                "ownerName": view.owner_name,
                "leaseExpiresAt": view.lease_expires_at.isoformat()
                if view.lease_expires_at
                else None,
                "canClaim": view.can_claim,
                "canResolve": view.can_resolve,
                "nextContact": None,
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
        _finish_moment(ctx, alert)
        return _response(200, {"alertId": alert.alert_id, "state": alert.state.value})

    return _problem(404, "No such route", "NOT_FOUND")


# -- subject ------------------------------------------------------------------


def _profile_repository(ctx: bootstrap.Context) -> Any:
    if ctx.profiles is None:
        raise RuntimeError("profile repository is not configured")
    return ctx.profiles


def _profile_view(profile: Profile) -> dict[str, Any]:
    return {
        "displayName": profile.display_name,
        "locale": profile.locale.value,
        "timezone": profile.timezone,
        "country": profile.country.value,
        "status": profile.status.value,
        "createdAt": profile.created_at.isoformat(),
        "updatedAt": profile.updated_at.isoformat(),
    }


def _profile(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    profile = _profile_repository(ctx).get(person)
    if profile is None:
        return _problem(404, "Complete your account profile", "PROFILE_NOT_FOUND")
    return _response(200, _profile_view(profile))


def _update_profile(
    ctx: bootstrap.Context, event: dict[str, Any], person: PersonId
) -> dict[str, Any]:
    payload = _body(event)
    allowed = {"displayName", "locale", "timezone", "country"}
    if not payload or set(payload) - allowed:
        raise ValueError("profile contains unsupported or no fields")

    repository = _profile_repository(ctx)
    current = repository.get(person)
    now = ctx.now()
    for field in payload:
        if not isinstance(payload[field], str):
            raise ValueError(f"{field} must be a string")
    display_name = payload["displayName"].strip() if "displayName" in payload else None
    locale = SupportedLocale(payload["locale"]) if "locale" in payload else None
    timezone = payload["timezone"] if "timezone" in payload else None
    country = SupportedCountry(payload["country"]) if "country" in payload else None
    if current is None:
        if None in {display_name, locale, timezone, country}:
            return _problem(
                422,
                "A new profile requires displayName, locale, timezone, and country",
                "PROFILE_INCOMPLETE",
            )
        profile = Profile(
            person_id=person,
            display_name=cast(str, display_name),
            locale=cast(SupportedLocale, locale),
            timezone=cast(str, timezone),
            country=cast(SupportedCountry, country),
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    else:
        profile = current.update(
            at=now,
            display_name=display_name,
            locale=locale,
            timezone=timezone,
            country=country,
        )
    repository.save(profile)
    return _response(200, _profile_view(profile))


def _allowed_countries() -> frozenset[SupportedCountry]:
    configured = os.environ.get("ICO_ALLOWED_COUNTRIES", "EG,US")
    return frozenset(
        SupportedCountry(value.strip()) for value in configured.split(",") if value.strip()
    )


def _admissions_open() -> bool:
    default = "false" if os.environ.get("ICO_ENV") == "prod" else "true"
    value = os.environ.get("ICO_ADMISSIONS_OPEN", default).lower()
    if value not in {"true", "false"}:
        raise RuntimeError("ICO_ADMISSIONS_OPEN must be true or false")
    return value == "true"


def _max_active_plans() -> int:
    value = int(os.environ.get("ICO_MAX_ACTIVE_PLANS_PER_ACCOUNT", "3"))
    if value < 1 or value > 20:
        raise RuntimeError("ICO_MAX_ACTIVE_PLANS_PER_ACCOUNT must be between 1 and 20")
    return value


def _has_verified_endpoint(ctx: bootstrap.Context, person: PersonId, kind: EndpointType) -> bool:
    if ctx.endpoints is None:
        return False
    endpoint = ctx.endpoints.for_person(person, kind)
    return endpoint is not None and endpoint.is_usable


def _account_readiness(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    profile = ctx.profiles.get(person) if ctx.profiles is not None else None
    plans = ctx.plans.list_for_subject(person)
    active_count = sum(plan.is_active for plan in plans)
    maximum = _max_active_plans()
    country_supported = profile is not None and profile.country in _allowed_countries()
    profile_ready = profile is not None and profile.status is AccountStatus.ACTIVE
    admissions_open = _admissions_open()
    reasons: list[str] = []
    if not profile_ready:
        reasons.append("PROFILE_REQUIRED")
    if profile is not None and not country_supported:
        reasons.append("COUNTRY_UNSUPPORTED")
    if not admissions_open:
        reasons.append("ADMISSIONS_PAUSED")
    if active_count >= maximum:
        reasons.append("CAPACITY_EXHAUSTED")
    circle = ctx.circles.for_owner(person)
    accepted_members = len(circle.accepted_members) if circle else 0
    return {
        "profileReady": profile_ready,
        "countrySupported": country_supported,
        "admissionsOpen": admissions_open,
        "activePlanCount": active_count,
        "maxActivePlans": maximum,
        "remainingPlanCapacity": max(0, maximum - active_count),
        "subjectChannels": {
            "push": _has_verified_endpoint(ctx, person, EndpointType.PUSH_TOKEN),
            "sms": _has_verified_endpoint(ctx, person, EndpointType.PHONE),
            "call": False,
        },
        "acceptedResponderCount": accepted_members,
        "accountReady": not reasons,
        "reasons": reasons,
    }


def _readiness_response(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    return _response(200, _account_readiness(ctx, person))


def _activation_readiness_problem(
    ctx: bootstrap.Context,
    person: PersonId,
    plan: Plan,
    version: PlanVersion,
) -> dict[str, Any] | None:
    if os.environ.get("ICO_ENV") != "prod":
        return None
    readiness = _account_readiness(ctx, person)
    for reason in readiness["reasons"]:
        title = {
            "PROFILE_REQUIRED": "Complete your account profile",
            "COUNTRY_UNSUPPORTED": "This country is not available",
            "ADMISSIONS_PAUSED": "New plan activation is temporarily paused",
            "CAPACITY_EXHAUSTED": "Your active plan limit has been reached",
        }[reason]
        return _problem(409, title, reason)

    circle = ctx.circles.get(CircleId(plan.circle_id))
    channel_missing = False
    for step in version.steps:
        channel = step.action.channel
        if step.action.is_subject_directed:
            endpoint_type = {
                Channel.PUSH: EndpointType.PUSH_TOKEN,
                Channel.SMS: EndpointType.PHONE,
            }.get(channel)
            if endpoint_type is None or not _has_verified_endpoint(ctx, person, endpoint_type):
                channel_missing = True
        elif step.target_role is not None:
            member = circle.member_for_role(step.target_role) if circle else None
            permission = {
                Channel.PUSH: ContactChannelPermission.PUSH,
                Channel.SMS: ContactChannelPermission.SMS,
                Channel.CALL: ContactChannelPermission.CALL,
            }[channel]
            consent = (
                ctx.circles.consents_for(plan.plan_id).get(member.person_id) if member else None
            )
            endpoint_type = {
                Channel.PUSH: EndpointType.PUSH_TOKEN,
                Channel.SMS: EndpointType.PHONE,
            }.get(channel)
            if (
                member is None
                or consent is None
                or not consent.is_active(ctx.now())
                or not consent.permits_channel(permission)
                or endpoint_type is None
                or not _has_verified_endpoint(ctx, member.person_id, endpoint_type)
            ):
                channel_missing = True
    if channel_missing:
        return _problem(
            409,
            "Verify every channel and responder required by this plan",
            "CHANNEL_NOT_READY",
        )
    return None


def _create_plan(ctx: bootstrap.Context, event: dict[str, Any], person: PersonId) -> dict[str, Any]:
    payload = _body(event)
    document = payload.get("compiledPlan", payload)
    if not isinstance(document, dict):
        raise ValueError("compiledPlan must be an object")

    circle = ctx.circles.for_owner(person)
    requested_circle = payload.get("circleId") if "compiledPlan" in payload else None
    if requested_circle:
        candidate = ctx.circles.get(CircleId(str(requested_circle)))
        if candidate is None or candidate.owner_person_id != person:
            raise NotAuthorized("circle is not reachable")
        circle = candidate
    if circle is None:
        circle = Circle(
            circle_id=CircleId(_stable_id("circles", str(person))),
            owner_person_id=person,
            owner_display_name=str(payload.get("ownerDisplayName") or "You")[:60],
        )
        ctx.circles.save_circle(circle)

    plan, result = planning.create_plan(
        ctx,
        document,
        subject_person_id=person,
        circle_id=circle.circle_id,
    )
    return _response(
        201,
        {
            **_plan_view(ctx, plan),
            "requiresActivation": True,
            "warnings": list(result.warnings),
        },
    )


def _activate_plan(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    plan_id: PlanId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    plan = _owned_plan(ctx, plan_id, person)
    version = _version_for(ctx, plan)
    if version is None:
        return _problem(409, "This plan has no version to activate", "NO_PLAN_VERSION")
    if plan.is_active and plan.active_version_id == version.version_id:
        moment = next(
            (
                candidate
                for candidate in ctx.moments.outstanding_for_subject(person)
                if _moment_belongs_to_plan(ctx, candidate, plan_id)
            ),
            None,
        )
        return _response(
            200,
            {
                **_plan_view(ctx, plan),
                "moment": _moment_view(ctx, moment, version) if moment else None,
                "replayed": True,
            },
        )

    circle = ctx.circles.get(CircleId(plan.circle_id))
    consents = ctx.circles.consents_for(plan.plan_id)
    missing_roles = []
    for role in sorted(version.responder_roles, key=str):
        member = circle.member_for_role(role) if circle else None
        consent = consents.get(member.person_id) if member else None
        if member is None or consent is None or not consent.is_active(ctx.now()):
            missing_roles.append(role.value)
    if missing_roles:
        return _problem(
            409,
            "Required Circle consent is still pending",
            "CONSENT_REQUIRED",
        )

    readiness_problem = _activation_readiness_problem(ctx, person, plan, version)
    if readiness_problem is not None:
        return readiness_problem

    activation = planning.activate_plan(
        ctx,
        plan.plan_id,
        version.version_id,
        now=ctx.now(),
    )
    return _response(
        200,
        {
            **_plan_view(ctx, activation.plan),
            "moment": _moment_view(ctx, activation.moment, activation.version),
            "scheduleName": activation.schedule_name,
        },
    )


def _pause_plan(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    plan_id: PlanId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    plan = _owned_plan(ctx, plan_id, person)
    paused = replace(plan, paused=True)
    ctx.plans.save_plan(paused)
    for moment in ctx.moments.outstanding_for_subject(person):
        version = ctx.plans.get_version(moment.version_id)
        if version and version.plan_id == plan_id:
            ctx.moments.save(replace(moment, status=MomentStatus.CANCELLED))
            if ctx.scheduler is not None:
                ctx.scheduler.cancel(moment.moment_id)
    return _response(200, _plan_view(ctx, paused))


def _resume_plan(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    plan_id: PlanId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    plan = _owned_plan(ctx, plan_id, person)
    if plan.active_version_id is None:
        return _problem(409, "Activate this plan before resuming it", "PLAN_NOT_ACTIVE")
    version = ctx.plans.get_version(plan.active_version_id)
    if version is None:
        return _problem(409, "This plan's active version is missing", "NO_PLAN_VERSION")
    resumed = replace(plan, paused=False)
    ctx.plans.save_plan(resumed)
    moment = next(
        (
            candidate
            for candidate in ctx.moments.outstanding_for_subject(person)
            if _moment_belongs_to_plan(ctx, candidate, plan_id)
        ),
        None,
    )
    if moment is None:
        moment = planning.schedule_following_moment(ctx, version, after=ctx.now())
    return _response(
        200,
        {
            **_plan_view(ctx, resumed),
            "moment": _moment_view(ctx, moment, version) if moment else None,
        },
    )


def _next_moment(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    """The next thing expected of this person.

    404 when there is nothing outstanding, which is the normal, good state — the client
    reads it as "all clear" rather than as a failure.
    """
    moment = ctx.moments.next_for_subject(person, ctx.now())
    if moment is None:
        return _problem(404, "Nothing expected right now", "NO_PENDING_MOMENT")
    version = ctx.plans.get_version(moment.version_id)
    if version is None:
        return _problem(409, "The moment's plan version is missing", "NO_PLAN_VERSION")
    return _response(200, _moment_view(ctx, moment, version))


def _moment(ctx: bootstrap.Context, moment_id: MomentId, person: PersonId) -> dict[str, Any]:
    moment, _, version = _owned_moment(ctx, moment_id, person)
    return _response(200, _moment_view(ctx, moment, version))


def _confirm(ctx: bootstrap.Context, event: dict[str, Any], moment_id: MomentId) -> dict[str, Any]:
    """ "I'm okay." Always wins, from any non-terminal state."""
    person = _caller(event)
    _idempotency_key(event)
    _owned_moment(ctx, moment_id, person)
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
    _finish_moment(ctx, resolved)
    return _response(200, {"alertId": resolved.alert_id, "state": resolved.state.value})


def _extend(ctx: bootstrap.Context, event: dict[str, Any], moment_id: MomentId) -> dict[str, Any]:
    """ "Give me another thirty minutes." Moves this Moment only, never the plan."""
    person = _caller(event)
    _idempotency_key(event)
    moment, _, version = _owned_moment(ctx, moment_id, person)

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
    ctx.moments.save(extended, subject_person_id=person)
    if ctx.scheduler is not None:
        ctx.scheduler.schedule(extended)

    return _response(
        200,
        {
            "momentId": extended.moment_id,
            "planLabel": version.label or "Check-in",
            "dueAt": extended.due_at.isoformat(),
            "graceUntil": extended.grace_until.isoformat(),
        },
    )


def _cancel_moment(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    moment_id: MomentId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    moment, _, version = _owned_moment(ctx, moment_id, person)
    if moment.status is MomentStatus.CANCELLED:
        return _response(200, {**_moment_view(ctx, moment, version), "replayed": True})
    alert = ctx.alerts.alert_for_moment(moment_id)
    if alert is not None:
        cancelled_alert = alert.cancel(ctx.now(), person)
        ctx.alerts.save(cancelled_alert)
        ctx.audit.append(
            alert_id=alert.alert_id,
            actor_type="SUBJECT",
            actor_id=person,
            event_type="MOMENT_CANCELLED",
            at=ctx.now(),
        )
    cancelled = replace(moment, status=MomentStatus.CANCELLED)
    ctx.moments.save(cancelled, subject_person_id=person)
    if ctx.scheduler is not None:
        ctx.scheduler.cancel(moment_id)
    return _response(200, _moment_view(ctx, cancelled, version))


def _plans(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    return _response(
        200, {"plans": [_plan_view(ctx, plan) for plan in ctx.plans.list_for_subject(person)]}
    )


def _history(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    entries = []
    for alert in ctx.alerts.list_for_subject(person):
        if not alert.is_terminal:
            continue
        resolution = alert.resolution
        resolved_by = "No one"
        method = "Escalation exhausted"
        if resolution is not None:
            resolved_by = "You" if resolution.resolved_by_person_id == person else "Circle"
            plan = ctx.plans.get_plan(PlanId(alert.version.plan_id))
            circle = ctx.circles.get(CircleId(plan.circle_id)) if plan else None
            member = (
                circle.member(resolution.resolved_by_person_id)
                if circle is not None and resolution.resolved_by_person_id is not None
                else None
            )
            if member is not None:
                resolved_by = member.display_name
            method = resolution.method.value.replace("_", " ").title()
        entries.append(
            {
                "id": alert.moment_id,
                "alertId": alert.alert_id,
                "planLabel": alert.version.label or "Check-in",
                "resolvedAt": (alert.resolved_at or alert.opened_at).isoformat(),
                "resolvedBy": resolved_by,
                "method": method,
                "state": alert.state.value,
            }
        )
    return _response(200, {"history": entries})


def _plan(ctx: bootstrap.Context, plan_id: PlanId, person: PersonId) -> dict[str, Any]:
    return _response(200, _plan_view(ctx, _owned_plan(ctx, plan_id, person)))


def _test_plan(ctx: bootstrap.Context, event: dict[str, Any], plan_id: PlanId) -> dict[str, Any]:
    """Drill Mode — run the real workflow on a compressed schedule (§25)."""
    person = _caller(event)
    idempotency_key = _idempotency_key(event)
    plan = _owned_plan(ctx, plan_id, person)
    version = _version_for(ctx, plan)
    if version is None:
        return _problem(409, "This plan has no version to test", "NO_PLAN_VERSION")

    moment_id = MomentId(_stable_id(f"plans/{plan_id}/drills", idempotency_key))
    existing = ctx.moments.get(moment_id)
    if existing is not None:
        return _response(
            202,
            {
                "status": "DRILL_STARTED",
                "replayed": True,
                "moment": _moment_view(ctx, existing, version),
            },
        )

    scale = 0.02
    due_at = ctx.now() + timedelta(seconds=5)
    moment = ExpectedMoment(
        moment_id=moment_id,
        version_id=version.version_id,
        due_at=due_at,
        grace_until=due_at + timedelta(seconds=max(1, int(version.grace_seconds * scale))),
        is_drill=True,
        time_scale=scale,
    )
    ctx.moments.save(moment, subject_person_id=person)
    schedule_name = ctx.scheduler.schedule(moment) if ctx.scheduler is not None else None

    return _response(
        202,
        {
            "status": "DRILL_STARTED",
            "planId": plan.plan_id,
            "timeScale": scale,
            "scheduleName": schedule_name,
            "moment": _moment_view(ctx, moment, version),
            "message": "Drill Mode is using the real workflow on a 0.02x schedule",
        },
    )


def _circle(ctx: bootstrap.Context, person: PersonId) -> dict[str, Any]:
    circle = ctx.circles.for_owner(person)
    if circle is None:
        return _response(200, {"circleId": None, "members": []})
    return _response(
        200,
        {
            "circleId": circle.circle_id,
            "ownerDisplayName": circle.owner_display_name,
            "members": [
                {
                    "memberId": member.membership_id,
                    "displayName": member.display_name,
                    "relationship": member.relationship,
                    "role": member.role.value,
                    "priority": member.priority,
                    "status": member.status.value,
                }
                for member in circle.members
            ],
        },
    )


def _invite(ctx: bootstrap.Context, event: dict[str, Any], person: PersonId) -> dict[str, Any]:
    key = _idempotency_key(event)
    payload = _body(event)
    display_name = str(payload.get("displayName") or "").strip()
    if not display_name or len(display_name) > 60:
        raise ValueError("displayName is required and must be at most 60 characters")
    role = ResponderRole(str(payload.get("role") or "PRIMARY"))

    circle = ctx.circles.for_owner(person)
    if circle is None:
        circle = Circle(
            circle_id=CircleId(_stable_id("circles", str(person))),
            owner_person_id=person,
            owner_display_name=str(payload.get("ownerDisplayName") or "Someone")[:60],
        )

    invitation_id = InvitationId(_stable_id(f"people/{person}/invitations", key))
    repository = _invitation_repository(ctx)
    existing = repository.get(invitation_id)
    if existing is not None:
        if existing.status is InvitationStatus.PENDING and existing.expires_at <= ctx.now():
            existing = replace(
                existing,
                expires_at=ctx.now().replace(microsecond=0) + timedelta(days=7),
            )
            repository.save(existing)
        token = _invitation_token(ctx, existing)
        return _response(
            200,
            {
                **_invitation_view(ctx, existing),
                "inviteUrl": f"https://incaof.com/i/{token}",
                "replayed": True,
            },
        )

    responder_id = PersonId(_stable_id(f"invitations/{invitation_id}", "responder"))
    member = CircleMember(
        membership_id=MembershipId(_stable_id(f"invitations/{invitation_id}", "member")),
        circle_id=circle.circle_id,
        person_id=responder_id,
        role=role,
        priority=int(payload.get("priority", 1)),
        status=MemberStatus.INVITED,
        display_name=display_name,
        relationship=str(payload.get("relationship") or "").strip() or None,
    )
    circle = replace(circle, members=(*circle.members, member))

    requested_plan_ids = payload.get("planIds")
    owned_plan_ids = {plan.plan_id for plan in ctx.plans.list_for_subject(person)}
    if requested_plan_ids is None:
        plan_ids = tuple(sorted(owned_plan_ids, key=str))
    elif isinstance(requested_plan_ids, list):
        plan_ids = tuple(PlanId(str(value)) for value in requested_plan_ids)
        if any(plan_id not in owned_plan_ids for plan_id in plan_ids):
            raise NotAuthorized("plan is not reachable")
    else:
        raise ValueError("planIds must be an array")

    ctx.circles.save_circle(circle)

    invitation = CircleInvitation(
        invitation_id=invitation_id,
        circle_id=circle.circle_id,
        owner_person_id=person,
        responder_person_id=responder_id,
        membership_id=member.membership_id,
        plan_ids=plan_ids,
        expires_at=ctx.now().replace(microsecond=0) + timedelta(days=7),
    )
    repository.save(invitation)
    token = _invitation_token(ctx, invitation)
    return _response(
        201,
        {
            **_invitation_view(ctx, invitation),
            "inviteUrl": f"https://incaof.com/i/{token}",
            "delivery": "LINK_READY",
        },
    )


def _resend_invitation(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    invitation_id: InvitationId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    repository = _invitation_repository(ctx)
    invitation = repository.get(invitation_id)
    if invitation is None or invitation.owner_person_id != person:
        raise NotAuthorized("invitation is not reachable")
    if invitation.status is not InvitationStatus.PENDING:
        return _problem(409, "This invitation is already closed", "INVITATION_CLOSED")
    refreshed = replace(invitation, expires_at=ctx.now().replace(microsecond=0) + timedelta(days=7))
    repository.save(refreshed)
    token = _invitation_token(ctx, refreshed)
    return _response(
        200,
        {
            **_invitation_view(ctx, refreshed),
            "inviteUrl": f"https://incaof.com/i/{token}",
            "delivery": "LINK_READY",
        },
    )


def _remove_member(
    ctx: bootstrap.Context,
    event: dict[str, Any],
    member_id: MembershipId,
    person: PersonId,
) -> dict[str, Any]:
    _idempotency_key(event)
    circle = ctx.circles.for_owner(person)
    member = (
        next(
            (candidate for candidate in circle.members if candidate.membership_id == member_id),
            None,
        )
        if circle
        else None
    )
    if circle is None or member is None:
        raise NotAuthorized("member is not reachable")
    ctx.circles.save_circle(
        replace(
            circle,
            members=tuple(
                replace(candidate, status=MemberStatus.REMOVED)
                if candidate.membership_id == member_id
                else candidate
                for candidate in circle.members
            ),
        )
    )
    for plan in ctx.plans.list_for_subject(person):
        consent = ctx.circles.consents_for(plan.plan_id).get(member.person_id)
        if consent is not None and consent.status is ConsentStatus.ACTIVE:
            ctx.circles.save_consent(consent.withdrawn_at(ctx.now()))
    return {"statusCode": 204, "headers": {"cache-control": "no-store"}, "body": ""}


def _register_device(
    ctx: bootstrap.Context, event: dict[str, Any], person: PersonId
) -> dict[str, Any]:
    payload = _body(event)
    device_id = DeviceId(str(payload.get("deviceId") or "").strip())
    registration_token = str(payload.get("registrationToken") or "").strip()
    if not device_id or len(device_id) > 200:
        raise ValueError("deviceId is required")
    if len(registration_token) < 20 or len(registration_token) > 4096:
        raise ValueError("registrationToken is invalid")
    if ctx.devices is None:
        return _problem(503, "Push registration is not configured", "CHANNEL_UNAVAILABLE")
    ctx.devices.register(
        device_id=device_id,
        person_id=person,
        registration_token=registration_token,
        now=ctx.now(),
    )
    return _response(201, {"deviceId": device_id, "channel": "FCM", "status": "ACTIVE"})


def _remove_device(ctx: bootstrap.Context, device_id: DeviceId, person: PersonId) -> dict[str, Any]:
    if ctx.devices is None:
        return _problem(503, "Push registration is not configured", "CHANNEL_UNAVAILABLE")
    if not ctx.devices.remove(device_id=device_id, person_id=person):
        raise NotAuthorized("device is not reachable")
    return {"statusCode": 204, "headers": {"cache-control": "no-store"}, "body": ""}


def _claim(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    responder = _caller(event)
    _idempotency_key(event)
    alert, _, _ = _authorized_alert(ctx, alert_id, responder)

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
    _idempotency_key(event)
    alert, _, _ = _authorized_alert(ctx, alert_id, responder)

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
    _finish_moment(ctx, resolved)
    return _response(200, {"alertId": alert_id, "state": resolved.state.value})


def _release(ctx: bootstrap.Context, event: dict[str, Any], alert_id: AlertId) -> dict[str, Any]:
    responder = _caller(event)
    _idempotency_key(event)
    alert, _, _ = _authorized_alert(ctx, alert_id, responder)
    if alert.lease is None or alert.lease.owner_person_id != responder:
        raise NotAuthorized("only the responder holding this alert may release it")
    released = alert.responder_unable(ctx.now())
    ctx.alerts.save(released)
    ctx.audit.append(
        alert_id=alert_id,
        actor_type="RESPONDER",
        actor_id=responder,
        event_type="LEASE_RELEASED",
        at=ctx.now(),
    )
    return _response(200, _alert_view(released))


def _alert(ctx: bootstrap.Context, alert_id: AlertId, person: PersonId) -> dict[str, Any]:
    alert, _, _ = _authorized_alert(ctx, alert_id, person)
    return _response(200, _alert_view(alert))


def _timeline(ctx: bootstrap.Context, alert_id: AlertId, person: PersonId) -> dict[str, Any]:
    """What happened, in order. Nothing happens invisibly."""
    _authorized_alert(ctx, alert_id, person)
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
