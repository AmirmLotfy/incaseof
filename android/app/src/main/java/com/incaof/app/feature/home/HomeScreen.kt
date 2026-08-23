package com.incaof.app.feature.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.design.IcoOnColor
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.core.time.TimeFormat
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import com.incaof.app.domain.Vocabulary
import com.incaof.app.ui.components.LadderRung
import com.incaof.app.ui.components.MomentTime
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.SecondaryAction
import com.incaof.app.ui.components.SectionHeading
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
import java.time.Duration
import java.time.Instant

/**
 * Home. Build contract §60 (all clear) and §61 (action needed).
 *
 * The resting state answers one question at a glance: *is anything expected of me?* No
 * greeting, no feed, no dashboard. When the answer becomes yes, the screen gets simpler
 * rather than louder — urgency reduces interface complexity.
 */
@Composable
fun HomeScreen(
    state: HomeUiState,
    onConfirm: () -> Unit,
    onExtend: (Int) -> Unit,
    onNeedSomeone: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
    now: Instant = Instant.now(),
) {
    when (state) {
        HomeUiState.Loading -> {
            Column(
                modifier = modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator() }
        }

        is HomeUiState.Failed -> {
            Column(modifier = modifier.fillMaxSize().padding(24.dp)) {
                Notice(state.message)
                SecondaryAction(stringResource(R.string.retry), onRetry)
            }
        }

        is HomeUiState.Content -> {
            HomeContent(state, onConfirm, onExtend, onNeedSomeone, modifier, now)
        }
    }
}

@Composable
private fun HomeContent(
    state: HomeUiState.Content,
    onConfirm: () -> Unit,
    onExtend: (Int) -> Unit,
    onNeedSomeone: () -> Unit,
    modifier: Modifier = Modifier,
    now: Instant = Instant.now(),
) {
    val ico = LocalIcoColors.current
    val needsAction = state.needsAction

    Column(
        modifier =
            modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 16.dp),
    ) {
        // Status first. The word carries the meaning; the marker only reinforces it, so
        // nothing here depends on colour being perceived.
        StatusMarker(
            label =
                if (needsAction) {
                    stringResource(R.string.status_action_needed)
                } else {
                    stringResource(R.string.status_all_clear)
                },
            color = if (needsAction) ico.signal else ico.primary,
            description =
                stringResource(
                    if (needsAction) R.string.cd_status_action_needed else R.string.cd_status_all_clear,
                ),
            modifier =
                Modifier.semantics {
                    heading()
                    liveRegion = LiveRegionMode.Polite
                },
        )

        Spacer(Modifier.height(24.dp))

        if (state.moment == null) {
            Notice(Vocabulary.explanation(null))
        } else if (needsAction) {
            WaitingOnYou(state.moment, state, onConfirm, onExtend, onNeedSomeone, now)
        } else {
            NextMoment(state.moment, state.activePlan)
        }

        state.error?.let {
            Spacer(Modifier.height(16.dp))
            Text(
                text = it,
                style = MaterialTheme.typography.bodyLarge,
                color = ico.critical,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Assertive },
            )
        }
    }
}

/** §61. One primary action, two quieter ones, and a plain statement of what happens next. */
@Composable
private fun WaitingOnYou(
    moment: Moment,
    state: HomeUiState.Content,
    onConfirm: () -> Unit,
    onExtend: (Int) -> Unit,
    onNeedSomeone: () -> Unit,
    now: Instant,
) {
    val ico = LocalIcoColors.current

    Text(moment.planLabel, style = MaterialTheme.typography.headlineMedium, color = ico.ink)
    Spacer(Modifier.height(8.dp))
    Text(
        Vocabulary.explanation(moment.alertState),
        style = MaterialTheme.typography.bodyLarge,
        color = ico.graphite,
    )

    Spacer(Modifier.height(24.dp))
    Text(stringResource(R.string.expected), style = MaterialTheme.typography.labelSmall, color = ico.graphite)
    MomentTime(TimeFormat.time(moment.dueAt), color = ico.ink)

    Spacer(Modifier.height(32.dp))
    PrimaryAction(
        label = stringResource(R.string.action_im_okay),
        onClick = onConfirm,
        enabled = !state.submitting,
        description = stringResource(R.string.cd_confirm_okay),
        // Signal Orange takes INK text, never white: white measures 3.52:1 and fails AA.
        container = ico.signal,
        content = IcoOnColor.signal,
    )

    Spacer(Modifier.height(8.dp))
    SecondaryAction(stringResource(R.string.need_someone), onNeedSomeone)
    SecondaryAction(
        label = stringResource(R.string.give_me_more_time),
        onClick = { onExtend(THIRTY_MINUTES) },
    )

    Spacer(Modifier.height(24.dp))
    SectionHeading(stringResource(R.string.next_action))
    Spacer(Modifier.height(12.dp))
    Text(
        text = nextActionSentence(moment, now),
        style = MaterialTheme.typography.bodyLarge,
        color = ico.graphite,
    )
}

