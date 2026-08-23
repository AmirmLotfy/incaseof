package com.incaof.app.feature.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.core.auth.AuthRepository
import com.incaof.app.core.auth.AuthState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class AuthViewModel(
    private val auth: AuthRepository,
) : ViewModel() {
    val session: StateFlow<AuthState> = auth.session

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

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
                _error.value = "Couldn't sign in. Check your email and password."
            }
            _busy.value = false
        }
    }

    fun signOut() {
        viewModelScope.launch { auth.signOut() }
    }
}
