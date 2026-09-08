package com.incaof.app.data

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DemoFallbackIcoRepositoryTest {
    @Test
    fun `fallback is explicit and remains a server-valid plan document`() {
        val draft = safeDemoDraft("Africa/Cairo")
        val document = Json.parseToJsonElement(draft.compiledPlanJson).jsonObject
        val steps = document.getValue("steps").jsonArray

        assertEquals("ROUTINE", document.getValue("type").jsonPrimitive.content)
        assertEquals("Africa/Cairo", document.getValue("timezone").jsonPrimitive.content)
        assertEquals(5, steps.size)
        assertEquals(
            4500,
            steps
                .last()
                .jsonObject
                .getValue("offsetSeconds")
                .jsonPrimitive
                .int,
        )
        assertTrue(draft.warnings.single().contains("no model trace", ignoreCase = true))
        assertTrue(!draft.preview.active)
    }
}
