package com.incaseof.app.features.review

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.background.WorkScheduler
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.core.model.RiskLevel
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseWorkflow
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import javax.inject.Inject

data class ReviewUiState(
    val caseEntity: CaseEntity? = null,
    val workflow: CaseWorkflow? = null,
    val riskLevel: RiskLevel = RiskLevel.LOW,
    val isActivating: Boolean = false,
    val isActivated: Boolean = false,
    val hasTrustedContact: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class SafetyReviewViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val caseRepository: CaseRepository,
    private val workScheduler: WorkScheduler,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) : ViewModel() {

    private val caseId: String = savedStateHandle["caseId"] ?: ""
    private val _uiState = MutableStateFlow(ReviewUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            caseRepository.observeCase(caseId).collect { entity ->
                if (entity != null) {
                    try {
                        val workflow = json.decodeFromString<CaseWorkflow>(entity.planJson)
                        val risk = try { RiskLevel.valueOf(entity.riskLevel) } catch (e: Exception) { RiskLevel.LOW }
                        _uiState.update {
                            it.copy(
                                caseEntity = entity,
                                workflow = workflow,
                                riskLevel = risk,
                                hasTrustedContact = !entity.trustedContactName.isNullOrBlank()
                            )
                        }
                    } catch (e: Exception) {
                        _uiState.update { it.copy(error = "Failed to parse plan: ${e.message}") }
                    }
                }
            }
        }
    }

    fun activateCase() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActivating = true) }
            try {
                caseRepository.updateStatus(caseId, CaseStatus.ACTIVE.name)
                caseRepository.recordCheckIn(caseId) // Start the clock

                eventLogger.log(
                    caseId = caseId,
                    type = CaseEventType.ACTIVATED,
                    message = "Case activated. Check-in timer started."
                )

                // Start the global inactivity checker
                workScheduler.scheduleGlobalInactivityChecker()

                _uiState.update { it.copy(isActivating = false, isActivated = true) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isActivating = false, error = e.message) }
            }
        }
    }
}
