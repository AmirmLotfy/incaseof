package com.incaseof.app.core.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationChannels @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        const val SAFETY_CHECK_CHANNEL_ID = "safety_check"
        const val SAFETY_CHECK_CHANNEL_NAME = "Safety Check-ins"
        const val SAFETY_CHECK_CHANNEL_DESC = "Notifications for missed check-ins and safety verification"

        const val ACTION_READY_CHANNEL_ID = "action_ready"
        const val ACTION_READY_CHANNEL_NAME = "Action Alerts"
        const val ACTION_READY_CHANNEL_DESC = "Notifications when safety actions are ready to execute"

        const val GENERAL_CHANNEL_ID = "general"
        const val GENERAL_CHANNEL_NAME = "General"
        const val GENERAL_CHANNEL_DESC = "General app notifications"
    }

    fun createAll() {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val safetyChannel = NotificationChannel(
            SAFETY_CHECK_CHANNEL_ID,
            SAFETY_CHECK_CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = SAFETY_CHECK_CHANNEL_DESC
            enableVibration(true)
            setShowBadge(true)
        }

        val actionChannel = NotificationChannel(
            ACTION_READY_CHANNEL_ID,
            ACTION_READY_CHANNEL_NAME,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = ACTION_READY_CHANNEL_DESC
            enableVibration(true)
            setShowBadge(true)
        }

        val generalChannel = NotificationChannel(
            GENERAL_CHANNEL_ID,
            GENERAL_CHANNEL_NAME,
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = GENERAL_CHANNEL_DESC
        }

        manager.createNotificationChannels(
            listOf(safetyChannel, actionChannel, generalChannel)
        )
    }
}
