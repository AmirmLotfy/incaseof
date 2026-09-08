package com.incaof.app.data

import com.incaof.app.domain.ContextRelease
import com.incaof.app.domain.EscalationStep
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import com.incaof.app.domain.ReleaseLevel
import com.incaof.app.domain.ResponderRole
import com.incaof.app.domain.StepAction
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject

/**
 * Keeps the isolated judge walkthrough usable when its model runtime is unavailable.
 *
 * Only compilation falls back. Saving, scheduling, escalation, responder authorization,
 * and the audit timeline still use the deployed demo API through [upstream]. The preview
 * carries an explicit warning so a deterministic template is never presented as model output.
 */
class DemoFallbackIcoRepository(
    private val upstream: IcoRepository,
) : IcoRepository by upstream {
    override suspend fun compilePlan(description: String, timezone: String): Result<CompiledPlanDraft> =
        upstream.compilePlan(description, timezone).recover { safeDemoDraft(timezone) }
}

internal fun safeDemoDraft(timezone: String): CompiledPlanDraft {
    val steps =
        listOf(
            EscalationStep(1, 0, StepAction.PUSH_SUBJECT, null),
            EscalationStep(2, 600, StepAction.PUSH_SUBJECT, null),
            EscalationStep(3, 1200, StepAction.SMS_SUBJECT, null),
            EscalationStep(4, 1500, StepAction.MESSAGE_RESPONDER, ResponderRole.PRIMARY),
            // About a minute for a judge to read and claim before the accelerated backup rung.
            EscalationStep(5, 4500, StepAction.MESSAGE_RESPONDER, ResponderRole.BACKUP),
        )
    val document =
        buildJsonObject {
            put("type", "ROUTINE")
            put("label", "Mona’s evening check-in")
            put("timezone", timezone)
            putJsonObject("trigger") {
                put("kind", "RECURRING")
                put("timeOfDay", "21:00")
            }
            putJsonObject("grace") { put("seconds", 0) }
            put(
                "steps",
                buildJsonArray {
                    for (step in steps) {
                        add(
                            buildJsonObject {
                                put("sequence", step.sequence)
                                put("offsetSeconds", step.offsetSeconds)
                                put("action", step.action.name)
                                step.targetRole?.let { put("targetRole", it.name) }
                            },
                        )
                    }
                },
            )
            put(
                "stopConditions",
                buildJsonArray {
                    add(JsonPrimitive("SUBJECT_EXPLICIT_CONFIRMATION"))
                    add(JsonPrimitive("RESPONDER_VERIFIED_CONTACT"))
                },
            )
            putJsonObject("contextPolicy") {
                put("location", "NEVER")
                put("battery", "AFTER_SUBJECT_CALL_FAILED")
                put("lastConnection", "CIRCLE_ESCALATION")
            }
            put("leaseSeconds", 600)
        }
    return CompiledPlanDraft(
        compiledPlanJson = document.toString(),
        preview =
            Plan(
                id = "demo-template-preview",
                label = "Mona’s evening check-in",
                type = PlanType.ROUTINE,
                cadence = "Daily",
                timeOfDay = "21:00",
                active = false,
                steps = steps,
                contextPolicy =
                    listOf(
                        ContextRelease("Location", ReleaseLevel.NEVER),
                        ContextRelease("Battery", ReleaseLevel.AFTER_SUBJECT_CALL_FAILED),
                        ContextRelease("Last connection", ReleaseLevel.CIRCLE_ESCALATION),
                    ),
            ),
        warnings =
            listOf(
                "AgentCore was unavailable. This is the validated Routine template; no model trace exists for this preview.",
            ),
    )
}
