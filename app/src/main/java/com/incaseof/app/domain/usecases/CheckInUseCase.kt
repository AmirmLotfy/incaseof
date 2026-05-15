package com.incaseof.app.domain.usecases

import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.data.repositories.CaseRepository
import javax.inject.Inject

class CheckInUseCase @Inject constructor(
    private val repository: CaseRepository,
    private val eventLogger: CaseEventLogger
) {
    /**
     * Record a check-in for a specific case.
     */
    suspend fun execute(caseId: String) {
        repository.recordCheckIn(caseId)
        eventLogger.log(
            caseId = caseId,
            type = CaseEventType.CHECK_IN,
            message = "User checked in."
        )
    }

    /**
     * Record a check-in for all active cases.
     */
    suspend fun checkInAll() {
        val activeCases = repository.getActiveCases()
        activeCases.forEach { case ->
            repository.recordCheckIn(case.id)
            eventLogger.log(
                caseId = case.id,
                type = CaseEventType.CHECK_IN,
                message = "User checked in (global)."
            )
        }
    }
}
