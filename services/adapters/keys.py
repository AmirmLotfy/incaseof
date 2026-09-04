"""Single-table key layout.

One place that knows how domain identity maps to partition and sort keys, so the shape in
docs/ERD.md section 3 is expressed once rather than restated at every call site.

Everything about one Alert -- its metadata, ownership history, actions, agent decisions and
audit trail -- shares a partition key, so rendering the Incident Room and the full audit
timeline is a single query rather than a fan-out.
"""

from __future__ import annotations

from datetime import datetime

from services.domain.ids import (
    AlertId,
    CircleId,
    InvitationId,
    MembershipId,
    MomentId,
    PersonId,
    PlanId,
    PlanVersionId,
)

# Sparse GSI over unresolved Moments, bucketed by due date.
#
# Access pattern (recorded here and in docs/ERD.md): the reconciliation sweeper asks
# "which Moments were due by now and never opened an Alert?". EventBridge Scheduler owns
# the timers, so this is a backstop for a schedule that failed to deliver -- in a safety
# product the failure of the thing that notices cannot itself go unnoticed.
#
# Bucketed by day rather than a single "DUE" partition so the index does not become one
# hot key, and *sparse*: the attributes are removed once a Moment resolves, so the index
# holds only outstanding work and shrinks as things close.
GSI1 = "gsi1-moments-due"
GSI1_PK = "gsi1pk"
GSI1_SK = "gsi1sk"

# Owner-scoped listing index. Public handlers never scan the shared table and never
# infer ownership from caller-controlled ids. The partition is the validated Cognito
# subject; sort-key prefixes keep Plans, Circles and Moments independently queryable.
GSI2 = "gsi2-person"
GSI2_PK = "gsi2pk"
GSI2_SK = "gsi2sk"


def person(person_id: PersonId) -> str:
    return f"PERSON#{person_id}"


def circle(circle_id: CircleId) -> str:
    return f"CIRCLE#{circle_id}"


def member(membership_id: MembershipId) -> str:
    return f"MEMBER#{membership_id}"


def plan(plan_id: PlanId) -> str:
    return f"PLAN#{plan_id}"


def version_sk(version_number: int) -> str:
    """Zero-padded so lexicographic order matches numeric order past version 9."""
    return f"VERSION#{version_number:04d}"


def version_pointer(version_id: PlanVersionId) -> str:
    """Lookup by version id, for an Alert resolving its pinned version directly."""
    return f"PLANVERSION#{version_id}"


def moment(moment_id: MomentId) -> str:
    return f"MOMENT#{moment_id}"


def alert(alert_id: AlertId) -> str:
    return f"ALERT#{alert_id}"


def invitation(invitation_id: InvitationId) -> str:
    return f"INVITATION#{invitation_id}"


def owner_invitation(invitation_id: InvitationId) -> str:
    return f"INVITATION#{invitation_id}"


def consent_sk(responder_id: PersonId) -> str:
    return f"CONSENT#{responder_id}"


def idempotency(key: str) -> str:
    return f"IDEM#{key}"


def timeline_sk(prefix: str, at: datetime, suffix: str) -> str:
    """Sortable timeline entry: ``ACTION#2026-08-26T21:00:00+00:00#a-1``."""
    return f"{prefix}#{at.isoformat()}#{suffix}"


def due_bucket(due_at: datetime) -> str:
    return f"DUE#{due_at.date().isoformat()}"


def due_sort(due_at: datetime, moment_id: MomentId) -> str:
    return f"{due_at.isoformat()}#{moment_id}"


def owner_partition(person_id: PersonId) -> str:
    return person(person_id)


def owner_plan(plan_id: PlanId) -> str:
    return f"PLAN#{plan_id}"


def owner_circle(circle_id: CircleId) -> str:
    return f"CIRCLE#{circle_id}"


def owner_moment(due_at: datetime, moment_id: MomentId) -> str:
    return f"MOMENT#{due_at.isoformat()}#{moment_id}"


def owner_alert(opened_at: datetime, alert_id: AlertId) -> str:
    return f"ALERT#{opened_at.isoformat()}#{alert_id}"


META = "META"
ALERT_LOCK = "ALERT_LOCK"
LOCK = "LOCK"
