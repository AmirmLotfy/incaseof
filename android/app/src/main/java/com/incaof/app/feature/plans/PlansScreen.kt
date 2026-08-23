package com.incaof.app.feature.plans

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.core.time.TimeFormat
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import com.incaof.app.domain.Vocabulary
import com.incaof.app.ui.components.LadderRung
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.SectionHeading
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel

@Composable
fun PlansScreen(state: PlansUiState, onSelect: (String) -> Unit, modifier: Modifier = Modifier) {
    when (state) {
        PlansUiState.Loading -> {
            Column(
                modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator() }
        }

        is PlansUiState.Failed -> {
            Notice(state.message, modifier.padding(24.dp))
        }

        is PlansUiState.Content -> {
            LazyColumn(
                modifier = modifier.fillMaxSize(),
                contentPadding =
                    androidx.compose.foundation.layout
                        .PaddingValues(24.dp),
            ) {
                items(state.plans, key = { it.id }) { plan ->
                    PlanRow(plan, onClick = { onSelect(plan.id) })
                    HorizontalDivider(color = LocalIcoColors.current.stone)
                }
            }
        }
    }
}

@Composable
private fun PlanRow(plan: Plan, onClick: () -> Unit) {
    val ico = LocalIcoColors.current
    val statusLabel =
        if (plan.active) {
            stringResource(R.string.plan_active)
        } else {
            stringResource(R.string.plan_paused)
        }

    Column(
        Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clickable(onClick = onClick)
            .padding(vertical = 16.dp)
            .semantics {
                contentDescription =
                    "${plan.label}, ${plan.cadence} at ${plan.timeOfDay}, $statusLabel"
            },
    ) {
        Text(plan.label, style = MaterialTheme.typography.titleMedium, color = ico.ink)
        Spacer(Modifier.height(4.dp))
        TabularLabel("${plan.cadence} · ${plan.timeOfDay}")
        Spacer(Modifier.height(8.dp))
        StatusMarker(
            label = statusLabel,
            // Paused is Stone-adjacent but never carries the meaning on its own; the word
            // does. A missed plan is not an error, so this is never Brick.
            color = if (plan.active) ico.primary else ico.graphite,
        )
    }
}

/**
 * Plan detail. Build contract §65.
 *
 * The ladder is shown literally — offsets and actions — because "who gets contacted and
 * when" is the thing somebody most needs to verify. No health score: Plan Health is
 * objective facts only (§26), never an invented number.
 */
@Composable
fun PlanDetailScreen(plan: Plan, onTest: () -> Unit, modifier: Modifier = Modifier) {
    val ico = LocalIcoColors.current

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding =
            androidx.compose.foundation.layout
                .PaddingValues(24.dp),
    ) {
        item {
            Text(
                plan.label,
                style = MaterialTheme.typography.headlineMedium,
                color = ico.ink,
                modifier = Modifier.semantics { heading() },
            )
            Spacer(Modifier.height(4.dp))
            TabularLabel("${Vocabulary.planType(plan.type)} · ${plan.cadence} · ${plan.timeOfDay}")
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.what_happens))
            Spacer(Modifier.height(8.dp))
        }

        items(plan.steps, key = { it.sequence }) { step ->
            LadderRung(
                time = TimeFormat.offset(step.offsetSeconds),
                action =
                    buildString {
                        append(Vocabulary.action(step.action))
                        step.targetRole?.let { role ->
                            val member = plan.circle.firstOrNull { it.role == role }
                            append(" ")
                            append(member?.displayName ?: Vocabulary.role(role))
                        }
                    },
            )
        }

        item {
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.shared_if_needed))
            Spacer(Modifier.height(8.dp))
        }

        items(plan.contextPolicy) { release ->
            LadderRung(time = "", action = "${release.signal} — ${Vocabulary.release(release.level)}")
        }

        item {
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.your_circle))
            Spacer(Modifier.height(8.dp))
        }

        items(plan.circle, key = { it.id }) { member ->
            LadderRung(
                time = "",
                action = "${member.displayName} — ${Vocabulary.role(member.role)}",
            )
        }

        item {
            Spacer(Modifier.height(32.dp))
            PrimaryAction(stringResource(R.string.test_plan), onTest)
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun PlanDetailPreview() {
    InCaseOfTheme {
        PlanDetailScreen(
            plan =
                Plan(
                    id = "p",
                    label = "Evening check",
                    type = PlanType.ROUTINE,
                    cadence = "Daily",
                    timeOfDay = "21:00",
                    active = true,
                ),
            onTest = {},
        )
    }
}
