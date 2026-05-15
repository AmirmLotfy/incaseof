package com.incaseof.app.background

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.core.notifications.SafetyNotificationService
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseWorkflow
import com.incaseof.app.domain.models.TriggerSpec
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.serialization.json.Json
import java.util.concurrent.TimeUnit

/**
 * Global periodic worker that checks all active cases for missed check-ins.
 * Runs every 15 minutes via WorkManager.
 */
@HiltWorker
class InactivityCheckWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val caseRepository: CaseRepository,
    private val notificationService: SafetyNotificationService,
    private val workScheduler: WorkScheduler,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        return try {
            val now = System.currentTimeMillis()
            val activeCases = caseRepository.getActiveCases()

            activeCases.forEach { caseEntity ->
                if (caseEntity.isVerificationPending) return@forEach
                if (caseEntity.status != CaseStatus.ACTIVE.name) return@forEach

                try {
                    val workflow = json.decodeFromString<CaseWorkflow>(caseEntity.planJson)
                    val trigger = workflow.trigger

                    if (trigger is TriggerSpec.MissedCheckIn) {
                        val lastCheckIn = caseEntity.lastCheckInAt ?: caseEntity.createdAt
                        val elapsedHours = TimeUnit.MILLISECONDS.toHours(now - lastCheckIn)

                        if (elapsedHours >= trigger.durationHours) {
                            // Missed check-in detected
                            caseRepository.markVerificationPending(caseEntity.id)

                            eventLogger.log(
                                caseId = caseEntity.id,
                                type = CaseEventType.MISSED_CHECK_IN,
                                message = "Missed check-in detected after ${elapsedHours}h."
                            )

                            eventLogger.log(
                                caseId = caseEntity.id,
                                type = CaseEventType.VERIFICATION_STARTED,
                                message = "Verification notification sent. Waiting ${workflow.verification.waitMinutes} minutes."
                            )

                            notificationService.showSafetyCheckNotification(
                                caseId = caseEntity.id,
                                title = workflow.verification.notificationTitle,
                                body = workflow.verification.notificationBody,
                                cancelLabel = workflow.verification.cancelActionLabel
                            )

                            workScheduler.scheduleVerificationTimeout(
                                caseId = caseEntity.id,
                                waitMinutes = workflow.verification.waitMinutes
                            )
                        }
                    }
                } catch (e: Exception) {
                    eventLogger.log(
                        caseId = caseEntity.id,
                        type = CaseEventType.ERROR,
                        message = "Error checking case: ${e.message}"
                    )
                }
            }

            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
