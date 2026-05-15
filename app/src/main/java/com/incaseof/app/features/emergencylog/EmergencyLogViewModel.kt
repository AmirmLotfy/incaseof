package com.incaseof.app.features.emergencylog

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.data.entities.CaseEventEntity
import com.incaseof.app.data.repositories.CaseRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import javax.inject.Inject

@HiltViewModel
class EmergencyLogViewModel @Inject constructor(
    private val caseRepository: CaseRepository
) : ViewModel() {
    val events: StateFlow<List<CaseEventEntity>> = caseRepository.observeAllEvents()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
}
