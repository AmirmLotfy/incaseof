from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any, cast

import pytest

from services.adapters import keys
from services.adapters.contact import DeliveryStatus, ProviderNotInvoked, PushSender, SmsSender
from services.adapters.queue import ActionIntent
from services.domain.plan import ResponderRole
from services.handlers import action_worker, escalation, outbox_relay

from .conftest import CIRCLE, MAYA, MONA, Slice


def pending(s: Slice, sequence: int = 4) -> ActionIntent:
    activation = s.create_plan()
    s.clock.instant = activation.moment.due_at
    s.fire_moment()
    assert s.alert_id is not None
    for _ in range(30):
        decision = escalation.decide(s.ctx, s.alert_id)
        if decision["decision"] == escalation.DISPATCH:
            escalation.dispatch(s.ctx, s.alert_id, decision["sequences"])
            for intent in s.queue.drain():
                if intent.sequence == sequence:
                    return intent
                action_worker.deliver(s.ctx, intent)
        else:
            s.advance(float(decision["seconds"]))
    raise AssertionError("requested rung was never reached")


def test_identical_sqs_payload_is_not_sent_twice(a_slice: Slice) -> None:
    intent = pending(a_slice)
    action_worker.deliver(a_slice.ctx, intent)
    action_worker.deliver(
        a_slice.ctx, ActionIntent.from_dict(__import__("json").loads(intent.to_json()))
    )
    assert len(a_slice.sender.to("Maya")) == 1


def test_concurrent_workers_obtain_one_provider_attempt(a_slice: Slice) -> None:
    intent = pending(a_slice)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: action_worker.deliver(a_slice.ctx, intent), range(2)))

    assert len(a_slice.sender.to("Maya")) == 1
    assert all(
        result.status in {DeliveryStatus.ACCEPTED, DeliveryStatus.UNKNOWN} for result in results
    )


def test_withdrawal_between_enqueue_and_delivery_blocks_contact(a_slice: Slice) -> None:
    intent = pending(a_slice)
    assert a_slice.plan_id is not None
    grants = a_slice.ctx.circles.consents_for(a_slice.plan_id)
    a_slice.ctx.circles.save_consent(grants[MAYA].withdrawn_at(a_slice.clock.now()))
    result = action_worker.deliver(a_slice.ctx, intent)
    assert result.error_code == "NOT_AUTHORIZED"
    assert not a_slice.sender.to("Maya")
    assert "CONTACT_DENIED" in a_slice.timeline()


def test_failed_queue_write_leaves_recoverable_intent(a_slice: Slice) -> None:
    activation = a_slice.create_plan()
    a_slice.clock.instant = activation.moment.due_at
    a_slice.fire_moment()
    assert a_slice.alert_id is not None
    assert a_slice.ctx.outbox is not None
    decision = escalation.decide(a_slice.ctx, a_slice.alert_id)
    while decision["decision"] == escalation.WAIT:
        a_slice.advance(float(decision["seconds"]))
        decision = escalation.decide(a_slice.ctx, a_slice.alert_id)

    class BrokenQueue:
        def enqueue(self, intent: ActionIntent) -> None:
            raise ConnectionError("queue unavailable")

    broken = replace(a_slice.ctx, queue=BrokenQueue())
    with pytest.raises(ConnectionError):
        escalation.dispatch(broken, a_slice.alert_id, decision["sequences"])
    assert a_slice.ctx.outbox.pending()
    assert outbox_relay.relay(a_slice.ctx) == 1
    a_slice.deliver_queued(replay=True)
    assert len(a_slice.sender.sent) == 1


def test_unknown_outcome_is_not_automatically_retried(a_slice: Slice) -> None:
    intent = pending(a_slice)

    class UncertainSender:
        calls = 0

        def send(self, **kwargs: Any) -> Any:
            self.calls += 1
            raise TimeoutError("acceptance may have happened")

    sender = UncertainSender()
    ctx = replace(a_slice.ctx, sender=sender)
    assert action_worker.deliver(ctx, intent).status is DeliveryStatus.UNKNOWN
    assert action_worker.deliver(ctx, intent).status is DeliveryStatus.UNKNOWN
    assert sender.calls == 1
    assert "ACTION_OUTCOME_UNKNOWN" in a_slice.timeline()


def test_process_death_after_ownership_is_reconciled_without_resend(a_slice: Slice) -> None:
    intent = pending(a_slice)
    assert a_slice.ctx.outbox is not None
    assert a_slice.alert_id is not None
    assert a_slice.ctx.outbox.begin(intent, a_slice.clock.now())
    a_slice.advance(91)
    outbox_relay.relay(a_slice.ctx)
    row = a_slice.ctx.outbox.get(intent.idempotency_key)
    assert row is not None and row["status"] == "UNKNOWN"
    action_worker.deliver(a_slice.ctx, intent)
    assert not a_slice.sender.to("Maya")


def test_stale_attempt_reconciles_even_after_alert_closes(a_slice: Slice) -> None:
    intent = pending(a_slice)
    assert a_slice.ctx.outbox is not None
    assert a_slice.ctx.outbox.begin(intent, a_slice.clock.now())
    a_slice.ctx.alerts.save(a_slice.alert.confirm_subject(a_slice.clock.now(), MONA))
    a_slice.advance(91)

    outbox_relay.relay(a_slice.ctx)

    row = a_slice.ctx.outbox.get(intent.idempotency_key)
    assert row is not None and row["status"] == "UNKNOWN"


