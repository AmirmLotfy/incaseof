package com.incaseof.app.domain.models

/**
 * User's two-field input for creating a case.
 */
data class CaseDraftInput(
    val condition: String, // "In case of..."
    val action: String     // "The app should..."
)
