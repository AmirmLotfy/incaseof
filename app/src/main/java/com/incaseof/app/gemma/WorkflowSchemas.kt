package com.incaseof.app.gemma

/**
 * Schema constants for workflow validation.
 */
object WorkflowSchemas {
    const val CURRENT_VERSION = 1

    val SUPPORTED_TRIGGER_TYPES = listOf("missed_checkin", "scheduled_time")
    val SUPPORTED_ACTION_TYPES = listOf("send_sms", "send_email", "call_contact", "open_whatsapp")
    val VALID_RISK_LEVELS = listOf("low", "medium", "high")

    const val MIN_CHECK_IN_HOURS = 1
    const val MAX_CHECK_IN_HOURS = 168 // 7 days
    const val MIN_VERIFICATION_MINUTES = 1
    const val MAX_VERIFICATION_MINUTES = 60
    const val MAX_SMS_LENGTH = 1600
    const val MAX_TITLE_LENGTH = 200
}
