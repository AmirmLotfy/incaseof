package com.incaseof.app.data.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "cases")
data class CaseEntity(
    @PrimaryKey val id: String,
    val title: String,
    val summary: String,
    val status: String,
    val createdAt: Long,
    val updatedAt: Long,
    val lastCheckInAt: Long?,
    val planJson: String,
    val riskLevel: String,
    val trustedContactName: String?,
    val trustedContactPhone: String?,
    val trustedContactEmail: String?,
    val trustedContactRelationship: String?,
    val requiresLocation: Boolean,
    val isSimulationEnabled: Boolean,
    val isVerificationPending: Boolean = false,
    val inputCondition: String = "",
    val inputAction: String = ""
)
