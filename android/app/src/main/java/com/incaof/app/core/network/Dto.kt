package com.incaof.app.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

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
    val id: String,
    val displayName: String,
    val relationship: String? = null,
    val role: String,
    val accepted: Boolean,
    val phoneVerified: Boolean,
)

@Serializable
data class PlanDto(
    val planId: String,
    val label: String,
    val type: String,
    val cadence: String,
    val timeOfDay: String,
    val active: Boolean,
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

/** RFC 9457 problem detail. `reason_code` is stable; `title` is not for parsing. */
@Serializable
data class ProblemDto(
    val title: String = "",
    val status: Int = 0,
    @SerialName("reason_code") val reasonCode: String = "",
)
