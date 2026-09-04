package com.incaof.app.data

import com.incaof.app.domain.Alert
import com.incaof.app.domain.CircleMember
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import com.incaof.app.domain.ResolvedMoment

data class CompiledPlanDraft(
    val compiledPlanJson: String,
    val preview: Plan,
    val warnings: List<String>,
)

/**
 * Everything the app reads and does.
 *
 * The device never decides anything about safety state. Confirming a Moment sends an
 * intent to the backend and reflects the answer; it does not resolve anything locally and
 * then sync. A local decision could disagree with the authoritative one, and for an Alert
 * that disagreement means somebody is or is not being contacted.
 */
interface IcoRepository {
    suspend fun compilePlan(description: String, timezone: String): Result<CompiledPlanDraft>

    suspend fun createPlan(draft: CompiledPlanDraft): Result<Plan>

    suspend fun nextMoment(): Result<Moment?>

    suspend fun plans(): Result<List<Plan>>

    suspend fun plan(planId: String): Result<Plan>

    suspend fun activatePlan(planId: String): Result<Plan>

    suspend fun pausePlan(planId: String): Result<Plan>

    suspend fun resumePlan(planId: String): Result<Plan>

    suspend fun circle(): Result<List<CircleMember>>

    suspend fun inviteCircleMember(
        displayName: String,
        relationship: String?,
        role: com.incaof.app.domain.ResponderRole,
    ): Result<String>

    suspend fun history(): Result<List<ResolvedMoment>>

    suspend fun timeline(alertId: String): Result<Alert>

    suspend fun momentIdForAlert(alertId: String): Result<String>

    /**
     * "I'm okay."
     *
     * [idempotencyKey] is supplied by the caller and stable for one user intent, so a retry
     * after a dropped connection confirms the same Moment rather than racing a new one.
     */
    suspend fun confirmMoment(momentId: String, idempotencyKey: String, source: ConfirmSource): Result<Unit>

    suspend fun extendMoment(momentId: String, seconds: Int): Result<Moment>

    /**
     * Drill Mode — run the real workflow on a compressed schedule (§25).
     */
    suspend fun testPlan(planId: String): Result<Unit>

    suspend fun registerDevice(deviceId: String, registrationToken: String): Result<Unit>
}

/**
 * Where a confirmation physically came from.
 *
 * Recorded separately from the method: "the subject confirmed in the app" and "the subject
 * confirmed from the lock screen" are the same decision through different surfaces, and the
 * audit trail should be able to tell them apart later.
 */
enum class ConfirmSource(
    val wireValue: String,
) {
    APP("app"),
    NOTIFICATION("notification"),
}
