package com.incaof.app.feature.plans

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.CompiledPlanDraft
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

    private val _composer = MutableStateFlow(PlanComposerUiState())
    val composer: StateFlow<PlanComposerUiState> = _composer.asStateFlow()

    private val _action = MutableStateFlow(PlanActionUiState())
    val action: StateFlow<PlanActionUiState> = _action.asStateFlow()

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

    fun startCreate() {
        _composer.value = PlanComposerUiState(visible = true)
    }

    fun cancelCreate() {
        _composer.value = PlanComposerUiState()
    }

    fun compile(description: String) {
        val utterance = description.trim()
        if (utterance.isEmpty()) {
            _composer.value = _composer.value.copy(error = "Describe what you expect and when.")
            return
        }
        viewModelScope.launch {
            _composer.value = _composer.value.copy(busy = true, error = null)
            _composer.value =
                repository
                    .compilePlan(
                        utterance,
                        java.time.ZoneId
                            .systemDefault()
                            .id,
                    ).fold(
                        onSuccess = { _composer.value.copy(busy = false, draft = it) },
                        onFailure = { _composer.value.copy(busy = false, error = it.userMessage()) },
                    )
        }
    }

    fun saveDraft() {
        val draft = _composer.value.draft ?: return
        viewModelScope.launch {
            _composer.value = _composer.value.copy(busy = true, error = null)
            repository.createPlan(draft).fold(
                onSuccess = {
                    _composer.value = PlanComposerUiState()
                    refresh()
                    _selected.value = it
                },
                onFailure = { error ->
                    _composer.value = _composer.value.copy(busy = false, error = error.userMessage())
                },
            )
        }
    }

    fun activate(planId: String) = mutatePlan { repository.activatePlan(planId) }

    fun pause(planId: String) = mutatePlan { repository.pausePlan(planId) }

    fun resume(planId: String) = mutatePlan { repository.resumePlan(planId) }

    private fun mutatePlan(request: suspend () -> Result<Plan>) {
        viewModelScope.launch {
            _action.value = PlanActionUiState(busy = true)
            request().fold(
                onSuccess = {
                    _selected.value = it
                    _action.value = PlanActionUiState(notice = "Plan updated.")
                    refresh()
                },
                onFailure = { _action.value = PlanActionUiState(error = it.userMessage()) },
            )
        }
    }
}

data class PlanComposerUiState(
    val visible: Boolean = false,
    val busy: Boolean = false,
    val draft: CompiledPlanDraft? = null,
    val error: String? = null,
)

data class PlanActionUiState(
    val busy: Boolean = false,
    val notice: String? = null,
    val error: String? = null,
)

sealed interface PlansUiState {
    data object Loading : PlansUiState

    data class Content(
        val plans: List<Plan>,
    ) : PlansUiState

    data class Failed(
        val message: String,
    ) : PlansUiState
}
