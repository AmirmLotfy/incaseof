package com.incaof.app.feature.drill

import com.incaof.app.data.RecordingRepository
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DrillViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    private val testPlan =
        Plan(
            id = "plan-evening",
            label = "Evening check",
            type = PlanType.ROUTINE,
            cadence = "Every day",
            timeOfDay = "21:00",
            active = true,
        )

    @Before fun setUp() = Dispatchers.setMain(dispatcher)

    @After fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `starting a drill calls testPlan on repository and activates initial steps`() =
        runTest(dispatcher) {
            val repo = RecordingRepository.waiting()
            val vm = DrillViewModel(repo, testPlan)
            runCurrent()

            assertEquals("expected testPlan to be called", listOf("plan-evening"), repo.testPlanCalls)

            val state = vm.state.value as DrillUiState.Active
            assertEquals(testPlan.id, state.plan.id)
            assertEquals("SELF_CONTACT", state.telemetry.alertState)
            assertEquals("0.02x", state.telemetry.timeScale)
            assertEquals(1, state.steps.size)
        }

    @Test
    fun `drill never invents terminal progress while backend alert remains open`() =
        runTest(dispatcher) {
            val repo = RecordingRepository.waiting()
            val vm = DrillViewModel(repo, testPlan)
            runCurrent()

            runCurrent()

            val state = vm.state.value as DrillUiState.Active
            assertTrue("backend alert is still open", !state.isComplete)
            assertEquals("SELF_CONTACT", state.telemetry.alertState)
            assertEquals("Check requested", state.steps.single().title)
        }
}
