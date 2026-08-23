package com.incaof.app.data

import com.incaof.app.domain.Alert
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.CircleMember
import com.incaof.app.domain.ContextRelease
import com.incaof.app.domain.EscalationStep
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import com.incaof.app.domain.ReleaseLevel
import com.incaof.app.domain.ResolvedMoment
import com.incaof.app.domain.ResponderRole
import com.incaof.app.domain.StepAction
import com.incaof.app.domain.TimelineEvent
import kotlinx.coroutines.flow.MutableStateFlow
import java.time.Clock
import java.time.Duration
import java.time.Instant

/**
 * In-memory data, for running the app before the stack is deployed.
 *
 * This is a data source, not a second product. Every screen, view model and state
 * transition above it is the same code the API implementation drives; what differs is
 * where the bytes come from. There is no branch anywhere in the UI that asks which
 * repository it is talking to.
 *
 * The escalation ladder below is the one from the build contract §60, so what the app
 * shows locally is what the deployed plan would actually do.
 */
class LocalIcoRepository(
    private val clock: Clock = Clock.systemUTC(),
    initialState: AlertState? = null,
) : IcoRepository {
    private val alertState = MutableStateFlow(initialState)
    private val confirmed = MutableStateFlow(false)
    private var dueAt: Instant = clock.instant().plus(Duration.ofHours(3))

    private val maya =
        CircleMember(
            id = "member-maya",
            displayName = "Maya",
            relationship = "Sister",
            role = ResponderRole.PRIMARY,
            accepted = true,
            phoneVerified = true,
        )

    private val omar =
        CircleMember(
            id = "member-omar",
            displayName = "Omar",
            relationship = "Friend",
            role = ResponderRole.BACKUP,
            accepted = true,
            phoneVerified = true,
        )

    private val eveningCheck =
        Plan(
            id = "plan-evening",
            label = "Evening check",
            type = PlanType.ROUTINE,
            cadence = "Daily",
            timeOfDay = "21:00",
            active = true,
            steps =
                listOf(
                    EscalationStep(1, 0, StepAction.PUSH_SUBJECT, null),
                    EscalationStep(2, 600, StepAction.PUSH_SUBJECT, null),
                    EscalationStep(3, 1200, StepAction.SMS_SUBJECT, null),
                    EscalationStep(4, 1500, StepAction.MESSAGE_RESPONDER, ResponderRole.PRIMARY),
                    EscalationStep(5, 2700, StepAction.MESSAGE_RESPONDER, ResponderRole.BACKUP),
                ),
            contextPolicy =
                listOf(
                    ContextRelease("Location", ReleaseLevel.NEVER),
                    ContextRelease("Battery", ReleaseLevel.AFTER_SUBJECT_CALL_FAILED),
                    ContextRelease("Last connection", ReleaseLevel.CIRCLE_ESCALATION),
                ),
            circle = listOf(maya, omar),
        )

    private val journeyHome =
        Plan(
            id = "plan-journey",
            label = "Journey home",
            type = PlanType.JOURNEY,
            cadence = "When travelling",
            timeOfDay = "00:00",
            active = false,
            steps =
                listOf(
                    EscalationStep(1, 0, StepAction.PUSH_SUBJECT, null),
                    EscalationStep(2, 600, StepAction.SMS_SUBJECT, null),
                    EscalationStep(3, 1200, StepAction.MESSAGE_RESPONDER, ResponderRole.PRIMARY),
                ),
            contextPolicy = listOf(ContextRelease("Location", ReleaseLevel.NEVER)),
            circle = listOf(maya),
        )

    override suspend fun nextMoment(): Result<Moment?> =
        Result.success(
            if (confirmed.value) {
                null
            } else {
                Moment(
                    id = "moment-evening",
                    planLabel = eveningCheck.label,
                    dueAt = dueAt,
                    graceUntil = dueAt,
                    alertState = alertState.value,
                )
            },
        )

    override suspend fun plans(): Result<List<Plan>> = Result.success(listOf(eveningCheck, journeyHome))

    override suspend fun plan(planId: String): Result<Plan> =
        plans().mapCatching { all ->
            all.firstOrNull { it.id == planId } ?: error("no such plan")
        }

    override suspend fun circle(): Result<List<CircleMember>> = Result.success(listOf(maya, omar))

    override suspend fun history(): Result<List<ResolvedMoment>> {
        val now = clock.instant()
        return Result.success(
            listOf(
                ResolvedMoment(
                    id = "moment-1",
                    planLabel = "Evening check",
                    resolvedAt = now.minus(Duration.ofHours(20)),
                    resolvedBy = "You",
                    method = "You confirmed",
                ),
                ResolvedMoment(
                    id = "moment-2",
                    planLabel = "Journey home",
                    resolvedAt = now.minus(Duration.ofHours(44)),
                    resolvedBy = "You",
                    method = "You confirmed",
                ),
                ResolvedMoment(
                    id = "moment-3",
                    planLabel = "Morning check",
                    resolvedAt = now.minus(Duration.ofDays(3)),
                    resolvedBy = "Maya",
                    method = "Maya verified contact",
                ),
            ),
        )
    }

    override suspend fun timeline(alertId: String): Result<Alert> {
        val expected = dueAt
        return Result.success(
            Alert(
                id = alertId,
                state = alertState.value ?: AlertState.SCHEDULED,
                planLabel = eveningCheck.label,
                expectedAt = expected,
                ownerName = null,
                leaseExpiresAt = null,
                timeline =
                    listOf(
                        TimelineEvent(expected, "SYSTEM", "MOMENT_DUE"),
                        TimelineEvent(expected.plus(Duration.ofMinutes(10)), "SYSTEM", "ACTION_QUEUED"),
                        TimelineEvent(expected.plus(Duration.ofMinutes(20)), "WORKER", "ACTION_ACCEPTED"),
                    ),
            ),
        )
    }

    override suspend fun confirmMoment(momentId: String, idempotencyKey: String, source: ConfirmSource): Result<Unit> {
        confirmed.value = true
        alertState.value = AlertState.RESOLVED
        return Result.success(Unit)
    }

    override suspend fun extendMoment(momentId: String, seconds: Int): Result<Moment> {
        dueAt = dueAt.plusSeconds(seconds.toLong())
        return nextMoment().mapCatching { it ?: error("no moment") }
    }

    /** Drives the app into the waiting state, for previews and manual checks. */
    fun simulateDue() {
        confirmed.value = false
        dueAt = clock.instant()
        alertState.value = AlertState.SELF_CONTACT
    }
}
