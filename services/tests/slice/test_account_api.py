from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, cast

import pytest

from services.adapters.memory import InMemoryProfileRepository
from services.adapters.otp import PhoneVerificationRepository
from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.contact_endpoint import ContactEndpoint, EndpointStatus, EndpointType
from services.domain.ids import CircleId, PersonId
from services.domain.phone_verification import PhoneVerification, PhoneVerificationStatus
from services.domain.plan import ActionType, Plan, PlanType
from services.handlers import api, bootstrap
from services.tests.domain.conftest import make_version
from services.tests.slice.conftest import Slice

EG_TEST_NUMBER = "+20" + "10" + "00000000"


class EndpointStore:
    def __init__(self) -> None:
        self.values: dict[tuple[PersonId, EndpointType], ContactEndpoint] = {}
        self.candidates: dict[tuple[PersonId, EndpointType, str], ContactEndpoint] = {}

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

    def save(self, **kwargs: Any) -> ContactEndpoint:
        endpoint = ContactEndpoint(
            endpoint_id=kwargs["endpoint_id"],
            person_id=kwargs["person_id"],
            endpoint_type=kwargs["endpoint_type"],
            ciphertext=kwargs["value"].encode(),
            status=kwargs.get("status", EndpointStatus.UNVERIFIED),
            verified_at=kwargs.get("verified_at"),
        )
        self.values[(endpoint.person_id, endpoint.endpoint_type)] = endpoint
        return endpoint

    def reveal(self, _endpoint: ContactEndpoint) -> str:
        raise NotImplementedError

    def save_candidate(self, **kwargs: Any) -> ContactEndpoint:
        endpoint = ContactEndpoint(
            endpoint_id=kwargs["endpoint_id"],
            person_id=kwargs["person_id"],
            endpoint_type=kwargs["endpoint_type"],
            ciphertext=kwargs["value"].encode(),
            status=EndpointStatus.UNVERIFIED,
        )
        self.candidates[(endpoint.person_id, endpoint.endpoint_type, endpoint.endpoint_id)] = (
            endpoint
        )
        return endpoint

    def candidate(
        self, person_id: PersonId, endpoint_type: EndpointType, endpoint_id: str
    ) -> ContactEndpoint | None:
        return self.candidates.get((person_id, endpoint_type, endpoint_id))

    def reveal_for_verification(self, _endpoint: ContactEndpoint) -> str:
        return _endpoint.ciphertext.decode()

    def revoke(self, _person_id: PersonId, _endpoint_type: EndpointType, _endpoint_id: str) -> bool:
        current = self.values.get((_person_id, _endpoint_type))
        if current is None or current.endpoint_id != _endpoint_id:
            return False
        self.values[(_person_id, _endpoint_type)] = replace(
            current, status=EndpointStatus.REVOKED, verified_at=None
        )
        return True

    def revoke_candidate(
        self, _person_id: PersonId, _endpoint_type: EndpointType, _endpoint_id: str
    ) -> bool:
        key = (_person_id, _endpoint_type, _endpoint_id)
        candidate = self.candidates.get(key)
        if candidate is None or candidate.status is EndpointStatus.REVOKED:
            return False
        self.candidates[key] = replace(candidate, status=EndpointStatus.REVOKED)
        return True

    def delete(self, _person_id: PersonId, _endpoint_type: EndpointType, _endpoint_id: str) -> bool:
        raise NotImplementedError


class ChallengeStore(PhoneVerificationRepository):
    def __init__(self, endpoints: EndpointStore | None = None) -> None:
        self.values: dict[tuple[PersonId, str], PhoneVerification] = {}
        self.endpoints = endpoints

    def reserve(self, challenge: PhoneVerification) -> None:
        self.values[(challenge.person_id, challenge.verification_id)] = challenge

    def get(self, person_id: PersonId, verification_id: str) -> PhoneVerification | None:
        return self.values.get((person_id, verification_id))

    def mark_sent(self, challenge: PhoneVerification, at: Any) -> PhoneVerification:
        return self._save(challenge.sent(at))

    def mark_failed(self, challenge: PhoneVerification) -> PhoneVerification:
        return self._save(replace(challenge, status=PhoneVerificationStatus.FAILED))

    def record_invalid_attempt(self, challenge: PhoneVerification, at: Any) -> PhoneVerification:
        del at
        attempts = challenge.attempts + 1
        status = PhoneVerificationStatus.FAILED if attempts >= 5 else challenge.status
        return self._save(replace(challenge, attempts=attempts, status=status))

    def mark_verified(
        self, challenge: PhoneVerification, endpoint: ContactEndpoint, at: Any
    ) -> PhoneVerification | None:
        if self.endpoints is not None:
            current = self.endpoints.candidate(
                challenge.person_id, EndpointType.PHONE, challenge.endpoint_id
            )
            active = self.endpoints.for_person(challenge.person_id, EndpointType.PHONE)
            current_active_id = active.endpoint_id if active else None
            if current is None or current.status is not EndpointStatus.UNVERIFIED:
                return None
            if current_active_id != challenge.previous_endpoint_id:
                return None
            verified_endpoint = replace(endpoint, status=EndpointStatus.VERIFIED, verified_at=at)
            self.endpoints.values[(challenge.person_id, EndpointType.PHONE)] = verified_endpoint
            self.endpoints.candidates[
                (challenge.person_id, EndpointType.PHONE, challenge.endpoint_id)
            ] = verified_endpoint
        return self._save(challenge.verified(at))

    def _save(self, challenge: PhoneVerification) -> PhoneVerification:
        self.values[(challenge.person_id, challenge.verification_id)] = challenge
        return challenge


