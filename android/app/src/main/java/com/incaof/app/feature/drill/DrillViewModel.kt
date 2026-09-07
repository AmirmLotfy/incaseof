package com.incaof.app.feature.drill

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.Plan
import com.incaof.app.domain.Vocabulary
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class DrillViewModel(
    private val repository: IcoRepository,
    private val plan: Plan,
) : ViewModel() {
    private val _state = MutableStateFlow<DrillUiState>(DrillUiState.Active(plan = plan))
    val state: StateFlow<DrillUiState> = _state.asStateFlow()

    init {
        startDrill()
    }

    fun startDrill() {
        viewModelScope.launch {
            repository
                .testPlan(plan.id)
                .onFailure { error ->
                    _state.value = DrillUiState.Failed(error.message ?: "Failed to start drill")
                    return@launch
                }

            pollAuthoritativeState()
        }
    }

    private suspend fun pollAuthoritativeState() {
        repeat(MAX_POLLS) { attempt ->
            if (attempt > 0) delay(POLL_INTERVAL_MS)

            val moment = repository.nextMoment().getOrNull()
            if (moment == null) {
                updateStatus("Waiting for the deployed Moment…")
                return@repeat
            }

            val alert = moment.alertId?.let { repository.timeline(it).getOrNull() }
            val timeline = alert?.timeline.orEmpty()
            val stateName = alert?.state?.name ?: moment.alertState?.name ?: momentStatus(moment.alertId)
            val steps =
                timeline.mapIndexed { index, event ->
                    DrillStep(
                        id = "${event.at}-$index",
                        title = Vocabulary.timelineEvent(event.event),
                        detail = "${event.actor} · ${event.at}",
                    )
                }

            val complete = alert?.state?.isTerminal == true
            _state.value =
                DrillUiState.Active(
                    plan = plan,
                    steps = steps,
                    telemetry =
                        DrillTelemetry(
                            alertId = moment.alertId ?: "Not opened",
                            alertState = stateName,
                            timeScale = if (moment.isDrill) "${moment.timeScale}x" else "Normal",
                            eventCount = timeline.size.toString(),
                            lastActor = timeline.lastOrNull()?.actor ?: "None",
                            leaseExpiresAt = alert?.leaseExpiresAt?.toString() ?: "None",
                        ),
                    statusMessage =
                        when {
                            complete -> "The backend recorded a terminal Alert state."
                            moment.alertId == null -> "Waiting for EventBridge Scheduler to open the Alert…"
                            else -> "Following the deployed Alert timeline…"
                        },
                    isComplete = complete,
                )
            if (complete) return
        }

        updateStatus("The Drill is still open. Reopen this screen to continue checking live state.")
    }

    private fun updateStatus(message: String) {
        val current = _state.value
        if (current is DrillUiState.Active) _state.value = current.copy(statusMessage = message)
    }

    private fun momentStatus(alertId: String?): String = if (alertId == null) "SCHEDULED" else "OPEN"

    private companion object {
        const val POLL_INTERVAL_MS = 2_000L
        const val MAX_POLLS = 90
    }
}
