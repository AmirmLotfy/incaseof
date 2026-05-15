package com.incaseof.app.background.actions

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.incaseof.app.core.location.LastKnownLocationProvider
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.notifications.SafetyNotificationService
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.domain.models.ActionSpec
import com.incaseof.app.domain.models.CaseWorkflow
import dagger.hilt.android.qualifiers.ApplicationContext
import java.net.URLEncoder
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Executes approved safety actions via Android intents.
 * V1 uses prepared intents that require user confirmation —
 * no silent dangerous execution.
 */
@Singleton
class ActionExecutor @Inject constructor(
    @ApplicationContext private val context: Context,
    private val locationProvider: LastKnownLocationProvider,
    private val notificationService: SafetyNotificationService,
    private val eventLogger: CaseEventLogger
) {

    suspend fun executeActions(caseEntity: CaseEntity, workflow: CaseWorkflow) {
        workflow.actions.forEach { action ->
            when (action) {
                is ActionSpec.SendSms -> prepareSms(caseEntity, action)
                is ActionSpec.SendEmail -> prepareEmail(caseEntity, action)
                is ActionSpec.CallContact -> prepareCall(caseEntity, action)
                is ActionSpec.OpenWhatsAppPreparedMessage -> openWhatsApp(caseEntity, action)
            }
        }
    }

    private suspend fun prepareSms(caseEntity: CaseEntity, action: ActionSpec.SendSms) {
        val phone = caseEntity.trustedContactPhone ?: return

        val message = buildMessage(action.message, action.includeLastKnownLocation)

        // Show notification that SMS is ready
        notificationService.showActionReadyNotification(
            caseId = caseEntity.id,
            title = "Safety alert ready",
            body = "Tap to review and send SMS to ${caseEntity.trustedContactName ?: "trusted contact"}."
        )

        eventLogger.log(
            caseId = caseEntity.id,
            type = CaseEventType.ACTION_PREPARED,
            message = "SMS prepared for ${caseEntity.trustedContactName ?: "trusted contact"}: ${message.take(100)}..."
        )
    }

    /**
     * Build SMS intent that opens the user's SMS app with prepared message.
     */
    fun buildSmsIntent(phone: String, message: String): Intent {
        return Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("smsto:$phone")
            putExtra("sms_body", message)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }

    private suspend fun prepareEmail(caseEntity: CaseEntity, action: ActionSpec.SendEmail) {
        val email = caseEntity.trustedContactEmail ?: return
        val body = buildMessage(action.body, action.includeLastKnownLocation)

        val intent = Intent(Intent.ACTION_SENDTO).apply {
            data = Uri.parse("mailto:$email")
            putExtra(Intent.EXTRA_SUBJECT, action.subject)
            putExtra(Intent.EXTRA_TEXT, body)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        try {
            context.startActivity(intent)
        } catch (e: Exception) {
            // No email app available
        }

        eventLogger.log(
            caseId = caseEntity.id,
            type = CaseEventType.ACTION_PREPARED,
            message = "Email intent opened for ${caseEntity.trustedContactName ?: "trusted contact"}."
        )
    }

    private fun prepareCall(caseEntity: CaseEntity, action: ActionSpec.CallContact) {
        val phone = caseEntity.trustedContactPhone ?: return

        val intent = Intent(Intent.ACTION_DIAL).apply {
            data = Uri.parse("tel:$phone")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        try {
            context.startActivity(intent)
        } catch (e: Exception) {
            // No dialer available
        }

        // Log synchronously since this doesn't need suspend
        // EventLogger.log will be called from a coroutine context
    }

    private fun openWhatsApp(caseEntity: CaseEntity, action: ActionSpec.OpenWhatsAppPreparedMessage) {
        val encoded = URLEncoder.encode(action.message, "UTF-8")
        val intent = Intent(Intent.ACTION_VIEW).apply {
            data = Uri.parse("https://wa.me/?text=$encoded")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        try {
            context.startActivity(intent)
        } catch (e: Exception) {
            // WhatsApp not installed
        }
    }

    private suspend fun buildMessage(base: String, includeLocation: Boolean): String {
        if (!includeLocation) return base

        val location = locationProvider.getLastKnownLocationOrNull()
        val locationText = location?.let {
            "\n\nLast known location: https://maps.google.com/?q=${it.latitude},${it.longitude}"
        } ?: "\n\nLast known location unavailable."

        return base + locationText
    }
}
