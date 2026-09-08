package com.incaof.app.feature.drill

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.SectionHeading
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
import com.incaof.app.ui.localizedTimelineEvent
import com.incaof.app.ui.localizedUiMessage

@Composable
fun DrillScreen(
    state: DrillUiState,
    onFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (state) {
        is DrillUiState.Failed -> {
            Column(
                modifier = modifier.fillMaxSize().padding(24.dp),
                verticalArrangement = Arrangement.Center,
            ) {
                Notice(localizedUiMessage(state.message))
                Spacer(Modifier.height(16.dp))
                PrimaryAction(stringResource(R.string.drill_action_done), onFinish)
            }
        }

        is DrillUiState.Active -> {
            DrillContent(state, onFinish, modifier)
        }
    }
}

@Composable
private fun DrillContent(
    state: DrillUiState.Active,
    onFinish: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val ico = LocalIcoColors.current
    val timingDescription = stringResource(R.string.drill_timing_banner)

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding =
            androidx.compose.foundation.layout
                .PaddingValues(24.dp),
    ) {
        item {
            // §125: Timing is compressed by the deployed demo environment, never locally.
            Box(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .background(ico.stone)
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .semantics {
                            contentDescription = timingDescription
                        },
            ) {
                Text(
                    text = stringResource(R.string.drill_timing_banner),
                    style = MaterialTheme.typography.labelMedium,
                    color = ico.ink,
                )
            }

            Spacer(Modifier.height(24.dp))

            Text(
                text = "${stringResource(R.string.drill_title)}: ${state.plan.label}",
                style = MaterialTheme.typography.headlineMedium,
                color = ico.ink,
                modifier = Modifier.semantics { heading() },
            )

            Spacer(Modifier.height(8.dp))

            StatusMarker(
                label =
                    if (state.isComplete) {
                        stringResource(R.string.drill_ready)
                    } else {
                        drillStatusLabel(state.status)
                    },
                color = if (state.isComplete) ico.resolved else ico.signal,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )

            Spacer(Modifier.height(28.dp))

            SectionHeading(stringResource(R.string.drill_backend_timeline))
            Spacer(Modifier.height(8.dp))
        }

        if (state.steps.isEmpty()) {
            item {
                Text(
                    stringResource(R.string.drill_no_events),
                    color = ico.graphite,
                    modifier = Modifier.padding(vertical = 14.dp),
                )
            }
        } else {
            items(state.steps, key = { it.id }) { step ->
                DrillStepRow(step)
                HorizontalDivider(color = ico.stone)
            }
        }

        item {
            Spacer(Modifier.height(32.dp))
            SectionHeading(stringResource(R.string.drill_trace_title))
            Spacer(Modifier.height(12.dp))

            TelemetryCard(state.telemetry)

            if (state.isComplete) {
                Spacer(Modifier.height(32.dp))
                PrimaryAction(
                    label = stringResource(R.string.drill_action_done),
                    onClick = onFinish,
                )
            }
        }
    }
}

@Composable
private fun DrillStepRow(step: DrillStep) {
    val ico = LocalIcoColors.current
    val title = localizedTimelineEvent(step.event)
    val statusDesc =
        when {
            step.completed -> stringResource(R.string.drill_status_completed)
            step.inProgress -> stringResource(R.string.drill_status_progress)
            else -> stringResource(R.string.drill_status_pending)
        }
    val stepDescription = stringResource(R.string.drill_step_description, title, statusDesc)

    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(vertical = 14.dp)
                .semantics {
                    contentDescription = stepDescription
                },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        val markText =
            when {
                step.completed -> "✓"
                step.inProgress -> "●"
                else -> "○"
            }
        val markColor =
            when {
                step.completed -> ico.resolved
                step.inProgress -> ico.signal
                else -> ico.graphite
            }

        Text(
            text = markText,
            style = MaterialTheme.typography.titleMedium,
            color = markColor,
            modifier = Modifier.width(24.dp),
        )

        Spacer(Modifier.width(8.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                color = if (step.completed || step.inProgress) ico.ink else ico.graphite,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = "${step.actor} · ${step.at}",
                style = MaterialTheme.typography.bodySmall,
                color = ico.graphite,
            )
        }

        if (step.inProgress) {
            CircularProgressIndicator(
                modifier = Modifier.size(16.dp),
                color = ico.signal,
                strokeWidth = 2.dp,
            )
        }
    }
}

/**
 * Technical trace view (§114) exposing only facts returned by the backend.
 */
@Composable
private fun TelemetryCard(t: DrillTelemetry) {
    val ico = LocalIcoColors.current

    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .background(ico.surface)
                .padding(16.dp),
    ) {
        val none = stringResource(R.string.drill_none)
        TelemetryRow(stringResource(R.string.drill_alert_state), t.alertState)
        TelemetryRow(
            stringResource(R.string.drill_alert_id),
            t.alertId ?: stringResource(R.string.drill_not_opened),
        )
        TelemetryRow(
            stringResource(R.string.drill_server_time_scale),
            if (t.timeScale == null) {
                stringResource(R.string.drill_awaiting_server)
            } else if (t.isDrill) {
                "${t.timeScale}x"
            } else {
                stringResource(R.string.drill_normal_time)
            },
        )
        TelemetryRow(stringResource(R.string.drill_audit_events), t.eventCount.toString())
        TelemetryRow(stringResource(R.string.drill_last_actor), t.lastActor ?: none)
        TelemetryRow(stringResource(R.string.drill_lease_expires), t.leaseExpiresAt ?: none)
    }
}

@Composable
private fun drillStatusLabel(status: DrillStatus): String =
    stringResource(
        when (status) {
            DrillStatus.STARTING -> R.string.drill_status_starting
            DrillStatus.WAITING_MOMENT -> R.string.drill_status_waiting_moment
            DrillStatus.TERMINAL -> R.string.drill_status_terminal
            DrillStatus.WAITING_SCHEDULER -> R.string.drill_status_waiting_scheduler
            DrillStatus.FOLLOWING -> R.string.drill_status_following
            DrillStatus.STILL_OPEN -> R.string.drill_status_still_open
        },
    )

@Composable
private fun TelemetryRow(label: String, value: String) {
    val ico = LocalIcoColors.current
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = ico.graphite,
        )
        TabularLabel(value)
    }
}
