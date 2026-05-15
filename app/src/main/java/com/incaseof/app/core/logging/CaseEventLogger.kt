package com.incaseof.app.core.logging

import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.data.entities.CaseEventEntity
import com.incaseof.app.data.dao.CaseEventDao
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CaseEventLogger @Inject constructor(
    private val caseEventDao: CaseEventDao
) {
    suspend fun log(
        caseId: String,
        type: CaseEventType,
        message: String,
        metadata: String? = null
    ) {
        val event = CaseEventEntity(
            id = UUID.randomUUID().toString(),
            caseId = caseId,
            timestamp = System.currentTimeMillis(),
            type = type.name,
            message = message,
            metadataJson = metadata
        )
        caseEventDao.insert(event)
    }
}
