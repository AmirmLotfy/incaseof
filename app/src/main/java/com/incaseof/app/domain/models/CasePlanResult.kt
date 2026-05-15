package com.incaseof.app.domain.models

/**
 * Result of Gemma case compilation.
 */
sealed class CasePlanResult {
    data class Valid(val workflow: CaseWorkflow) : CasePlanResult()
    data class Invalid(val errors: String) : CasePlanResult()
    data class NeedsClarification(val questions: List<String>, val partialWorkflow: CaseWorkflow?) : CasePlanResult()
}
