package com.incaof.app.core.auth

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DemoAuthRepositoryTest {
    @Test
    fun `holds only the issued token and cannot run account operations`() =
        runTest {
            val auth = DemoAuthRepository("token", "Mona")

            assertEquals("token", auth.currentAccessTokenBlocking())
            assertTrue(auth.session.value is AuthState.SignedIn)
            assertTrue(auth.signIn("judge@example.test", "irrelevant").isFailure)

            auth.signOut()
            assertEquals(AuthState.SignedOut, auth.session.value)
        }
}
