@file:Suppress("DEPRECATION")
package com.incaseof.app.features.review

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import com.incaseof.app.core.model.RiskLevel
import com.incaseof.app.domain.models.ActionSpec
import com.incaseof.app.domain.models.TriggerSpec

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SafetyReviewScreen(
    onActivate: (String) -> Unit,
    onPickContact: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: SafetyReviewViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // Location permission launcher — fires when activating a case that shares location
    val locationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { /* Permission results — activation proceeds regardless */ }

    // Check if this workflow needs location
    val needsLocation = remember(uiState.workflow) {
        uiState.workflow?.actions?.any { action ->
            when (action) {
                is ActionSpec.SendSms -> action.includeLastKnownLocation
                is ActionSpec.SendEmail -> action.includeLastKnownLocation
                else -> false
            }
        } ?: false
    }

    // Auto-navigate after activation
    LaunchedEffect(uiState.isActivated) {
        if (uiState.isActivated) {
            uiState.caseEntity?.id?.let { onActivate(it) }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Safety Review", fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background
                )
            )
        }
    ) { padding ->
        val workflow = uiState.workflow
        val caseEntity = uiState.caseEntity

        if (workflow == null || caseEntity == null) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Title and summary
            SafetyCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    BrandShield(height = 44)
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = workflow.title,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        RiskBadge(level = uiState.riskLevel)
                    }
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = workflow.summary,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Trigger section
            ReviewSection(
                icon = Icons.Default.Timer,
                title = "What will trigger this?",
                iconTint = MaterialTheme.colorScheme.primary
            ) {
                when (val trigger = workflow.trigger) {
                    is TriggerSpec.MissedCheckIn -> {
                        Text(
                            text = "No check-in for ${trigger.durationHours} hours.",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Medium
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = trigger.checkInPrompt,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    is TriggerSpec.ScheduledTime -> {
                        Text(
                            text = "At ${trigger.localTime} (${trigger.timezone}).",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            // Verification section
            if (workflow.verification.enabled) {
                ReviewSection(
                    icon = Icons.Default.NotificationsActive,
                    title = "What happens first?",
                    iconTint = AmberWarning
                ) {
                    Text(
                        text = "You get a notification asking if you are okay.",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                text = workflow.verification.notificationTitle,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = workflow.verification.notificationBody,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Wait: ${workflow.verification.waitMinutes} minutes",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.outline
                            )
                        }
                    }
                }
            }

            // Actions section
            ReviewSection(
                icon = Icons.Filled.Send,
                title = "What happens if you don't respond?",
                iconTint = CoralAccent
            ) {
                workflow.actions.forEach { action ->
                    when (action) {
                        is ActionSpec.SendSms -> {
                            ActionPreview(
                                type = "SMS",
                                description = "Send to ${action.contactRole}",
                                detail = action.message,
                                includesLocation = action.includeLastKnownLocation
                            )
                        }
                        is ActionSpec.SendEmail -> {
                            ActionPreview(
                                type = "Email",
                                description = "Subject: ${action.subject}",
                                detail = action.body,
                                includesLocation = action.includeLastKnownLocation
                            )
                        }
                        is ActionSpec.CallContact -> {
                            ActionPreview(
                                type = "Call",
                                description = "Call ${action.contactRole}",
                                detail = "Opens phone dialer",
                                includesLocation = false
                            )
                        }
                        is ActionSpec.OpenWhatsAppPreparedMessage -> {
                            ActionPreview(
                                type = "WhatsApp",
                                description = "Prepared message",
                                detail = action.message,
                                includesLocation = false
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }

            // Permissions section
            if (workflow.permissions.isNotEmpty()) {
                ReviewSection(
                    icon = Icons.Default.VerifiedUser,
                    title = "Permissions",
                    iconTint = SafetyGreen
                ) {
                    workflow.permissions.forEach { perm ->
                        Row(
                            modifier = Modifier.padding(vertical = 4.dp),
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(
                                if (perm.required) Icons.Default.CheckCircle else Icons.Default.RadioButtonUnchecked,
                                contentDescription = null,
                                tint = if (perm.required) SafetyGreen else MaterialTheme.colorScheme.outline,
                                modifier = Modifier.size(18.dp)
                            )
                            Column {
                                Text(
                                    text = "${perm.permission} ${if (perm.required) "(required)" else "(optional)"}",
                                    style = MaterialTheme.typography.labelLarge,
                                    fontWeight = FontWeight.Medium
                                )
                                Text(
                                    text = perm.reason,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }

            // Risk section
            ReviewSection(
                icon = Icons.Default.Warning,
                title = "Risk Assessment",
                iconTint = when (uiState.riskLevel) {
                    RiskLevel.LOW -> SafetyGreen
                    RiskLevel.MEDIUM -> AmberWarning
                    RiskLevel.HIGH -> DangerRed
                }
            ) {
                RiskBadge(level = uiState.riskLevel)
                Spacer(modifier = Modifier.height(8.dp))
                workflow.risk.reasons.forEach { reason ->
                    Text(
                        text = "• $reason",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Trusted Contact button
            OutlinedButton(
                onClick = { onPickContact(caseEntity.id) },
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(Icons.Default.PersonAdd, contentDescription = null, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (uiState.hasTrustedContact) "Change trusted contact (${caseEntity.trustedContactName})"
                    else "Choose trusted contact",
                    fontWeight = FontWeight.Medium
                )
            }

            // Activate button
            PrimaryCTA(
                text = if (uiState.isActivating) "Activating..." else "Enable case",
                onClick = {
                    // Request location permission if this case shares location
                    if (needsLocation) {
                        locationPermissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            )
                        )
                    }
                    viewModel.activateCase()
                },
                enabled = !uiState.isActivating,
                icon = Icons.Default.Shield
            )

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun ReviewSection(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    iconTint: androidx.compose.ui.graphics.Color,
    content: @Composable ColumnScope.() -> Unit
) {
    SafetyCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.padding(bottom = 12.dp)
        ) {
            Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(22.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }
        content()
    }
}

@Composable
private fun ActionPreview(
    type: String,
    description: String,
    detail: String,
    includesLocation: Boolean
) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
                ) {
                    Text(
                        text = type,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                    )
                }
                Text(
                    text = description,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "\"$detail\"",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (includesLocation) {
                Spacer(modifier = Modifier.height(4.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Icon(
                        Icons.Default.LocationOn,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.outline,
                        modifier = Modifier.size(14.dp)
                    )
                    Text(
                        text = "Includes last known location",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }
        }
    }
}
