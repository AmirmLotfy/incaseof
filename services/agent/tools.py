"""The tool surface.

This is the security boundary, and it is a boundary of **vocabulary** rather than of
checks. The question to ask of every signature below is not "is this validated?" but:

    could a completely compromised model cause harm through this, even saying anything?

The answer has to be no, because there is no parameter anywhere here that can carry a phone
number, an email address, a URL, or a person. The model names a **role**. Resolving a role
to a human, and a human to an address, happens far below, after authorisation — see
docs/AI-SAFETY.md section 3.

Every function is a thin wrapper. Tools hold no references to repositories or to the
domain; they call the gateway and hand back what it says. A tool that could reach state
directly would be one refactor away from bypassing policy.
"""

from __future__ import annotations

from typing import Any

from strands import tool

from services.agent.gateway import Gateway
from services.domain.ids import AlertId, MomentId


def build_tools(gateway: Gateway) -> list[Any]:
    """Bind the tool surface to one authenticated subject.

    The gateway is captured, never passed as an argument. There is deliberately no way for
    the model to say which subject it is acting for.
    """

    @tool
    def get_active_moment() -> dict[str, Any]:
        """Get what In Case of is currently expecting from this person.

        Returns the next or current check-in: its id, the plan it belongs to, when it is
        due, and whether it is still outstanding. Returns null when nothing is expected.
        """
        return gateway.active_moment().to_model()

    @tool
    def get_alert(alert_id: str) -> dict[str, Any]:
        """Get the state of one alert belonging to this person.

        An alert exists when a check-in went unresolved. Tells you whether it is still
        open, when the check was expected, and whether anybody has closed it. Only alerts
        belonging to this person are visible; anything else returns the same "no such
        alert" answer.

        Args:
            alert_id: The alert's identifier, as returned by get_active_moment.
        """
        return gateway.alert(AlertId(alert_id)).to_model()

    @tool
    def get_circle() -> dict[str, Any]:
        """List the roles in this person's Circle and the first name in each.

        Returns roles such as PRIMARY and BACKUP with a display name, so you can say
        "Maya" to the person. It returns no contact details of any kind, and there is no
        way to obtain them.
        """
        return gateway.circle_roles().to_model()

    @tool
    def request_extension(moment_id: str, seconds: int) -> dict[str, Any]:
        """Propose moving a single check-in later.

        This only proposes. The person must confirm before anything moves, and the result
        includes a preview to show them. It affects that one check-in and never the
        recurring plan.

        Args:
            moment_id: The check-in to move.
            seconds: How much later, in seconds. Maximum four hours.
        """
        return gateway.propose_extension(MomentId(moment_id), seconds).to_model()

    @tool
    def confirm_subject_okay(moment_id: str, unambiguous: bool) -> dict[str, Any]:
        """Record that the person has clearly said they are okay.

        Only call this when the person's answer is unmistakable. Pass unambiguous=false for
        anything hedged — "probably", "I think so", "I guess" — and the system will ask
        them explicitly instead. Reading a hedge as a confirmation means nobody comes.

        Args:
            moment_id: The check-in they are answering.
            unambiguous: Whether their answer was clear and unqualified.
        """
        return gateway.propose_subject_confirmation(
            MomentId(moment_id), unambiguous=unambiguous
        ).to_model()

    @tool
    def request_circle_contact(alert_id: str, role: str) -> dict[str, Any]:
        """Ask for someone in this person's Circle to be contacted, by role.

        Use this when the person asks for someone to be contacted. You name a role, never
        a person and never a number; the system resolves who that is and whether they may
        be contacted right now.

        Args:
            alert_id: The alert this concerns.
            role: PRIMARY, BACKUP or TERTIARY.
        """
        return gateway.propose_circle_contact(AlertId(alert_id), role).to_model()

    @tool
    def release_context(alert_id: str, signal: str) -> dict[str, Any]:
        """Ask for a context signal to be shared, if the person allowed it in advance.

        Only signals the person opted into, at the stage they chose. Location is off unless
        they explicitly enabled it.

        Args:
            alert_id: The alert this concerns.
            signal: location, battery, lastConnection or networkStatus.
        """
        return gateway.propose_context_release(AlertId(alert_id), signal).to_model()

    @tool
    def add_alert_note(alert_id: str, text: str) -> dict[str, Any]:
        """Attach a short factual note to an alert's timeline.

        Record what the person said, in their terms. Do not speculate about danger, and do
        not draw conclusions about their condition.

        Args:
            alert_id: The alert to annotate.
            text: The note. Maximum 500 characters.
        """
        return gateway.add_note(AlertId(alert_id), text).to_model()

    return [
        get_active_moment,
        get_alert,
        get_circle,
        request_extension,
        confirm_subject_okay,
        request_circle_contact,
        release_context,
        add_alert_note,
    ]


# Names of every tool the agent may ever have. Used by the guard test that asserts nothing
# has been added without being considered against the endpoint rule.
TOOL_NAMES = frozenset(
    {
        "get_active_moment",
        "get_alert",
        "get_circle",
        "request_extension",
        "confirm_subject_okay",
        "request_circle_contact",
        "release_context",
        "add_alert_note",
    }
)
