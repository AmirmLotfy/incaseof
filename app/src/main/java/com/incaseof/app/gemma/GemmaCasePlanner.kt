package com.incaseof.app.gemma

import com.incaseof.app.domain.models.CaseDraftInput
import com.incaseof.app.domain.models.CasePlanResult
import com.incaseof.app.domain.models.CaseWorkflow
import com.incaseof.app.domain.validators.WorkflowSafetyValidator
import kotlinx.serialization.json.Json
import javax.inject.Inject

/**
 * Real Gemma case planner using LiteRT-LM on-device inference.
 * Uses Approach B (prompt-only JSON output) from the PRD.
 *
 * Architecture:
 * 1. Build prompt from user's condition + action using PromptTemplates
 * 2. Send to Gemma 4 E2B via GemmaEngineProvider (LiteRT-LM 0.11.0)
 * 3. Extract JSON from model response (handles markdown wrapping)
 * 4. Deserialize into CaseWorkflow
 * 5. Validate against deterministic safety rules
 * 6. Return typed result (Valid, Invalid, or NeedsClarification)
 *
 * The system instruction is configured in GemmaEngineProvider's ConversationConfig,
 * so the prompt sent here is just the user's case description.
 */
class GemmaCasePlanner @Inject constructor(
    private val engineProvider: GemmaEngineProvider,
    private val json: Json
) : CasePlannerModel {

    override suspend fun compileCase(input: CaseDraftInput): CasePlanResult {
        val prompt = PromptTemplates.compileCasePrompt(input.condition, input.action)

        return try {
            // Generate response from on-device Gemma model
            // When LiteRT-LM is enabled, this calls:
            //   engine.createConversation(config).use { conversation ->
            //       conversation.sendMessage(prompt).text
            //   }
            val response = engineProvider.generate(prompt)

            // Extract JSON from model output (handles ```json blocks, surrounding text)
            val jsonBlock = JsonExtractor.extractFirstJsonObject(response)
                ?: return CasePlanResult.Invalid(
                    "Gemma did not return valid JSON. Raw response: ${response.take(200)}"
                )

            // Deserialize into typed workflow model
            val workflow = try {
                json.decodeFromString<CaseWorkflow>(jsonBlock)
            } catch (e: Exception) {
                return CasePlanResult.Invalid(
                    "Failed to parse workflow JSON: ${e.message}"
                )
            }

            // Check for clarifying questions from the model
            if (workflow.userQuestions.isNotEmpty()) {
                return CasePlanResult.NeedsClarification(
                    questions = workflow.userQuestions,
                    partialWorkflow = workflow
                )
            }

            // Deterministic safety validation — never trust model output
            val validation = WorkflowSafetyValidator.validate(workflow)
            if (validation.isValid) {
                CasePlanResult.Valid(workflow)
            } else {
                CasePlanResult.Invalid(
                    "Safety validation failed:\n${validation.errors.joinToString("\n• ", "• ")}"
                )
            }
        } catch (e: UnsupportedOperationException) {
            // Engine not enabled — this is expected when using MockCasePlanner
            CasePlanResult.Invalid(
                "On-device model not available. The app is using the mock planner."
            )
        } catch (e: Exception) {
            CasePlanResult.Invalid("Failed to compile case: ${e.message}")
        }
    }
}
