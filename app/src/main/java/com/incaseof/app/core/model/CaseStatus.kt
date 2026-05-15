package com.incaseof.app.core.model

/**
 * Lifecycle status of a safety case.
 */
enum class CaseStatus {
    DRAFT,
    ACTIVE,
    PAUSED,
    TRIGGERED,
    VERIFICATION_PENDING,
    RESOLVED
}
