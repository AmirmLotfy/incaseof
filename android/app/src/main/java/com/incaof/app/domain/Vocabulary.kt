package com.incaof.app.domain

/**
 * Engineering names never reach the screen.
 *
 * PRD §3 lists the mapping and is explicit that the state machine is *never exposed*. This
 * is the single place that translation happens, so a raw enum name cannot leak into the UI
 * by someone reaching for `state.name` in a hurry.
 *
 * The strings are also deliberately non-speculative: nothing here says "danger", "risk" or
 * "emergency", because the product does not make that judgement (docs/design/COPY.md §3).
 */
object Vocabulary {
    /** Headline status for the Home screen. */
    fun status(state: AlertState?): String =
        when (state) {
            null -> "All clear"
            AlertState.SCHEDULED -> "All clear"
            AlertState.DUE, AlertState.GRACE, AlertState.SELF_CONTACT -> "Action needed"
            AlertState.CIRCLE_ESCALATION -> "Reaching your Circle"
            AlertState.CHECKING -> "Someone is checking"
            AlertState.RESOLVED -> "Resolved"
            AlertState.CANCELLED -> "Cancelled"
            AlertState.ESCALATION_EXHAUSTED -> "Unresolved"
        }

    /**
     * What the app is waiting for, in plain words.
     *
     * "Missing" is never phrased as an emergency: a missed Moment means unresolved, which
     * is a different thing and the whole reason the product can be calm.
     */
    fun explanation(state: AlertState?, subjectName: String? = null): String {
        val who = subjectName ?: "you"
        return when (state) {
            null, AlertState.SCHEDULED -> "Nothing needs your attention."
            AlertState.DUE, AlertState.GRACE -> "We're waiting for your check."
            AlertState.SELF_CONTACT -> "We're trying to reach $who."
            AlertState.CIRCLE_ESCALATION -> "We're contacting the people you chose."
            AlertState.CHECKING -> "Backup contacts are paused while they check."
            AlertState.RESOLVED -> "This was closed."
            AlertState.CANCELLED -> "You cancelled this check."
            AlertState.ESCALATION_EXHAUSTED -> "Nobody confirmed. Everyone on your plan was contacted."
        }
    }

    fun action(action: StepAction): String =
        when (action) {
            StepAction.PUSH_SUBJECT -> "Check with you"
            StepAction.SMS_SUBJECT -> "Message you"
            StepAction.CALL_SUBJECT -> "Call you"
            StepAction.MESSAGE_RESPONDER -> "Message"
            StepAction.CALL_RESPONDER -> "Call"
        }

    fun role(role: ResponderRole): String =
        when (role) {
            ResponderRole.PRIMARY -> "Primary"
            ResponderRole.BACKUP -> "Backup"
            ResponderRole.TERTIARY -> "Third"
        }

    fun release(level: ReleaseLevel): String =
        when (level) {
            ReleaseLevel.NEVER -> "Never"
            ReleaseLevel.ON_ALERT_OPEN -> "When a check is missed"
            ReleaseLevel.AFTER_SUBJECT_CALL_FAILED -> "After a failed call"
            ReleaseLevel.CIRCLE_ESCALATION -> "Circle escalation only"
        }

    fun planType(type: PlanType): String =
        when (type) {
            PlanType.ROUTINE -> "Routine"
            PlanType.JOURNEY -> "Journey"
            PlanType.SOLO -> "Solo"
            PlanType.RECOVERY -> "Recovery"
        }

    /** Timeline entries, translated from the audit event types the backend records. */
    fun timelineEvent(event: String): String =
        when (event) {
            "MOMENT_DUE" -> "Check requested"

            // Queued, sent and delivered are three separate facts, and the timeline keeps
            // them apart. A carrier taking custody of a text is not a phone receiving it —
            // and someone reading this is deciding whether to go round in person.
            "ACTION_QUEUED" -> "Reminder queued"

            "ACTION_ACCEPTED" -> "Text sent"

            "ACTION_DELIVERED" -> "Text delivered"

            "ACTION_UNDELIVERED" -> "Text did not arrive"

            "ACTION_FAILED" -> "Could not send"

            "ACTION_SUPPRESSED" -> "Not sent — already resolved"

            "CHANNEL_UNAVAILABLE" -> "Call unavailable"

            "CONTACT_DENIED" -> "Contact not permitted"

            "SUBJECT_CONFIRMED" -> "You confirmed"

            "ALERT_CLAIMED" -> "Someone started checking"

            "RESPONDER_VERIFIED" -> "Confirmed by your Circle"

            "STATE_CIRCLE_ESCALATION" -> "Your Circle was contacted"

            "STATE_CHECKING" -> "Someone is checking"

            "STATE_RESOLVED" -> "Resolved"

            else -> event.lowercase().replace('_', ' ').replaceFirstChar { it.uppercase() }
        }
}
