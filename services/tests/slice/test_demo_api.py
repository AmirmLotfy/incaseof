from __future__ import annotations

import json
from typing import Any, cast

import pytest

from services.domain.ids import PlanId
from services.handlers import api, bootstrap
from services.tests.slice.conftest import EVENING_PLAN, Slice


def _call(
    route: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    **params: str,
) -> dict[str, Any]:
    return {
        "routeKey": route,
        "pathParameters": params,
        "headers": {"authorization": f"Bearer {token}"} if token else {},
        "body": json.dumps(body or {}),
    }


def _body(response: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(response["body"]))


def test_service_descriptor_is_public_and_side_effect_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_bootstrap() -> None:
        pytest.fail("the public descriptor must not bootstrap tenant infrastructure")

    monkeypatch.setattr(bootstrap, "build", unexpected_bootstrap)
    response = api.handler(_call("GET /"))

    assert response["statusCode"] == 200
    assert _body(response) == {
        "service": "In Case Of API",
        "status": "ok",
        "productBoundary": "Monitors expected moments, not people.",
    }


def test_public_demo_session_is_isolated_and_runs_real_plan_handlers(
    a_slice: Slice,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ICO_ENV", "demo")
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    first = api.handler(_call("POST /v1/demo/session"))
    second = api.handler(_call("POST /v1/demo/session"))
    assert first["statusCode"] == 201
    assert _body(first)["synthetic"] is True
    assert _body(first)["sessionToken"] != _body(second)["sessionToken"]

    session = _body(first)["sessionToken"]
    created = api.handler(_call("POST /v1/demo/plans", token=session, body=EVENING_PLAN))
    assert created["statusCode"] == 201
    plan_id = PlanId(str(_body(created)["planId"]))
    assert len(a_slice.ctx.circles.consents_for(plan_id)) == 2

    started = api.handler(
        _call(
            "POST /v1/demo/plans/{planId}/test",
            token=session,
            planId=plan_id,
            body={},
        )
        | {"headers": {"authorization": f"Bearer {session}", "idempotency-key": "demo-1"}}
    )
    assert started["statusCode"] == 202
    assert _body(started)["moment"]["isDrill"] is True


def test_demo_routes_fail_closed_outside_demo_and_on_bad_token(
    a_slice: Slice,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)
    monkeypatch.setenv("ICO_ENV", "dev")
    assert api.handler(_call("POST /v1/demo/session"))["statusCode"] == 404

    monkeypatch.setenv("ICO_ENV", "demo")
    response = api.handler(_call("GET /v1/demo/plans", token="not-a-token"))  # noqa: S106
    assert response["statusCode"] == 403
    assert _body(response)["title"] == "Not permitted"
