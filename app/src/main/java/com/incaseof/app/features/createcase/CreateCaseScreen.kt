@file:Suppress("DEPRECATION")
package com.incaseof.app.features.createcase

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.incaseof.app.core.design.*
import java.util.Locale

data class CaseSuggestion(
    val label: String,
    val condition: String,
    val action: String
)

val caseSuggestions = listOf(
    CaseSuggestion(
        "Daily check-in",
        "I don't check in for 24 hours",
        "Ask me if I'm okay, then message my emergency contact"
    ),
    CaseSuggestion(
        "Travel arrival",
        "I don't confirm my arrival within 12 hours",
        "Send my location and a message to my family"
    ),
    CaseSuggestion(
        "Solo hike",
        "I don't check in for 4 hours during my hike",
        "Send my last known location and call my emergency contact"
    ),
    CaseSuggestion(
        "Medication",
        "I don't confirm taking my medication by 10 AM",
        "Send a reminder, then alert my caregiver"
    ),
    CaseSuggestion(
        "Night shift",
        "I don't check in after my 8 hour shift",
        "Message my partner that I haven't checked in"
    )
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateCaseScreen(
    onCompile: (String, String) -> Unit,
    onBack: () -> Unit,
    viewModel: CreateCaseViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // Voice launcher for condition field
    val conditionVoiceLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val text = result.data
                ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull() ?: return@rememberLauncherForActivityResult
            viewModel.updateCondition(text)
        }
    }

    // Voice launcher for action field
    val actionVoiceLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val text = result.data
                ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull() ?: return@rememberLauncherForActivityResult
            viewModel.updateAction(text)
        }
    }

    fun launchVoice(launcher: androidx.activity.result.ActivityResultLauncher<Intent>, hint: String) {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PROMPT, hint)
        }
        launcher.launch(intent)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Create Case",
                        fontWeight = FontWeight.SemiBold
                    )
                },
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Condition input
            SafetyCard {
                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(20.dp)
                        )
                        Text(
                            text = "In case of...",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedTextField(
                        value = uiState.condition,
                        onValueChange = viewModel::updateCondition,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = {
                            Text(
                                "I don't check in for 24 hours",
                                color = MaterialTheme.colorScheme.outline
                            )
                        },
                        trailingIcon = {
                            IconButton(onClick = {
                                launchVoice(conditionVoiceLauncher, "Describe the situation")
                            }) {
                                Icon(
                                    Icons.Default.Mic,
                                    contentDescription = "Voice input",
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        },
                        shape = RoundedCornerShape(16.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                        ),
                        minLines = 2,
                        maxLines = 4
                    )
                }
            }

            // Action input
            SafetyCard {
                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.secondary,
                            modifier = Modifier.size(20.dp)
                        )
                        Text(
                            text = "The app should...",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.secondary
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedTextField(
                        value = uiState.action,
                        onValueChange = viewModel::updateAction,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = {
                            Text(
                                "Ask me if I'm okay, then message my mom",
                                color = MaterialTheme.colorScheme.outline
                            )
                        },
                        trailingIcon = {
                            IconButton(onClick = {
                                launchVoice(actionVoiceLauncher, "What should the app do?")
                            }) {
                                Icon(
                                    Icons.Default.Mic,
                                    contentDescription = "Voice input",
                                    tint = MaterialTheme.colorScheme.secondary
                                )
                            }
                        },
                        shape = RoundedCornerShape(16.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.secondary,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                        ),
                        minLines = 2,
                        maxLines = 4
                    )
                }
            }

            // Quick suggestions
            Column {
                Text(
                    text = "Quick suggestions",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 4.dp, bottom = 8.dp)
                )
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(caseSuggestions.size) { index ->
                        val suggestion = caseSuggestions[index]
                        SuggestedCaseChip(
                            label = suggestion.label,
                            icon = when (index) {
                                0 -> Icons.Default.Today
                                1 -> Icons.Default.Flight
                                2 -> Icons.Filled.DirectionsRun
                                3 -> Icons.Default.Medication
                                else -> Icons.Default.NightShelter
                            },
                            onClick = {
                                viewModel.applySuggestion(suggestion.condition, suggestion.action)
                            }
                        )
                    }
                }
            }

            // Privacy note
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.1f),
                        RoundedCornerShape(12.dp)
                    )
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    Icons.Default.Lock,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(16.dp)
                )
                Text(
                    text = "Processed on device with Gemma 4. Your data stays local.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Generate button
            PrimaryCTA(
                text = "Generate safety plan",
                onClick = { onCompile(uiState.condition, uiState.action) },
                enabled = uiState.isValid,
                icon = Icons.Default.AutoAwesome
            )
        }
    }
}
