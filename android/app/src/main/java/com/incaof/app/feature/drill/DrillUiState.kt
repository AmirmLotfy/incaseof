package com.incaof.app.feature.drill

import com.incaof.app.domain.Plan
import com.incaof.app.ui.UiMessage

/** A single audit event returned by the deployed Alert timeline. */
data class DrillStep(
    val id: String,
    val event: String,
    val actor: String,
    val at: String,
    val completed: Boolean = true,
    val inProgress: Boolean = false,
)

/** Only backend-supplied facts. No browser/device-derived AWS or policy claims. */
data class DrillTelemetry(
    val alertId: String? = null,
    val alertState: String = "STARTING",
    val timeScale: Double? = null,
    val isDrill: Boolean = false,
    val eventCount: Int = 0,
    val lastActor: String? = null,
    val leaseExpiresAt: String? = null,
)

enum class DrillStatus {
    STARTING,
    WAITING_MOMENT,
    TERMINAL,
    WAITING_SCHEDULER,
    FOLLOWING,
    STILL_OPEN,
}

sealed interface DrillUiState {
    data class Active(
        val plan: Plan,
        val steps: List<DrillStep> = emptyList(),
        val telemetry: DrillTelemetry = DrillTelemetry(),
        val status: DrillStatus = DrillStatus.STARTING,
        val isComplete: Boolean = false,
    ) : DrillUiState

    data class Failed(
        val message: UiMessage,
    ) : DrillUiState
}
