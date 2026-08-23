package com.incaof.app.core.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.incaof.app.MainActivity
import com.incaof.app.R

/**
 * Notifications.
 *
 * The important requirement is §15: **"I'M OKAY" works from the notification, without
 * opening the app.** Somebody checking in at 2am should not have to unlock, wait for a
 * cold start and navigate. The action goes to a broadcast receiver that performs the
 * confirmation directly.
 *
 * The channel is set to a normal importance rather than high. This is a check-in, not an
 * alarm, and a product whose premise is reducing background dread should not shout.
 */
private const val TAG = "IcoNotifications"

object IcoNotifications {
    const val CHANNEL_MOMENTS = "moments"
    const val NOTIFICATION_ID_MOMENT = 1001

    const val ACTION_CONFIRM = "com.incaof.app.action.CONFIRM_MOMENT"
    const val EXTRA_MOMENT_ID = "momentId"
    const val EXTRA_PLAN_LABEL = "planLabel"

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel =
            NotificationChannel(
                CHANNEL_MOMENTS,
                context.getString(R.string.channel_moments),
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = context.getString(R.string.channel_moments_description)
                // No custom vibration pattern. An anxiety-inducing buzz undoes the calm the
                // product exists to provide (DESIGN.md §10).
                enableVibration(true)
                setShowBadge(true)
            }
        context.getSystemService(NotificationManager::class.java)?.createNotificationChannel(channel)
    }

    /**
     * The check-in notification.
     *
     * Content is factual and non-speculative: it says a check is expected, never that
     * anything is wrong (docs/design/COPY.md §3).
     */
    fun showMomentDue(context: Context, momentId: String, planLabel: String) {
        val confirm =
            Intent(context, MomentActionReceiver::class.java).apply {
                action = ACTION_CONFIRM
                putExtra(EXTRA_MOMENT_ID, momentId)
                putExtra(EXTRA_PLAN_LABEL, planLabel)
            }
        val confirmPending =
            PendingIntent.getBroadcast(
                context,
                momentId.hashCode(),
                confirm,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

        val open =
            PendingIntent.getActivity(
                context,
                0,
                Intent(context, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    putExtra(EXTRA_MOMENT_ID, momentId)
                },
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

        val notification =
            NotificationCompat
                .Builder(context, CHANNEL_MOMENTS)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(planLabel)
                .setContentText(context.getString(R.string.notification_moment_body))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setCategory(NotificationCompat.CATEGORY_REMINDER)
                .setContentIntent(open)
                .setAutoCancel(true)
                .addAction(
                    R.drawable.ic_notification,
                    context.getString(R.string.action_im_okay),
                    confirmPending,
                ).build()

        // Checked inline rather than through canNotify() below: Lint's data-flow analysis
        // only recognises the guard when it sits directly before the call, and suppressing
        // the warning instead would hide a genuine missing-permission bug the next time
        // this file changes.
        val granted =
            Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS,
                ) == PackageManager.PERMISSION_GRANTED

        if (!granted) {
            // Not a failure to recover from. The ladder continues either way, because the
            // timers live in EventBridge — the person is reached by the next rung rather
            // than by this one.
            Log.i(TAG, "notification permission not granted; skipping local notification")
            return
        }

        NotificationManagerCompat
            .from(context)
            .notify(NOTIFICATION_ID_MOMENT, notification)
    }

    /** Whether this app may post notifications at all. */
    fun canNotify(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        } else {
            NotificationManagerCompat.from(context).areNotificationsEnabled()
        }

    fun dismissMoment(context: Context) {
        NotificationManagerCompat.from(context).cancel(NOTIFICATION_ID_MOMENT)
    }
}
