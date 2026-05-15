package com.incaseof.app.background

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.incaseof.app.background.actions.ActionExecutor
import com.incaseof.app.core.logging.CaseEventLogger
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.data.repositories.CaseRepository
import com.incaseof.app.domain.models.CaseWorkflow
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.serialization.json.Json

/**
 * One-time worker that fires when the verification window expires.
 * If the user hasn't responded, prepares the approved actions.
 */
@HiltWorker
class VerificationTimeoutWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val caseRepository: CaseRepository,
    private val actionExecutor: ActionExecutor,
    private val eventLogger: CaseEventLogger,
    private val json: Json
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val caseId = inputData.getString("caseId") ?: return Result.failure()

        return try {
            val caseEntity = caseRepository.getCase(caseId) ?: return Result.failure()

            // Only proceed if still verification pending and active
            if (!caseEntity.isVerificationPending || caseEntity.status != CaseStatus.ACTIVE.name) {
                return Result.success()
            }

            eventLogger.log(
                caseId = caseId,
                type = CaseEventType.VERIFICATION_EXPIRED,
                message = "Verification timed out. Preparing approved actions."
            )

            // Update status to triggered
            caseRepository.updateStatus(caseId, CaseStatus.TRIGGERED.name)

            // Parse workflow and execute actions
            val workflow = json.decodeFromString<CaseWorkflow>(caseEntity.planJson)
            actionExecutor.executeActions(caseEntity, workflow)

            Result.success()
        } catch (e: Exception) {
            eventLogger.log(
                caseId = caseId,
                type = CaseEventType.ERROR,
                message = "Error executing actions: ${e.message}"
            )
            Result.failure()
        }
    }
}
