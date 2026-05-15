package com.incaseof.app.data.dao

import androidx.room.*
import com.incaseof.app.data.entities.CaseEventEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CaseEventDao {

    @Query("SELECT * FROM case_events WHERE caseId = :caseId ORDER BY timestamp DESC")
    fun observeByCaseId(caseId: String): Flow<List<CaseEventEntity>>

    @Query("SELECT * FROM case_events ORDER BY timestamp DESC LIMIT :limit")
    fun observeRecent(limit: Int = 50): Flow<List<CaseEventEntity>>

    @Query("SELECT * FROM case_events ORDER BY timestamp DESC")
    fun observeAll(): Flow<List<CaseEventEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(event: CaseEventEntity)

    @Query("DELETE FROM case_events WHERE caseId = :caseId")
    suspend fun deleteByCaseId(caseId: String)
}
