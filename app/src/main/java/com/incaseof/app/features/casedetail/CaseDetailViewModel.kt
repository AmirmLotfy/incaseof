package com.incaseof.app.features.casedetail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.core.model.RiskLevel
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.entities.CaseEventEntity
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseWorkflow
import com.incaseof.app.domain.usecases.CheckInUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import javax.inject.Inject

data class CaseDetailUiState(
    val caseEntity: CaseEntity? = null,
    val workflow: CaseWorkflow? = null,
    val events: List<CaseEventEntity> = emptyList(),
    val riskLevel: RiskLevel = RiskLevel.LOW,
    val status: CaseStatus = CaseStatus.DRAFT,
    val isCheckingIn: Boolean = false
)

@HiltViewModel
class CaseDetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val caseRepository: CaseRepository,
    private val checkInUseCase: CheckInUseCase,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) : ViewModel() {

    val caseId: String = savedStateHandle["caseId"] ?: ""
    private val _uiState = MutableStateFlow(CaseDetailUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            caseRepository.observeCase(caseId).collect { entity ->
                if (entity != null) {
                    val workflow = try {
                        json.decodeFromString<CaseWorkflow>(entity.planJson)
                    } catch (e: Exception) { null }
                    val risk = try { RiskLevel.valueOf(entity.riskLevel) } catch (e: Exception) { RiskLevel.LOW }
                    val status = try { CaseStatus.valueOf(entity.status) } catch (e: Exception) { CaseStatus.DRAFT }

                    _uiState.update {
                        it.copy(caseEntity = entity, workflow = workflow, riskLevel = risk, status = status)
                    }
                }
            }
        }
        viewModelScope.launch {
            caseRepository.observeEvents(caseId).collect { events ->
                _uiState.update { it.copy(events = events) }
            }
        }
    }

    fun checkIn() {
        viewModelScope.launch {
            _uiState.update { it.copy(isCheckingIn = true) }
            checkInUseCase.execute(caseId)
            _uiState.update { it.copy(isCheckingIn = false) }
        }
    }

    fun pauseCase() {
        viewModelScope.launch {
            caseRepository.updateStatus(caseId, CaseStatus.PAUSED.name)
            eventLogger.log(caseId, CaseEventType.PAUSED, "Case paused by user.")
        }
    }

    fun resumeCase() {
        viewModelScope.launch {
            caseRepository.updateStatus(caseId, CaseStatus.ACTIVE.name)
            caseRepository.recordCheckIn(caseId)
            eventLogger.log(caseId, CaseEventType.RESUMED, "Case resumed by user.")
        }
    }

    fun deleteCase() {
        viewModelScope.launch {
            caseRepository.deleteCase(caseId)
        }
    }
}
