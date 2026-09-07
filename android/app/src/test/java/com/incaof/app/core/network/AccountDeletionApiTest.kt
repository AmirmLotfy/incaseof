package com.incaof.app.core.network

import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import okhttp3.MediaType.Companion.toMediaType
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

class AccountDeletionApiTest {
    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.close()
    }

    @Test
    fun `account deletion sends an HTTP DELETE with the exact confirmation body`() =
        runTest {
            server.enqueue(
                MockResponse
                    .Builder()
                    .code(202)
                    .addHeader("Content-Type", "application/json")
                    .body(
                        """{"requestId":"request-1","status":"PENDING","requestedAt":"2026-09-08T12:00:00Z","monitoringStopped":true,"nextSteps":[]}""",
                    ).build(),
            )
            val api =
                Retrofit
                    .Builder()
                    .baseUrl(server.url("/"))
                    .addConverterFactory(
                        Json.asConverterFactory("application/json".toMediaType()),
                    ).build()
                    .create(IcoApi::class.java)

            assertTrue(api.deleteAccount(DeleteAccountRequest("DELETE")).isSuccessful)

            val request = server.takeRequest()
            assertEquals("DELETE", request.method)
            assertEquals("/v1/account", request.target)
            assertEquals("{\"confirmation\":\"DELETE\"}", request.body?.utf8())
        }
}
