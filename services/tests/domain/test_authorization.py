"""Policy layer tests.

These are the domain-level counterparts to the adversarial eval suite in evals/. That
suite checks the model does not *ask* for these things. This checks the system refuses
them anyway when it does -- which is the guarantee that actually matters, because it holds
even if the model is fully compromised.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from services.domain.alert import Alert
from services.domain.authorization import (
    Reason,
    authorize_contact,
    evaluate_contact,
    evaluate_context_release,
    evaluate_responder_action,
    reached_stage,
)
from services.domain.circle import (
    Circle,
    CircleMember,
    ConsentGrant,
    ConsentStatus,
    ContactChannelPermission,
    MemberStatus,
)
from services.domain.errors import NotAuthorized
from services.domain.ids import CircleId, ConsentId, MembershipId, PersonId, PlanId
from services.domain.plan import (
    ActionType,
    ContextSignal,
    ReleaseLevel,
    ResponderRole,
)

from .conftest import (
    DUE_AT,
    EVENING_STEPS,
    escalating,
    in_circle_escalation,
    make_version,
)

PLAN = PlanId("plan-1")
MONA = PersonId("person-mona")
MAYA = PersonId("person-maya")
OMAR = PersonId("person-omar")
STRANGER = PersonId("person-stranger")


def member(
    person_id: PersonId,
    role: ResponderRole,
    *,
    status: MemberStatus = MemberStatus.ACCEPTED,
    priority: int = 1,
) -> CircleMember:
    return CircleMember(
        membership_id=MembershipId(f"m-{person_id}"),
        circle_id=CircleId("circle-1"),
        person_id=person_id,
        role=role,
        priority=priority,
        status=status,
        display_name=person_id.split("-")[-1].title(),
    )


def consent(
    person_id: PersonId,
    *,
    status: ConsentStatus = ConsentStatus.ACTIVE,
    channels: frozenset[ContactChannelPermission] | None = None,
    plan_id: PlanId = PLAN,
    revoked_at: object = None,
) -> ConsentGrant:
    return ConsentGrant(
        consent_id=ConsentId(f"c-{person_id}"),
        subject_person_id=MONA,
        responder_person_id=person_id,
        plan_id=plan_id,
        status=status,
        accepted_at=DUE_AT - timedelta(days=30),
        revoked_at=revoked_at,  # type: ignore[arg-type]
        channels=channels
        if channels is not None
        else frozenset({ContactChannelPermission.PUSH, ContactChannelPermission.SMS}),
    )


def full_circle() -> Circle:
    return Circle(
        circle_id=CircleId("circle-1"),
        owner_person_id=MONA,
        members=(
            member(MAYA, ResponderRole.PRIMARY),
            member(OMAR, ResponderRole.BACKUP),
        ),
    )


def consents() -> dict[PersonId, ConsentGrant]:
    return {MAYA: consent(MAYA), OMAR: consent(OMAR)}


def primary_seq(alert: Alert) -> int:
    """Sequence of the first responder rung."""
    return alert.version.responder_steps[0].sequence


# -- the happy path -----------------------------------------------------------


def test_a_valid_contact_resolves_the_role_to_a_person() -> None:
    alert = in_circle_escalation()
    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=consents(),
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert decision.allowed
    assert decision.reason is Reason.ALLOWED
    assert decision.member is not None
    assert decision.member.person_id == MAYA


# -- denials ------------------------------------------------------------------


def test_a_closed_alert_contacts_nobody() -> None:
    alert = in_circle_escalation()
    sequence = primary_seq(alert)
    resolved = alert.confirm_subject(DUE_AT, MONA)

    decision = evaluate_contact(
        alert=resolved,
        circle=full_circle(),
        consents=consents(),
        sequence=sequence,
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.ALERT_NOT_OPEN


def test_a_rung_the_pinned_version_does_not_have_is_refused() -> None:
    """Invariant 2 at the policy layer: only the pinned version may drive this Alert.

    A caller cannot hand in a step object at all -- the rung is resolved from the Alert's
    own version -- so the only way to aim at a foreign rung is a sequence number the
    pinned version does not contain.
    """
    alert = in_circle_escalation()
    longer = make_version(
        version_number=9,
        steps=(
            *EVENING_STEPS,
            (6, 3600, ActionType.MESSAGE_RESPONDER, ResponderRole.TERTIARY),
        ),
    )
    assert longer.step(6).target_role is ResponderRole.TERTIARY

    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=consents(),
        sequence=6,
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.STEP_NOT_IN_PLAN_VERSION


def test_withdrawn_consent_stops_contact_mid_alert() -> None:
    """Consent is checked at contact time, not at invitation time."""
    alert = in_circle_escalation()
    grants = consents()
    grants[MAYA] = grants[MAYA].withdrawn_at(DUE_AT - timedelta(minutes=1))

    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=grants,
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.CONSENT_NOT_ACTIVE


def test_expired_consent_stops_contact() -> None:
    alert = in_circle_escalation()
    grants = consents()
    grants[MAYA] = ConsentGrant(
        consent_id=ConsentId("c-expiring"),
        subject_person_id=MONA,
        responder_person_id=MAYA,
        plan_id=PLAN,
        status=ConsentStatus.ACTIVE,
        expires_at=DUE_AT - timedelta(seconds=1),
    )
    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=grants,
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.CONSENT_NOT_ACTIVE


def test_consent_for_a_different_plan_does_not_transfer() -> None:
    """Agreeing to be a contact for the evening check is not agreeing to every plan."""
    alert = in_circle_escalation()
    grants = consents()
    grants[MAYA] = consent(MAYA, plan_id=PlanId("plan-other"))

    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=grants,
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.CONSENT_NOT_ACTIVE


def test_an_invited_but_unaccepted_member_is_never_contacted() -> None:
    alert = in_circle_escalation()
    circle = Circle(
        circle_id=CircleId("circle-1"),
        owner_person_id=MONA,
        members=(member(MAYA, ResponderRole.PRIMARY, status=MemberStatus.INVITED),),
    )
    decision = evaluate_contact(
        alert=alert,
        circle=circle,
        consents=consents(),
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.NO_MEMBER_FOR_ROLE


def test_an_unfilled_role_does_not_silently_fall_through_to_another() -> None:
    """Contacting the backup because the primary is missing would rewrite the subject's plan."""
    alert = in_circle_escalation()
    only_backup = Circle(
        circle_id=CircleId("circle-1"),
        owner_person_id=MONA,
        members=(member(OMAR, ResponderRole.BACKUP),),
    )
    decision = evaluate_contact(
        alert=alert,
        circle=only_backup,
        consents=consents(),
        sequence=primary_seq(alert),
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.NO_MEMBER_FOR_ROLE


def test_a_channel_the_member_never_agreed_to_is_refused() -> None:
    alert = in_circle_escalation()
    grants = consents()
    grants[MAYA] = consent(MAYA, channels=frozenset({ContactChannelPermission.PUSH}))

    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=grants,
        sequence=primary_seq(alert),  # MESSAGE_RESPONDER -> SMS
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.CHANNEL_NOT_PERMITTED


def test_a_subject_directed_step_cannot_be_used_to_contact_a_responder() -> None:
    alert = in_circle_escalation()
    push = alert.version.subject_steps[0]

    decision = evaluate_contact(
        alert=alert,
        circle=full_circle(),
        consents=consents(),
        sequence=push.sequence,
        plan_id=PLAN,
        now=DUE_AT,
    )
    assert not decision.allowed
    assert decision.reason is Reason.STEP_NOT_RESPONDER_DIRECTED


def test_a_role_the_plan_never_authorised_is_unreachable() -> None:
    """A ladder with no TERTIARY rung must never reach a TERTIARY member.

    There is no TERTIARY rung to name, and no way to supply one, so the role is
    unreachable by construction rather than by a check that could be forgotten.
    """
    alert = in_circle_escalation()
    assert ResponderRole.TERTIARY not in alert.version.responder_roles

    for sequence in range(1, 20):
        decision = evaluate_contact(
            alert=alert,
            circle=full_circle(),
            consents=consents(),
            sequence=sequence,
            plan_id=PLAN,
            now=DUE_AT,
        )
        if decision.allowed:
            assert decision.member is not None
            assert decision.member.role is not ResponderRole.TERTIARY


def test_authorize_contact_raises_rather_than_returning_a_denial() -> None:
    alert = in_circle_escalation()
    with pytest.raises(NotAuthorized):
        authorize_contact(
            alert=alert,
            circle=full_circle(),
            consents={},
            sequence=primary_seq(alert),
            plan_id=PLAN,
            now=DUE_AT,
        )


# -- context release ----------------------------------------------------------


def test_location_is_never_released_by_default() -> None:
    alert = in_circle_escalation()
    decision = evaluate_context_release(alert=alert, signal=ContextSignal.LOCATION, now=DUE_AT)
    assert not decision.allowed
    assert decision.reason is Reason.SIGNAL_NEVER_RELEASABLE


def test_a_signal_unlocks_only_once_escalation_reaches_its_stage() -> None:
    version = make_version(location=ReleaseLevel.CIRCLE_ESCALATION)

    early = escalating(version)
    assert not evaluate_context_release(
        alert=early, signal=ContextSignal.LOCATION, now=DUE_AT
    ).allowed

    late = in_circle_escalation(version)
    assert evaluate_context_release(alert=late, signal=ContextSignal.LOCATION, now=DUE_AT).allowed


def test_an_earlier_stage_policy_is_satisfied_by_a_later_stage() -> None:
    """ON_ALERT_OPEN is the most permissive policy: reaching the Circle must satisfy it.

    The inverse ranking is a real hazard here -- ordering these by "permissiveness" rather
    than by escalation stage silently inverts this case and withholds a signal the subject
    chose to share.
    """
    version = make_version(location=ReleaseLevel.ON_ALERT_OPEN)
    late = in_circle_escalation(version)

    assert reached_stage(late) is ReleaseLevel.CIRCLE_ESCALATION
    assert evaluate_context_release(alert=late, signal=ContextSignal.LOCATION, now=DUE_AT).allowed


def test_a_closed_alert_releases_nothing() -> None:
    version = make_version(location=ReleaseLevel.ON_ALERT_OPEN)
    resolved = in_circle_escalation(version).confirm_subject(DUE_AT, MONA)

    assert reached_stage(resolved) is ReleaseLevel.NEVER
    assert not evaluate_context_release(
        alert=resolved, signal=ContextSignal.LOCATION, now=DUE_AT
    ).allowed


# -- responder surface --------------------------------------------------------


def test_a_stranger_cannot_act_on_an_alert() -> None:
    alert = in_circle_escalation()
    decision = evaluate_responder_action(
        alert=alert, circle=full_circle(), responder_id=STRANGER, now=DUE_AT
    )
    assert not decision.allowed
    assert decision.reason is Reason.NOT_A_CIRCLE_MEMBER


def test_a_removed_member_loses_access_immediately() -> None:
    alert = in_circle_escalation()
    circle = Circle(
        circle_id=CircleId("circle-1"),
        owner_person_id=MONA,
        members=(member(MAYA, ResponderRole.PRIMARY, status=MemberStatus.REMOVED),),
    )
    decision = evaluate_responder_action(alert=alert, circle=circle, responder_id=MAYA, now=DUE_AT)
    assert not decision.allowed
    assert decision.reason is Reason.NOT_A_CIRCLE_MEMBER


def test_a_member_may_act_on_an_alert_their_role_covers() -> None:
    alert = in_circle_escalation()
    decision = evaluate_responder_action(
        alert=alert, circle=full_circle(), responder_id=MAYA, now=DUE_AT
    )
    assert decision.allowed
