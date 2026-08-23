package com.incaof.app.core.notifications

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import android.widget.Toast
import com.incaof.app.IcoApplication
import com.incaof.app.R
import com.incaof.app.data.ConfirmSource
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "MomentAction"

/**
 * Confirms a Moment straight from the notification.
 *
 * This is the path someone actually uses at 2am, so it must not require the app to be
 * running, visible, or even warm. `goAsync()` holds the broadcast open while the request
 * completes; without it the process can be killed mid-flight and the confirmation lost.
 *
 * The idempotency key is derived from the Moment, not generated, so a double-tap or a
 * retry after a dropped connection confirms the same Moment once rather than racing.
 */
class MomentActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != IcoNotifications.ACTION_CONFIRM) return
        val momentId = intent.getStringExtra(IcoNotifications.EXTRA_MOMENT_ID) ?: return

        // Dismiss immediately. The tap has been registered, and leaving the notification up
        // while the network call completes reads as though it did not work.
        IcoNotifications.dismissMoment(context)

        val app = context.applicationContext as? IcoApplication ?: return
        val pending = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val result =
                    app.container.repository.confirmMoment(
                        momentId = momentId,
                        idempotencyKey = "confirm-$momentId",
                        source = ConfirmSource.NOTIFICATION,
                    )
                result.onFailure { error ->
                    Log.w(TAG, "confirmation failed: ${error.javaClass.simpleName}")
                    // Say so rather than failing silently: someone who tapped "I'm okay"
                    // and was not heard needs to know their Circle may still be contacted.
                    withContext(Dispatchers.Main) {
                        Toast
                            .makeText(
                                context,
                                context.getString(R.string.confirm_failed),
                                Toast.LENGTH_LONG,
                            ).show()
                    }
                }
            } finally {
                pending.finish()
            }
        }
    }
}
