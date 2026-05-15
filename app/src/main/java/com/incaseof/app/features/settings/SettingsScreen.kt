@file:Suppress("DEPRECATION")
package com.incaseof.app.features.settings

import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.incaseof.app.core.design.SafetyCard

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit, onAbout: () -> Unit) {
    val context = LocalContext.current

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.SemiBold) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SafetyCard {
                ListItem(
                    headlineContent = { Text("Dark Mode", fontWeight = FontWeight.Medium) },
                    supportingContent = { Text("Follow system setting") },
                    leadingContent = { Icon(Icons.Default.DarkMode, null, tint = MaterialTheme.colorScheme.primary) }
                )
            }
            SafetyCard(onClick = {
                // Open Android notification settings for this app
                val intent = Intent().apply {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        action = Settings.ACTION_APP_NOTIFICATION_SETTINGS
                        putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)
                    } else {
                        action = Settings.ACTION_APPLICATION_DETAILS_SETTINGS
                        data = android.net.Uri.fromParts("package", context.packageName, null)
                    }
                }
                context.startActivity(intent)
            }) {
                ListItem(
                    headlineContent = { Text("Notifications", fontWeight = FontWeight.Medium) },
                    supportingContent = { Text("Manage notification permissions") },
                    leadingContent = { Icon(Icons.Default.Notifications, null, tint = MaterialTheme.colorScheme.primary) },
                    trailingContent = { Icon(Icons.Default.OpenInNew, null, tint = MaterialTheme.colorScheme.outline, modifier = Modifier.size(18.dp)) }
                )
            }
            SafetyCard(onClick = onAbout) {
                ListItem(
                    headlineContent = { Text("About & Hackathon Info", fontWeight = FontWeight.Medium) },
                    supportingContent = { Text("How Gemma 4 is used, architecture details") },
                    leadingContent = { Icon(Icons.Default.Info, null, tint = MaterialTheme.colorScheme.primary) },
                    trailingContent = { Icon(Icons.Default.ChevronRight, null) }
                )
            }
            SafetyCard {
                ListItem(
                    headlineContent = { Text("Version", fontWeight = FontWeight.Medium) },
                    supportingContent = { Text("1.0.0 (Gemma 4 Good Hackathon)") },
                    leadingContent = { Icon(Icons.Default.Code, null, tint = MaterialTheme.colorScheme.outline) }
                )
            }
        }
    }
}
