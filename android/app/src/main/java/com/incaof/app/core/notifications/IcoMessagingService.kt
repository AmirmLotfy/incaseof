package com.incaof.app.core.notifications

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

private const val TAG = "IcoMessaging"

/**
 * Push delivery.
 *
 * Push is a *delivery* channel, never a source of truth. The payload carries identifiers
 * and a label — never Alert state, never a decision. Anything that matters is re-read from
 * the API, because a stale or spoofed push must not be able to tell this app that somebody
 * is fine.
 */
class IcoMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val alertId = message.data["alertId"] ?: return
        IcoNotifications.showAlertDue(this, alertId)
    }

    /**
     * Registration.
     *
     * Uploading the token is a Phase 4 concern, once the device-registration endpoint
     * exists. Logging only the fact of rotation, never the token itself: a push token is a
     * capability to send this person notifications.
     */
    @Suppress("OVERRIDE_DEPRECATION")
    override fun onNewToken(token: String) {
        val repository = (application as com.incaof.app.IcoApplication).container.repository
        PushRegistration.register(this, repository, token)
        Log.i(TAG, "push token rotated and registration requested")
    }
}
