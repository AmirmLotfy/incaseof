package com.incaseof.app.gemma

import com.incaseof.app.domain.models.CaseDraftInput
import com.incaseof.app.domain.models.CasePlanResult

/**
 * Interface for case planning models.
 * Implementations: GemmaCasePlanner (real), MockCasePlanner (demo/testing).
 */
interface CasePlannerModel {
    suspend fun compileCase(input: CaseDraftInput): CasePlanResult
}
