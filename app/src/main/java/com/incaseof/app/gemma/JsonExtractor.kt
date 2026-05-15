package com.incaseof.app.gemma

/**
 * Extracts JSON objects from model text responses.
 */
object JsonExtractor {

    /**
     * Extract the first JSON object from a string that may contain
     * markdown formatting, explanatory text, or other content.
     */
    fun extractFirstJsonObject(text: String): String? {
        // Try to find JSON in code blocks first
        val codeBlockPattern = Regex("```(?:json)?\\s*\\n?(\\{[\\s\\S]*?\\})\\s*\\n?```")
        codeBlockPattern.find(text)?.let {
            return it.groupValues[1].trim()
        }

        // Try to find a raw JSON object
        val firstBrace = text.indexOf('{')
        if (firstBrace == -1) return null

        var depth = 0
        var inString = false
        var escape = false

        for (i in firstBrace until text.length) {
            val char = text[i]

            if (escape) {
                escape = false
                continue
            }

            when {
                char == '\\' && inString -> escape = true
                char == '"' -> inString = !inString
                char == '{' && !inString -> depth++
                char == '}' && !inString -> {
                    depth--
                    if (depth == 0) {
                        return text.substring(firstBrace, i + 1).trim()
                    }
                }
            }
        }

        return null
    }
}
