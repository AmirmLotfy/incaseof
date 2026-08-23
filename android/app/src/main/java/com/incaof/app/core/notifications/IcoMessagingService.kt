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
        val momentId = message.data["momentId"] ?: return
        val planLabel = message.data["planLabel"] ?: getString(com.incaof.app.R.string.check_in)
        IcoNotifications.showMomentDue(this, momentId, planLabel)
    }

    /**
     * Registration.
     *
     * Uploading the token is a Phase 4 concern, once the device-registration endpoint
     * exists. Logging only the fact of rotation, never the token itself: a push token is a
     * capability to send this person notifications.
     */
    override fun onNewToken(token: String) {
        Log.i(TAG, "push token rotated")
    }
}
