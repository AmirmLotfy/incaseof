package com.incaseof.app.domain.usecases

import com.incaseof.app.background.WorkScheduler
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.notifications.SafetyNotificationService
import com.incaseof.app.data.repositories.CaseRepository
import javax.inject.Inject

class MarkSafeUseCase @Inject constructor(
    private val repository: CaseRepository,
    private val workScheduler: WorkScheduler,
    private val notificationService: SafetyNotificationService,
    private val eventLogger: CaseEventLogger
) {
    suspend fun execute(caseId: String) {
        repository.markSafe(caseId)
        workScheduler.cancelVerification(caseId)
        notificationService.cancelNotifications(caseId)

        eventLogger.log(
            caseId = caseId,
            type = CaseEventType.USER_MARKED_SAFE,
            message = "User marked themselves safe."
        )
    }
}
