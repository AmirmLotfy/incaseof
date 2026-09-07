package com.incaof.app

import android.app.Application
import android.util.Log
import com.amplifyframework.auth.cognito.AWSCognitoAuthPlugin
import com.amplifyframework.core.Amplify
import com.amplifyframework.core.AmplifyConfiguration
import com.incaof.app.core.di.AppContainer
import com.incaof.app.core.notifications.IcoNotifications
import org.json.JSONObject

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
            val pool =
                JSONObject()
                    .put("PoolId", BuildConfig.COGNITO_POOL_ID)
                    .put("AppClientId", BuildConfig.COGNITO_CLIENT_ID)
                    .put("Region", BuildConfig.COGNITO_REGION)
            val plugin =
                JSONObject()
                    .put("UserAgent", "ico-android/0.2")
                    .put("Version", "1.0")
                    .put("IdentityManager", JSONObject().put("Default", JSONObject()))
                    .put("CognitoUserPool", JSONObject().put("Default", pool))
                    .put(
                        "Auth",
                        JSONObject().put(
                            "Default",
                            JSONObject().put("authenticationFlowType", "USER_SRP_AUTH"),
                        ),
                    )
            val configuration =
                AmplifyConfiguration.fromJson(
                    JSONObject().put(
                        "auth",
                        JSONObject().put("plugins", JSONObject().put("awsCognitoAuthPlugin", plugin)),
                    ),
                )
            Amplify.configure(configuration, applicationContext)
        }.onFailure {
            Log.e("IcoApplication", "Amplify configuration failed: ${it.javaClass.simpleName}")
            if (!BuildConfig.ALLOW_LOCAL_DATA) throw it
        }
    }
}
