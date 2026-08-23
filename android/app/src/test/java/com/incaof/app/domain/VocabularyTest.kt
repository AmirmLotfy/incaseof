package com.incaof.app.domain

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Locale

/**
 * The vocabulary rules, enforced rather than trusted.
 *
 * PRD §3 says the state machine is never exposed and lists the words that must not appear.
 * COPY.md §3 says the product never speculates about danger. Both are easy to violate by
 * reaching for `state.name` in a hurry, so this checks every string the mapping can emit.
 */
class VocabularyTest {
    /** Words that would tell a user how the machine works. PRD §3. */
    private val engineeringJargon =
        listOf(
            "workflow",
            "state machine",
            "orchestration",
            "llm",
            "agent loop",
            "prompt",
            "tool call",
            "escalation_",
            "alert_",
            "self_contact",
        )

    /**
     * The product notices unresolved expectations. It does not assess danger, and language
     * that implies it would be a claim the system cannot support.
     */
    private val speculation =
        listOf(
            "danger",
            "emergency",
            "risk",
            "unsafe",
            "critical",
            "urgent",
            "panic",
        )

    private val allStrings: List<String>
        get() =
            buildList {
                val states = AlertState.entries + null
                states.forEach { add(Vocabulary.status(it)) }
                states.forEach { add(Vocabulary.explanation(it)) }
                StepAction.entries.forEach { add(Vocabulary.action(it)) }
                ResponderRole.entries.forEach { add(Vocabulary.role(it)) }
                ReleaseLevel.entries.forEach { add(Vocabulary.release(it)) }
                PlanType.entries.forEach { add(Vocabulary.planType(it)) }
                listOf(
                    "MOMENT_DUE",
                    "ACTION_ACCEPTED",
                    "SUBJECT_CONFIRMED",
                    "ALERT_CLAIMED",
                    "STATE_CIRCLE_ESCALATION",
                    "CONTACT_DENIED",
                ).forEach { add(Vocabulary.timelineEvent(it)) }
            }

    @Test
    fun `no user-facing string leaks engineering jargon`() {
        allStrings.forEach { text ->
            val lower = text.lowercase(Locale.ROOT)
            engineeringJargon.forEach { term ->
                assertFalse("\"$text\" contains \"$term\"", lower.contains(term))
            }
        }
    }

    @Test
    fun `no user-facing string speculates about danger`() {
        allStrings.forEach { text ->
            val lower = text.lowercase(Locale.ROOT)
            speculation.forEach { term ->
                assertFalse("\"$text\" speculates with \"$term\"", lower.contains(term))
            }
        }
    }

    @Test
    fun `every alert state maps to something a person can read`() {
        AlertState.entries.forEach { state ->
            val status = Vocabulary.status(state)
            assertNotEquals("$state is shown raw", state.name, status)
            assertTrue("$state has no status text", status.isNotBlank())
            assertTrue("$state has no explanation", Vocabulary.explanation(state).isNotBlank())
        }
    }

    @Test
    fun `a missed check reads as unresolved rather than as an alarm`() {
        // Missing means unresolved, not emergency. This is the distinction the whole
        // product rests on, so the wording is asserted rather than left to review.
        val text = Vocabulary.explanation(AlertState.SELF_CONTACT).lowercase(Locale.ROOT)
        assertTrue("expected calm phrasing, got: $text", text.contains("trying to reach"))
    }

    @Test
    fun `an unknown timeline event degrades to something readable`() {
        // Backends add event types. An unrecognised one must not surface as a raw constant.
        val rendered = Vocabulary.timelineEvent("SOME_NEW_BACKEND_EVENT")
        assertFalse(rendered.contains("_"))
        assertEqualsIgnoringCase("Some new backend event", rendered)
    }

    @Test
    fun `terminal states are classified correctly`() {
        assertTrue(AlertState.RESOLVED.isTerminal)
        assertTrue(AlertState.CANCELLED.isTerminal)
        assertTrue(AlertState.ESCALATION_EXHAUSTED.isTerminal)
        assertFalse(AlertState.CHECKING.isTerminal)
        assertFalse(AlertState.CIRCLE_ESCALATION.isTerminal)
    }

    @Test
    fun `only the subject-facing states ask the subject for something`() {
        // CHECKING must NOT prompt the subject: somebody else is already looking into it,
        // and asking at that point would double-contact a person who may be asleep.
        assertTrue(AlertState.DUE.needsSubjectAction)
        assertTrue(AlertState.GRACE.needsSubjectAction)
        assertTrue(AlertState.SELF_CONTACT.needsSubjectAction)
        assertFalse(AlertState.CHECKING.needsSubjectAction)
        assertFalse(AlertState.CIRCLE_ESCALATION.needsSubjectAction)
        assertFalse(AlertState.RESOLVED.needsSubjectAction)
    }

    private fun assertEqualsIgnoringCase(expected: String, actual: String) {
        assertTrue(
            "expected \"$expected\" (ignoring case), got \"$actual\"",
            expected.equals(actual, ignoreCase = true),
        )
    }
}
