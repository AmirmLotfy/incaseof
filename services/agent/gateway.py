"""The gate between the model and everything real.

Tools do not touch state. They call this, and this decides.

The structure matters more than any individual check. A tool that could reach the domain
directly would be one refactor away from bypassing policy, so the gate owns the only
references to repositories and the domain, and tools own none. Every method here follows
the same three steps, in this order:

    1. evaluate policy, deterministically, outside the model
    2. record the proposal *and its outcome*, including denials
    3. only then, if allowed, do the thing

Step 2 is not bookkeeping. A denial that merely raises leaves no trace, and "nothing
happened" becomes indistinguishable from "something was blocked" — which is exactly what
the developer trace and the audit timeline exist to tell apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from services.domain.agent_decision import AgentDecision, PolicyResult
from services.domain.alert import Alert
from services.domain.authorization import (
    Reason,
    evaluate_contact,
    evaluate_context_release,
)
from services.domain.ids import (
    AlertId,
    CircleId,
    IdFactory,
    MomentId,
    PersonId,
    PlanId,
    uuid_factory,
)
from services.domain.plan import ContextSignal, ResponderRole
from services.handlers import bootstrap

MAX_EXTENSION_SECONDS = 4 * 3600
MAX_NOTE_LENGTH = 500


@dataclass(frozen=True, slots=True)
class Outcome:
    """What the gate decided, in a shape a tool can hand straight back to the model."""

    allowed: bool
    reason: str
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False

    def to_model(self) -> dict[str, Any]:
        """What the model is told.

        Denials come back as ordinary results rather than errors, so the model can say
        something useful to the person instead of retrying. It is never told *how* to get
        past a refusal.
        """
        payload: dict[str, Any] = {"allowed": self.allowed, "reason": self.reason}
        if self.detail:
            payload["detail"] = self.detail
        if self.requires_confirmation:
            payload["requiresConfirmation"] = True
        payload.update(self.data)
        return payload


@dataclass
class Gateway:
    """One conversation's worth of authority.

    Bound to a single authenticated subject at construction. Nothing the model says can
    widen that: there is no parameter anywhere below for "act as somebody else".
    """

    ctx: bootstrap.Context
    subject_person_id: PersonId
    # Bound at construction rather than discovered. The model cannot name a circle, so it
    # cannot reach one it was not given.
    circle_id: CircleId | None = None
    model_id: str = "gemini-3.7-flash"
    input_hash: str = ""
    new_id: IdFactory = uuid_factory

    # -- recording --------------------------------------------------------

    def _record(
        self,
        tool: str,
        result: PolicyResult,
        reason: str,
        *,
        alert_id: AlertId | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> None:
        if self.ctx.decisions is None:
            return
        self.ctx.decisions.append(
            AgentDecision(
                decision_id=self.new_id(),
                alert_id=alert_id,
                model_id=self.model_id,
                proposed_tool=tool,
                policy_result=result,
                reason_code=reason,
                created_at=self.ctx.now(),
                input_hash=self.input_hash,
                arguments=arguments or {},
            )
        )

    def _allow(
        self,
        tool: str,
        *,
        alert_id: AlertId | None = None,
        data: dict[str, Any] | None = None,
        arguments: dict[str, Any] | None = None,
        requires_confirmation: bool = False,
    ) -> Outcome:
        self._record(
            tool, PolicyResult.ALLOW, Reason.ALLOWED, alert_id=alert_id, arguments=arguments
        )
        return Outcome(
            allowed=True,
            reason=str(Reason.ALLOWED),
            data=data or {},
            requires_confirmation=requires_confirmation,
        )

    def _deny(
        self,
        tool: str,
        reason: str,
        detail: str = "",
        *,
        alert_id: AlertId | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> Outcome:
        self._record(tool, PolicyResult.DENY, reason, alert_id=alert_id, arguments=arguments)
        return Outcome(allowed=False, reason=reason, detail=detail)

    # -- reads ------------------------------------------------------------

    def active_moment(self) -> Outcome:
        """What is expected of this person right now."""
        pending = self.ctx.moments.due_before(self.ctx.now() + timedelta(days=1))
        if not pending:
            return self._allow("get_active_moment", data={"moment": None})

        moment = pending[0]
        alert = self.ctx.alerts.alert_for_moment(moment.moment_id)
        version = self.ctx.plans.get_version(moment.version_id)
        return self._allow(
            "get_active_moment",
            alert_id=alert.alert_id if alert else None,
            data={
                "moment": {
                    "momentId": moment.moment_id,
                    "planLabel": (version.label if version else None) or "Check-in",
                    "dueAt": moment.due_at.isoformat(),
                    "state": alert.state.value if alert else "SCHEDULED",
                }
            },
        )

    def alert(self, alert_id: AlertId) -> Outcome:
        """One Alert, if it belongs to this subject's plan."""
        found = self._own_alert(alert_id)
        if found is None:
            # Same answer whether it does not exist or belongs to somebody else. A
            # distinguishable "not yours" confirms that somebody else's Alert exists.
            return self._deny(
                "get_alert", Reason.ALERT_NOT_OPEN, "no such alert", alert_id=alert_id
            )
        return self._allow(
            "get_alert",
            alert_id=alert_id,
            data={
                "alert": {
                    "alertId": found.alert_id,
                    "state": found.state.value,
                    "expectedAt": found.opened_at.isoformat(),
                    "isResolved": found.is_terminal,
                }
            },
        )

    def circle_roles(self) -> Outcome:
        """Who can be reached, by **role and first name only**.

        No phone numbers, no email addresses, no membership ids the model could use to
        address somebody directly. The model learns that a 'Maya' exists and holds the
        primary role; turning that into an address happens far below, after authorisation.
        """
        circle = self.ctx.circles.get(self.circle_id) if self.circle_id else None
        if circle is None:
            return self._allow("get_circle", data={"roles": []})

        return self._allow(
            "get_circle",
            data={
                "roles": [
                    {"role": member.role.value, "name": member.display_name}
                    for member in circle.accepted_members
                ]
            },
        )

    # -- proposals --------------------------------------------------------

    def propose_extension(self, moment_id: MomentId, seconds: int) -> Outcome:
        """ "Give me another thirty minutes."

        Always requires confirmation. Moving a safety deadline is a change to protection,
        and §4.5 is explicit that the model never changes protection silently.
        """
        arguments = {"momentId": moment_id, "seconds": seconds}

        if seconds <= 0 or seconds > MAX_EXTENSION_SECONDS:
            return self._deny(
                "request_extension",
                "EXTENSION_OUT_OF_RANGE",
                f"extensions are limited to {MAX_EXTENSION_SECONDS // 3600} hours",
                arguments=arguments,
            )

        moment = self.ctx.moments.get(moment_id)
        if moment is None:
            return self._deny(
                "request_extension", "NOT_FOUND", "no such moment", arguments=arguments
            )

        return self._allow(
            "request_extension",
            arguments=arguments,
            requires_confirmation=True,
            data={
                "preview": {
                    "from": moment.due_at.isoformat(),
                    "to": (moment.due_at + timedelta(seconds=seconds)).isoformat(),
                    # Always say what a change does NOT affect.
                    "affects": "this check only",
                }
            },
        )

    def propose_subject_confirmation(self, moment_id: MomentId, *, unambiguous: bool) -> Outcome:
        """ "I'm okay."

        The model classifies; the system decides. An ambiguous utterance never resolves an
        Alert -- "probably" and "I think so" fall back to the explicit buttons, because the
        cost of reading a hedge as a confirmation is that nobody comes.
        """
        arguments = {"momentId": moment_id}

        if not unambiguous:
            return self._deny(
                "confirm_subject_okay",
                "AMBIGUOUS",
                "an ambiguous answer cannot close an alert",
                arguments=arguments,
            )

        alert = self.ctx.alerts.alert_for_moment(moment_id)
        if alert is None:
            return self._deny(
                "confirm_subject_okay", "NOT_FOUND", "no open alert", arguments=arguments
            )
        if alert.is_terminal:
            return self._deny(
                "confirm_subject_okay",
                "ALERT_CLOSED",
                "already closed",
                alert_id=alert.alert_id,
                arguments=arguments,
            )
        if not self._owns(alert):
            return self._deny(
                "confirm_subject_okay",
                "NOT_AUTHORIZED",
                "not your check",
                alert_id=alert.alert_id,
                arguments=arguments,
            )

        return self._allow(
            "confirm_subject_okay",
            alert_id=alert.alert_id,
            arguments=arguments,
            data={"alertId": alert.alert_id},
        )

    def propose_circle_contact(self, alert_id: AlertId, role: str) -> Outcome:
        """ "Contact Maya." Named by **role**, never by person and never by number.

        The role is resolved to a rung of the Alert's pinned version. A role the plan never
        authorised has no rung, so there is nothing to resolve and nothing to contact --
        the refusal is structural rather than a check that could be forgotten.
        """
        arguments = {"alertId": alert_id, "role": role}

        try:
            requested = ResponderRole(role)
        except ValueError:
            return self._deny(
                "request_circle_contact",
                "UNKNOWN_ROLE",
                f"{role} is not a role",
                alert_id=alert_id,
                arguments=arguments,
            )

        alert = self._own_alert(alert_id)
        if alert is None:
            return self._deny(
                "request_circle_contact",
                "NOT_AUTHORIZED",
                "no such alert",
                alert_id=alert_id,
                arguments=arguments,
            )

        rung = next((s for s in alert.version.responder_steps if s.target_role is requested), None)
        if rung is None:
            return self._deny(
                "request_circle_contact",
                Reason.ROLE_NOT_IN_PLAN_VERSION,
                f"this plan never contacts a {role}",
                alert_id=alert_id,
                arguments=arguments,
            )

        plan, circle = self._plan_and_circle(alert)
        if plan is None or circle is None:
            return self._deny(
                "request_circle_contact",
                Reason.NO_MEMBER_FOR_ROLE,
                "no circle",
                alert_id=alert_id,
                arguments=arguments,
            )

        decision = evaluate_contact(
            alert=alert,
            circle=circle,
            consents=self.ctx.circles.consents_for(PlanId(plan.plan_id)),
            sequence=rung.sequence,
            plan_id=PlanId(plan.plan_id),
            now=self.ctx.now(),
        )
        if not decision.allowed or decision.member is None:
            return self._deny(
                "request_circle_contact",
                str(decision.reason),
                decision.detail,
                alert_id=alert_id,
                arguments=arguments,
            )

        return self._allow(
            "request_circle_contact",
            alert_id=alert_id,
            arguments=arguments,
            data={"sequence": rung.sequence, "name": decision.member.display_name},
        )

    def propose_context_release(self, alert_id: AlertId, signal: str) -> Outcome:
        """Release a context signal, if the subject opted in ahead of time."""
        arguments = {"alertId": alert_id, "signal": signal}

        try:
            requested = ContextSignal(signal)
        except ValueError:
            return self._deny(
                "release_context",
                "UNKNOWN_SIGNAL",
                f"{signal} is not a signal",
                alert_id=alert_id,
                arguments=arguments,
            )

        alert = self._own_alert(alert_id)
        if alert is None:
            return self._deny(
                "release_context",
                "NOT_AUTHORIZED",
                "no such alert",
                alert_id=alert_id,
                arguments=arguments,
            )

        decision = evaluate_context_release(alert=alert, signal=requested, now=self.ctx.now())
        if not decision.allowed:
            return self._deny(
                "release_context",
                str(decision.reason),
                decision.detail,
                alert_id=alert_id,
                arguments=arguments,
            )
        return self._allow("release_context", alert_id=alert_id, arguments=arguments)

    def add_note(self, alert_id: AlertId, text: str) -> Outcome:
        """Attach context to an Alert. The one write with no safety consequence.

        Length-capped and recorded as an audit event, never as a state change.
        """
        arguments = {"alertId": alert_id, "length": len(text)}

        alert = self._own_alert(alert_id)
        if alert is None:
            return self._deny(
                "add_alert_note",
                "NOT_AUTHORIZED",
                "no such alert",
                alert_id=alert_id,
                arguments=arguments,
            )
        if len(text) > MAX_NOTE_LENGTH:
            return self._deny(
                "add_alert_note",
                "NOTE_TOO_LONG",
                f"notes are limited to {MAX_NOTE_LENGTH} characters",
                alert_id=alert_id,
                arguments=arguments,
            )

        self.ctx.audit.append(
            alert_id=alert_id,
            actor_type="AGENT",
            actor_id=self.model_id,
            event_type="NOTE_ADDED",
            at=self.ctx.now(),
            metadata={"text": text},
        )
        return self._allow("add_alert_note", alert_id=alert_id, arguments=arguments)

    # -- scoping ----------------------------------------------------------

    def _own_alert(self, alert_id: AlertId) -> Alert | None:
        alert = self.ctx.alerts.get(alert_id)
        if alert is None or not self._owns(alert):
            return None
        return alert

    def _owns(self, alert: Alert) -> bool:
        """Whether this Alert belongs to the subject this gateway is bound to."""
        plan = self.ctx.plans.get_plan(PlanId(alert.version.plan_id))
        return plan is not None and plan.subject_person_id == self.subject_person_id

    def _plan_and_circle(self, alert: Alert) -> tuple[Any, Any]:
        plan = self.ctx.plans.get_plan(PlanId(alert.version.plan_id))
        circle = self.ctx.circles.get(CircleId(plan.circle_id)) if plan else None
        return plan, circle
