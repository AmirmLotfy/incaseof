package com.incaseof.app.data.dao

import androidx.room.*
import com.incaseof.app.data.entities.CaseEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CaseDao {

    @Query("SELECT * FROM cases ORDER BY updatedAt DESC")
    fun observeAll(): Flow<List<CaseEntity>>

    @Query("SELECT * FROM cases WHERE status = 'ACTIVE' OR status = 'VERIFICATION_PENDING' OR status = 'TRIGGERED'")
    suspend fun getActiveCases(): List<CaseEntity>

    @Query("SELECT * FROM cases WHERE status = 'ACTIVE' OR status = 'VERIFICATION_PENDING' OR status = 'TRIGGERED'")
    fun observeActiveCases(): Flow<List<CaseEntity>>

    @Query("SELECT * FROM cases WHERE id = :id")
    suspend fun getById(id: String): CaseEntity?

    @Query("SELECT * FROM cases WHERE id = :id")
    fun observeById(id: String): Flow<CaseEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(case: CaseEntity)

    @Update
    suspend fun update(case: CaseEntity)

    @Query("UPDATE cases SET status = :status, updatedAt = :updatedAt WHERE id = :id")
    suspend fun updateStatus(id: String, status: String, updatedAt: Long = System.currentTimeMillis())

    @Query("UPDATE cases SET lastCheckInAt = :timestamp, updatedAt = :timestamp, isVerificationPending = 0 WHERE id = :id")
    suspend fun recordCheckIn(id: String, timestamp: Long)

    @Query("UPDATE cases SET isVerificationPending = 1, updatedAt = :now WHERE id = :id")
    suspend fun markVerificationPending(id: String, now: Long = System.currentTimeMillis())

    @Query("UPDATE cases SET isVerificationPending = 0, lastCheckInAt = :timestamp, updatedAt = :timestamp WHERE id = :id")
    suspend fun markSafe(id: String, timestamp: Long)

    @Query("UPDATE cases SET trustedContactName = :name, trustedContactPhone = :phone, trustedContactEmail = :email, trustedContactRelationship = :relationship, updatedAt = :now WHERE id = :id")
    suspend fun updateTrustedContact(
        id: String,
        name: String?,
        phone: String?,
        email: String?,
        relationship: String?,
        now: Long = System.currentTimeMillis()
    )

    @Query("DELETE FROM cases WHERE id = :id")
    suspend fun deleteById(id: String)

    @Query("SELECT COUNT(*) FROM cases")
    suspend fun count(): Int
}
