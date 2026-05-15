package com.incaseof.app.data.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.incaseof.app.data.dao.CaseDao
import com.incaseof.app.data.dao.CaseEventDao
import com.incaseof.app.data.entities.CaseEntity
import com.incaseof.app.data.entities.CaseEventEntity

@Database(
    entities = [CaseEntity::class, CaseEventEntity::class],
    version = 1,
    exportSchema = true
)
abstract class InCaseOfDatabase : RoomDatabase() {
    abstract fun caseDao(): CaseDao
    abstract fun caseEventDao(): CaseEventDao
}
