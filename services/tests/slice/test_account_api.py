from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, cast

import pytest

from services.adapters.account_deletion import DynamoAccountDeletionRepository
from services.adapters.memory import InMemoryPlanCapacityRepository, InMemoryProfileRepository
from services.adapters.otp import PhoneVerificationRepository
from services.adapters.profile import DynamoProfileRepository
from services.domain.account import (
    AccountStatus,
    Profile,
    SupportedCountry,
    SupportedLocale,
)
from services.domain.contact_endpoint import ContactEndpoint, EndpointStatus, EndpointType
from services.domain.ids import CircleId, PersonId, PlanId
from services.domain.phone_verification import PhoneVerification, PhoneVerificationStatus
from services.domain.plan import ActionType, Plan, PlanType, Trigger, TriggerKind
from services.handlers import api, bootstrap
from services.tests.domain.conftest import make_version
from services.tests.slice.conftest import EVENING_PLAN, MONA, Slice

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


def test_account_deletion_is_confirmed_idempotent_and_closes_every_normal_route(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    table = cast(Any, a_slice.ctx.plans).table
    profiles = DynamoProfileRepository(table)
    profiles.save(_profile(person, a_slice))
    deletions = DynamoAccountDeletionRepository(table)
    a_slice.ctx = replace(a_slice.ctx, profiles=profiles, account_deletions=deletions)
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)

    refused = api.handler(_event("DELETE /v1/account", str(person), {"confirmation": "delete"}))
    assert refused["statusCode"] == 422
    assert _body(refused)["reason_code"] == "DELETION_CONFIRMATION_REQUIRED"

    accepted = api.handler(_event("DELETE /v1/account", str(person), {"confirmation": "DELETE"}))
    replay = api.handler(_event("DELETE /v1/account", str(person), {"confirmation": "DELETE"}))
    assert accepted["statusCode"] == replay["statusCode"] == 202
    assert _body(accepted)["requestId"] == _body(replay)["requestId"]
    assert _body(accepted)["monitoringStopped"] is True
    profile = profiles.get(person)
    assert profile is not None
    assert profile.status is AccountStatus.DELETION_PENDING

    status = api.handler(_event("GET /v1/account/deletion", str(person)))
    assert status["statusCode"] == 200
    assert _body(status)["status"] == "PENDING"
    closed = api.handler(_event("GET /v1/profile", str(person)))
    assert closed["statusCode"] == 410
    assert _body(closed)["reason_code"] == "ACCOUNT_DELETION_PENDING"


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
    assert body["globalCapacityAvailable"] is False
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
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=profiles,
        endpoints=endpoints,
        capacity=InMemoryPlanCapacityRepository(),
    )
    version = make_version(steps=((1, 0, ActionType.PUSH_SUBJECT, None),))
    plan = Plan(
        plan_id=version.plan_id,
        subject_person_id=person,
        circle_id=CircleId("circle-1"),
        plan_type=PlanType.ROUTINE,
    )
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "false")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_GLOBAL", "10")

    paused = api._activation_readiness_problem(a_slice.ctx, person, plan, version)
    assert paused is not None
    assert _body(paused)["reason_code"] == "ADMISSIONS_PAUSED"

    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    missing = api._activation_readiness_problem(a_slice.ctx, person, plan, version)
    assert missing is not None
    assert _body(missing)["reason_code"] == "CHANNEL_NOT_READY"

    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    assert api._activation_readiness_problem(a_slice.ctx, person, plan, version) is None


def test_production_activation_fails_closed_when_capacity_storage_is_unavailable(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=EndpointStore(),
        capacity=None,
    )
    version = make_version(steps=((1, 0, ActionType.PUSH_SUBJECT, None),))
    plan = Plan(
        plan_id=version.plan_id,
        subject_person_id=person,
        circle_id=CircleId("circle-1"),
        plan_type=PlanType.ROUTINE,
    )
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_GLOBAL", "10")

    response = api._activation_readiness_problem(a_slice.ctx, person, plan, version)

    assert response is not None and response["statusCode"] == 503
    assert _body(response)["reason_code"] == "CAPACITY_UNAVAILABLE"


