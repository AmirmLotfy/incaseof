package com.incaof.app.domain

import java.time.Instant

// What the app knows.
//
// These mirror the API contract in packages/contracts/openapi.yaml. They are read models:
// the device never decides anything about safety state, it displays what the backend says.
// DynamoDB is authoritative; this is a view of it.
//
// Note what is absent: no phone numbers, no contact endpoints, anywhere. The API never
// returns them, so there is nothing here to hold one.

/** Alert lifecycle, mirroring docs/PRODUCT-STATES.md. Never shown to the user verbatim. */
enum class AlertState {
    SCHEDULED,
    DUE,
    GRACE,
    SELF_CONTACT,
    CIRCLE_ESCALATION,
    CHECKING,
    RESOLVED,
    ESCALATION_EXHAUSTED,
    CANCELLED,
    ;

    val isTerminal: Boolean
        get() = this == RESOLVED || this == ESCALATION_EXHAUSTED || this == CANCELLED

    /** Whether the subject is being asked for something right now. */
    val needsSubjectAction: Boolean
        get() = this == DUE || this == GRACE || this == SELF_CONTACT
}

enum class PlanType { ROUTINE, JOURNEY, SOLO, RECOVERY }

enum class ResponderRole { PRIMARY, BACKUP, TERTIARY }

enum class StepAction {
    PUSH_SUBJECT,
    SMS_SUBJECT,
    CALL_SUBJECT,
    MESSAGE_RESPONDER,
    CALL_RESPONDER,
    ;

    val isSubjectDirected: Boolean
        get() = this == PUSH_SUBJECT || this == SMS_SUBJECT || this == CALL_SUBJECT
}

enum class ReleaseLevel { NEVER, ON_ALERT_OPEN, AFTER_SUBJECT_CALL_FAILED, CIRCLE_ESCALATION }

/** One rung of the ladder, as the plan detail screen shows it. */
data class EscalationStep(
    val sequence: Int,
    val offsetSeconds: Int,
    val action: StepAction,
    val targetRole: ResponderRole?,
)

data class ContextRelease(
    val signal: String,
    val level: ReleaseLevel,
)

data class CircleMember(
    val id: String,
    val displayName: String,
    val relationship: String?,
    val role: ResponderRole,
    val accepted: Boolean,
    val phoneVerified: Boolean,
)

/** The next thing expected of the subject. */
data class Moment(
    val id: String,
    val planLabel: String,
    val dueAt: Instant,
    val graceUntil: Instant,
    val alertState: AlertState?,
    val alertId: String? = null,
    val isDrill: Boolean = false,
    val timeScale: Double = 1.0,
) {
    /** True when In Case of is currently waiting on this person. */
    val isWaitingOnMe: Boolean
        get() = alertState?.needsSubjectAction == true
}

data class Plan(
    val id: String,
    val label: String,
    val type: PlanType,
    val cadence: String,
    val timeOfDay: String,
    val active: Boolean,
    val paused: Boolean = false,
    val steps: List<EscalationStep> = emptyList(),
    val contextPolicy: List<ContextRelease> = emptyList(),
    val circle: List<CircleMember> = emptyList(),
)

data class TimelineEvent(
    val at: Instant,
    val actor: String,
    val event: String,
    val metadata: Map<String, String> = emptyMap(),
)

data class Alert(
    val id: String,
    val state: AlertState,
    val planLabel: String,
    val expectedAt: Instant,
    val ownerName: String?,
    val leaseExpiresAt: Instant?,
    val timeline: List<TimelineEvent> = emptyList(),
)

/** A closed Moment, for History. */
data class ResolvedMoment(
    val id: String,
    val planLabel: String,
    val resolvedAt: Instant,
    val resolvedBy: String,
    val method: String,
)
