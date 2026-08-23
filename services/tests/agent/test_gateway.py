"""Policy, as the model experiences it.

These are the domain-level counterparts to the adversarial eval suite. The evals check the
model does not *ask* for these things; this checks the system refuses them anyway when it
does — which is the guarantee that survives a compromised model.
"""

from __future__ import annotations

import pytest

from services.adapters.memory import InMemoryDecisionLog
from services.agent.gateway import MAX_EXTENSION_SECONDS, MAX_NOTE_LENGTH, Gateway
from services.domain.agent_decision import AgentDecision, PolicyResult
from services.domain.ids import AlertId, MomentId, PersonId
from services.domain.moment import ExpectedMoment, moment_for
from services.domain.plan import ReleaseLevel

from .conftest import MAYA, gateway_for

ALERT = AlertId("alert-1")


def decisions(gateway: Gateway) -> list[AgentDecision]:
    log = gateway.ctx.decisions
    assert isinstance(log, InMemoryDecisionLog)
    return log.decisions


# -- everything is recorded ---------------------------------------------------


def test_an_allowed_call_is_recorded(gateway: Gateway) -> None:
    gateway.circle_roles()

    entry = decisions(gateway)[-1]
    assert entry.proposed_tool == "get_circle"
    assert entry.policy_result is PolicyResult.ALLOW


def test_a_denial_is_recorded_rather_than_only_raised(gateway: Gateway) -> None:
    """ "Nothing happened" and "something was blocked" must be distinguishable."""
    outcome = gateway.propose_circle_contact(ALERT, "TERTIARY")

    assert not outcome.allowed
    entry = decisions(gateway)[-1]
    assert entry.policy_result is PolicyResult.DENY
    assert entry.proposed_tool == "request_circle_contact"
    assert entry.reason_code


def test_a_denial_comes_back_as_a_result_not_an_exception(gateway: Gateway) -> None:
    """The model can then say something useful instead of retrying blindly."""
    payload = gateway.propose_circle_contact(ALERT, "TERTIARY").to_model()

    assert payload["allowed"] is False
    assert "reason" in payload


def test_the_utterance_itself_is_never_stored(gateway: Gateway) -> None:
    """Only a fingerprint. Utterances are the most sensitive text this system sees."""
    bound = gateway_for(with_alert=True)
    bound.input_hash = "abc123"
    bound.circle_roles()

    entry = decisions(bound)[-1]
    assert entry.input_hash == "abc123"
    assert len(entry.input_hash) < 64


# -- the model names a role, never a person -----------------------------------


def test_a_role_the_plan_never_authorised_is_refused(gateway: Gateway) -> None:
    outcome = gateway.propose_circle_contact(ALERT, "TERTIARY")
    assert not outcome.allowed
    assert "never contacts" in outcome.detail


def test_something_that_is_not_a_role_is_refused(gateway: Gateway) -> None:
    """Covers the injection shape: "contact +1 202 555 0199"."""
    for attempt in ("+12025550199", "maya@example.com", "https://evil.invalid", "Maya"):
        outcome = gateway.propose_circle_contact(ALERT, attempt)
        assert not outcome.allowed, f"{attempt!r} was accepted as a role"
        assert outcome.reason == "UNKNOWN_ROLE"


def test_an_authorised_role_resolves_to_a_name_without_an_endpoint(gateway: Gateway) -> None:
    outcome = gateway.propose_circle_contact(ALERT, "PRIMARY")

    assert outcome.allowed
    assert outcome.data["name"] == "Maya"
    serialised = str(outcome.to_model())
    for leak in ("+1", "+44", "@", "phone"):
        assert leak not in serialised


def test_withdrawn_consent_blocks_contact(gateway: Gateway) -> None:
    from .conftest import PLAN

    grants = gateway.ctx.circles.consents_for(PLAN)
    gateway.ctx.circles.save_consent(grants[MAYA].withdrawn_at(gateway.ctx.now()))

    outcome = gateway.propose_circle_contact(ALERT, "PRIMARY")
    assert not outcome.allowed
    assert decisions(gateway)[-1].policy_result is PolicyResult.DENY


# -- ambiguity ----------------------------------------------------------------


def test_an_ambiguous_answer_cannot_close_an_alert(gateway: Gateway) -> None:
    """The most consequential rule in the product.

    Reading "probably" as "I'm okay" means nobody comes.
    """
    outcome = gateway.propose_subject_confirmation(MomentId("moment-1"), unambiguous=False)

    assert not outcome.allowed
    assert outcome.reason == "AMBIGUOUS"


