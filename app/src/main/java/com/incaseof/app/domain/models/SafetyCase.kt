package com.incaseof.app.domain.models

/**
 * Domain model combining entity data with parsed workflow.
 */
data class SafetyCase(
    val id: String,
    val title: String,
    val summary: String,
    val status: com.incaseof.app.core.model.CaseStatus,
    val createdAt: Long,
    val updatedAt: Long,
    val lastCheckInAt: Long?,
    val workflow: CaseWorkflow,
    val riskLevel: com.incaseof.app.core.model.RiskLevel,
    val trustedContactName: String?,
    val trustedContactPhone: String?,
    val trustedContactEmail: String?,
    val trustedContactRelationship: String?,
    val requiresLocation: Boolean,
    val isSimulationEnabled: Boolean,
    val isVerificationPending: Boolean,
    val inputCondition: String,
    val inputAction: String
)
