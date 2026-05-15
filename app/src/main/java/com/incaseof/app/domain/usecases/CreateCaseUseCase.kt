package com.incaseof.app.domain.usecases

import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.core.model.RiskLevel
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseDraftInput
import com.incaseof.app.domain.models.CasePlanResult
import com.incaseof.app.domain.models.CaseWorkflow
import com.incaseof.app.domain.models.ActionSpec
import com.incaseof.app.domain.validators.WorkflowSafetyValidator
import com.incaseof.app.gemma.CasePlannerModel
import kotlinx.serialization.json.Json
import java.util.UUID
import javax.inject.Inject

class CreateCaseUseCase @Inject constructor(
    private val planner: CasePlannerModel,
    private val repository: CaseRepository,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) {
    /**
     * Compile a case from user input, validate it, and save as draft.
     */
    suspend fun execute(input: CaseDraftInput): CreateCaseResult {
        // Step 1: Have Gemma compile the case
        val planResult = planner.compileCase(input)

        return when (planResult) {
            is CasePlanResult.Valid -> {
                // Step 2: Validate with deterministic rules
                val validation = WorkflowSafetyValidator.validate(planResult.workflow)
                if (!validation.isValid) {
                    CreateCaseResult.ValidationFailed(validation.errors)
                } else {
                    // Step 3: Save as draft
                    val caseId = UUID.randomUUID().toString()
                    val now = System.currentTimeMillis()
                    val workflow = planResult.workflow

                    val riskLevel = when (workflow.risk.level.lowercase()) {
                        "high" -> RiskLevel.HIGH
                        "medium" -> RiskLevel.MEDIUM
                        else -> RiskLevel.LOW
                    }

                    val requiresLocation = workflow.actions.any { action ->
                        when (action) {
                            is ActionSpec.SendSms -> action.includeLastKnownLocation
                            is ActionSpec.SendEmail -> action.includeLastKnownLocation
                            else -> false
                        }
                    }

                    val entity = CaseEntity(
                        id = caseId,
                        title = workflow.title,
                        summary = workflow.summary,
                        status = CaseStatus.DRAFT.name,
                        createdAt = now,
                        updatedAt = now,
                        lastCheckInAt = null,
                        planJson = json.encodeToString(CaseWorkflow.serializer(), workflow),
                        riskLevel = riskLevel.name,
                        trustedContactName = null,
                        trustedContactPhone = null,
                        trustedContactEmail = null,
                        trustedContactRelationship = null,
                        requiresLocation = requiresLocation,
                        isSimulationEnabled = false,
                        isVerificationPending = false,
                        inputCondition = input.condition,
                        inputAction = input.action
                    )

                    repository.saveCase(entity)

                    eventLogger.log(
                        caseId = caseId,
                        type = CaseEventType.CREATED,
                        message = "Case created: ${workflow.title}"
                    )

                    CreateCaseResult.Success(caseId, workflow)
                }
            }
            is CasePlanResult.Invalid -> {
                CreateCaseResult.CompilationFailed(planResult.errors)
            }
            is CasePlanResult.NeedsClarification -> {
                CreateCaseResult.NeedsClarification(
                    questions = planResult.questions,
                    partialWorkflow = planResult.partialWorkflow
                )
            }
        }
    }
}

sealed class CreateCaseResult {
    data class Success(val caseId: String, val workflow: CaseWorkflow) : CreateCaseResult()
    data class CompilationFailed(val error: String) : CreateCaseResult()
    data class ValidationFailed(val errors: List<String>) : CreateCaseResult()
    data class NeedsClarification(val questions: List<String>, val partialWorkflow: CaseWorkflow?) : CreateCaseResult()
}