def test_production_capacity_is_reserved_once_and_released_across_pause_resume(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    profiles = InMemoryProfileRepository({person: _profile(person, a_slice)})
    endpoints = EndpointStore()
    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    capacity = InMemoryPlanCapacityRepository()
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=profiles,
        endpoints=endpoints,
        capacity=capacity,
    )
    a_slice.given_a_circle(consent_for=())
    version = replace(
        make_version(steps=((1, 0, ActionType.PUSH_SUBJECT, None),)),
        trigger=Trigger(kind=TriggerKind.RECURRING, time_of_day="21:00"),
    )
    plan = Plan(
        plan_id=version.plan_id,
        subject_person_id=person,
        circle_id=CircleId("circle-1"),
        plan_type=PlanType.ROUTINE,
    )
    a_slice.ctx.plans.save_plan(plan)
    a_slice.ctx.plans.save_version(version)
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_PER_ACCOUNT", "1")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_GLOBAL", "1")
    event = {"headers": {"Idempotency-Key": "capacity-lifecycle"}}

    activated = api._activate_plan(a_slice.ctx, event, plan.plan_id, person)
    replayed = api._activate_plan(a_slice.ctx, event, plan.plan_id, person)

    assert activated["statusCode"] == replayed["statusCode"] == 200
    assert _body(replayed)["replayed"] is True
    assert capacity.usage(person).account_reserved == 1
    assert capacity.usage(person).global_reserved == 1

    paused = api._pause_plan(a_slice.ctx, event, plan.plan_id, person)
    assert paused["statusCode"] == 200
    assert capacity.usage(person).global_reserved == 0

    endpoint = endpoints.for_person(person, EndpointType.PUSH_TOKEN)
    assert endpoint is not None
    endpoints.revoke(person, EndpointType.PUSH_TOKEN, endpoint.endpoint_id)
    refused = api._resume_plan(a_slice.ctx, event, plan.plan_id, person)
    assert refused["statusCode"] == 409
    assert _body(refused)["reason_code"] == "CHANNEL_NOT_READY"
    assert capacity.usage(person).global_reserved == 0

    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    resumed = api._resume_plan(a_slice.ctx, event, plan.plan_id, person)
    assert resumed["statusCode"] == 200
    assert capacity.usage(person).global_reserved == 1


def test_production_readiness_reports_global_capacity_exhaustion(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    capacity = InMemoryPlanCapacityRepository()
    capacity.reserve(
        person_id=PersonId("person-maya"),
        plan_id=PlanId("plan-maya"),
        account_limit=1,
        global_limit=1,
        at=a_slice.ctx.now(),
    )
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=EndpointStore(),
        capacity=capacity,
    )
    monkeypatch.setattr(bootstrap, "build", lambda: a_slice.ctx)
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_GLOBAL", "1")

    response = api.handler(_event("GET /v1/readiness", str(person)))
    body = _body(response)

    assert response["statusCode"] == 200
    assert body["globalCapacityAvailable"] is False
    assert "GLOBAL_CAPACITY_EXHAUSTED" in body["reasons"]
    assert body["accountReady"] is False


