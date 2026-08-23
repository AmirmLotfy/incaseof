package com.incaof.app.core.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Sign-in without a user pool.
 *
 * Used when no Cognito pool is configured, which is the state of the world until the stack
 * is deployed, and by unit tests.
 *
 * This is **not** a fake path through the product. It authenticates a local session and
 * nothing else; every screen, view model and repository behind it runs exactly the code the
 * Cognito implementation feeds. What is stubbed is the identity provider, not the product.
 */
class LocalAuthRepository(
    private val personId: String = "person-local",
) : AuthRepository {
    private val _session = MutableStateFlow<AuthState>(AuthState.SignedOut)
    override val session: StateFlow<AuthState> = _session.asStateFlow()

    override suspend fun signIn(email: String, password: String): Result<Unit> {
        if (password.length < 12) {
            // Mirrors the pool's policy, so the sign-in screen behaves the same either way.
            return Result.failure(IllegalArgumentException("Password must be at least 12 characters"))
        }
        _session.value = AuthState.SignedIn(personId = personId, email = email)
        return Result.success(Unit)
    }

    override suspend fun signUp(email: String, password: String): Result<Unit> {
        _session.value = AuthState.NeedsConfirmation(email)
        return Result.success(Unit)
    }

    override suspend fun confirmSignUp(email: String, code: String): Result<Unit> {
        _session.value = AuthState.SignedOut
        return Result.success(Unit)
    }

    override suspend fun signOut() {
        _session.value = AuthState.SignedOut
    }

    override suspend fun refresh() = Unit

    override fun currentAccessTokenBlocking(): String? = null
}
