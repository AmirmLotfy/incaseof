package com.incaseof.app.data.repositories

import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.entities.CaseEventEntity
import kotlinx.coroutines.flow.Flow

interface CaseRepository {
    fun observeAllCases(): Flow<List<CaseEntity>>
    fun observeActiveCases(): Flow<List<CaseEntity>>
    fun observeCase(id: String): Flow<CaseEntity?>
    fun observeEvents(caseId: String): Flow<List<CaseEventEntity>>
    fun observeRecentEvents(limit: Int = 50): Flow<List<CaseEventEntity>>
    fun observeAllEvents(): Flow<List<CaseEventEntity>>

    suspend fun getActiveCases(): List<CaseEntity>
    suspend fun getCase(id: String): CaseEntity?
    suspend fun saveCase(case: CaseEntity)
    suspend fun updateCase(case: CaseEntity)
    suspend fun updateStatus(id: String, status: String)
    suspend fun recordCheckIn(id: String)
    suspend fun markVerificationPending(id: String)
    suspend fun markSafe(id: String)
    suspend fun updateTrustedContact(
        id: String,
        name: String?,
        phone: String?,
        email: String?,
        relationship: String?
    )
    suspend fun deleteCase(id: String)
    suspend fun caseCount(): Int
}
