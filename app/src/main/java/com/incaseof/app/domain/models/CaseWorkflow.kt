package com.incaseof.app.domain.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CaseWorkflow(
    val version: Int = 1,
    val title: String,
    val summary: String,
    val trigger: TriggerSpec,
    val verification: VerificationSpec,
    val actions: List<ActionSpec>,
    val permissions: List<PermissionSpec> = emptyList(),
    val risk: RiskSpec,
    val unsupportedRequests: List<String> = emptyList(),
    val userQuestions: List<String> = emptyList()
)

@Serializable
sealed class TriggerSpec {
    @Serializable
    @SerialName("missed_checkin")
    data class MissedCheckIn(
        val durationHours: Int,
        val checkInPrompt: String
    ) : TriggerSpec()

    @Serializable
    @SerialName("scheduled_time")
    data class ScheduledTime(
        val localTime: String,
        val timezone: String
    ) : TriggerSpec()
}

@Serializable
data class VerificationSpec(
    val enabled: Boolean = true,
    val notificationTitle: String = "Are you okay?",
    val notificationBody: String = "You missed your safety check-in. Tap I'm safe to cancel the alert.",
    val waitMinutes: Int = 15,
    val cancelActionLabel: String = "I'm safe"
)

@Serializable
sealed class ActionSpec {
    @Serializable
    @SerialName("send_sms")
    data class SendSms(
        val contactRole: String,
        val message: String,
        val includeLastKnownLocation: Boolean = false,
        val requiresFinalUserApproval: Boolean = true
    ) : ActionSpec()

    @Serializable
    @SerialName("send_email")
    data class SendEmail(
        val contactRole: String = "",
        val subject: String,
        val body: String,
        val includeLastKnownLocation: Boolean = false
    ) : ActionSpec()

    @Serializable
    @SerialName("call_contact")
    data class CallContact(
        val contactRole: String
    ) : ActionSpec()

    @Serializable
    @SerialName("open_whatsapp")
    data class OpenWhatsAppPreparedMessage(
        val message: String
    ) : ActionSpec()
}

@Serializable
data class PermissionSpec(
    val permission: String,
    val reason: String,
    val required: Boolean
)

@Serializable
data class RiskSpec(
    val level: String, // low, medium, high
    val reasons: List<String>,
    val safetyRequirements: List<String> = emptyList()
)
