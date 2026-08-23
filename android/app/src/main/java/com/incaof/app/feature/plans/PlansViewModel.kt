package com.incaof.app.feature.plans

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.Plan
import com.incaof.app.feature.home.userMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PlansViewModel(
    private val repository: IcoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<PlansUiState>(PlansUiState.Loading)
    val state: StateFlow<PlansUiState> = _state.asStateFlow()

    private val _selected = MutableStateFlow<Plan?>(null)
    val selected: StateFlow<Plan?> = _selected.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value =
                repository.plans().fold(
                    onSuccess = { PlansUiState.Content(it) },
                    onFailure = { PlansUiState.Failed(it.userMessage()) },
                )
        }
    }

    fun select(planId: String) {
        viewModelScope.launch {
            _selected.value = repository.plan(planId).getOrNull()
        }
    }

    fun clearSelection() {
        _selected.value = null
    }
}

sealed interface PlansUiState {
    data object Loading : PlansUiState

    data class Content(
        val plans: List<Plan>,
    ) : PlansUiState

    data class Failed(
        val message: String,
    ) : PlansUiState
}
