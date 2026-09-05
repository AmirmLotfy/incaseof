from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, cast

import pytest

from services.adapters.memory import InMemoryProfileRepository
from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.contact_endpoint import ContactEndpoint, EndpointStatus, EndpointType
from services.domain.ids import CircleId, PersonId
from services.domain.plan import ActionType, Plan, PlanType
from services.handlers import api, bootstrap
from services.tests.domain.conftest import make_version
from services.tests.slice.conftest import Slice


class EndpointStore:
    def __init__(self) -> None:
        self.values: dict[tuple[PersonId, EndpointType], ContactEndpoint] = {}

    def verify(self, person: PersonId, endpoint_type: EndpointType) -> None:
        self.values[(person, endpoint_type)] = ContactEndpoint(
            endpoint_id=f"{person}-{endpoint_type.value}",
            person_id=person,
            endpoint_type=endpoint_type,
            ciphertext=b"sealed",
            status=EndpointStatus.VERIFIED,
        )

    def for_person(
        self, person_id: PersonId, endpoint_type: EndpointType
    ) -> ContactEndpoint | None:
        return self.values.get((person_id, endpoint_type))

    def save(self, **_kwargs: Any) -> ContactEndpoint:
        raise NotImplementedError

    def reveal(self, _endpoint: ContactEndpoint) -> str:
        raise NotImplementedError

    def delete(self, _person_id: PersonId, _endpoint_type: EndpointType, _endpoint_id: str) -> bool:
        raise NotImplementedError


def _event(route: str, person: str | None, body: dict[str, Any] | None = None) -> dict[str, Any]:
    request_context = (
        {"authorizer": {"jwt": {"claims": {"sub": person}}}} if person is not None else {}
    )
    return {
        "routeKey": route,
        "requestContext": request_context,
        "headers": {},
        "body": json.dumps(body or {}),
    }


def _body(response: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(response["body"]))


def _profile(person: PersonId, a_slice: Slice) -> Profile:
    return Profile(
        person_id=person,
        display_name="Mona",
        locale=SupportedLocale.ARABIC,
        timezone="Africa/Cairo",
        country=SupportedCountry.EGYPT,
        status=AccountStatus.ACTIVE,
        created_at=a_slice.ctx.now(),
        updated_at=a_slice.ctx.now(),
    )


def test_profile_is_authenticated_and_cannot_be_read_cross_account(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    profiles = InMemoryProfileRepository()
    a_slice.ctx = replace(a_slice.ctx, profiles=profiles, endpoints=EndpointStore())
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    assert api.handler(_event("GET /v1/profile", None))["statusCode"] == 403
    saved = api.handler(
        _event(
            "PATCH /v1/profile",
            "person-mona",
            {
                "displayName": "Mona",
                "locale": "ar",
                "timezone": "Africa/Cairo",
                "country": "EG",
            },
        )
    )
    assert saved["statusCode"] == 200
    assert _body(saved)["locale"] == "ar"
    assert "personId" not in _body(saved)

    other = api.handler(_event("GET /v1/profile", "person-other"))
    assert other["statusCode"] == 404
    assert _body(other)["reason_code"] == "PROFILE_NOT_FOUND"

    malformed = api.handler(_event("PATCH /v1/profile", "person-mona", {"displayName": None}))
    assert malformed["statusCode"] == 400


def test_readiness_fails_closed_without_exposing_endpoint_values(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    profiles = InMemoryProfileRepository({person: _profile(person, a_slice)})
    endpoints = EndpointStore()
    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    a_slice.ctx = replace(a_slice.ctx, profiles=profiles, endpoints=endpoints)
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "false")

    response = api.handler(_event("GET /v1/readiness", str(person)))
    body = _body(response)
    assert response["statusCode"] == 200
    assert body["subjectChannels"] == {"push": True, "sms": False, "call": False}
    assert body["accountReady"] is False
    assert body["reasons"] == ["ADMISSIONS_PAUSED"]
    serialized = json.dumps(body).lower()
    assert "sealed" not in serialized and "token" not in serialized


def test_production_activation_requires_admission_and_the_exact_plan_channel(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    profiles = InMemoryProfileRepository({person: _profile(person, a_slice)})
    endpoints = EndpointStore()
    a_slice.ctx = replace(a_slice.ctx, profiles=profiles, endpoints=endpoints)
    version = make_version(steps=((1, 0, ActionType.PUSH_SUBJECT, None),))
    plan = Plan(
        plan_id=version.plan_id,
        subject_person_id=person,
        circle_id=CircleId("circle-1"),
        plan_type=PlanType.ROUTINE,
    )
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "false")

    paused = api._activation_readiness_problem(a_slice.ctx, person, plan, version)
    assert paused is not None
    assert _body(paused)["reason_code"] == "ADMISSIONS_PAUSED"

    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    missing = api._activation_readiness_problem(a_slice.ctx, person, plan, version)
    assert missing is not None
    assert _body(missing)["reason_code"] == "CHANNEL_NOT_READY"

    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    assert api._activation_readiness_problem(a_slice.ctx, person, plan, version) is None
