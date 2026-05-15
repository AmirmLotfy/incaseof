package com.incaseof.app.features.compiling

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.design.*
import com.incaseof.app.domain.models.CaseDraftInput
import com.incaseof.app.domain.usecases.CreateCaseResult
import com.incaseof.app.domain.usecases.CreateCaseUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CompilingStep(
    val icon: ImageVector,
    val label: String,
    val isComplete: Boolean,
    val isActive: Boolean
)

data class CompilingUiState(
    val steps: List<CompilingStep> = listOf(
        CompilingStep(Icons.Default.Psychology, "Understanding your case", false, true),
        CompilingStep(Icons.Default.Security, "Checking safety rules", false, false),
        CompilingStep(Icons.Default.Architecture, "Building action plan", false, false),
        CompilingStep(Icons.Default.RateReview, "Preparing review", false, false)
    ),
    val currentStep: Int = 0,
    val resultCaseId: String? = null,
    val error: String? = null,
    val isComplete: Boolean = false
)

@HiltViewModel
class CompilingViewModel @Inject constructor(
    private val createCaseUseCase: CreateCaseUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(CompilingUiState())
    val uiState = _uiState.asStateFlow()

    fun compile(condition: String, action: String) {
        viewModelScope.launch {
            // Step 1: Understanding
            delay(600)
            advanceStep(1)

            // Step 2: Safety check
            delay(500)
            advanceStep(2)

            // Actual compilation happens here (includes mock delay)
            val result = createCaseUseCase.execute(CaseDraftInput(condition, action))

            // Step 3: Building plan
            advanceStep(3)
            delay(400)

            // Step 4: Complete
            when (result) {
                is CreateCaseResult.Success -> {
                    _uiState.update {
                        it.copy(
                            steps = it.steps.mapIndexed { i, step ->
                                step.copy(isComplete = true, isActive = false)
                            },
                            currentStep = 4,
                            resultCaseId = result.caseId,
                            isComplete = true
                        )
                    }
                }
                is CreateCaseResult.CompilationFailed -> {
                    _uiState.update { it.copy(error = result.error) }
                }
                is CreateCaseResult.ValidationFailed -> {
                    _uiState.update { it.copy(error = result.errors.joinToString("\n")) }
                }
                is CreateCaseResult.NeedsClarification -> {
                    _uiState.update {
                        it.copy(error = "Clarification needed:\n${result.questions.joinToString("\n• ", "• ")}")
                    }
                }
            }
        }
    }

    private fun advanceStep(to: Int) {
        _uiState.update {
            it.copy(
                steps = it.steps.mapIndexed { i, step ->
                    when {
                        i < to -> step.copy(isComplete = true, isActive = false)
                        i == to -> step.copy(isComplete = false, isActive = true)
                        else -> step.copy(isComplete = false, isActive = false)
                    }
                },
                currentStep = to
            )
        }
    }
}

@Composable
fun CompilingScreen(
    condition: String,
    action: String,
    onComplete: (String) -> Unit,
    onError: () -> Unit,
    viewModel: CompilingViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.compile(condition, action)
    }

    // Auto-navigate on completion
    LaunchedEffect(uiState.resultCaseId) {
        uiState.resultCaseId?.let { caseId ->
            delay(800)
            onComplete(caseId)
        }
    }

    // Pulse animation
    val infiniteTransition = rememberInfiniteTransition(label = "compiling_pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.08f)
                    )
                )
            ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp)
        ) {
            // Animated shield
            BrandShield(
                size = 80,
                modifier = Modifier.scale(
                    if (!uiState.isComplete) {
                        val scale by infiniteTransition.animateFloat(
                            initialValue = 0.95f,
                            targetValue = 1.05f,
                            animationSpec = infiniteRepeatable(
                                animation = tween(1000, easing = EaseInOutCubic),
                                repeatMode = RepeatMode.Reverse
                            ),
                            label = "shield_scale"
                        )
                        scale
                    } else 1f
                )
            )

            Spacer(modifier = Modifier.height(32.dp))

            Text(
                text = if (uiState.isComplete) "Plan ready!" else "Building your safety plan",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onBackground
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Powered by Gemma 4 on-device",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Steps
            SafetyCard {
                uiState.steps.forEachIndexed { index, step ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Step indicator
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(
                                    when {
                                        step.isComplete -> SafetyGreen.copy(alpha = 0.15f)
                                        step.isActive -> MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)
                                        else -> MaterialTheme.colorScheme.surfaceVariant
                                    }
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            if (step.isComplete) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = SafetyGreen,
                                    modifier = Modifier.size(18.dp)
                                )
                            } else {
                                Icon(
                                    step.icon,
                                    contentDescription = null,
                                    tint = if (step.isActive)
                                        MaterialTheme.colorScheme.primary
                                    else
                                        MaterialTheme.colorScheme.outline,
                                    modifier = Modifier
                                        .size(18.dp)
                                        .alpha(if (step.isActive) pulseAlpha else 0.5f)
                                )
                            }
                        }

                        Text(
                            text = step.label,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = if (step.isActive) FontWeight.SemiBold else FontWeight.Normal,
                            color = when {
                                step.isComplete -> SafetyGreen
                                step.isActive -> MaterialTheme.colorScheme.onSurface
                                else -> MaterialTheme.colorScheme.outline
                            }
                        )
                    }

                    if (index < uiState.steps.size - 1) {
                        Box(
                            modifier = Modifier
                                .padding(start = 17.dp)
                                .width(2.dp)
                                .height(12.dp)
                                .background(
                                    if (step.isComplete) SafetyGreen.copy(alpha = 0.3f)
                                    else MaterialTheme.colorScheme.outlineVariant
                                )
                        )
                    }
                }
            }

            // Error state
            uiState.error?.let { error ->
                Spacer(modifier = Modifier.height(20.dp))
                SafetyCard {
                    Row(
                        verticalAlignment = Alignment.Top,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(
                            Icons.Default.ErrorOutline,
                            contentDescription = null,
                            tint = DangerRed,
                            modifier = Modifier.size(24.dp)
                        )
                        Column {
                            Text(
                                text = "Could not compile plan",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold,
                                color = DangerRed
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = error,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(16.dp))
                PrimaryCTA(
                    text = "Go back and try again",
                    onClick = onError,
                    icon = Icons.Default.Refresh
                )
            }
        }
    }
}
