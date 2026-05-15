package com.incaseof.app.features.createcase

import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import javax.inject.Inject

data class CreateCaseUiState(
    val condition: String = "",
    val action: String = "",
    val isValid: Boolean = false
)

@HiltViewModel
class CreateCaseViewModel @Inject constructor() : ViewModel() {

    private val _uiState = MutableStateFlow(CreateCaseUiState())
    val uiState = _uiState.asStateFlow()

    fun updateCondition(text: String) {
        _uiState.update {
            it.copy(condition = text, isValid = text.isNotBlank() && it.action.isNotBlank())
        }
    }

    fun updateAction(text: String) {
        _uiState.update {
            it.copy(action = text, isValid = it.condition.isNotBlank() && text.isNotBlank())
        }
    }

    fun applySuggestion(condition: String, action: String) {
        _uiState.update {
            it.copy(condition = condition, action = action, isValid = true)
        }
    }
}
