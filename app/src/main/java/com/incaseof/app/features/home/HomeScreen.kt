@file:Suppress("DEPRECATION")
package com.incaseof.app.features.home

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.incaseof.app.core.design.*
import com.incaseof.app.core.model.CaseEventType
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onCreateCase: () -> Unit,
    onCaseClick: (String) -> Unit,
    onViewLog: () -> Unit,
    onSettings: () -> Unit,
    onAbout: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // Check-in button animation
    val checkInScale by animateFloatAsState(
        targetValue = if (uiState.isCheckingIn) 0.95f else 1f,
        animationSpec = tween(200),
        label = "checkin_scale"
    )

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentPadding = PaddingValues(bottom = 100.dp)
    ) {
        // Header
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.verticalGradient(
                            colors = listOf(
                                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.15f),
                                MaterialTheme.colorScheme.background
                            )
                        )
                    )
                    .padding(24.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "In Case Of",
                                style = MaterialTheme.typography.headlineLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Text(
                                text = "Your safety dashboard",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        BrandShield(size = 48)
                    }
                }
            }
        }

        // "I'm safe" Check-in Button
        item {
            Box(modifier = Modifier.padding(horizontal = 20.dp)) {
                Button(
                    onClick = { viewModel.checkInAll() },
                    enabled = !uiState.isCheckingIn,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(72.dp)
                        .scale(checkInScale),
                    shape = RoundedCornerShape(20.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (uiState.checkInSuccess)
                            SafetyGreen
                        else
                            MaterialTheme.colorScheme.primary
                    ),
                    elevation = ButtonDefaults.buttonElevation(
                        defaultElevation = 6.dp,
                        pressedElevation = 2.dp
                    )
                ) {
                    AnimatedContent(
                        targetState = uiState.checkInSuccess,
                        label = "checkin_content"
                    ) { success ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(
                                imageVector = if (success) Icons.Default.CheckCircle else Icons.Default.Shield,
                                contentDescription = null,
                                modifier = Modifier.size(28.dp)
                            )
                            Text(
                                text = if (success) "Checked in!" else "I'm safe",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
            Spacer(modifier = Modifier.height(24.dp))
        }

        // Active Cases
        item {
            SectionHeader(
                title = "Active Cases",
                modifier = Modifier.padding(horizontal = 20.dp),
                action = if (uiState.activeCases.isNotEmpty()) "View all" else null,
                onAction = onViewLog
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        if (uiState.activeCases.isEmpty()) {
            item {
                SafetyCard(
                    modifier = Modifier.padding(horizontal = 20.dp)
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = Icons.Default.AddCircleOutline,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "No active cases",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Create your first safety case to get started.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        PrimaryCTA(
                            text = "Create a case",
                            onClick = onCreateCase,
                            icon = Icons.Default.Add
                        )
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))
            }
        } else {
            items(uiState.activeCases) { case ->
                CaseCard(
                    title = case.title,
                    summary = case.summary,
                    status = viewModel.getCaseStatus(case.status),
                    riskLevel = viewModel.getRiskLevel(case.riskLevel),
                    onClick = { onCaseClick(case.id) },
                    modifier = Modifier.padding(horizontal = 20.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
            }
        }

        // Suggested Cases
        item {
            Spacer(modifier = Modifier.height(8.dp))
            SectionHeader(
                title = "Suggested Cases",
                modifier = Modifier.padding(horizontal = 20.dp)
            )
            Spacer(modifier = Modifier.height(12.dp))

            LazyRow(
                contentPadding = PaddingValues(horizontal = 20.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item {
                    SuggestedCaseChip(
                        label = "Daily check-in",
                        icon = Icons.Default.Today,
                        onClick = onCreateCase
                    )
                }
                item {
                    SuggestedCaseChip(
                        label = "Travel safety",
                        icon = Icons.Default.Flight,
                        onClick = onCreateCase
                    )
                }
                item {
                    SuggestedCaseChip(
                        label = "Medication",
                        icon = Icons.Default.Medication,
                        onClick = onCreateCase
                    )
                }
                item {
                    SuggestedCaseChip(
                        label = "Solo activity",
                        icon = Icons.Filled.DirectionsRun,
                        onClick = onCreateCase
                    )
                }
                item {
                    SuggestedCaseChip(
                        label = "Night shift",
                        icon = Icons.Default.NightShelter,
                        onClick = onCreateCase
                    )
                }
            }
            Spacer(modifier = Modifier.height(24.dp))
        }

        // Recent Activity
        if (uiState.recentEvents.isNotEmpty()) {
            item {
                SectionHeader(
                    title = "Recent Activity",
                    modifier = Modifier.padding(horizontal = 20.dp),
                    action = "View all",
                    onAction = onViewLog
                )
                Spacer(modifier = Modifier.height(12.dp))
            }

            item {
                SafetyCard(
                    modifier = Modifier.padding(horizontal = 20.dp)
                ) {
                    uiState.recentEvents.take(5).forEachIndexed { index, event ->
                        val eventType = try {
                            CaseEventType.valueOf(event.type)
                        } catch (e: Exception) {
                            CaseEventType.CREATED
                        }

                        val (icon, color) = when (eventType) {
                            CaseEventType.CREATED -> Icons.Default.Add to MaterialTheme.colorScheme.primary
                            CaseEventType.CHECK_IN -> Icons.Default.CheckCircle to SafetyGreen
                            CaseEventType.MISSED_CHECK_IN -> Icons.Default.Warning to AmberWarning
                            CaseEventType.VERIFICATION_STARTED -> Icons.Default.NotificationsActive to CoralAccent
                            CaseEventType.USER_MARKED_SAFE -> Icons.Default.Shield to SafetyGreen
                            CaseEventType.ACTION_PREPARED -> Icons.Filled.Send to CoralAccent
                            CaseEventType.ACTIVATED -> Icons.Default.PlayArrow to SafetyGreen
                            else -> Icons.Default.Info to MaterialTheme.colorScheme.onSurfaceVariant
                        }

                        val dateFormat = SimpleDateFormat("MMM d, h:mm a", Locale.getDefault())
                        val timestamp = dateFormat.format(Date(event.timestamp))

                        TimelineItem(
                            icon = icon,
                            iconTint = color,
                            title = event.message,
                            subtitle = event.caseId.take(8) + "...",
                            timestamp = timestamp,
                            isLast = index == minOf(uiState.recentEvents.size - 1, 4),
                            modifier = Modifier.padding(vertical = 0.dp)
                        )
                    }
                }
            }
        }
    }
}
