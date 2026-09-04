package com.incaof.app

import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertWidthIsAtLeast
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString
import androidx.compose.ui.unit.dp
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import com.incaof.app.feature.home.HomeScreen
import com.incaof.app.feature.home.HomeUiState
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import java.time.Instant

/**
 * Accessibility, asserted rather than hoped for.
 *
 * `.claude/rules/android.md` calls this blocking, not aspirational, and the reason is in
 * the product: someone reads this half-awake, one-handed, at 2am, possibly with TalkBack,
 * and always while worried. A control that needs aim or a state that only exists as a
 * colour is not a polish item here.
 *
 * These run on a device, because the properties that matter — measured touch targets, what
 * a screen reader would actually announce — only exist once something is laid out.
 */
class AccessibilityTest {
    @get:Rule
    val compose = createComposeRule()

    private val waitingOnYou =
        HomeUiState.Content(
            moment =
                Moment(
                    id = "moment-1",
                    planLabel = "Evening walk",
                    dueAt = Instant.parse("2026-08-23T21:30:00Z"),
                    graceUntil = Instant.parse("2026-08-23T21:40:00Z"),
                    alertState = AlertState.SELF_CONTACT,
                ),
            activePlan =
                Plan(
                    id = "plan-1",
                    label = "Evening walk",
                    type = PlanType.SOLO,
                    cadence = "Tonight",
                    timeOfDay = "9:30 PM",
                    active = true,
                ),
        )

    private fun showWaitingOnYou() {
        compose.setContent {
            InCaseOfTheme {
                HomeScreen(
                    state = waitingOnYou,
                    onConfirm = {},
                    onExtend = {},
                    onNeedSomeone = {},
                    onRetry = {},
                )
            }
        }
    }

    @Test
    fun everyControlClearsTheFortyEightDpFloor() {
        // The Material minimum, and the reason is mis-taps: this screen is used in the dark
        // by somebody who has just been woken by a notification.
        showWaitingOnYou()

        val clickable = compose.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsActions.OnClick))
        val count = clickable.fetchSemanticsNodes().size
        assertTrue("no controls were found — the screen did not render", count > 0)

        repeat(count) { index ->
            clickable[index].assertHeightIsAtLeast(48.dp)
            clickable[index].assertWidthIsAtLeast(48.dp)
        }
    }

    @Test
    fun everyControlSaysSomethingToAScreenReader() {
        // An unlabelled button is announced as "button" and nothing else. On this screen
        // that would be the difference between confirming you are safe and extending a
        // deadline.
        showWaitingOnYou()

        val clickable = compose.onAllNodes(SemanticsMatcher.keyIsDefined(SemanticsActions.OnClick))
        val unlabelled =
            clickable.fetchSemanticsNodes().filter { node ->
                val described =
                    node.config
                        .getOrNull(SemanticsProperties.ContentDescription)
                        ?.any { it.isNotBlank() } == true
                val texted =
                    node.config
                        .getOrNull(SemanticsProperties.Text)
                        ?.any { it.text.isNotBlank() } == true
                !described && !texted
            }

        assertTrue(
            "controls with nothing for TalkBack to announce: ${unlabelled.size}\n" +
                compose.onRoot().printToString(),
            unlabelled.isEmpty(),
        )
    }

    @Test
    fun theWaitingStateIsStatedInWordsNotOnlyInColour() {
        // DESIGN.md: a missed Moment is Signal Orange, and orange must never be the only
        // thing carrying that meaning. Someone who cannot distinguish it — or who is
        // looking at a greyscale screenshot in a bug report — must still be told.
        showWaitingOnYou()

        val text =
            compose.onRoot().fetchSemanticsNode().let { root ->
                buildString {
                    fun walk(node: androidx.compose.ui.semantics.SemanticsNode) {
                        node.config
                            .getOrNull(SemanticsProperties.Text)
                            ?.forEach { append(it.text).append(' ') }
                        node.config
                            .getOrNull(SemanticsProperties.ContentDescription)
                            ?.forEach { append(it).append(' ') }
                        node.children.forEach(::walk)
                    }
                    walk(root)
                }
            }

        assertTrue(
            "nothing on screen says the check is waiting; found: $text",
            text.contains("okay", ignoreCase = true) ||
                text.contains("waiting", ignoreCase = true) ||
                text.contains("expected", ignoreCase = true),
        )
    }
}
