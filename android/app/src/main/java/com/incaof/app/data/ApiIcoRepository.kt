package com.incaof.app.data

import com.incaof.app.core.network.CircleMemberDto
import com.incaof.app.core.network.CompilePlanRequest
import com.incaof.app.core.network.CreatePlanRequest
import com.incaof.app.core.network.IcoApi
import com.incaof.app.core.network.InviteCircleRequest
import com.incaof.app.core.network.MomentDto
import com.incaof.app.core.network.PlanDto
import com.incaof.app.core.network.RegisterDeviceRequest
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
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import retrofit2.Response
import java.time.Instant

/** Talks to the deployed API. */
class ApiIcoRepository(
    private val api: IcoApi,
    private val allowDeviceRegistration: Boolean = true,
) : IcoRepository {
    override suspend fun compilePlan(description: String, timezone: String): Result<CompiledPlanDraft> =
        runCatching {
            val response = api.compilePlan(CompilePlanRequest(description, timezone)).requireBody()
            CompiledPlanDraft(
                compiledPlanJson = response.compiledPlan.toString(),
                preview =
                    Plan(
                        id = "preview",
                        label = response.plan.label,
                        type = runCatching { PlanType.valueOf(response.plan.type) }.getOrDefault(PlanType.ROUTINE),
                        cadence = response.compiledPlan["trigger"]?.toString().orEmpty(),
                        timeOfDay = "",
                        active = false,
                        steps =
                            response.plan.steps.map {
                                EscalationStep(
                                    it.sequence,
                                    it.offsetSeconds,
                                    runCatching { StepAction.valueOf(it.action) }.getOrDefault(StepAction.PUSH_SUBJECT),
                                    it.targetRole?.let { role ->
                                        runCatching { ResponderRole.valueOf(role) }.getOrNull()
                                    },
                                )
                            },
                    ),
                warnings = response.warnings,
            )
        }

    override suspend fun createPlan(draft: CompiledPlanDraft): Result<Plan> =
        runCatching {
            val document = Json.parseToJsonElement(draft.compiledPlanJson) as JsonObject
            api.createPlan(CreatePlanRequest(document)).requireBody().toDomain()
        }

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
            api
                .plans()
                .requireBody()
                .plans
                .map { it.toDomain() }
        }

    override suspend fun plan(planId: String): Result<Plan> =
        runCatching {
            api.plan(planId).requireBody().toDomain()
        }

    override suspend fun activatePlan(planId: String): Result<Plan> =
        planMutation { key -> api.activatePlan(planId, key) }

    override suspend fun pausePlan(planId: String): Result<Plan> =
        planMutation { key -> api.pausePlan(planId, key) }

    override suspend fun resumePlan(planId: String): Result<Plan> =
        planMutation { key -> api.resumePlan(planId, key) }

    override suspend fun circle(): Result<List<CircleMember>> =
        runCatching {
            api
                .circle()
                .requireBody()
                .members
                .map { it.toDomain() }
        }

    override suspend fun inviteCircleMember(
        displayName: String,
        relationship: String?,
        role: ResponderRole,
    ): Result<String> =
        runCatching {
            val invitation =
                api
                    .inviteCircleMember(
                        InviteCircleRequest(displayName, relationship, role.name),
                        java.util.UUID
                            .randomUUID()
                            .toString(),
                    ).requireBody()
            invitation.inviteUrl
        }

    override suspend fun history(): Result<List<ResolvedMoment>> =
        runCatching {
            api.history().requireBody().history.map {
                ResolvedMoment(
                    id = it.id,
                    planLabel = it.planLabel,
                    resolvedAt = Instant.parse(it.resolvedAt),
                    resolvedBy = it.resolvedBy,
                    method = it.method,
                )
            }
        }

    override suspend fun timeline(alertId: String): Result<Alert> =
        runCatching {
            val summary = api.alert(alertId).requireBody()
            val audit = api.timeline(alertId).requireBody()
            Alert(
                id = summary.alertId,
                state = runCatching { AlertState.valueOf(summary.state) }.getOrDefault(AlertState.SCHEDULED),
                planLabel = summary.planLabel,
                expectedAt = summary.openedAt?.let { Instant.parse(it) } ?: Instant.EPOCH,
                ownerName = summary.leaseOwner,
                leaseExpiresAt = summary.leaseExpiresAt?.let { Instant.parse(it) },
                timeline = audit.toDomain().timeline,
            )
        }

    override suspend fun momentIdForAlert(alertId: String): Result<String> =
        runCatching { api.alert(alertId).requireBody().momentId }

    override suspend fun confirmMoment(momentId: String, idempotencyKey: String, source: ConfirmSource): Result<Unit> =
        runCatching {
            api.confirmMoment(momentId, source.wireValue, idempotencyKey).requireBody()
            return@runCatching
        }

    override suspend fun extendMoment(momentId: String, seconds: Int): Result<Moment> =
        runCatching {
            api
                .extendMoment(
                    momentId,
                    com.incaof.app.core.network
                        .ExtendRequest(seconds),
                    java.util.UUID
                        .randomUUID()
                        .toString(),
                ).requireBody()
                .toDomain()
        }

    override suspend fun testPlan(planId: String): Result<Unit> =
        runCatching {
            api
                .testPlan(
                    planId,
                    java.util.UUID
                        .randomUUID()
                        .toString(),
                ).requireBody()
            return@runCatching
        }

    override suspend fun registerDevice(deviceId: String, registrationToken: String): Result<Unit> =
        if (!allowDeviceRegistration) {
            Result.failure(IllegalStateException("Demo sessions cannot register delivery devices"))
        } else {
            runCatching {
                val registered =
                    api.registerDevice(RegisterDeviceRequest(deviceId, registrationToken)).requireBody()
                require(registered.deviceId == deviceId) { "device registration response mismatch" }
                return@runCatching
            }
        }

    private suspend fun planMutation(
        request: suspend (String) -> Response<PlanDto>,
    ): Result<Plan> =
        runCatching {
            request(
                java.util.UUID
                    .randomUUID()
                    .toString(),
            ).requireBody().toDomain()
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
        alertId = alertId,
        isDrill = isDrill,
        timeScale = timeScale,
    )

internal fun PlanDto.toDomain() =
    Plan(
        id = planId,
        label = label,
        type = runCatching { PlanType.valueOf(type) }.getOrDefault(PlanType.ROUTINE),
        cadence = cadence,
        timeOfDay = timeOfDay,
        active = active,
        paused = paused,
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
        id = memberId,
        displayName = displayName,
        relationship = relationship,
        role = runCatching { ResponderRole.valueOf(role) }.getOrDefault(ResponderRole.PRIMARY),
        accepted = status == "ACCEPTED",
        phoneVerified = false,
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
