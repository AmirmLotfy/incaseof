package com.incaof.app.core.network

import com.incaof.app.core.auth.DemoAuthRepository
import mockwebserver3.MockResponse
import mockwebserver3.MockWebServer
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

class DemoRouteInterceptorTest {
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
    fun `rewrites product calls into demo realm and preserves query and token`() {
        server.enqueue(MockResponse.Builder().code(200).build())
        val client =
            OkHttpClient
                .Builder()
                .addInterceptor(DemoRouteInterceptor())
                .addInterceptor(BearerTokenInterceptor(DemoAuthRepository("short-lived-token", "Mona")))
                .build()

        client.newCall(Request.Builder().url(server.url("/v1/plans/plan-1?view=full")).build()).execute().close()

        val request = server.takeRequest()
        assertEquals("/v1/demo/plans/plan-1?view=full", request.target)
        assertEquals("Bearer short-lived-token", request.headers["Authorization"])
    }

    @Test
    fun `does not rewrite demo session minting endpoint`() {
        server.enqueue(MockResponse.Builder().code(201).build())
        val client = OkHttpClient.Builder().addInterceptor(DemoRouteInterceptor()).build()

        client
            .newCall(
                Request
                    .Builder()
                    .url(
                        server.url("/v1/demo/session"),
                    ).post(byteArrayOf().toRequestBody())
                    .build(),
            ).execute()
            .close()

        assertEquals("/v1/demo/session", server.takeRequest().target)
    }
}
