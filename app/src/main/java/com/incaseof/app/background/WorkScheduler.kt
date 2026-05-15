package com.incaseof.app.background

import android.content.Context
import androidx.work.*
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class WorkScheduler @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        const val GLOBAL_INACTIVITY_CHECKER = "global_inactivity_checker"
        const val VERIFICATION_TIMEOUT_PREFIX = "verification_timeout_"
        const val TAG_INACTIVITY = "inactivity_checker"
    }

    /**
     * Schedule the global periodic inactivity checker (every 15 minutes).
     */
    fun scheduleGlobalInactivityChecker() {
        val request = PeriodicWorkRequestBuilder<InactivityCheckWorker>(
            15, TimeUnit.MINUTES
        )
            .addTag(TAG_INACTIVITY)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                30,
                TimeUnit.SECONDS
            )
            .build()

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            GLOBAL_INACTIVITY_CHECKER,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }

    /**
     * Schedule a one-time verification timeout worker.
     * Fires after the verification wait period expires.
     */
    fun scheduleVerificationTimeout(caseId: String, waitMinutes: Int) {
        val request = OneTimeWorkRequestBuilder<VerificationTimeoutWorker>()
            .setInitialDelay(waitMinutes.toLong(), TimeUnit.MINUTES)
            .setInputData(workDataOf("caseId" to caseId))
            .addTag("${VERIFICATION_TIMEOUT_PREFIX}$caseId")
            .build()

        WorkManager.getInstance(context).enqueueUniqueWork(
            "${VERIFICATION_TIMEOUT_PREFIX}$caseId",
            ExistingWorkPolicy.REPLACE,
            request
        )
    }

    /**
     * Cancel verification timeout for a case (user tapped "I'm safe").
     */
    fun cancelVerification(caseId: String) {
        WorkManager.getInstance(context)
            .cancelUniqueWork("${VERIFICATION_TIMEOUT_PREFIX}$caseId")
    }

    /**
     * Cancel all scheduled work.
     */
    fun cancelAll() {
        WorkManager.getInstance(context).cancelAllWork()
    }

    /**
     * Cancel the global inactivity checker.
     */
    fun cancelGlobalChecker() {
        WorkManager.getInstance(context)
            .cancelUniqueWork(GLOBAL_INACTIVITY_CHECKER)
    }
}
