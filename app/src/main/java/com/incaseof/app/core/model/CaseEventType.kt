package com.incaseof.app.core.model

/**
 * Types of events logged in the case timeline.
 */
enum class CaseEventType {
    CREATED,
    ACTIVATED,
    PAUSED,
    RESUMED,
    CHECK_IN,
    MISSED_CHECK_IN,
    VERIFICATION_STARTED,
    VERIFICATION_EXPIRED,
    USER_MARKED_SAFE,
    ACTION_PREPARED,
    ACTION_EXECUTED,
    CASE_EDITED,
    CASE_DELETED,
    SIMULATION_RUN,
    ERROR
}
