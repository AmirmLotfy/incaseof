package com.incaof.app.feature.account

import com.incaof.app.data.RecordingRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AccountViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before fun setUp() = Dispatchers.setMain(dispatcher)

    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `deletion stays disabled until the exact confirmation is entered`() {
        val vm = AccountViewModel(RecordingRepository())

        vm.changeConfirmation("delete")
        assertFalse((vm.state.value as AccountUiState.Ready).canDelete)
        vm.deleteAccount()

        assertTrue((vm.state.value as AccountUiState.Ready).confirmation == "delete")
    }

    @Test
    fun `confirmed deletion calls the repository once and shows stopped monitoring`() =
        runTest(dispatcher) {
            val repository = RecordingRepository()
            val vm = AccountViewModel(repository)
            vm.changeConfirmation("DELETE")

            vm.deleteAccount()
            runCurrent()

            assertEquals(listOf("DELETE"), repository.deleteAccountCalls)
            val requested = vm.state.value as AccountUiState.Requested
            assertTrue(requested.deletion.monitoringStopped)
        }

    @Test
    fun `failed deletion remains available for a retry`() =
        runTest(dispatcher) {
            val repository = RecordingRepository(failOnWrite = java.net.UnknownHostException("offline"))
            val vm = AccountViewModel(repository)
            vm.changeConfirmation("DELETE")

            vm.deleteAccount()
            runCurrent()

            val ready = vm.state.value as AccountUiState.Ready
            assertFalse(ready.busy)
            assertTrue(ready.canDelete)
            assertTrue(ready.error?.contains("still running") == true)
        }
}