def test_one_time_completion_releases_capacity_and_deactivates_the_plan(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = PersonId("person-mona")
    endpoints = EndpointStore()
    endpoints.verify(person, EndpointType.PUSH_TOKEN)
    capacity = InMemoryPlanCapacityRepository()
    a_slice.ctx = replace(
        a_slice.ctx,
        profiles=InMemoryProfileRepository({person: _profile(person, a_slice)}),
        endpoints=endpoints,
        capacity=capacity,
    )
    a_slice.given_a_circle(consent_for=())
    version = make_version(steps=((1, 0, ActionType.PUSH_SUBJECT, None),))
    plan = Plan(
        plan_id=version.plan_id,
        subject_person_id=person,
        circle_id=CircleId("circle-1"),
        plan_type=PlanType.ROUTINE,
    )
    a_slice.ctx.plans.save_plan(plan)
    a_slice.ctx.plans.save_version(version)
    monkeypatch.setenv("ICO_ENV", "prod")
    monkeypatch.setenv("ICO_ADMISSIONS_OPEN", "true")
    monkeypatch.setenv("ICO_MAX_ACTIVE_PLANS_GLOBAL", "1")
    event = {"headers": {"Idempotency-Key": "one-time-completion"}}
    activated = api._activate_plan(a_slice.ctx, event, plan.plan_id, person)
    moment_id = _body(activated)["moment"]["momentId"]

    api._finish_moment(a_slice.ctx, type("ResolvedAlert", (), {"moment_id": moment_id})())

    finished = a_slice.ctx.plans.get_plan(plan.plan_id)
    assert finished is not None and finished.active_version_id is None
    assert capacity.usage(person).account_reserved == 0
    assert capacity.usage(person).global_reserved == 0


def test_one_time_cancellation_releases_capacity_and_deactivates_the_plan(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = MONA
    capacity = InMemoryPlanCapacityRepository()
    a_slice.ctx = replace(a_slice.ctx, capacity=capacity)
    one_time = {
        **EVENING_PLAN,
        "trigger": {"kind": "ONE_TIME", "dueAt": "2026-08-26T21:00:00+02:00"},
    }
    activation = a_slice.create_plan(one_time)
    capacity.reserve(
        person_id=person,
        plan_id=activation.plan.plan_id,
        account_limit=3,
        global_limit=1,
        at=a_slice.ctx.now(),
    )
    monkeypatch.setenv("ICO_ENV", "prod")

    response = api._cancel_moment(
        a_slice.ctx,
        {"headers": {"Idempotency-Key": "cancel-one-time"}},
        activation.moment.moment_id,
        person,
    )

    finished = a_slice.ctx.plans.get_plan(activation.plan.plan_id)
    assert response["statusCode"] == 200
    assert finished is not None and finished.active_version_id is None
    assert capacity.usage(person).account_reserved == 0
    assert capacity.usage(person).global_reserved == 0


def test_recurring_cancellation_keeps_capacity_and_creates_one_successor(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = MONA
    capacity = InMemoryPlanCapacityRepository()
    a_slice.ctx = replace(a_slice.ctx, capacity=capacity)
    activation = a_slice.create_plan()
    capacity.reserve(
        person_id=person,
        plan_id=activation.plan.plan_id,
        account_limit=3,
        global_limit=1,
        at=a_slice.ctx.now(),
    )
    monkeypatch.setenv("ICO_ENV", "prod")
    event = {"headers": {"Idempotency-Key": "cancel-recurring"}}

    first = api._cancel_moment(a_slice.ctx, event, activation.moment.moment_id, person)
    replay = api._cancel_moment(a_slice.ctx, event, activation.moment.moment_id, person)

    outstanding = a_slice.ctx.moments.outstanding_for_subject(person)
    current = a_slice.ctx.plans.get_plan(activation.plan.plan_id)
    assert first["statusCode"] == 200
    assert _body(replay)["replayed"] is True
    assert len(outstanding) == 1
    assert outstanding[0].due_at > activation.moment.due_at
    assert current is not None and current.is_active
    assert capacity.usage(person).global_reserved == 1


def test_bounded_recurring_cancellation_releases_capacity_at_the_end(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = MONA
    capacity = InMemoryPlanCapacityRepository()
    a_slice.ctx = replace(a_slice.ctx, capacity=capacity)
    bounded = {
        **EVENING_PLAN,
        "trigger": {
            "kind": "RECURRING",
            "timeOfDay": "21:00",
            "untilAt": "2026-08-26T21:00:00+02:00",
        },
    }
    activation = a_slice.create_plan(bounded)
    capacity.reserve(
        person_id=person,
        plan_id=activation.plan.plan_id,
        account_limit=3,
        global_limit=1,
        at=a_slice.ctx.now(),
    )
    monkeypatch.setenv("ICO_ENV", "prod")

    api._cancel_moment(
        a_slice.ctx,
        {"headers": {"Idempotency-Key": "cancel-bounded"}},
        activation.moment.moment_id,
        person,
    )

    finished = a_slice.ctx.plans.get_plan(activation.plan.plan_id)
    assert finished is not None and finished.active_version_id is None
    assert a_slice.ctx.moments.outstanding_for_subject(person) == ()
    assert capacity.usage(person).global_reserved == 0


def test_cancellation_replay_recovers_after_scheduler_failure(a_slice: Slice) -> None:
    class FailOnceScheduler:
        def __init__(self) -> None:
            self.failed = False
            self.scheduled: list[str] = []

        def schedule(self, moment: Any) -> str:
            if not self.failed:
                self.failed = True
                raise RuntimeError("scheduler unavailable")
            self.scheduled.append(str(moment.moment_id))
            return f"moment-{moment.moment_id}"

        def cancel(self, moment_id: Any) -> None:
            del moment_id

    activation = a_slice.create_plan()
    scheduler = FailOnceScheduler()
    a_slice.ctx = replace(a_slice.ctx, scheduler=scheduler)
    event = {"headers": {"Idempotency-Key": "cancel-recovery"}}

    with pytest.raises(RuntimeError, match="scheduler unavailable"):
        api._cancel_moment(a_slice.ctx, event, activation.moment.moment_id, MONA)

    cancelled = a_slice.ctx.moments.get(activation.moment.moment_id)
    assert cancelled is not None and cancelled.status.value == "CANCELLED"
    saved = a_slice.ctx.moments.outstanding_for_subject(MONA)
    assert len(saved) == 1

    replay = api._cancel_moment(a_slice.ctx, event, activation.moment.moment_id, MONA)

    assert _body(replay)["replayed"] is True
    recovered = a_slice.ctx.moments.outstanding_for_subject(MONA)
    assert [moment.moment_id for moment in recovered] == [saved[0].moment_id]
    assert scheduler.scheduled == [str(saved[0].moment_id)]


def test_terminal_replay_finishes_capacity_release_after_partial_failure(
    a_slice: Slice, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailOnceCapacity(InMemoryPlanCapacityRepository):
        def __init__(self) -> None:
            super().__init__()
            self.failed = False

        def release(self, **kwargs: Any) -> None:
            if not self.failed:
                self.failed = True
                raise RuntimeError("capacity unavailable")
            super().release(**kwargs)

    capacity = FailOnceCapacity()
    a_slice.ctx = replace(a_slice.ctx, capacity=capacity)
    one_time = {
        **EVENING_PLAN,
        "trigger": {"kind": "ONE_TIME", "dueAt": "2026-08-26T21:00:00+02:00"},
    }
    activation = a_slice.create_plan(one_time)
    capacity.reserve(
        person_id=MONA,
        plan_id=activation.plan.plan_id,
        account_limit=3,
        global_limit=1,
        at=a_slice.ctx.now(),
    )
    monkeypatch.setenv("ICO_ENV", "prod")
    resolved = type("ResolvedAlert", (), {"moment_id": activation.moment.moment_id})()

    with pytest.raises(RuntimeError, match="capacity unavailable"):
        api._finish_moment(a_slice.ctx, resolved)

    inactive = a_slice.ctx.plans.get_plan(activation.plan.plan_id)
    assert inactive is not None and inactive.active_version_id is None
    assert capacity.usage(MONA).global_reserved == 1

    api._finish_moment(a_slice.ctx, resolved)

    assert capacity.usage(MONA).global_reserved == 0


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
