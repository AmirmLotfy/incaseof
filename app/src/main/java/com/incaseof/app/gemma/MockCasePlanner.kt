package com.incaseof.app.gemma

import com.incaseof.app.domain.models.*
import kotlinx.coroutines.delay
import javax.inject.Inject

/**
 * Mock planner that returns realistic pre-built workflows.
 * Used for demo, testing, and when the on-device model isn't available.
 * Simulates ~2 second compilation delay for realistic UX.
 */
class MockCasePlanner @Inject constructor() : CasePlannerModel {

    override suspend fun compileCase(input: CaseDraftInput): CasePlanResult {
        // Simulate Gemma thinking time
        delay(2000)

        val conditionLower = input.condition.lowercase()
        val actionLower = input.action.lowercase()

        val workflow = when {
            // Check-in / safety check scenarios
            conditionLower.contains("check in") ||
            conditionLower.contains("check-in") ||
            conditionLower.contains("don't respond") ||
            conditionLower.contains("disappear") ||
            conditionLower.contains("don't hear") -> {
                buildCheckInWorkflow(input)
            }

            // Travel / arrival scenarios
            conditionLower.contains("travel") ||
            conditionLower.contains("arrive") ||
            conditionLower.contains("arrival") ||
            conditionLower.contains("flight") ||
            conditionLower.contains("trip") -> {
                buildTravelWorkflow(input)
            }

            // Medication reminder scenarios
            conditionLower.contains("medication") ||
            conditionLower.contains("medicine") ||
            conditionLower.contains("pill") ||
            conditionLower.contains("dose") -> {
                buildMedicationWorkflow(input)
            }

            // Solo activity scenarios
            conditionLower.contains("alone") ||
            conditionLower.contains("solo") ||
            conditionLower.contains("hike") ||
            conditionLower.contains("run") ||
            conditionLower.contains("walk") -> {
                buildSoloActivityWorkflow(input)
            }

            // Work / shift scenarios
            conditionLower.contains("work") ||
            conditionLower.contains("shift") ||
            conditionLower.contains("night") -> {
                buildWorkShiftWorkflow(input)
            }

            // Default: generic check-in
            else -> buildCheckInWorkflow(input)
        }

        return CasePlanResult.Valid(workflow)
    }

    private fun buildCheckInWorkflow(input: CaseDraftInput): CaseWorkflow {
        val hours = extractHours(input.condition) ?: 24
        val includeLocation = input.action.lowercase().let {
            it.contains("location") || it.contains("where")
        }

        return CaseWorkflow(
            version = 1,
            title = "${hours}-hour safety check-in",
            summary = "If you do not check in for $hours hours, the app will ask if you are okay. If you do not respond within 15 minutes, it will prepare an alert for your trusted contact.",
            trigger = TriggerSpec.MissedCheckIn(
                durationHours = hours,
                checkInPrompt = "Tap \"I'm safe\" once every $hours hours."
            ),
            verification = VerificationSpec(
                enabled = true,
                notificationTitle = "Are you okay?",
                notificationBody = "You missed your safety check-in. Tap \"I'm safe\" to cancel the alert.",
                waitMinutes = 15,
                cancelActionLabel = "I'm safe"
            ),
            actions = buildList {
                add(ActionSpec.SendSms(
                    contactRole = "trusted contact",
                    message = "Hi, this is an automated safety alert from In Case Of. I have not checked in for $hours hours. Please try calling me or checking on me.",
                    includeLastKnownLocation = includeLocation,
                    requiresFinalUserApproval = true
                ))
                if (input.action.lowercase().contains("call")) {
                    add(ActionSpec.CallContact(contactRole = "trusted contact"))
                }
                if (input.action.lowercase().contains("email")) {
                    add(ActionSpec.SendEmail(
                        contactRole = "trusted contact",
                        subject = "Safety Alert - Missed Check-in",
                        body = "This is an automated safety alert. I have not checked in for $hours hours. Please try to reach me.",
                        includeLastKnownLocation = includeLocation
                    ))
                }
            },
            permissions = buildList {
                add(PermissionSpec(
                    permission = "POST_NOTIFICATIONS",
                    reason = "Needed to ask whether you are safe before contacting anyone.",
                    required = true
                ))
                if (includeLocation) {
                    add(PermissionSpec(
                        permission = "ACCESS_FINE_LOCATION",
                        reason = "Needed only if you choose to include your last known location in the alert.",
                        required = false
                    ))
                }
            },
            risk = RiskSpec(
                level = if (includeLocation) "medium" else "low",
                reasons = buildList {
                    add("This workflow may contact another person.")
                    if (includeLocation) add("This workflow may share your location.")
                },
                safetyRequirements = listOf(
                    "Show final review before activation.",
                    "Allow cancellation from notification.",
                    "Log every action."
                )
            ),
            unsupportedRequests = emptyList(),
            userQuestions = listOf("Which trusted contact should receive the alert?")
        )
    }

