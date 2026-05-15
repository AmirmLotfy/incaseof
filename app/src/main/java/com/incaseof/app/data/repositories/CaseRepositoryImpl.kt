package com.incaseof.app.data.repositories

import com.incaseof.app.data.dao.CaseDao
import com.incaseof.app.data.dao.CaseEventDao
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.entities.CaseEventEntity
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CaseRepositoryImpl @Inject constructor(
    private val caseDao: CaseDao,
    private val caseEventDao: CaseEventDao
) : CaseRepository {

    override fun observeAllCases(): Flow<List<CaseEntity>> = caseDao.observeAll()

    override fun observeActiveCases(): Flow<List<CaseEntity>> = caseDao.observeActiveCases()

    override fun observeCase(id: String): Flow<CaseEntity?> = caseDao.observeById(id)

    override fun observeEvents(caseId: String): Flow<List<CaseEventEntity>> =
        caseEventDao.observeByCaseId(caseId)

    override fun observeRecentEvents(limit: Int): Flow<List<CaseEventEntity>> =
        caseEventDao.observeRecent(limit)

    override fun observeAllEvents(): Flow<List<CaseEventEntity>> = caseEventDao.observeAll()

    override suspend fun getActiveCases(): List<CaseEntity> = caseDao.getActiveCases()

    override suspend fun getCase(id: String): CaseEntity? = caseDao.getById(id)

    override suspend fun saveCase(case: CaseEntity) = caseDao.insert(case)

    override suspend fun updateCase(case: CaseEntity) = caseDao.update(case)

    override suspend fun updateStatus(id: String, status: String) =
        caseDao.updateStatus(id, status)

    override suspend fun recordCheckIn(id: String) =
        caseDao.recordCheckIn(id, System.currentTimeMillis())

    override suspend fun markVerificationPending(id: String) =
        caseDao.markVerificationPending(id)

    override suspend fun markSafe(id: String) =
        caseDao.markSafe(id, System.currentTimeMillis())

    override suspend fun updateTrustedContact(
        id: String,
        name: String?,
        phone: String?,
        email: String?,
        relationship: String?
    ) = caseDao.updateTrustedContact(id, name, phone, email, relationship)

    override suspend fun deleteCase(id: String) {
        caseEventDao.deleteByCaseId(id)
        caseDao.deleteById(id)
    }

    override suspend fun caseCount(): Int = caseDao.count()
}
