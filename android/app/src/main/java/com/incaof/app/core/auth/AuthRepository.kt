package com.incaof.app.core.auth

import kotlinx.coroutines.flow.StateFlow

/**
 * Who is signed in.
 *
 * An interface rather than a concrete Cognito client for two reasons. Tests must not need
 * a user pool, and the app has to be runnable before any environment is deployed — which,
 * during Phase 3, is the actual situation.
 */
interface AuthRepository {
    val session: StateFlow<AuthState>

    suspend fun signIn(email: String, password: String): Result<Unit>

    suspend fun signUp(email: String, password: String): Result<Unit>

    suspend fun confirmSignUp(email: String, code: String): Result<Unit>

    suspend fun signOut()

    suspend fun refresh()

    /**
     * The current access token, or null.
     *
     * Blocking because OkHttp interceptors are synchronous. Implementations must return a
     * cached token rather than performing a network call here.
     */
    fun currentAccessTokenBlocking(): String?
}

sealed interface AuthState {
    /** Before the first check has completed. The UI shows the splash, not a sign-in form. */
    data object Unknown : AuthState

    data object SignedOut : AuthState

    data class NeedsConfirmation(
        val email: String,
    ) : AuthState

    data class SignedIn(
        val personId: String,
        val email: String,
    ) : AuthState
}
