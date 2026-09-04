package com.incaof.app.core.notifications

import android.content.Context
import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import com.incaof.app.data.ApiException
import com.incaof.app.data.IcoRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.UUID

/** Registers only an opaque FCM capability; the token is never written to logs. */
object PushRegistration {
    private const val PREFERENCES = "ico_push"
    private const val DEVICE_ID = "device_id"
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    @Suppress("DEPRECATION")
    fun refresh(context: Context, repository: IcoRepository) {
        FirebaseMessaging
            .getInstance()
            .token
            .addOnSuccessListener { register(context, repository, it) }
            .addOnFailureListener { Log.w("IcoPush", "push token unavailable") }
    }

    fun register(context: Context, repository: IcoRepository, token: String) {
        val deviceId = deviceId(context.applicationContext)
        scope.launch {
            repository.registerDevice(deviceId, token).onFailure { error ->
                val reason =
                    if (error is ApiException) {
                        "HTTP ${error.status}"
                    } else {
                        error.javaClass.simpleName
                    }
                Log.w("IcoPush", "push registration deferred: $reason")
            }
        }
    }

    @Synchronized
    private fun deviceId(context: Context): String {
        val preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
        preferences.getString(DEVICE_ID, null)?.let { return it }

        return UUID.randomUUID().toString().also { generated ->
            preferences.edit().putString(DEVICE_ID, generated).apply()
        }
    }
}
