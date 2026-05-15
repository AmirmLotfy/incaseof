package com.incaseof.app.core.notifications

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.incaseof.app.background.MarkSafeReceiver
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SafetyNotificationService @Inject constructor(
    @ApplicationContext private val context: Context
) {

    companion object {
        private const val SAFETY_CHECK_NOTIFICATION_BASE_ID = 1000
        private const val ACTION_READY_NOTIFICATION_BASE_ID = 2000
    }

    /**
     * Show "Are you okay?" verification notification with "I'm safe" action.
     */
    fun showSafetyCheckNotification(
        caseId: String,
        title: String,
        body: String,
        cancelLabel: String
    ) {
        val notificationId = SAFETY_CHECK_NOTIFICATION_BASE_ID + caseId.hashCode()

        // "I'm safe" action intent
        val markSafeIntent = Intent(context, MarkSafeReceiver::class.java).apply {
            action = "com.incaseof.app.MARK_SAFE"
            putExtra("caseId", caseId)
        }
        val markSafePending = PendingIntent.getBroadcast(
            context,
            notificationId,
            markSafeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Open app intent
        val openAppIntent = context.packageManager.getLaunchIntentForPackage(context.packageName)
        val openAppPending = PendingIntent.getActivity(
            context,
            notificationId + 1,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, NotificationChannels.SAFETY_CHECK_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(openAppPending)
            .addAction(
                android.R.drawable.ic_menu_save,
                cancelLabel,
                markSafePending
            )
            .addAction(
                android.R.drawable.ic_menu_view,
                "Open App",
                openAppPending
            )
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (e: SecurityException) {
            // Notification permission not granted
        }
    }

    /**
     * Show notification that a safety action is ready for user review.
     */
    fun showActionReadyNotification(
        caseId: String,
        title: String,
        body: String
    ) {
        val notificationId = ACTION_READY_NOTIFICATION_BASE_ID + caseId.hashCode()

        val openAppIntent = context.packageManager.getLaunchIntentForPackage(context.packageName)
        val openAppPending = PendingIntent.getActivity(
            context,
            notificationId,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, NotificationChannels.ACTION_READY_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .setContentIntent(openAppPending)
            .build()

        try {
            NotificationManagerCompat.from(context).notify(notificationId, notification)
        } catch (e: SecurityException) {
            // Notification permission not granted
        }
    }

    /**
     * Cancel all notifications for a case.
     */
    fun cancelNotifications(caseId: String) {
        val manager = NotificationManagerCompat.from(context)
        manager.cancel(SAFETY_CHECK_NOTIFICATION_BASE_ID + caseId.hashCode())
        manager.cancel(ACTION_READY_NOTIFICATION_BASE_ID + caseId.hashCode())
    }
}
