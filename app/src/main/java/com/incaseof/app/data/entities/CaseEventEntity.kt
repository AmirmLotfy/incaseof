package com.incaseof.app.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "case_events")
data class CaseEventEntity(
    @PrimaryKey val id: String,
    val caseId: String,
    val timestamp: Long,
    val type: String,
    val message: String,
    val metadataJson: String? = null
)
