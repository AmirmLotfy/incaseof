package com.incaseof.app.features.simulation

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseWorkflow
import com.incaseof.app.domain.models.TriggerSpec
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import javax.inject.Inject

data class SimStep(
    val label: String,
    val detail: String,
    val isComplete: Boolean,
    val isActive: Boolean
)

data class SimulationUiState(
    val caseTitle: String = "",
    val steps: List<SimStep> = emptyList(),
    val isRunning: Boolean = false,
    val isComplete: Boolean = false,
    val currentStep: Int = -1
)

@HiltViewModel
class SimulationViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val caseRepository: CaseRepository,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) : ViewModel() {

    private val caseId: String = savedStateHandle["caseId"] ?: ""
    private val _uiState = MutableStateFlow(SimulationUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val caseEntity = caseRepository.getCase(caseId) ?: return@launch
            val workflow = try { json.decodeFromString<CaseWorkflow>(caseEntity.planJson) } catch (e: Exception) { return@launch }

            val hours = when (val t = workflow.trigger) {
                is TriggerSpec.MissedCheckIn -> t.durationHours
                is TriggerSpec.ScheduledTime -> 0
            }

            _uiState.update {
                it.copy(
                    caseTitle = workflow.title,
                    steps = listOf(
                        SimStep("Case activated", "Timer starts for ${hours}h check-in", false, false),
                        SimStep("Simulate ${hours} hours passing", "Fast-forwarding time...", false, false),
                        SimStep("Missed check-in detected", "No check-in recorded in ${hours}h", false, false),
                        SimStep("Verification notification sent", "\"${workflow.verification.notificationTitle}\"", false, false),
                        SimStep("Waiting ${workflow.verification.waitMinutes} minutes", "User has not responded", false, false),
                        SimStep("Verification expired", "Timeout reached", false, false),
                        SimStep("Safety alert prepared", "Actions ready for ${workflow.actions.size} action(s)", false, false)
                    )
                )
            }
        }
    }

    fun runSimulation() {
        viewModelScope.launch {
            _uiState.update { it.copy(isRunning = true, currentStep = 0) }

            eventLogger.log(caseId, CaseEventType.SIMULATION_RUN, "Simulation started.")

            for (i in _uiState.value.steps.indices) {
                _uiState.update { state ->
                    state.copy(
                        currentStep = i,
                        steps = state.steps.mapIndexed { idx, step ->
                            when {
                                idx < i -> step.copy(isComplete = true, isActive = false)
                                idx == i -> step.copy(isComplete = false, isActive = true)
                                else -> step
                            }
                        }
                    )
                }
                delay(if (i == 1) 2000 else 1200) // Longer delay for "time passing"
            }

            // Complete all
            _uiState.update { state ->
                state.copy(
                    isRunning = false,
                    isComplete = true,
                    steps = state.steps.map { it.copy(isComplete = true, isActive = false) }
                )
            }

            eventLogger.log(caseId, CaseEventType.SIMULATION_RUN, "Simulation completed successfully.")
        }
    }
}
