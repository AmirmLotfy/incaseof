package com.incaof.app.core.di

import android.content.Context
import com.incaof.app.BuildConfig
import com.incaof.app.core.auth.AuthRepository
import com.incaof.app.core.auth.CognitoAuthRepository
import com.incaof.app.core.auth.LocalAuthRepository
import com.incaof.app.core.network.NetworkModule
import com.incaof.app.data.ApiIcoRepository
import com.incaof.app.data.IcoRepository
import com.incaof.app.data.LocalIcoRepository

/**
 * The object graph, by hand.
 *
 * Not Hilt. AGP 9 compiles Kotlin natively, and layering KSP's compiler plugin on top of
 * that is an unproven combination this project does not need: the graph is a handful of
 * singletons, which reads more clearly here than in generated code, and it costs no build
 * time. If the graph grows past what one file explains, that is the signal to reconsider.
 *
 * Which implementation is chosen depends on configuration, never on a debug flag. A build
 * pointed at a deployed pool talks to it; one that is not, cannot, and says so.
 */
class AppContainer(
    context: Context,
) {
    /** Whether a Cognito pool has been configured for this build. */
    val hasBackend: Boolean =
        BuildConfig.COGNITO_POOL_ID.isNotBlank() && BuildConfig.COGNITO_CLIENT_ID.isNotBlank()

    init {
        check(hasBackend || BuildConfig.ALLOW_LOCAL_DATA) {
            "This release has no Cognito backend configuration and cannot use local data."
        }
    }

    val auth: AuthRepository = if (hasBackend) CognitoAuthRepository() else LocalAuthRepository()

    val repository: IcoRepository =
        if (hasBackend) ApiIcoRepository(NetworkModule.api(auth)) else LocalIcoRepository()

    val appContext: Context = context.applicationContext
}
