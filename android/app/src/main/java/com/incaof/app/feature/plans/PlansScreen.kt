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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
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
import com.incaof.app.domain.Plan
import com.incaof.app.domain.PlanType
import com.incaof.app.ui.components.LadderRung
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.SecondaryAction
import com.incaof.app.ui.components.SectionHeading
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
import com.incaof.app.ui.localizedAction
import com.incaof.app.ui.localizedOffset
import com.incaof.app.ui.localizedPlanType
import com.incaof.app.ui.localizedRelease
import com.incaof.app.ui.localizedRole
import com.incaof.app.ui.localizedUiMessage

@Composable
fun PlansScreen(
    state: PlansUiState,
    onSelect: (String) -> Unit,
    onCreate: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (state) {
        PlansUiState.Loading -> {
            Column(
                modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator() }
        }

        is PlansUiState.Failed -> {
            Notice(localizedUiMessage(state.message), modifier.padding(24.dp))
        }

        is PlansUiState.Content -> {
            LazyColumn(
                modifier = modifier.fillMaxSize(),
                contentPadding =
                    androidx.compose.foundation.layout
                        .PaddingValues(24.dp),
            ) {
                item {
                    PrimaryAction(stringResource(R.string.plan_create), onCreate)
                    Spacer(Modifier.height(24.dp))
                    if (state.plans.isEmpty()) {
                        Text(
                            stringResource(R.string.plan_empty),
                            color = LocalIcoColors.current.graphite,
                        )
                        Spacer(Modifier.height(16.dp))
                    }
                }
                items(state.plans, key = { it.id }) { plan ->
                    PlanRow(plan, onClick = { onSelect(plan.id) })
                    HorizontalDivider(color = LocalIcoColors.current.stone)
                }
            }
        }
    }
}

@Composable
fun PlanComposerScreen(
    state: PlanComposerUiState,
    onCompile: (String) -> Unit,
    onSave: () -> Unit,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var description by remember { mutableStateOf("") }
    val preview = state.draft?.preview
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding =
            androidx.compose.foundation.layout
                .PaddingValues(24.dp),
    ) {
        item {
            Text(
                stringResource(R.string.plan_create),
                style = MaterialTheme.typography.headlineMedium,
                modifier = Modifier.semantics { heading() },
            )
            Spacer(Modifier.height(8.dp))
            Text(
                stringResource(R.string.plan_create_intro),
                color = LocalIcoColors.current.graphite,
            )
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(
                value = description,
                onValueChange = { description = it },
                enabled = !state.busy && preview == null,
                label = { Text(stringResource(R.string.plan_description_label)) },
                placeholder = { Text(stringResource(R.string.plan_description_placeholder)) },
                minLines = 4,
                modifier = Modifier.fillMaxWidth(),
            )
            state.error?.let {
                Spacer(Modifier.height(12.dp))
                Notice(localizedUiMessage(it))
            }
            Spacer(Modifier.height(16.dp))
            if (state.busy) {
                CircularProgressIndicator()
            } else if (preview == null) {
                PrimaryAction(stringResource(R.string.plan_compile_preview), onClick = { onCompile(description) })
            }
        }

        if (preview != null) {
            item {
                Spacer(Modifier.height(28.dp))
                SectionHeading(stringResource(R.string.plan_review))
                Spacer(Modifier.height(12.dp))
                Text(preview.label, style = MaterialTheme.typography.titleLarge)
                Spacer(Modifier.height(4.dp))
                TabularLabel("${localizedPlanType(preview.type)} · ${preview.cadence}")
                if (state.draft.warnings.isNotEmpty()) {
                    Spacer(Modifier.height(16.dp))
                    Notice(state.draft.warnings.joinToString("\n"))
                }
                Spacer(Modifier.height(24.dp))
                SectionHeading(stringResource(R.string.what_happens))
                Spacer(Modifier.height(8.dp))
            }
            items(preview.steps, key = { it.sequence }) { step ->
                val actionLabel = localizedAction(step.action)
                val roleLabel = step.targetRole?.let { localizedRole(it) }
                LadderRung(
                    time = localizedOffset(step.offsetSeconds),
                    action =
                        buildString {
                            append(actionLabel)
                            roleLabel?.let { append(" · $it") }
                        },
                )
            }
            item {
                Spacer(Modifier.height(28.dp))
                Text(
                    stringResource(R.string.plan_save_explanation),
                    color = LocalIcoColors.current.graphite,
                )
                Spacer(Modifier.height(16.dp))
                PrimaryAction(stringResource(R.string.plan_save_draft), onSave)
            }
        }

        item {
            Spacer(Modifier.height(8.dp))
            TextButton(onClick = onCancel, enabled = !state.busy) {
                Text(stringResource(R.string.plan_cancel))
            }
        }
    }
}

@Composable
private fun PlanRow(plan: Plan, onClick: () -> Unit) {
    val ico = LocalIcoColors.current
    val statusLabel =
        if (plan.active && !plan.paused) {
            stringResource(R.string.plan_active)
        } else if (plan.paused) {
            stringResource(R.string.plan_paused)
        } else {
            stringResource(R.string.plan_draft)
        }
    val rowDescription =
        stringResource(
            R.string.plan_row_description,
            plan.label,
            plan.cadence,
            plan.timeOfDay,
            statusLabel,
        )

    Column(
        Modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .clickable(onClick = onClick)
            .padding(vertical = 16.dp)
            .semantics {
                contentDescription = rowDescription
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
fun PlanDetailScreen(
    plan: Plan,
    action: PlanActionUiState,
    onActivate: () -> Unit,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onTest: () -> Unit,
    modifier: Modifier = Modifier,
) {
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
            TabularLabel("${localizedPlanType(plan.type)} · ${plan.cadence} · ${plan.timeOfDay}")
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.what_happens))
            Spacer(Modifier.height(8.dp))
        }

        items(plan.steps, key = { it.sequence }) { step ->
            val actionLabel = localizedAction(step.action)
            val roleLabel =
                step.targetRole?.let { role ->
                    plan.circle.firstOrNull { it.role == role }?.displayName ?: localizedRole(role)
                }
            LadderRung(
                time = localizedOffset(step.offsetSeconds),
                action =
                    buildString {
                        append(actionLabel)
                        roleLabel?.let {
                            append(" ")
                            append(it)
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
            LadderRung(time = "", action = "${release.signal} — ${localizedRelease(release.level)}")
        }

        item {
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.your_circle))
            Spacer(Modifier.height(8.dp))
        }

        items(plan.circle, key = { it.id }) { member ->
            LadderRung(
                time = "",
                action = "${member.displayName} — ${localizedRole(member.role)}",
            )
        }

        item {
            Spacer(Modifier.height(32.dp))
            action.error?.let {
                Notice(localizedUiMessage(it))
                Spacer(Modifier.height(12.dp))
            }
            action.notice?.let {
                Notice(localizedUiMessage(it))
                Spacer(Modifier.height(12.dp))
            }
            when {
                !plan.active -> {
                    PrimaryAction(stringResource(R.string.plan_activate), onActivate, enabled = !action.busy)
                }

                plan.paused -> {
                    PrimaryAction(stringResource(R.string.plan_resume), onResume, enabled = !action.busy)
                }

                else -> {
                    SecondaryAction(stringResource(R.string.plan_pause), onPause)
                }
            }
            Spacer(Modifier.height(12.dp))
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
            action = PlanActionUiState(),
            onActivate = {},
            onPause = {},
            onResume = {},
            onTest = {},
        )
    }
}