    private fun buildTravelWorkflow(input: CaseDraftInput): CaseWorkflow {
        val hours = extractHours(input.condition) ?: 12

        return CaseWorkflow(
            version = 1,
            title = "Travel arrival check",
            summary = "If you do not confirm arrival within $hours hours, the app will verify your safety and prepare an alert for your trusted contact.",
            trigger = TriggerSpec.MissedCheckIn(
                durationHours = hours,
                checkInPrompt = "Tap \"I've arrived\" to confirm safe arrival."
            ),
            verification = VerificationSpec(
                enabled = true,
                notificationTitle = "Have you arrived safely?",
                notificationBody = "You haven't confirmed your arrival. Tap below if you're safe.",
                waitMinutes = 15,
                cancelActionLabel = "I've arrived"
            ),
            actions = listOf(
                ActionSpec.SendSms(
                    contactRole = "trusted contact",
                    message = "Safety alert: I haven't confirmed my arrival as expected. Please try to reach me.",
                    includeLastKnownLocation = true,
                    requiresFinalUserApproval = true
                )
            ),
            permissions = listOf(
                PermissionSpec("POST_NOTIFICATIONS", "Needed to ask whether you've arrived safely.", true),
                PermissionSpec("ACCESS_FINE_LOCATION", "Needed to share your last known location if you don't respond.", false)
            ),
            risk = RiskSpec(
                level = "medium",
                reasons = listOf(
                    "This workflow may contact another person.",
                    "This workflow may share your location."
                ),
                safetyRequirements = listOf(
                    "Show final review before activation.",
                    "Allow cancellation from notification.",
                    "Log every action."
                )
            ),
            userQuestions = listOf("Who should be notified if you don't confirm arrival?")
        )
    }

    private fun buildMedicationWorkflow(input: CaseDraftInput): CaseWorkflow {
        return CaseWorkflow(
            version = 1,
            title = "Medication check-in",
            summary = "Reminds you to confirm you've taken your medication. If you don't respond, your caregiver will be notified.",
            trigger = TriggerSpec.MissedCheckIn(
                durationHours = extractHours(input.condition) ?: 8,
                checkInPrompt = "Have you taken your medication? Tap to confirm."
            ),
            verification = VerificationSpec(
                enabled = true,
                notificationTitle = "Medication reminder",
                notificationBody = "Have you taken your medication? Tap to confirm.",
                waitMinutes = 30,
                cancelActionLabel = "I've taken it"
            ),
            actions = listOf(
                ActionSpec.SendSms(
                    contactRole = "caregiver",
                    message = "Medication alert: I haven't confirmed taking my medication as scheduled. Please check on me.",
                    includeLastKnownLocation = false,
                    requiresFinalUserApproval = true
                )
            ),
            permissions = listOf(
                PermissionSpec("POST_NOTIFICATIONS", "Needed for medication reminders and safety checks.", true)
            ),
            risk = RiskSpec(
                level = "low",
                reasons = listOf("This workflow may notify your caregiver about missed medication."),
                safetyRequirements = listOf(
                    "Show final review before activation.",
                    "Allow cancellation from notification.",
                    "Log every action."
                )
            ),
            userQuestions = listOf("Who is your caregiver or emergency contact for medication reminders?")
        )
    }

