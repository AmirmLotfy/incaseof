package com.incaof.app.core.auth

import android.util.Log
import com.amplifyframework.auth.AuthUserAttributeKey
import com.amplifyframework.auth.cognito.AWSCognitoAuthSession
import com.amplifyframework.auth.options.AuthSignUpOptions
import com.amplifyframework.kotlin.core.Amplify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicReference

private const val TAG = "IcoAuth"

/**
 * Cognito, through Amplify.
 *
 * Amplify is used rather than hand-rolling SRP. The user pool allows only USER_SRP_AUTH,
 * deliberately — the simpler USER_PASSWORD_AUTH sends the password to Cognito, and choosing
 * it for implementation convenience would be trading a security property for a shortcut in
 * a product whose whole premise is trust.
 *
 * The access token is cached so [currentAccessTokenBlocking] can answer synchronously from
 * an OkHttp interceptor without a network round trip on every request.
 */
class CognitoAuthRepository : AuthRepository {
    private val _session = MutableStateFlow<AuthState>(AuthState.Unknown)
    override val session: StateFlow<AuthState> = _session.asStateFlow()

    private val cachedToken = AtomicReference<String?>(null)

    override suspend fun signIn(email: String, password: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                val result = Amplify.Auth.signIn(email, password)
                if (!result.isSignedIn) {
                    _session.value = AuthState.NeedsConfirmation(email)
                } else {
                    refresh()
                }
            }.onFailure { Log.w(TAG, "sign-in failed: ${it.javaClass.simpleName}") }
        }

    override suspend fun signUp(email: String, password: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                Amplify.Auth.signUp(
                    email,
                    password,
                    AuthSignUpOptions
                        .builder()
                        .userAttribute(AuthUserAttributeKey.email(), email)
                        .build(),
                )
                _session.value = AuthState.NeedsConfirmation(email)
            }.onFailure { Log.w(TAG, "sign-up failed: ${it.javaClass.simpleName}") }
        }

    override suspend fun confirmSignUp(email: String, code: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            runCatching {
                Amplify.Auth.confirmSignUp(email, code)
                _session.value = AuthState.SignedOut
            }.onFailure { Log.w(TAG, "confirmation failed: ${it.javaClass.simpleName}") }
        }

    override suspend fun signOut() =
        withContext(Dispatchers.IO) {
            Amplify.Auth.signOut()
            cachedToken.set(null)
            _session.value = AuthState.SignedOut
        }

    /**
     * Re-read the session and cache the token.
     *
     * Any failure resolves to signed out. A half-known auth state in a safety app leads to
     * silently unauthenticated requests, and a check that never reached the server is worse
     * than an obvious sign-in prompt.
     */
    override suspend fun refresh() =
        withContext(Dispatchers.IO) {
            runCatching {
                val session = Amplify.Auth.fetchAuthSession() as AWSCognitoAuthSession
                val tokens = session.userPoolTokensResult.value
                cachedToken.set(tokens?.accessToken)
                if (session.isSignedIn && tokens != null) {
                    val user = Amplify.Auth.getCurrentUser()
                    _session.value = AuthState.SignedIn(personId = user.userId, email = user.username)
                } else {
                    _session.value = AuthState.SignedOut
                }
            }.onFailure {
                Log.w(TAG, "session refresh failed: ${it.javaClass.simpleName}")
                cachedToken.set(null)
                _session.value = AuthState.SignedOut
            }
            Unit
        }

    override fun currentAccessTokenBlocking(): String? = cachedToken.get()
}
