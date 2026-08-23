package com.incaof.app.data

import com.incaof.app.domain.Alert
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.CircleMember
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import com.incaof.app.domain.ResolvedMoment
import java.time.Instant

/**
 * A repository that records what it was asked to do.
 *
 * Tests assert on the *call*, not just the outcome: whether a confirmation was sent with a
 * derived idempotency key matters as much as whether the UI updated, because that key is
 * what stops a double tap from racing.
 */
class RecordingRepository(
    private var moment: Moment? = null,
    /** Makes reads fail, e.g. the initial load. */
    private val failWith: Throwable? = null,
    /** Makes writes fail while reads still succeed — an offline confirmation. */
    private val failOnWrite: Throwable? = null,
) : IcoRepository {
    val confirmCalls = mutableListOf<Triple<String, String, ConfirmSource>>()
    var extendCalls = mutableListOf<Pair<String, Int>>()

    override suspend fun nextMoment(): Result<Moment?> = failWith?.let { Result.failure(it) } ?: Result.success(moment)

    override suspend fun plans(): Result<List<Plan>> = Result.success(emptyList())

    override suspend fun plan(planId: String): Result<Plan> = Result.failure(NoSuchElementException(planId))

    override suspend fun circle(): Result<List<CircleMember>> = Result.success(emptyList())

    override suspend fun history(): Result<List<ResolvedMoment>> = Result.success(emptyList())

    override suspend fun timeline(alertId: String): Result<Alert> = Result.failure(NoSuchElementException(alertId))

    override suspend fun confirmMoment(momentId: String, idempotencyKey: String, source: ConfirmSource): Result<Unit> {
        confirmCalls += Triple(momentId, idempotencyKey, source)
        (failOnWrite ?: failWith)?.let { return Result.failure(it) }
        moment = null
        return Result.success(Unit)
    }

    override suspend fun extendMoment(momentId: String, seconds: Int): Result<Moment> {
        extendCalls += momentId to seconds
        (failOnWrite ?: failWith)?.let { return Result.failure(it) }
        val extended = moment?.copy(dueAt = moment!!.dueAt.plusSeconds(seconds.toLong()))
        moment = extended
        return extended?.let { Result.success(it) }
            ?: Result.failure(IllegalStateException("no moment"))
    }

    companion object {
        fun waiting(now: Instant = Instant.parse("2026-08-26T21:00:00Z")) =
            RecordingRepository(
                Moment(
                    id = "moment-evening",
                    planLabel = "Evening check",
                    dueAt = now,
                    graceUntil = now,
                    alertState = AlertState.SELF_CONTACT,
                ),
            )
    }
}
