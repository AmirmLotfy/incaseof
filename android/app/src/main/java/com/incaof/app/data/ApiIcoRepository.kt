package com.incaof.app.data

import com.incaof.app.core.network.CircleMemberDto
import com.incaof.app.core.network.IcoApi
import com.incaof.app.core.network.MomentDto
import com.incaof.app.core.network.PlanDto
import com.incaof.app.core.network.TimelineDto
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
import retrofit2.Response
import java.time.Instant

/** Talks to the deployed API. */
class ApiIcoRepository(
    private val api: IcoApi,
) : IcoRepository {
    override suspend fun nextMoment(): Result<Moment?> =
        runCatching {
            val response = api.nextMoment()
            // 404 means nothing is expected right now, which is the normal, good state — not a
            // failure to surface to someone who just opened the app.
            if (response.code() == 404) return@runCatching null
            response.requireBody().toDomain()
        }

    override suspend fun plans(): Result<List<Plan>> =
        runCatching {
            api.plans().requireBody().map { it.toDomain() }
        }

    override suspend fun plan(planId: String): Result<Plan> =
        runCatching {
            api.plan(planId).requireBody().toDomain()
        }

    override suspend fun circle(): Result<List<CircleMember>> =
        runCatching {
            api.circle().requireBody().map { it.toDomain() }
        }

    override suspend fun history(): Result<List<ResolvedMoment>> =
        runCatching {
            // History is derived from resolved Moments; the dedicated endpoint lands with the
            // History surface in Phase 4. Returning empty is honest — the screen says so.
            emptyList()
        }

    override suspend fun timeline(alertId: String): Result<Alert> =
        runCatching {
            api.timeline(alertId).requireBody().toDomain()
        }

    override suspend fun confirmMoment(momentId: String, idempotencyKey: String, source: ConfirmSource): Result<Unit> =
        runCatching {
            api.confirmMoment(momentId, source.wireValue, idempotencyKey).requireBody()
            Unit
        }

    override suspend fun extendMoment(momentId: String, seconds: Int): Result<Moment> =
        runCatching {
            api
                .extendMoment(
                    momentId,
                    com.incaof.app.core.network
                        .ExtendRequest(seconds),
                ).requireBody()
                .toDomain()
        }
}

private fun <T> Response<T>.requireBody(): T {
    if (!isSuccessful) {
        throw ApiException(code(), errorBody()?.string().orEmpty())
    }
    return body() ?: throw ApiException(code(), "empty body")
}

/** Carries the HTTP status so callers can distinguish "not permitted" from "unreachable". */
class ApiException(
    val status: Int,
    val detail: String,
) : RuntimeException("HTTP $status: $detail")

internal fun MomentDto.toDomain() =
    Moment(
        id = momentId,
        planLabel = planLabel,
        dueAt = Instant.parse(dueAt),
        graceUntil = Instant.parse(graceUntil),
        alertState = alertState?.let { runCatching { AlertState.valueOf(it) }.getOrNull() },
    )

internal fun PlanDto.toDomain() =
    Plan(
        id = planId,
        label = label,
        type = runCatching { PlanType.valueOf(type) }.getOrDefault(PlanType.ROUTINE),
        cadence = cadence,
        timeOfDay = timeOfDay,
        active = active,
        steps =
            steps.map {
                EscalationStep(
                    sequence = it.sequence,
                    offsetSeconds = it.offsetSeconds,
                    action =
                        runCatching { StepAction.valueOf(it.action) }
                            .getOrDefault(StepAction.PUSH_SUBJECT),
                    targetRole =
                        it.targetRole?.let { role ->
                            runCatching { ResponderRole.valueOf(role) }.getOrNull()
                        },
                )
            },
        contextPolicy =
            contextPolicy.map {
                ContextRelease(
                    signal = it.signal,
                    level =
                        runCatching { ReleaseLevel.valueOf(it.level) }
                            .getOrDefault(ReleaseLevel.NEVER),
                )
            },
        circle = circle.map { it.toDomain() },
    )

internal fun CircleMemberDto.toDomain() =
    CircleMember(
        id = id,
        displayName = displayName,
        relationship = relationship,
        role = runCatching { ResponderRole.valueOf(role) }.getOrDefault(ResponderRole.PRIMARY),
        accepted = accepted,
        phoneVerified = phoneVerified,
    )

internal fun TimelineDto.toDomain() =
    Alert(
        id = alertId,
        state = AlertState.SCHEDULED,
        planLabel = "",
        expectedAt = Instant.EPOCH,
        ownerName = null,
        leaseExpiresAt = null,
        timeline =
            events.map {
                TimelineEvent(
                    at = runCatching { Instant.parse(it.at) }.getOrDefault(Instant.EPOCH),
                    actor = it.actor,
                    event = it.event,
                    metadata = it.metadata,
                )
            },
    )
