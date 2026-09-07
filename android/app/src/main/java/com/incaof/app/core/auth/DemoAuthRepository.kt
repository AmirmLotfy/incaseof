package com.incaof.app.core.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** A short-lived synthetic identity issued by the demo stack, never by Cognito. */
class DemoAuthRepository(
    private val token: String,
    displayName: String,
) : AuthRepository {
    private val _session =
        MutableStateFlow<AuthState>(
            AuthState.SignedIn(personId = "demo", email = "$displayName · synthetic judge session"),
        )
    override val session: StateFlow<AuthState> = _session.asStateFlow()

    override suspend fun signIn(email: String, password: String): Result<Unit> = unsupported()

    override suspend fun signUp(email: String, password: String): Result<Unit> = unsupported()

    override suspend fun confirmSignUp(email: String, code: String): Result<Unit> = unsupported()

    override suspend fun requestPasswordReset(email: String): Result<Unit> = unsupported()

    override suspend fun confirmPasswordReset(
        email: String,
        code: String,
        newPassword: String,
    ): Result<Unit> = unsupported()

    override suspend fun signOut() {
        _session.value = AuthState.SignedOut
    }

    override suspend fun refresh() = Unit

    override fun currentAccessTokenBlocking(): String = token

    private fun unsupported(): Result<Unit> =
        Result.failure(IllegalStateException("Account operations are unavailable in judge demo mode"))
}
