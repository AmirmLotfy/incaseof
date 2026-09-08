package com.incaof.app.feature.drill

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.Plan
import com.incaof.app.ui.UiMessage
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
                    _state.value = DrillUiState.Failed(UiMessage.GENERIC)
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
                updateStatus(DrillStatus.WAITING_MOMENT)
                return@repeat
            }

            val alert = moment.alertId?.let { repository.timeline(it).getOrNull() }
            val timeline = alert?.timeline.orEmpty()
            val stateName = alert?.state?.name ?: moment.alertState?.name ?: momentStatus(moment.alertId)
            val steps =
                timeline.mapIndexed { index, event ->
                    DrillStep(
                        id = "${event.at}-$index",
                        event = event.event,
                        actor = event.actor,
                        at = event.at.toString(),
                    )
                }

            val complete = alert?.state?.isTerminal == true
            _state.value =
                DrillUiState.Active(
                    plan = plan,
                    steps = steps,
                    telemetry =
                        DrillTelemetry(
                            alertId = moment.alertId,
                            alertState = stateName,
                            timeScale = moment.timeScale,
                            isDrill = moment.isDrill,
                            eventCount = timeline.size,
                            lastActor = timeline.lastOrNull()?.actor,
                            leaseExpiresAt = alert?.leaseExpiresAt?.toString(),
                        ),
                    status =
                        when {
                            complete -> DrillStatus.TERMINAL
                            moment.alertId == null -> DrillStatus.WAITING_SCHEDULER
                            else -> DrillStatus.FOLLOWING
                        },
                    isComplete = complete,
                )
            if (complete) return
        }

        updateStatus(DrillStatus.STILL_OPEN)
    }

    private fun updateStatus(status: DrillStatus) {
        val current = _state.value
        if (current is DrillUiState.Active) _state.value = current.copy(status = status)
    }

    private fun momentStatus(alertId: String?): String = if (alertId == null) "SCHEDULED" else "OPEN"

    private companion object {
        const val POLL_INTERVAL_MS = 2_000L
        const val MAX_POLLS = 90
    }
}