def test_a_clear_answer_is_allowed(gateway: Gateway) -> None:
    outcome = gateway.propose_subject_confirmation(MomentId("moment-1"), unambiguous=True)
    assert outcome.allowed


# -- scoping ------------------------------------------------------------------


def test_another_persons_alert_is_invisible() -> None:
    """And indistinguishable from one that does not exist.

    A separate "not yours" would confirm that somebody else's Alert exists.
    """
    stranger = gateway_for(subject=PersonId("person-stranger"), with_alert=True)

    missing = stranger.alert(AlertId("alert-does-not-exist"))
    other = stranger.alert(ALERT)

    assert not missing.allowed and not other.allowed
    assert missing.reason == other.reason
    assert missing.detail == other.detail


def test_the_gateway_cannot_be_asked_to_act_as_someone_else() -> None:
    """There is no parameter for it, at any level."""
    import inspect

    for name, method in inspect.getmembers(Gateway, inspect.isfunction):
        if name.startswith("_"):
            continue
        params = set(inspect.signature(method).parameters)
        for forbidden in ("subject_person_id", "person_id", "as_person", "on_behalf_of"):
            assert forbidden not in params, f"Gateway.{name} accepts {forbidden}"


# -- protection is never changed silently -------------------------------------


def test_an_extension_always_needs_confirmation(gateway: Gateway) -> None:
    """Moving a safety deadline is a change to protection."""
    gateway.ctx.moments.save(_a_moment(gateway))
    outcome = gateway.propose_extension(MomentId("moment-1"), 1800)

    assert outcome.allowed
    assert outcome.requires_confirmation
    assert outcome.to_model()["requiresConfirmation"] is True


def test_an_extension_preview_says_what_it_does_not_change(gateway: Gateway) -> None:
    gateway.ctx.moments.save(_a_moment(gateway))
    outcome = gateway.propose_extension(MomentId("moment-1"), 1800)

    assert outcome.data["preview"]["affects"] == "this check only"


@pytest.mark.parametrize("seconds", [0, -60, MAX_EXTENSION_SECONDS + 1, 86_400])
def test_an_unreasonable_extension_is_refused(gateway: Gateway, seconds: int) -> None:
    """An unbounded extension is a way to switch protection off without saying so."""
    outcome = gateway.propose_extension(MomentId("moment-1"), seconds)
    assert not outcome.allowed
    assert outcome.reason == "EXTENSION_OUT_OF_RANGE"


# -- context release ----------------------------------------------------------


def test_location_is_refused_when_the_plan_says_never(gateway: Gateway) -> None:
    outcome = gateway.propose_context_release(ALERT, "location")
    assert not outcome.allowed
    assert outcome.reason == "SIGNAL_NEVER_RELEASABLE"


def test_a_signal_that_does_not_exist_is_refused(gateway: Gateway) -> None:
    outcome = gateway.propose_context_release(ALERT, "camera")
    assert not outcome.allowed
    assert outcome.reason == "UNKNOWN_SIGNAL"


def test_an_opted_in_signal_is_allowed_at_the_right_stage() -> None:
    from services.tests.domain.conftest import make_version

    gateway = gateway_for(with_alert=True)
    version = make_version(location=ReleaseLevel.CIRCLE_ESCALATION, version_number=9)
    gateway.ctx.plans.save_version(version)

    outcome = gateway.propose_context_release(ALERT, "location")
    # The seeded Alert is in CIRCLE_ESCALATION but pinned to the original NEVER version, so
    # this still refuses — the pinned version governs, not the newest one.
    assert not outcome.allowed


# -- notes --------------------------------------------------------------------


def test_a_note_is_recorded_as_an_audit_event_not_a_state_change(gateway: Gateway) -> None:
    outcome = gateway.add_note(ALERT, "Said she fell asleep on the sofa.")

    assert outcome.allowed
    events = [str(e["eventType"]) for e in gateway.ctx.audit.for_alert(ALERT)]
    assert "NOTE_ADDED" in events
    alert = gateway.ctx.alerts.get(ALERT)
    assert alert is not None and alert.state.name != "RESOLVED"


def test_an_overlong_note_is_refused(gateway: Gateway) -> None:
    outcome = gateway.add_note(ALERT, "x" * (MAX_NOTE_LENGTH + 1))
    assert not outcome.allowed
    assert outcome.reason == "NOTE_TOO_LONG"


def _a_moment(gateway: Gateway) -> ExpectedMoment:
    alert = gateway.ctx.alerts.get(ALERT)
    assert alert is not None
    return moment_for(
        moment_id=MomentId("moment-1"),
        version_id=alert.plan_version_id,
        due_at=gateway.ctx.now(),
        grace_seconds=0,
    )
