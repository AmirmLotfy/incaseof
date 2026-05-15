package com.incaseof.app.domain.validators

import com.incaseof.app.domain.models.*
import kotlinx.serialization.json.Json

/**
 * Deterministic safety validator. Never trust model output.
 * Validates workflow JSON against safety rules before allowing activation.
 */
object WorkflowSafetyValidator {

    data class ValidationResult(
        val isValid: Boolean,
        val errors: List<String>
    )

    private val json = Json { ignoreUnknownKeys = true }

    fun validate(workflow: CaseWorkflow): ValidationResult {
        val errors = mutableListOf<String>()

        // Version check
        if (workflow.version != 1) {
            errors += "Unsupported workflow version: ${workflow.version}."
        }

        // Title check
        if (workflow.title.isBlank()) {
            errors += "Missing title."
        }

        // Title length
        if (workflow.title.length > 200) {
            errors += "Title exceeds maximum length."
        }

        // Summary check
        if (workflow.summary.isBlank()) {
            errors += "Missing summary."
        }

        // Trigger validation
        when (val trigger = workflow.trigger) {
            is TriggerSpec.MissedCheckIn -> {
                if (trigger.durationHours < 1) {
                    errors += "Check-in duration must be at least 1 hour."
                }
                if (trigger.durationHours > 168) {
                    errors += "Check-in duration cannot exceed 7 days (168 hours) in V1."
                }
                if (trigger.checkInPrompt.isBlank()) {
                    errors += "Check-in prompt cannot be empty."
                }
            }
            is TriggerSpec.ScheduledTime -> {
                if (!trigger.localTime.matches(Regex("^\\d{2}:\\d{2}$"))) {
                    errors += "Invalid scheduled time format. Expected HH:MM."
                }
            }
        }

        // Verification validation
        if (workflow.verification.enabled) {
            if (workflow.verification.waitMinutes < 1) {
                errors += "Verification wait time must be at least 1 minute."
            }
            if (workflow.verification.waitMinutes > 60) {
                errors += "Verification wait time cannot exceed 60 minutes in V1."
            }
            if (workflow.verification.notificationTitle.isBlank()) {
                errors += "Verification notification title cannot be empty."
            }
            if (workflow.verification.notificationBody.isBlank()) {
                errors += "Verification notification body cannot be empty."
            }
        }

        // Actions validation
        if (workflow.actions.isEmpty()) {
            errors += "Workflow must have at least one action."
        }

        workflow.actions.forEach { action ->
            when (action) {
                is ActionSpec.SendSms -> {
                    if (!action.requiresFinalUserApproval) {
                        errors += "SMS actions must require final user approval in V1."
                    }
                    if (action.message.isBlank()) {
                        errors += "SMS message cannot be empty."
                    }
                    if (action.message.length > 1600) {
                        errors += "SMS message exceeds maximum length."
                    }
                }
                is ActionSpec.SendEmail -> {
                    if (action.body.isBlank()) {
                        errors += "Email body cannot be empty."
                    }
                    if (action.subject.isBlank()) {
                        errors += "Email subject cannot be empty."
                    }
                }
                is ActionSpec.CallContact -> {
                    if (action.contactRole.isBlank()) {
                        errors += "Call action must specify a contact role."
                    }
                }
                is ActionSpec.OpenWhatsAppPreparedMessage -> {
                    if (action.message.isBlank()) {
                        errors += "WhatsApp message cannot be empty."
                    }
                }
            }
        }

        // Forbidden content check
        val forbiddenPatterns = listOf(
            "record audio",
            "spy",
            "track someone",
            "hide",
            "without consent",
            "call emergency services",
            "call 911",
            "call 112",
            "call 999",
            "stalk",
            "monitor secretly",
            "hidden camera",
            "wiretap",
            "surveillance"
        )

        val workflowText = try {
            json.encodeToString(CaseWorkflow.serializer(), workflow).lowercase()
        } catch (e: Exception) {
            ""
        }

        forbiddenPatterns.forEach { pattern ->
            if (workflowText.contains(pattern)) {
                errors += "Unsupported or unsafe request detected: \"$pattern\"."
            }
        }

        // Risk validation
        val validRiskLevels = listOf("low", "medium", "high")
        if (workflow.risk.level.lowercase() !in validRiskLevels) {
            errors += "Invalid risk level: ${workflow.risk.level}. Must be low, medium, or high."
        }

        return ValidationResult(
            isValid = errors.isEmpty(),
            errors = errors
        )
    }
}
