package com.incaof.app

import android.app.Application
import android.util.Log
import com.amplifyframework.auth.cognito.AWSCognitoAuthPlugin
import com.amplifyframework.core.Amplify
import com.incaof.app.core.di.AppContainer
import com.incaof.app.core.notifications.IcoNotifications

class IcoApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        IcoNotifications.createChannels(this)

        if (container.hasBackend) {
            configureAmplify()
        }
    }

    /**
     * Amplify is configured only when a pool exists.
     *
     * A failure here leaves the app signed out rather than crashing. Someone whose check is
     * due tonight should still reach a screen that can tell them something, even if the
     * identity provider is unreachable.
     */
    private fun configureAmplify() {
        runCatching {
            Amplify.addPlugin(AWSCognitoAuthPlugin())
            Amplify.configure(applicationContext)
        }.onFailure { Log.w("IcoApplication", "Amplify configuration failed: ${it.message}") }
    }
}
