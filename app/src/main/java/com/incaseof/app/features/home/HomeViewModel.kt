package com.incaseof.app.features.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.core.model.RiskLevel
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.entities.CaseEventEntity
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.usecases.CheckInUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeUiState(
    val activeCases: List<CaseEntity> = emptyList(),
    val recentEvents: List<CaseEventEntity> = emptyList(),
    val totalCases: Int = 0,
    val isCheckingIn: Boolean = false,
    val checkInSuccess: Boolean = false
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val caseRepository: CaseRepository,
    private val checkInUseCase: CheckInUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            caseRepository.observeActiveCases().collect { cases ->
                _uiState.update { it.copy(activeCases = cases) }
            }
        }
        viewModelScope.launch {
            caseRepository.observeRecentEvents(10).collect { events ->
                _uiState.update { it.copy(recentEvents = events) }
            }
        }
        viewModelScope.launch {
            _uiState.update { it.copy(totalCases = caseRepository.caseCount()) }
        }
    }

    fun checkInAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isCheckingIn = true) }
            try {
                checkInUseCase.checkInAll()
                _uiState.update { it.copy(isCheckingIn = false, checkInSuccess = true) }
                // Reset success after delay
                kotlinx.coroutines.delay(2000)
                _uiState.update { it.copy(checkInSuccess = false) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isCheckingIn = false) }
            }
        }
    }

    fun getCaseStatus(status: String): CaseStatus {
        return try { CaseStatus.valueOf(status) } catch (e: Exception) { CaseStatus.DRAFT }
    }

    fun getRiskLevel(level: String): RiskLevel {
        return try { RiskLevel.valueOf(level) } catch (e: Exception) { RiskLevel.LOW }
    }
}
