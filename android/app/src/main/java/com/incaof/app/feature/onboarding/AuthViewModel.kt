package com.incaof.app.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.core.auth.AuthRepository
import com.incaof.app.core.auth.AuthState
import com.incaof.app.ui.UiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AuthViewModel(
    private val auth: AuthRepository,
) : ViewModel() {
    val session: StateFlow<AuthState> = auth.session

    private val _error = MutableStateFlow<UiMessage?>(null)
    val error: StateFlow<UiMessage?> = _error.asStateFlow()

    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy.asStateFlow()

    init {
        viewModelScope.launch { auth.refresh() }
    }

    fun signIn(email: String, password: String) {
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            auth.signIn(email, password).onFailure {
                // Never echo the provider's message. It can distinguish "no such user" from
                // "wrong password", which confirms whether an account exists.
                _error.value = UiMessage.AUTH_SIGN_IN
            }
            _busy.value = false
        }
    }

    fun signUp(email: String, password: String) {
        perform(UiMessage.AUTH_SIGN_UP) {
            auth.signUp(email, password)
        }
    }

    fun confirmSignUp(email: String, code: String) {
        perform(UiMessage.AUTH_CONFIRMATION) {
            auth.confirmSignUp(email, code)
        }
    }

    fun requestPasswordReset(email: String) {
        perform(UiMessage.AUTH_RESET_REQUEST) {
            auth.requestPasswordReset(email)
        }
    }

    fun confirmPasswordReset(email: String, code: String, newPassword: String) {
        perform(UiMessage.AUTH_RESET_CONFIRM) {
            auth.confirmPasswordReset(email, code, newPassword)
        }
    }

    private fun perform(message: UiMessage, operation: suspend () -> Result<Unit>) {
        viewModelScope.launch {
            _busy.value = true
            _error.value = null
            operation().onFailure { _error.value = message }
            _busy.value = false
        }
    }

    fun signOut() {
        viewModelScope.launch { auth.signOut() }
    }
}
