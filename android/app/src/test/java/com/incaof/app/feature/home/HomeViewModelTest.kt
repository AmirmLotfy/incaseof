package com.incaof.app.feature.home

import com.incaof.app.data.ConfirmSource
import com.incaof.app.data.RecordingRepository
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.Moment
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
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.Instant

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before fun setUp() = Dispatchers.setMain(dispatcher)

    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `a waiting moment asks the person for something`() =
        runTest(dispatcher) {
            val vm = HomeViewModel(RecordingRepository.waiting())
            runCurrent()

            val state = vm.state.value as HomeUiState.Content
            assertTrue("expected the screen to ask for a check", state.needsAction)
        }

    @Test
    fun `confirming sends a key derived from the moment, not a fresh one`() =
        runTest(dispatcher) {
            // A generated key would make a double tap two different confirmations racing
            // each other. Derived, they collapse into one.
            val repo = RecordingRepository.waiting()
            val vm = HomeViewModel(repo)
            runCurrent()

            vm.confirm()
            runCurrent()
            vm.confirm()
            runCurrent()

            val keys = repo.confirmCalls.map { it.second }.distinct()
            assertEquals("all confirmations should share one key", 1, keys.size)
            assertEquals("confirm-moment-evening", keys.single())
        }

    @Test
    fun `confirming from the app is recorded as coming from the app`() =
        runTest(dispatcher) {
            val repo = RecordingRepository.waiting()
            val vm = HomeViewModel(repo)
            runCurrent()

            vm.confirm()
            runCurrent()

            assertEquals(ConfirmSource.APP, repo.confirmCalls.single().third)
        }

    @Test
    fun `a successful confirmation clears the request`() =
        runTest(dispatcher) {
            val vm = HomeViewModel(RecordingRepository.waiting())
            runCurrent()

            vm.confirm()
            runCurrent()

            val state = vm.state.value as HomeUiState.Content
            assertNull(state.moment)
            assertFalse(state.needsAction)
        }

    @Test
    fun `a failed confirmation keeps the action available`() =
        runTest(dispatcher) {
            // Someone who was not heard needs another way to be heard, not an error page.
            val repo =
                RecordingRepository(
                    moment =
                        Moment(
                            id = "moment-evening",
                            planLabel = "Evening check",
                            dueAt = Instant.parse("2026-08-26T21:00:00Z"),
                            graceUntil = Instant.parse("2026-08-26T21:00:00Z"),
                            alertState = AlertState.SELF_CONTACT,
                        ),
                    failOnWrite = java.net.UnknownHostException("offline"),
                )
            val vm = HomeViewModel(repo)
            runCurrent()

            vm.confirm()
            runCurrent()

            val state = vm.state.value as? HomeUiState.Content
            assertNotNull("should stay on the screen, not fall to an error state", state)
            assertNotNull(state!!.error)
            assertFalse("the action must be usable again", state.submitting)
            assertTrue("the check is still outstanding", state.needsAction)
        }

    @Test
    fun `an offline error explains that the plan is still running`() =
        runTest(dispatcher) {
            val vm =
                HomeViewModel(
                    RecordingRepository(null, failWith = java.net.UnknownHostException("offline")),
                )
            runCurrent()

            val message = (vm.state.value as HomeUiState.Failed).message
            assertTrue(
                "an offline message must reassure that protection continues, got: $message",
                message.contains("still running"),
            )
        }

    @Test
    fun `extending asks for the requested window`() =
        runTest(dispatcher) {
            val repo = RecordingRepository.waiting()
            val vm = HomeViewModel(repo)
            runCurrent()

            vm.extend(1800)
            runCurrent()

            assertEquals(1800, repo.extendCalls.single().second)
        }
}