/** §60. Next Moment, then the ladder as a compact preview. */
@Composable
private fun NextMoment(moment: Moment, plan: Plan?) {
    val ico = LocalIcoColors.current

    Text(stringResource(R.string.next_label), style = MaterialTheme.typography.labelSmall, color = ico.graphite)
    Spacer(Modifier.height(4.dp))
    Text(moment.planLabel, style = MaterialTheme.typography.headlineMedium, color = ico.ink)
    Spacer(Modifier.height(4.dp))
    TabularLabel(TimeFormat.dayAndTime(moment.dueAt), color = ico.graphite)

    if (plan != null && plan.steps.isNotEmpty()) {
        Spacer(Modifier.height(32.dp))
        SectionHeading(stringResource(R.string.if_unresolved))
        Spacer(Modifier.height(8.dp))
        Column(
            Modifier
                .fillMaxWidth()
                .semantics { heading() },
        ) {
            plan.steps.forEach { step ->
                LadderRung(
                    time = TimeFormat.offset(step.offsetSeconds),
                    action = rungLabel(step.action, step.targetRole, plan),
                )
            }
        }
    }
}

private fun rungLabel(
    action: com.incaof.app.domain.StepAction,
    role: com.incaof.app.domain.ResponderRole?,
    plan: Plan,
): String {
    if (action.isSubjectDirected) return Vocabulary.action(action)
    val member = plan.circle.firstOrNull { it.role == role }
    // Name the person when we know them; fall back to the role, never to a number.
    return "${Vocabulary.action(action)} ${member?.displayName ?: role?.let(Vocabulary::role).orEmpty()}"
        .trim()
}

private fun nextActionSentence(moment: Moment, now: Instant): String {
    val gap = Duration.between(now, moment.graceUntil)
    return if (gap.isNegative || gap.isZero) {
        "We'll try again shortly."
    } else {
        "We'll check again ${TimeFormat.relative(now, moment.graceUntil)}."
    }
}

private const val THIRTY_MINUTES = 1800

@Preview(showBackground = true, name = "Home — all clear")
@Composable
private fun HomeAllClearPreview() {
    InCaseOfTheme {
        HomeScreen(
            state =
                HomeUiState.Content(
                    moment =
                        Moment(
                            id = "m",
                            planLabel = "Evening check",
                            dueAt = Instant.now().plusSeconds(10800),
                            graceUntil = Instant.now().plusSeconds(10800),
                            alertState = null,
                        ),
                    activePlan = null,
                ),
            onConfirm = {},
            onExtend = {},
            onNeedSomeone = {},
            onRetry = {},
        )
    }
}

@Preview(showBackground = true, name = "Home — action needed")
@Composable
private fun HomeActionNeededPreview() {
    InCaseOfTheme {
        HomeScreen(
            state =
                HomeUiState.Content(
                    moment =
                        Moment(
                            id = "m",
                            planLabel = "Evening check",
                            dueAt = Instant.now(),
                            graceUntil = Instant.now().plusSeconds(600),
                            alertState = AlertState.SELF_CONTACT,
                        ),
                    activePlan = null,
                ),
            onConfirm = {},
            onExtend = {},
            onNeedSomeone = {},
            onRetry = {},
        )
    }
}