class Otp:
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid
        self.sent: list[tuple[str, str]] = []

    def send(self, *, destination: str, reference: str) -> str:
        self.sent.append((destination, reference))
        return "provider-message"

    def verify(self, *, destination: str, reference: str, otp: str) -> bool:
        del destination, reference, otp
        return self.valid


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


def test_changing_country_revokes_the_previously_verified_phone(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    endpoints = EndpointStore()
    endpoints.verify(person, EndpointType.PHONE)
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    response = api.handler(_event("PATCH /v1/profile", str(person), {"country": "US"}))

    assert response["statusCode"] == 200
    phone = endpoints.for_person(person, EndpointType.PHONE)
    assert phone is not None and phone.status is EndpointStatus.REVOKED


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


def test_phone_verification_requires_provider_before_storing_any_number(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    endpoints = EndpointStore()
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
        phone_verifications=ChallengeStore(),
        otp_provider=None,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    response = api.handler(
        _event("POST /v1/phone-verifications", str(person), {"phoneNumber": EG_TEST_NUMBER})
    )

    assert response["statusCode"] == 503
    assert endpoints.values == {}


def test_phone_verification_is_tenant_scoped_and_never_returns_the_number(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    endpoints = EndpointStore()
    endpoints.verify(person, EndpointType.PHONE)
    previous = endpoints.for_person(person, EndpointType.PHONE)
    assert previous is not None
    challenges = ChallengeStore(endpoints)
    provider = Otp()
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
        phone_verifications=challenges,
        otp_provider=provider,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    started = api.handler(
        _event("POST /v1/phone-verifications", str(person), {"phoneNumber": EG_TEST_NUMBER})
    )
    started_body = _body(started)
    verification_id = str(started_body["verificationId"])
    assert started["statusCode"] == 202
    assert started_body["status"] == "SENT"
    assert EG_TEST_NUMBER not in started["body"]
    assert len(provider.sent) == 1
    assert endpoints.for_person(person, EndpointType.PHONE) == previous

    cross_account = api.handler(
        _event(
            "POST /v1/phone-verifications/{verificationId}/confirm",
            "person-other",
            {"otp": "123456"},
        )
        | {"pathParameters": {"verificationId": verification_id}}
    )
    assert cross_account["statusCode"] == 404

    confirmed = api.handler(
        _event(
            "POST /v1/phone-verifications/{verificationId}/confirm",
            str(person),
            {"otp": "123456"},
        )
        | {"pathParameters": {"verificationId": verification_id}}
    )
    assert confirmed["statusCode"] == 200
    assert _body(confirmed)["phoneVerified"] is True
    endpoint = endpoints.for_person(person, EndpointType.PHONE)
    assert endpoint is not None and endpoint.is_usable
    assert endpoint.endpoint_id != previous.endpoint_id

    revoked = api.handler(_event("DELETE /v1/phone", str(person)))
    assert revoked["statusCode"] == 200
    endpoint = endpoints.for_person(person, EndpointType.PHONE)
    assert endpoint is not None and endpoint.status is EndpointStatus.REVOKED
    assert (
        api.handler(
            _event(
                "POST /v1/phone-verifications/{verificationId}/confirm",
                str(person),
                {"otp": "123456"},
            )
            | {"pathParameters": {"verificationId": verification_id}}
        )["statusCode"]
        == 409
    )


def test_phone_verification_rejects_country_mismatch_before_provider_call(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    provider = Otp()
    endpoints = EndpointStore()
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
        phone_verifications=ChallengeStore(endpoints),
        otp_provider=provider,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    response = api.handler(
        _event("POST /v1/phone-verifications", str(person), {"phoneNumber": "+12025550123"})
    )
    assert response["statusCode"] == 422
    assert provider.sent == []


def test_five_invalid_codes_revoke_the_pending_phone(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    endpoints = EndpointStore()
    provider = Otp(valid=False)
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
        phone_verifications=ChallengeStore(endpoints),
        otp_provider=provider,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)
    started = api.handler(
        _event("POST /v1/phone-verifications", str(person), {"phoneNumber": EG_TEST_NUMBER})
    )
    verification_id = str(_body(started)["verificationId"])
    event = _event(
        "POST /v1/phone-verifications/{verificationId}/confirm",
        str(person),
        {"otp": "123456"},
    ) | {"pathParameters": {"verificationId": verification_id}}

    assert [api.handler(event)["statusCode"] for _ in range(5)] == [422] * 5
    candidate = next(iter(endpoints.candidates.values()))
    assert candidate.status is EndpointStatus.REVOKED
    assert endpoints.for_person(person, EndpointType.PHONE) is None
    assert api.handler(event)["statusCode"] == 409