    private fun buildSoloActivityWorkflow(input: CaseDraftInput): CaseWorkflow {
        val hours = extractHours(input.condition) ?: 4

        return CaseWorkflow(
            version = 1,
            title = "Solo activity safety",
            summary = "If you don't check in within $hours hours of starting your activity, your emergency contact will be alerted with your last known location.",
            trigger = TriggerSpec.MissedCheckIn(
                durationHours = hours,
                checkInPrompt = "Tap \"I'm safe\" to confirm you're okay."
            ),
            verification = VerificationSpec(
                enabled = true,
                notificationTitle = "Activity check-in",
                notificationBody = "You haven't checked in during your activity. Are you okay?",
                waitMinutes = 10,
                cancelActionLabel = "I'm safe"
            ),
            actions = listOf(
                ActionSpec.SendSms(
                    contactRole = "emergency contact",
                    message = "Safety alert: I started a solo activity and haven't checked in for $hours hours. Please try to reach me.",
                    includeLastKnownLocation = true,
                    requiresFinalUserApproval = true
                ),
                ActionSpec.CallContact(contactRole = "emergency contact")
            ),
            permissions = listOf(
                PermissionSpec("POST_NOTIFICATIONS", "Needed for activity check-in reminders.", true),
                PermissionSpec("ACCESS_FINE_LOCATION", "Needed to share your last known location in an emergency.", false)
            ),
            risk = RiskSpec(
                level = "medium",
                reasons = listOf(
                    "This workflow may contact your emergency contact.",
                    "This workflow may share your location.",
                    "This workflow may initiate a phone call."
                ),
                safetyRequirements = listOf(
                    "Show final review before activation.",
                    "Allow cancellation from notification.",
                    "Log every action."
                )
            ),
            userQuestions = listOf("Who should be contacted if you don't check in?")
        )
    }

    private fun buildWorkShiftWorkflow(input: CaseDraftInput): CaseWorkflow {
        val hours = extractHours(input.condition) ?: 8

        return CaseWorkflow(
            version = 1,
            title = "Work shift safety",
            summary = "Check in after your shift. If you don't respond within $hours hours, your trusted contact will be notified.",
            trigger = TriggerSpec.MissedCheckIn(
                durationHours = hours,
                checkInPrompt = "Tap \"Shift complete\" when you finish work."
            ),
            verification = VerificationSpec(
                enabled = true,
                notificationTitle = "Shift check-in",
                notificationBody = "Your expected shift time has passed. Are you okay?",
                waitMinutes = 20,
                cancelActionLabel = "Shift complete"
            ),
            actions = listOf(
                ActionSpec.SendSms(
                    contactRole = "trusted contact",
                    message = "Safety alert: I haven't checked in after my work shift. Please try reaching me.",
                    includeLastKnownLocation = false,
                    requiresFinalUserApproval = true
                )
            ),
            permissions = listOf(
                PermissionSpec("POST_NOTIFICATIONS", "Needed for shift completion reminders.", true)
            ),
            risk = RiskSpec(
                level = "low",
                reasons = listOf("This workflow may contact your trusted contact."),
                safetyRequirements = listOf(
                    "Show final review before activation.",
                    "Allow cancellation from notification.",
                    "Log every action."
                )
            ),
            userQuestions = listOf("Who should be notified if you don't check in after your shift?")
        )
    }

    /**
     * Extract hour duration from text like "24 hours", "48h", etc.
     */
    private fun extractHours(text: String): Int? {
        val patterns = listOf(
            Regex("(\\d+)\\s*hours?"),
            Regex("(\\d+)\\s*h\\b"),
            Regex("(\\d+)\\s*hrs?")
        )
        for (pattern in patterns) {
            pattern.find(text.lowercase())?.let {
                return it.groupValues[1].toIntOrNull()
            }
        }
        return null
    }
}