def test_outcome_and_audit_are_one_transaction(a_slice: Slice) -> None:
    intent = pending(a_slice)
    assert a_slice.ctx.outbox is not None
    outbox = a_slice.ctx.outbox
    assert outbox.begin(intent, a_slice.clock.now())
    outbox.table.put_item(
        Item={
            "pk": keys.alert(intent.alert_id),
            "sk": f"AUDIT#{a_slice.clock.now().isoformat()}#OUTCOME#{intent.idempotency_key}",
            "eventType": "COLLISION",
        }
    )

    with pytest.raises(outbox.table.meta.client.exceptions.TransactionCanceledException):
        outbox.finish(intent.idempotency_key, "ACCEPTED", a_slice.clock.now())

    row = outbox.get(intent.idempotency_key)
    assert row is not None and row["status"] == "SENDING"


def test_pending_scan_paginates_past_one_page(a_slice: Slice) -> None:
    intent = pending(a_slice)
    assert a_slice.ctx.outbox is not None
    outbox = a_slice.ctx.outbox
    for index in range(101):
        candidate = replace(intent, idempotency_key=f"page-{index:03}")
        outbox.table.put_item(
            Item={
                **outbox._key(candidate.idempotency_key),
                "intent": json.loads(candidate.to_json()),
                "status": "PENDING",
                keys.GSI1_PK: "OUTBOX#PENDING",
                keys.GSI1_SK: candidate.idempotency_key,
            }
        )

    found = {candidate.idempotency_key for candidate in outbox.pending(limit=10)}
    assert "page-000" in found and "page-100" in found


def test_checking_race_releases_worker_ownership(a_slice: Slice) -> None:
    intent = pending(a_slice)
    open_alert = a_slice.alert
    checking = open_alert.claim(a_slice.clock.now(), MAYA)

    class RacingAlerts:
        calls = 0

        def get(self, alert_id: Any) -> Any:
            self.calls += 1
            return checking if self.calls >= 3 else open_alert

    result = action_worker.deliver(replace(a_slice.ctx, alerts=cast(Any, RacingAlerts())), intent)
    assert result.error_code == "CHECKING"
    assert a_slice.ctx.outbox is not None
    row = a_slice.ctx.outbox.get(intent.idempotency_key)
    assert row is not None and row["status"] == "PENDING"

    action_worker.deliver(a_slice.ctx, intent)
    assert len(a_slice.sender.to("Maya")) == 1


def test_pre_provider_failure_is_retried_without_unknown_outcome(a_slice: Slice) -> None:
    intent = pending(a_slice, sequence=1)

    class Endpoints:
        reveals = 0

        def for_person(self, person: str, kind: Any) -> Any:
            return type("Endpoint", (), {"is_usable": True})()

        def reveal(self, endpoint: Any) -> str:
            self.reveals += 1
            if self.reveals == 1:
                raise ConnectionError("endpoint store unavailable")
            return "test-endpoint"

    class Provider:
        calls = 0

        def publish(self, **kwargs: Any) -> dict[str, str]:
            self.calls += 1
            return {"MessageId": "accepted"}

    provider = Provider()
    ctx = replace(a_slice.ctx, sender=PushSender(sns=provider, endpoints=Endpoints()))
    with pytest.raises(ProviderNotInvoked):
        action_worker.deliver(ctx, intent)
    assert a_slice.ctx.outbox is not None
    row = a_slice.ctx.outbox.get(intent.idempotency_key)
    assert row is not None and row["status"] == "PENDING"

    assert action_worker.deliver(ctx, intent).status is DeliveryStatus.ACCEPTED
    assert provider.calls == 1


def test_role_reassignment_cannot_redirect_active_version(a_slice: Slice) -> None:
    intent = pending(a_slice)
    circle = a_slice.ctx.circles.get(CIRCLE)
    assert circle is not None
    reassigned = replace(
        circle,
        members=tuple(
            replace(
                member,
                role=(ResponderRole.BACKUP if member.person_id == MAYA else ResponderRole.PRIMARY),
            )
            for member in circle.members
        ),
    )
    a_slice.ctx.circles.save_circle(reassigned)

    result = action_worker.deliver(a_slice.ctx, intent)
    assert result.error_code == "NOT_AUTHORIZED"
    assert not a_slice.sender.to("Maya") and not a_slice.sender.to("Omar")


@pytest.mark.parametrize("sender_type,sequence", [(PushSender, 1), (SmsSender, 3)])
def test_subject_reaches_real_adapter_with_authorized_identity(
    a_slice: Slice,
    sender_type: Any,
    sequence: int,
) -> None:
    intent = pending(a_slice, sequence)

    class Endpoints:
        def __init__(self) -> None:
            self.seen: list[str] = []

        def for_person(self, person: str, kind: Any) -> Any:
            self.seen.append(person)
            return type("Endpoint", (), {"is_usable": True})()

        def reveal(self, endpoint: Any) -> str:
            return "test-endpoint"

    class Provider:
        def publish(self, **kwargs: Any) -> dict[str, str]:
            return {"MessageId": "test-provider-reference"}

    endpoints = Endpoints()
    ctx = replace(a_slice.ctx, sender=sender_type(sns=Provider(), endpoints=endpoints))
    result = action_worker.deliver(ctx, intent)
    assert result.status is DeliveryStatus.ACCEPTED
    assert endpoints.seen == [intent.recipient_id]
