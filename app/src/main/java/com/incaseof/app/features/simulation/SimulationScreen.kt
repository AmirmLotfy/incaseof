package com.incaseof.app.features.simulation

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.incaseof.app.core.design.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimulationScreen(
    onBack: () -> Unit,
    viewModel: SimulationViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    val infiniteTransition = rememberInfiniteTransition(label = "sim_pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(700, easing = EaseInOutCubic), RepeatMode.Reverse),
        label = "sim_alpha"
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Simulation", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                SafetyCard {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Icon(Icons.Default.Science, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(28.dp))
                        Column {
                            Text(uiState.caseTitle, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Demo simulation mode", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
                        }
                    }
                }
            }

            itemsIndexed(uiState.steps) { index, step ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(
                                    when {
                                        step.isComplete -> SafetyGreen.copy(alpha = 0.15f)
                                        step.isActive -> CoralAccent.copy(alpha = 0.15f)
                                        else -> MaterialTheme.colorScheme.surfaceVariant
                                    }
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (step.isComplete) {
                                Icon(Icons.Default.Check, null, tint = SafetyGreen, modifier = Modifier.size(18.dp))
                            } else if (step.isActive) {
                                Icon(Icons.Default.FiberManualRecord, null,
                                    tint = CoralAccent,
                                    modifier = Modifier.size(12.dp).alpha(pulseAlpha))
                            } else {
                                Text("${index + 1}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                            }
                        }
                        if (index < uiState.steps.size - 1) {
                            Box(
                                modifier = Modifier
                                    .width(2.dp).height(32.dp)
                                    .background(
                                        if (step.isComplete) SafetyGreen.copy(alpha = 0.3f)
                                        else MaterialTheme.colorScheme.outlineVariant
                                    )
                            )
                        }
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            step.label,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = if (step.isActive) FontWeight.Bold else FontWeight.Medium,
                            color = when {
                                step.isComplete -> SafetyGreen
                                step.isActive -> MaterialTheme.colorScheme.onSurface
                                else -> MaterialTheme.colorScheme.outline
                            }
                        )
                        Text(step.detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                if (!uiState.isRunning && !uiState.isComplete) {
                    PrimaryCTA(text = "Start simulation", onClick = { viewModel.runSimulation() }, icon = Icons.Default.PlayArrow)
                } else if (uiState.isComplete) {
                    SafetyCard {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Icon(Icons.Default.CheckCircle, null, tint = SafetyGreen, modifier = Modifier.size(24.dp))
                            Text("Simulation complete! All steps executed successfully.", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, color = SafetyGreen)
                        }
                    }
                }
            }
        }
    }
}
