@file:Suppress("DEPRECATION")
package com.incaseof.app.features.casedetail

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.incaseof.app.core.design.*
import com.incaseof.app.core.model.CaseEventType
import com.incaseof.app.core.model.CaseStatus
import com.incaseof.app.domain.models.ActionSpec
import com.incaseof.app.domain.models.TriggerSpec
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseDetailScreen(
    onSimulate: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: CaseDetailViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    var showDeleteDialog by remember { mutableStateOf(false) }
    var selectedTab by remember { mutableIntStateOf(0) }

    val workflow = uiState.workflow
    val caseEntity = uiState.caseEntity

    if (workflow == null || caseEntity == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(workflow.title, fontWeight = FontWeight.SemiBold, maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { showDeleteDialog = true }) {
                        Icon(Icons.Default.Delete, "Delete", tint = MaterialTheme.colorScheme.error)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Status & Actions
            item {
                SafetyCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            StatusPill(status = uiState.status)
                            Spacer(modifier = Modifier.height(4.dp))
                            RiskBadge(level = uiState.riskLevel)
                        }
                        // Check-in button
                        if (uiState.status == CaseStatus.ACTIVE) {
                            Button(
                                onClick = { viewModel.checkIn() },
                                enabled = !uiState.isCheckingIn,
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = SafetyGreen)
                            ) {
                                Icon(Icons.Default.CheckCircle, null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Check in", fontWeight = FontWeight.SemiBold)
                            }
                        }
                    }
                }
            }

            // Tabs
            item {
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor = MaterialTheme.colorScheme.surface
                ) {
                    Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }) {
                        Text("Plan", modifier = Modifier.padding(12.dp), fontWeight = FontWeight.Medium)
                    }
                    Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }) {
                        Text("Timeline", modifier = Modifier.padding(12.dp), fontWeight = FontWeight.Medium)
                    }
                    Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 }) {
                        Text("Actions", modifier = Modifier.padding(12.dp), fontWeight = FontWeight.Medium)
                    }
                }
            }

            when (selectedTab) {
                0 -> {
                    // Plan tab
                    item {
                        SafetyCard {
                            Text("Summary", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(workflow.summary, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    item {
                        SafetyCard {
                            Text("Trigger", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.height(4.dp))
                            when (val t = workflow.trigger) {
                                is TriggerSpec.MissedCheckIn -> Text("No check-in for ${t.durationHours}h", style = MaterialTheme.typography.bodyMedium)
                                is TriggerSpec.ScheduledTime -> Text("At ${t.localTime}", style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                    item {
                        SafetyCard {
                            Text("Actions", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Spacer(modifier = Modifier.height(4.dp))
                            workflow.actions.forEach { action ->
                                val desc = when (action) {
                                    is ActionSpec.SendSms -> "SMS to ${action.contactRole}: ${action.message.take(80)}..."
                                    is ActionSpec.SendEmail -> "Email: ${action.subject}"
                                    is ActionSpec.CallContact -> "Call ${action.contactRole}"
                                    is ActionSpec.OpenWhatsAppPreparedMessage -> "WhatsApp message"
                                }
                                Text("• $desc", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Spacer(modifier = Modifier.height(4.dp))
                            }
                        }
                    }
                }
                1 -> {
                    // Timeline tab
                    if (uiState.events.isEmpty()) {
                        item {
                            SafetyCard {
                                Text("No events yet.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.outline)
                            }
                        }
                    } else {
                        items(uiState.events) { event ->
                            val eventType = try { CaseEventType.valueOf(event.type) } catch (e: Exception) { CaseEventType.CREATED }
                            val (icon, color) = when (eventType) {
                                CaseEventType.CREATED -> Icons.Default.Add to MaterialTheme.colorScheme.primary
                                CaseEventType.ACTIVATED -> Icons.Default.PlayArrow to SafetyGreen
                                CaseEventType.CHECK_IN -> Icons.Default.CheckCircle to SafetyGreen
                                CaseEventType.MISSED_CHECK_IN -> Icons.Default.Warning to AmberWarning
                                CaseEventType.VERIFICATION_STARTED -> Icons.Default.NotificationsActive to CoralAccent
                                CaseEventType.VERIFICATION_EXPIRED -> Icons.Default.Timer to DangerRed
                                CaseEventType.USER_MARKED_SAFE -> Icons.Default.Shield to SafetyGreen
                                CaseEventType.ACTION_PREPARED -> Icons.Filled.Send to CoralAccent
                                CaseEventType.PAUSED -> Icons.Default.Pause to AmberWarning
                                CaseEventType.RESUMED -> Icons.Default.PlayArrow to SafetyGreen
                                CaseEventType.SIMULATION_RUN -> Icons.Default.Science to MaterialTheme.colorScheme.primary
                                else -> Icons.Default.Info to MaterialTheme.colorScheme.onSurfaceVariant
                            }
                            val fmt = SimpleDateFormat("MMM d, h:mm a", Locale.getDefault())
                            TimelineItem(
                                icon = icon, iconTint = color,
                                title = event.message,
                                subtitle = eventType.name.replace("_", " ").lowercase().replaceFirstChar { it.uppercase() },
                                timestamp = fmt.format(Date(event.timestamp)),
                                isLast = event == uiState.events.last()
                            )
                        }
                    }
                }
                2 -> {
                    // Actions tab
                    item {
                        if (uiState.status == CaseStatus.ACTIVE) {
                            OutlinedButton(
                                onClick = { viewModel.pauseCase() },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(16.dp)
                            ) {
                                Icon(Icons.Default.Pause, null); Spacer(Modifier.width(8.dp))
                                Text("Pause case")
                            }
                        } else if (uiState.status == CaseStatus.PAUSED) {
                            PrimaryCTA(text = "Resume case", onClick = { viewModel.resumeCase() }, icon = Icons.Default.PlayArrow)
                        }
                    }
                    item {
                        OutlinedButton(
                            onClick = { onSimulate(viewModel.caseId) },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Icon(Icons.Default.Science, null); Spacer(Modifier.width(8.dp))
                            Text("Run simulation")
                        }
                    }
                }
            }
        }
    }

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete case?") },
            text = { Text("This will permanently delete this case and all its events.") },
            confirmButton = {
                TextButton(onClick = { viewModel.deleteCase(); onBack() }) {
                    Text("Delete", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteDialog = false }) { Text("Cancel") }
            }
        )
    }
}
