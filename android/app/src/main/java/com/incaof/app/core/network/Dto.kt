package com.incaof.app.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

/**
 * Wire types.
 *
 * Mirrors packages/contracts/openapi.yaml. Kept separate from the domain models so a wire
 * change cannot silently reshape what the UI believes, and so an unexpected field is a
 * parse decision rather than a surprise in a composable.
 *
 * No DTO here carries a phone number or any other contact endpoint, because no endpoint
 * returns one — that is a property of the API, asserted on the server side, and this is
 * simply the shape that follows from it.
 */

@Serializable
data class MomentDto(
    val momentId: String,
    val planLabel: String,
    val dueAt: String,
    val graceUntil: String,
    val alertState: String? = null,
    val alertId: String? = null,
    val isDrill: Boolean = false,
    val timeScale: Double = 1.0,
)

@Serializable
data class EscalationStepDto(
    val sequence: Int,
    val offsetSeconds: Int,
    val action: String,
    val targetRole: String? = null,
)

@Serializable
data class ContextReleaseDto(
    val signal: String,
    val level: String,
)

@Serializable
data class CircleMemberDto(
    val memberId: String,
    val displayName: String,
    val relationship: String? = null,
    val role: String,
    val status: String,
)

@Serializable
data class PlansResponseDto(
    val plans: List<PlanDto> = emptyList(),
)

@Serializable
data class PlanPreviewDto(
    val label: String,
    val type: String,
    val timezone: String,
    val graceSeconds: Int,
    val steps: List<EscalationStepDto> = emptyList(),
)

@Serializable
data class CompilePlanRequest(
    val utterance: String,
    val timezone: String,
)

@Serializable
data class CompilePlanResponseDto(
    val active: Boolean,
    val requiresConfirmation: Boolean,
    val compiledPlan: JsonObject,
    val plan: PlanPreviewDto,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class CreatePlanRequest(
    val compiledPlan: JsonObject,
)

@Serializable
data class CircleResponseDto(
    val circleId: String? = null,
    val ownerDisplayName: String? = null,
    val members: List<CircleMemberDto> = emptyList(),
)

@Serializable
data class InviteCircleRequest(
    val displayName: String,
    val relationship: String? = null,
    val role: String,
    val priority: Int = 1,
)

@Serializable
data class InvitationResponseDto(
    val invitationId: String,
    val status: String,
    val inviteUrl: String,
)

@Serializable
data class RegisterDeviceRequest(
    val deviceId: String,
    val registrationToken: String,
)

@Serializable
data class RegisterDeviceResponseDto(
    val deviceId: String,
)

@Serializable
data class PlanDto(
    val planId: String,
    val label: String,
    val type: String,
    val cadence: String,
    val timeOfDay: String,
    val active: Boolean,
    val paused: Boolean = false,
    val steps: List<EscalationStepDto> = emptyList(),
    val contextPolicy: List<ContextReleaseDto> = emptyList(),
    val circle: List<CircleMemberDto> = emptyList(),
)

@Serializable
data class TimelineEntryDto(
    val at: String,
    val actor: String,
    val event: String,
    val metadata: Map<String, String> = emptyMap(),
)

@Serializable
data class TimelineDto(
    val alertId: String,
    val events: List<TimelineEntryDto> = emptyList(),
)

@Serializable
data class AlertSummaryDto(
    val alertId: String,
    val momentId: String,
    val planLabel: String,
    val state: String,
    val openedAt: String? = null,
    val leaseOwner: String? = null,
    val leaseExpiresAt: String? = null,
)

@Serializable
data class HistoryEntryDto(
    val id: String,
    val planLabel: String,
    val resolvedAt: String,
    val resolvedBy: String,
    val method: String,
)

@Serializable
data class HistoryResponseDto(
    val history: List<HistoryEntryDto> = emptyList(),
)

@Serializable
data class ConfirmResponseDto(
    val alertId: String,
    val state: String,
)

@Serializable
data class ClaimResponseDto(
    val alertId: String,
    val state: String,
    val leaseExpiresAt: String,
    /** Always false. Acknowledged is not resolved, and the wire says so out loud. */
    val resolved: Boolean = false,
)

@Serializable
data class DrillResponseDto(
    val status: String,
    val planId: String,
    val timeScale: Double,
    val message: String,
)

/** RFC 9457 problem detail. `reason_code` is stable; `title` is not for parsing. */
@Serializable
data class ProblemDto(
    val title: String = "",
    val status: Int = 0,
    @SerialName("reason_code") val reasonCode: String = "",
)
