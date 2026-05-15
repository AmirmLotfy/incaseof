package com.incaseof.app.features.about

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.incaseof.app.core.design.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AboutScreen(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("About", fontWeight = FontWeight.SemiBold) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            BrandShield(size = 72)
            Text("In Case Of", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
            Text("Built for Gemma 4 Good Hackathon", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)

            Spacer(Modifier.height(8.dp))

            AboutItem(Icons.Default.Memory, "Gemma 4 E2B", "On-device natural language to workflow JSON conversion. No data leaves your phone.")
            AboutItem(Icons.Default.Shield, "Local-first", "All processing happens on your device. Your safety plans are private by design.")
            AboutItem(Icons.Default.Architecture, "Architecture", "Gemma plans. Kotlin validates. WorkManager schedules. Android intents execute after user approval.")
            AboutItem(Icons.Default.VerifiedUser, "User control", "You approve every action. No hidden monitoring. No automatic unsafe execution.")
            AboutItem(Icons.Default.Security, "Safety validation", "Every workflow is validated against deterministic safety rules before activation.")
            AboutItem(Icons.Default.Schedule, "Background checking", "WorkManager detects missed check-ins and sends verification notifications.")

            SafetyCard {
                Column {
                    Text("Tech Stack", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    val techs = listOf(
                        "Kotlin",
                        "Jetpack Compose",
                        "Material 3",
                        "LiteRT-LM 0.11.0 / Gemma 4 E2B",
                        "WorkManager",
                        "Room",
                        "DataStore",
                        "Hilt",
                        "kotlinx.serialization"
                    )
                    techs.forEach { Text("• $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    Spacer(Modifier.height(8.dp))
                    Text("No API key required — Gemma runs fully on-device.",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.primary)
                }
            }

            SafetyCard {
                Column {
                    Text("Limitations", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(8.dp))
                    val limits = listOf("WhatsApp is manual prepared-message only", "SMS uses user-confirmed intent", "Background execution follows Android restrictions", "Not a replacement for emergency services")
                    limits.forEach { Text("• $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                }
            }

            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
private fun AboutItem(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, desc: String) {
    SafetyCard {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(icon, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
            Column {
                Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(desc, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
