package com.incaof.app.core.network

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class RegisterDeviceRequestTest {
    @Test
    fun usesTheBackendDeviceRegistrationContract() {
        val payload =
            Json
                .parseToJsonElement(
                    Json.encodeToString(
                        RegisterDeviceRequest(
                            deviceId = "device-123",
                            registrationToken = "opaque-fcm-capability",
                        ),
                    ),
                ).jsonObject

        assertEquals("device-123", payload.getValue("deviceId").toString().trim('"'))
        assertEquals(
            "opaque-fcm-capability",
            payload.getValue("registrationToken").toString().trim('"'),
        )
        assertFalse(payload.containsKey("token"))
        assertFalse(payload.containsKey("platform"))
    }
}
