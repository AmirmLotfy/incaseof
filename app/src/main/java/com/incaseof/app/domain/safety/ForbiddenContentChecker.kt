package com.incaseof.app.domain.safety

/**
 * Scans content for forbidden/unsafe patterns.
 */
object ForbiddenContentChecker {

    private val forbiddenPhrases = listOf(
        "record audio",
        "spy on",
        "track someone else",
        "track another person",
        "hide from",
        "without their consent",
        "without consent",
        "call emergency services",
        "call 911",
        "call 112",
        "call 999",
        "stalk",
        "monitor secretly",
        "hidden camera",
        "wiretap",
        "surveillance",
        "background microphone",
        "listen in",
        "eavesdrop",
        "keylogger",
        "screen capture someone",
        "read their messages",
        "access their phone",
        "unlock their device",
        "medical diagnosis",
        "prescribe medication",
        "legal advice"
    )

    /**
     * Check if text contains any forbidden content.
     * Returns list of detected forbidden phrases.
     */
    fun check(text: String): List<String> {
        val lowerText = text.lowercase()
        return forbiddenPhrases.filter { lowerText.contains(it) }
    }

    /**
     * Returns true if the text is safe (no forbidden content).
     */
    fun isSafe(text: String): Boolean = check(text).isEmpty()
}
