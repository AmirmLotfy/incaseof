package com.incaof.app.feature.drill

import com.incaof.app.domain.Plan

/** A single audit event returned by the deployed Alert timeline. */
data class DrillStep(
    val id: String,
    val title: String,
    val detail: String,
    val completed: Boolean = true,
    val inProgress: Boolean = false,
)

/** Only backend-supplied facts. No browser/device-derived AWS or policy claims. */
data class DrillTelemetry(
    val alertId: String = "Awaiting Alert",
    val alertState: String = "STARTING",
    val timeScale: String = "Awaiting server",
    val eventCount: String = "0",
    val lastActor: String = "None",
    val leaseExpiresAt: String = "None",
)

sealed interface DrillUiState {
    data class Active(
        val plan: Plan,
        val steps: List<DrillStep> = emptyList(),
        val telemetry: DrillTelemetry = DrillTelemetry(),
        val statusMessage: String = "Starting the deployed Drill workflow…",
        val isComplete: Boolean = false,
    ) : DrillUiState

    data class Failed(
        val message: String,
    ) : DrillUiState
}
