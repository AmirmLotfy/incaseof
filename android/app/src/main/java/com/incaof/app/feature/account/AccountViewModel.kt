package com.incaof.app.feature.account

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.AccountDeletion
import com.incaof.app.data.IcoRepository
import com.incaof.app.feature.home.userMessage
import com.incaof.app.ui.UiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class AccountViewModel(
    private val repository: IcoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<AccountUiState>(AccountUiState.Ready())
    val state: StateFlow<AccountUiState> = _state.asStateFlow()

    fun changeConfirmation(value: String) {
        _state.update { current ->
            if (current is AccountUiState.Ready && !current.busy) {
                current.copy(confirmation = value, error = null)
            } else {
                current
            }
        }
    }

    fun deleteAccount() {
        val current = _state.value as? AccountUiState.Ready ?: return
        if (current.confirmation != REQUIRED_CONFIRMATION || current.busy) return

        viewModelScope.launch {
            _state.value = current.copy(busy = true, error = null)
            repository.deleteAccount(current.confirmation).fold(
                onSuccess = { _state.value = AccountUiState.Requested(it) },
                onFailure = { error ->
                    _state.value = current.copy(busy = false, error = error.userMessage())
                },
            )
        }
    }

    companion object {
        const val REQUIRED_CONFIRMATION = "DELETE"
    }
}

sealed interface AccountUiState {
    data class Ready(
        val confirmation: String = "",
        val busy: Boolean = false,
        val error: UiMessage? = null,
    ) : AccountUiState {
        val canDelete: Boolean get() = confirmation == AccountViewModel.REQUIRED_CONFIRMATION && !busy
    }

    data class Requested(
        val deletion: AccountDeletion,
    ) : AccountUiState
}
