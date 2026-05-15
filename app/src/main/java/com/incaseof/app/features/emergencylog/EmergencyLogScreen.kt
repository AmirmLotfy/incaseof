@file:Suppress("DEPRECATION")
package com.incaseof.app.features.emergencylog

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EmergencyLogScreen(
    onBack: () -> Unit,
    viewModel: EmergencyLogViewModel = hiltViewModel()
) {
    val events by viewModel.events.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Safety Log", fontWeight = FontWeight.SemiBold) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        if (events.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.History, null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outline)
                    Spacer(Modifier.height(12.dp))
                    Text("No events yet", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.outline)
                    Text("Events will appear here as your cases run.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline)
                }
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(16.dp)) {
                items(events) { event ->
                    val type = try { CaseEventType.valueOf(event.type) } catch (e: Exception) { CaseEventType.CREATED }
                    val (icon, color) = when (type) {
                        CaseEventType.CREATED -> Icons.Default.Add to MaterialTheme.colorScheme.primary
                        CaseEventType.ACTIVATED -> Icons.Default.PlayArrow to SafetyGreen
                        CaseEventType.CHECK_IN -> Icons.Default.CheckCircle to SafetyGreen
                        CaseEventType.MISSED_CHECK_IN -> Icons.Default.Warning to AmberWarning
                        CaseEventType.VERIFICATION_STARTED -> Icons.Default.NotificationsActive to CoralAccent
                        CaseEventType.VERIFICATION_EXPIRED -> Icons.Default.Timer to DangerRed
                        CaseEventType.USER_MARKED_SAFE -> Icons.Default.Shield to SafetyGreen
                        CaseEventType.ACTION_PREPARED -> Icons.Filled.Send to CoralAccent
                        CaseEventType.SIMULATION_RUN -> Icons.Default.Science to MaterialTheme.colorScheme.primary
                        else -> Icons.Default.Info to MaterialTheme.colorScheme.onSurfaceVariant
                    }
                    val fmt = SimpleDateFormat("MMM d, h:mm:ss a", Locale.getDefault())
                    TimelineItem(icon = icon, iconTint = color, title = event.message,
                        subtitle = "Case: ${event.caseId.take(8)}…",
                        timestamp = fmt.format(Date(event.timestamp)),
                        isLast = event == events.last())
                }
            }
        }
    }
}
