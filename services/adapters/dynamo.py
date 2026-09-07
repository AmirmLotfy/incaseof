"""DynamoDB adapters.

Implements the Phase 1 ports against a single table. Three operations here are the ones
that make invariants true under concurrency, and each is a **conditional write** rather
than a read followed by a write -- because the read-then-write version is a race that
looks correct in every test that runs one thing at a time:

* :meth:`DynamoAlertRepository.open_for_moment` -- invariant 1, one Moment at most one Alert.
* :class:`DynamoOutbox` -- action ownership and outcomes are durable and conditional.
* :meth:`DynamoAlertRepository.save` -- optimistic locking, so two responders claiming an
  Alert at the same instant cannot both succeed by overwriting each other.

Optimistic locking uses a ``revision`` attribute the domain knows nothing about. The
repository remembers the revision it last read, per instance, and conditions the write on
it. Threading a revision through the domain would put a persistence concern into the
safety core, which is exactly what the ports exist to prevent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from botocore.exceptions import ClientError

from services.adapters import codec, keys
from services.domain.agent_decision import AgentDecision
from services.domain.alert import Alert
from services.domain.circle import Circle, ConsentGrant
from services.domain.idempotency import IdempotencyKey
from services.domain.ids import (
    AlertId,
    CircleId,
    InvitationId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
)
from services.domain.invitation import CircleInvitation
from services.domain.moment import ExpectedMoment, MomentStatus
from services.domain.plan import Plan, PlanVersion

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_dynamodb.service_resource import Table
else:
    Table = Any

CONDITION_FAILED = "ConditionalCheckFailedException"
TRANSACTION_CANCELLED = "TransactionCanceledException"

# A standalone conditional write raises "ConditionalCheckFailedException"; the same failure
# inside a transaction is reported in CancellationReasons as "ConditionalCheckFailed",
# without the suffix. Matching only one spelling turns an expected duplicate delivery into
# an unhandled exception.
CONDITION_FAILED_CODES = frozenset({CONDITION_FAILED, "ConditionalCheckFailed"})


class ConcurrentModification(RuntimeError):
    """Someone else wrote this item since it was read.

    Not an error condition to swallow: for an Alert it usually means two responders acted
    at once, and the correct response is to re-read and re-decide, not to overwrite.
    """


def _doc(item: Mapping[str, Any]) -> dict[str, Any]:
    """Read our own nested document out of an item.

    boto3-stubs types every attribute as the full DynamoDB value union, which is correct:
    the service really can return any of those. We wrote these items ourselves, so
    narrowing here states what our own schema guarantees rather than papering over an
    unknown. A malformed item raises loudly at the codec instead of silently degrading.
    """
    return cast("dict[str, Any]", item["data"])


def _text(item: Mapping[str, Any], attribute: str) -> str:
    return cast("str", item[attribute])


def _revision(item: Mapping[str, Any]) -> int:
    return int(cast("Decimal | int", item.get("revision", 0)))


def _is(error: ClientError, code: str) -> bool:
    return bool(error.response.get("Error", {}).get("Code") == code)


def _cancelled_by_condition(error: ClientError) -> bool:
    """A transaction cancelled specifically because a condition failed."""
    if not _is(error, TRANSACTION_CANCELLED):
        return False
    reasons = error.response.get("CancellationReasons") or []
    return any(r.get("Code") in CONDITION_FAILED_CODES for r in reasons)


@dataclass
class DynamoPlanRepository:
    table: Table

    def get_plan(self, plan_id: PlanId) -> Plan | None:
        item = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.plan(plan_id), "sk": keys.META}
        ).get("Item")
        return codec.plan_from(_doc(item)) if item else None

    def get_version(self, version_id: PlanVersionId) -> PlanVersion | None:
        item = self.table.get_item(
            ConsistentRead=True,
            Key={"pk": keys.version_pointer(version_id), "sk": keys.META},
        ).get("Item")
        return codec.version_from(_doc(item)) if item else None

    def latest_version(self, plan_id: PlanId) -> PlanVersion | None:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.plan(plan_id))
            & Key("sk").begins_with("VERSION#"),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        return codec.version_from(_doc(items[0])) if items else None

    def save_plan(self, plan: Plan) -> None:
        self.table.put_item(
            Item={
                "pk": keys.plan(plan.plan_id),
                "sk": keys.META,
                "data": codec.plan_to(plan),
                keys.GSI2_PK: keys.owner_partition(plan.subject_person_id),
                keys.GSI2_SK: keys.owner_plan(plan.plan_id),
            }
        )

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Plan, ...]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            IndexName=keys.GSI2,
            KeyConditionExpression=Key(keys.GSI2_PK).eq(keys.owner_partition(subject_person_id))
            & Key(keys.GSI2_SK).begins_with("PLAN#"),
        )
        return tuple(codec.plan_from(_doc(item)) for item in response.get("Items", []))

    def save_version(self, version: PlanVersion) -> None:
        """Write a version once. Re-saving is refused, not merged.

        Versions are immutable by design: a live Alert reads its ladder from the version it
        pinned, so a version that could change would change what a running Alert does.
        """
        data = codec.version_to(version)
        try:
            self.table.put_item(
                Item={
                    "pk": keys.version_pointer(version.version_id),
                    "sk": keys.META,
                    "data": data,
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as error:
            if _is(error, CONDITION_FAILED):
                raise ValueError(
                    f"version {version.version_id} already exists; versions are immutable"
                ) from error
            raise

        # Second copy under the plan partition, so "list this plan's versions" is one query.
        self.table.put_item(
            Item={
                "pk": keys.plan(version.plan_id),
                "sk": keys.version_sk(version.version_number),
                "data": data,
            }
        )

    def activate(
        self,
        plan_id: PlanId,
        version_id: PlanVersionId,
        at: datetime,
        bindings: dict[str, str] | None = None,
    ) -> Plan:
        from dataclasses import replace

        version = self.get_version(version_id)
        if version is None:
            raise ValueError(f"no such version {version_id}")
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"no such plan {plan_id}")
        if version.plan_id != plan_id:
            raise ValueError("version does not belong to the requested plan")
        activated_version = replace(
            version,
            activated_at=version.activated_at or at,
            responder_bindings=version.responder_bindings
            if version.activated_at
            else (bindings or {}),
        )
        activated = replace(plan, active_version_id=version_id, paused=False)
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": {"pk": keys.version_pointer(version_id), "sk": keys.META},
                            "UpdateExpression": "SET #data = :after",
                            "ConditionExpression": "#data = :before",
                            "ExpressionAttributeNames": {"#data": "data"},
                            "ExpressionAttributeValues": {
                                ":before": codec.version_to(version),
                                ":after": codec.version_to(activated_version),
                            },
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": {
                                "pk": keys.plan(plan_id),
                                "sk": keys.version_sk(version.version_number),
                            },
                            "UpdateExpression": "SET #data = :after",
                            "ConditionExpression": "#data = :before",
                            "ExpressionAttributeNames": {"#data": "data"},
                            "ExpressionAttributeValues": {
                                ":before": codec.version_to(version),
                                ":after": codec.version_to(activated_version),
                            },
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.table.name,
                            "Key": {"pk": keys.plan(plan_id), "sk": keys.META},
                            "UpdateExpression": "SET #data = :after",
                            "ConditionExpression": "#data = :before",
                            "ExpressionAttributeNames": {"#data": "data"},
                            "ExpressionAttributeValues": {
                                ":before": codec.plan_to(plan),
                                ":after": codec.plan_to(activated),
                            },
                        }
                    },
                ]
            )
        except ClientError as error:
            if _is(error, TRANSACTION_CANCELLED):
                raise ConcurrentModification(
                    "plan or version changed during activation; re-read before retrying"
                ) from error
            raise
        return activated


@dataclass
class DynamoMomentRepository:
    table: Table

    def get(self, moment_id: MomentId) -> ExpectedMoment | None:
        item = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.moment(moment_id), "sk": keys.META}
        ).get("Item")
        return codec.moment_from(_doc(item)) if item else None

    def save(
        self,
        moment: ExpectedMoment,
        *,
        subject_person_id: PersonId | None = None,
    ) -> None:
        if subject_person_id is None:
            existing = self.table.get_item(
                Key={"pk": keys.moment(moment.moment_id), "sk": keys.META}
            ).get("Item")
            if existing:
                owner = existing.get(keys.GSI2_PK)
                if isinstance(owner, str) and owner.startswith("PERSON#"):
                    subject_person_id = PersonId(owner.removeprefix("PERSON#"))
        item: dict[str, Any] = {
            "pk": keys.moment(moment.moment_id),
            "sk": keys.META,
            "data": codec.moment_to(moment),
        }
        # Sparse index: only outstanding Moments are indexed, so the sweeper's query
        # returns work rather than history, and the index shrinks as things resolve.
        if moment.status in {MomentStatus.SCHEDULED, MomentStatus.DUE}:
            item[keys.GSI1_PK] = keys.due_bucket(moment.due_at)
            item[keys.GSI1_SK] = keys.due_sort(moment.due_at, moment.moment_id)
        if subject_person_id is not None:
            item[keys.GSI2_PK] = keys.owner_partition(subject_person_id)
            item[keys.GSI2_SK] = keys.owner_moment(moment.due_at, moment.moment_id)
        self.table.put_item(Item=item)

    def next_for_subject(
        self, subject_person_id: PersonId, instant: datetime
    ) -> ExpectedMoment | None:
        del instant  # overdue moments are intentionally returned before future moments
        moments = self.outstanding_for_subject(subject_person_id)
        return min(moments, key=lambda moment: moment.due_at, default=None)

    def outstanding_for_subject(self, subject_person_id: PersonId) -> tuple[ExpectedMoment, ...]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            IndexName=keys.GSI2,
            KeyConditionExpression=Key(keys.GSI2_PK).eq(keys.owner_partition(subject_person_id))
            & Key(keys.GSI2_SK).begins_with("MOMENT#"),
        )
        decoded = tuple(codec.moment_from(_doc(item)) for item in response.get("Items", []))
        return tuple(
            moment
            for moment in sorted(decoded, key=lambda candidate: candidate.due_at)
            if moment.status in {MomentStatus.SCHEDULED, MomentStatus.DUE}
        )

    def due_before(self, instant: datetime) -> tuple[ExpectedMoment, ...]:
        """Reconciliation sweep: outstanding Moments whose time has passed.

        EventBridge Scheduler owns the timers; this is the backstop for a schedule that
        never delivered. Queries today's and yesterday's buckets, which covers any
        realistic delivery failure without scanning the table.
        """
        from datetime import timedelta

        from boto3.dynamodb.conditions import Key

        found: list[ExpectedMoment] = []
        for day_offset in (0, -1):
            bucket = keys.due_bucket(instant + timedelta(days=day_offset))
            response = self.table.query(
                IndexName=keys.GSI1,
                KeyConditionExpression=Key(keys.GSI1_PK).eq(bucket)
                & Key(keys.GSI1_SK).lte(f"{instant.isoformat()}#￿"),
            )
            found += [codec.moment_from(_doc(i)) for i in response.get("Items", [])]
        return tuple(sorted(found, key=lambda m: m.due_at))


@dataclass
class DynamoAlertRepository:
    table: Table
    _revisions: dict[AlertId, int] = field(default_factory=dict)
    _owners: dict[AlertId, PersonId] = field(default_factory=dict)

    def get(self, alert_id: AlertId) -> Alert | None:
        item = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.alert(alert_id), "sk": keys.META}
        ).get("Item")
        if not item:
            return None
        alert = codec.alert_from(_doc(item))
        self._revisions[alert.alert_id] = _revision(item)
        owner = item.get(keys.GSI2_PK)
        if isinstance(owner, str) and owner.startswith("PERSON#"):
            self._owners[alert.alert_id] = PersonId(owner.removeprefix("PERSON#"))
        return alert

    def list_for_subject(self, subject_person_id: PersonId) -> tuple[Alert, ...]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            IndexName=keys.GSI2,
            KeyConditionExpression=Key(keys.GSI2_PK).eq(keys.owner_partition(subject_person_id))
            & Key(keys.GSI2_SK).begins_with("ALERT#"),
            ScanIndexForward=False,
        )
        alerts = []
        for item in response.get("Items", []):
            alert = codec.alert_from(_doc(item))
            self._revisions[alert.alert_id] = _revision(item)
            self._owners[alert.alert_id] = subject_person_id
            alerts.append(alert)
        return tuple(alerts)

    def save(self, alert: Alert) -> None:
        """Write, conditional on nobody else having written since we read.

        Two responders tapping "I'm checking" in the same second both pass the domain's
        lease guard, because each read an Alert with no owner. This is what stops the
        second write from silently overwriting the first.
        """
        expected = self._revisions.get(alert.alert_id, 0)
        item: dict[str, Any] = {
            "pk": keys.alert(alert.alert_id),
            "sk": keys.META,
            "data": codec.alert_to(alert),
            "revision": expected + 1,
        }
        owner = self._owners.get(alert.alert_id)
        if owner is not None:
            item[keys.GSI2_PK] = keys.owner_partition(owner)
            item[keys.GSI2_SK] = keys.owner_alert(alert.opened_at, alert.alert_id)
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression=("attribute_not_exists(pk) OR revision = :expected"),
                ExpressionAttributeValues={":expected": Decimal(expected)},
            )
        except ClientError as error:
            if _is(error, CONDITION_FAILED):
                raise ConcurrentModification(
                    f"alert {alert.alert_id} changed since it was read; re-read and retry"
                ) from error
            raise
        self._revisions[alert.alert_id] = expected + 1

    def open_for_moment(
        self,
        alert: Alert,
        *,
        subject_person_id: PersonId | None = None,
    ) -> Alert:
        """Open an Alert for a Moment, conditional on none existing.

        A single transaction writes the Alert and a lock keyed on the Moment. A duplicate
        scheduler delivery loses the condition and gets back the Alert that already exists,
        which is normal operation rather than an error -- invariant 1.
        """
        try:
            # ``table.meta.client`` carries boto3's DynamoDB document transform, so items
            # go in as plain Python values. Hand-serialising them here would serialise
            # twice and fail deep inside the transaction with an opaque TypeError.
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": keys.moment(alert.moment_id),
                                "sk": keys.ALERT_LOCK,
                                "alertId": alert.alert_id,
                            },
                            "ConditionExpression": "attribute_not_exists(pk)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {
                                "pk": keys.alert(alert.alert_id),
                                "sk": keys.META,
                                "data": codec.alert_to(alert),
                                "revision": 1,
                                **(
                                    {
                                        keys.GSI2_PK: keys.owner_partition(subject_person_id),
                                        keys.GSI2_SK: keys.owner_alert(
                                            alert.opened_at, alert.alert_id
                                        ),
                                    }
                                    if subject_person_id is not None
                                    else {}
                                ),
                            },
                        }
                    },
                ]
            )
        except ClientError as error:
            if _cancelled_by_condition(error):
                existing = self.alert_for_moment(alert.moment_id)
                if existing is not None:
                    return existing
            raise
        self._revisions[alert.alert_id] = 1
        if subject_person_id is not None:
            self._owners[alert.alert_id] = subject_person_id
        return alert

    def alert_for_moment(self, moment_id: MomentId) -> Alert | None:
        """The Alert opened for this Moment, if one was.

        A real access pattern, not an internal detail: the API resolves a Moment the
        subject is confirming into the Alert that is escalating about them."""
        lock = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.moment(moment_id), "sk": keys.ALERT_LOCK}
        ).get("Item")
        if not lock:
            return None
        return self.get(AlertId(_text(lock, "alertId")))


@dataclass
class DynamoCircleRepository:
    table: Table

    def get(self, circle_id: CircleId) -> Circle | None:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            ConsistentRead=True, KeyConditionExpression=Key("pk").eq(keys.circle(circle_id))
        )
        items = response.get("Items", [])
        meta = next((i for i in items if _text(i, "sk") == keys.META), None)
        if meta is None:
            return None
        members = tuple(
            codec.member_from(_doc(i)) for i in items if _text(i, "sk").startswith("MEMBER#")
        )
        return codec.circle_from(_doc(meta), members)

    def for_owner(self, owner_person_id: PersonId) -> Circle | None:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            IndexName=keys.GSI2,
            KeyConditionExpression=Key(keys.GSI2_PK).eq(keys.owner_partition(owner_person_id))
            & Key(keys.GSI2_SK).begins_with("CIRCLE#"),
            Limit=1,
        )
        items = response.get("Items", [])
        if not items:
            return None
        circle_id = CircleId(_text(items[0], "pk").removeprefix("CIRCLE#"))
        return self.get(circle_id)

    def save_circle(self, circle: Circle) -> None:
        self.table.put_item(
            Item={
                "pk": keys.circle(circle.circle_id),
                "sk": keys.META,
                "data": codec.circle_to(circle),
                keys.GSI2_PK: keys.owner_partition(circle.owner_person_id),
                keys.GSI2_SK: keys.owner_circle(circle.circle_id),
            }
        )
        for member in circle.members:
            self.table.put_item(
                Item={
                    "pk": keys.circle(circle.circle_id),
                    "sk": keys.member(member.membership_id),
                    "data": codec.member_to(member),
                }
            )

    def consents_for(self, plan_id: PlanId) -> dict[PersonId, ConsentGrant]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            ConsistentRead=True,
            KeyConditionExpression=Key("pk").eq(keys.plan(plan_id))
            & Key("sk").begins_with("CONSENT#"),
        )
        grants = [codec.consent_from(_doc(i)) for i in response.get("Items", [])]
        return {g.responder_person_id: g for g in grants}

    def save_consent(self, consent: ConsentGrant) -> None:
        self.table.put_item(
            Item={
                "pk": keys.plan(consent.plan_id),
                "sk": keys.consent_sk(consent.responder_person_id),
                "data": codec.consent_to(consent),
            }
        )


@dataclass
class DynamoInvitationRepository:
    table: Table

    def get(self, invitation_id: InvitationId) -> CircleInvitation | None:
        item = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.invitation(invitation_id), "sk": keys.META}
        ).get("Item")
        return codec.invitation_from(_doc(item)) if item else None

    def save(self, invitation: CircleInvitation) -> None:
        self.table.put_item(
            Item={
                "pk": keys.invitation(invitation.invitation_id),
                "sk": keys.META,
                "data": codec.invitation_to(invitation),
                keys.GSI2_PK: keys.owner_partition(invitation.owner_person_id),
                keys.GSI2_SK: keys.owner_invitation(invitation.invitation_id),
            }
        )


@dataclass
class DynamoActionLog:
    table: Table

    def claim_key(self, key: IdempotencyKey) -> bool:
        """Reserve the right to dispatch. False means somebody already did.

        Invariant 5. The person on the other end of a duplicate is being told twice, at
        night, that someone they care about may not be okay.
        """
        try:
            self.table.put_item(
                Item={"pk": keys.idempotency(key.value), "sk": keys.LOCK},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as error:
            if _is(error, CONDITION_FAILED):
                return False
            raise
        return True

    def was_dispatched(self, key: IdempotencyKey) -> bool:
        item = self.table.get_item(
            ConsistentRead=True, Key={"pk": keys.idempotency(key.value), "sk": keys.LOCK}
        ).get("Item")
        return item is not None


@dataclass
class DynamoDecisionLog:
    """Agent decisions, stored under the Alert they concern.

    Denials are written exactly like allowances. A refused proposal that left no record
    would make the policy layer unfalsifiable.
    """

    table: Table

    def append(self, decision: AgentDecision) -> None:
        partition = keys.alert(decision.alert_id) if decision.alert_id else "AGENT#unattached"
        self.table.put_item(
            Item={
                "pk": partition,
                "sk": keys.timeline_sk("DECISION", decision.created_at, decision.decision_id),
                "decisionId": decision.decision_id,
                "modelId": decision.model_id,
                "proposedTool": decision.proposed_tool,
                "policyResult": decision.policy_result.value,
                "reasonCode": decision.reason_code,
                "inputHash": decision.input_hash,
                "arguments": decision.arguments,
                "at": decision.created_at.isoformat(),
            }
        )

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.alert(alert_id))
            & Key("sk").begins_with("DECISION#")
        )
        return tuple(dict(item) for item in response.get("Items", []))


@dataclass
class DynamoAuditLog:
    table: Table

    def append(
        self,
        *,
        alert_id: AlertId,
        actor_type: str,
        actor_id: str,
        event_type: str,
        at: datetime,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.table.put_item(
            Item={
                "pk": keys.alert(alert_id),
                "sk": keys.timeline_sk("AUDIT", at, event_type),
                # Stored explicitly as well as encoded in the partition key, so a reader
                # never has to parse `pk` to know what an event belongs to.
                "alertId": alert_id,
                "actorType": actor_type,
                "actorId": actor_id,
                "eventType": event_type,
                "at": at.isoformat(),
                "metadata": metadata or {},
            }
        )

    def for_alert(self, alert_id: AlertId) -> tuple[dict[str, object], ...]:
        from boto3.dynamodb.conditions import Key

        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(keys.alert(alert_id))
            & Key("sk").begins_with("AUDIT#")
        )
        return tuple(dict(item) for item in response.get("Items", []))
