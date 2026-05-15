package com.incaseof.app.background

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.notifications.SafetyNotificationService
import com.incaseof.app.data.repositories.CaseRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Broadcast receiver for the "I'm safe" notification action.
 */
@AndroidEntryPoint
class MarkSafeReceiver : BroadcastReceiver() {

    @Inject lateinit var caseRepository: CaseRepository
    @Inject lateinit var workScheduler: WorkScheduler
    @Inject lateinit var notificationService: SafetyNotificationService
    @Inject lateinit var eventLogger: CaseEventLogger

    override fun onReceive(context: Context, intent: Intent) {
        val caseId = intent.getStringExtra("caseId") ?: return

        val pendingResult = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                caseRepository.markSafe(caseId)
                workScheduler.cancelVerification(caseId)
                notificationService.cancelNotifications(caseId)

                eventLogger.log(
                    caseId = caseId,
                    type = CaseEventType.USER_MARKED_SAFE,
                    message = "User marked themselves safe from notification."
                )
            } finally {
                pendingResult.finish()
            }
        }
    }
}
