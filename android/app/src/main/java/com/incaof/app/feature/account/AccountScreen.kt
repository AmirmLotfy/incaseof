package com.incaof.app.feature.account

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.design.IcoOnColor
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.SecondaryAction
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.localizedUiMessage

@Composable
fun AccountScreen(
    state: AccountUiState,
    onConfirmationChange: (String) -> Unit,
    onDelete: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier =
            modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 20.dp),
    ) {
        SecondaryAction(stringResource(R.string.account_back), onBack)
        Spacer(Modifier.height(12.dp))

        when (state) {
            is AccountUiState.Ready -> DeleteAccountForm(state, onConfirmationChange, onDelete)
            is AccountUiState.Requested -> DeletionRequested(state)
        }
    }
}

@Composable
private fun DeleteAccountForm(
    state: AccountUiState.Ready,
    onConfirmationChange: (String) -> Unit,
    onDelete: () -> Unit,
) {
    val ico = LocalIcoColors.current
    Text(
        stringResource(R.string.account_title),
        style = MaterialTheme.typography.headlineMedium,
        color = ico.ink,
        modifier = Modifier.semantics { heading() },
    )
    Spacer(Modifier.height(12.dp))
    Text(
        stringResource(R.string.account_deletion_intro),
        style = MaterialTheme.typography.bodyLarge,
        color = ico.graphite,
    )
    Spacer(Modifier.height(24.dp))
    Text(
        stringResource(R.string.account_deletion_consequences_title),
        style = MaterialTheme.typography.titleMedium,
        color = ico.ink,
    )
    Spacer(Modifier.height(8.dp))
    Text(stringResource(R.string.account_deletion_consequences), color = ico.graphite)
    Spacer(Modifier.height(24.dp))
    OutlinedTextField(
        value = state.confirmation,
        onValueChange = onConfirmationChange,
        enabled = !state.busy,
        singleLine = true,
        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Characters),
        label = { Text(stringResource(R.string.account_deletion_confirmation_label)) },
        supportingText = { Text(stringResource(R.string.account_deletion_confirmation_help)) },
        modifier = Modifier.fillMaxWidth(),
    )
    state.error?.let {
        Spacer(Modifier.height(8.dp))
        Notice(localizedUiMessage(it), Modifier.semantics { liveRegion = LiveRegionMode.Assertive })
    }
    Spacer(Modifier.height(16.dp))
    PrimaryAction(
        label =
            stringResource(
                if (state.busy) R.string.account_deletion_requesting else R.string.account_deletion_action,
            ),
        onClick = onDelete,
        enabled = state.canDelete,
        description = stringResource(R.string.account_deletion_action_description),
        container = ico.critical,
        content = IcoOnColor.critical,
    )
}

@Composable
private fun DeletionRequested(state: AccountUiState.Requested) {
    val ico = LocalIcoColors.current
    StatusMarker(
        label = stringResource(R.string.account_deletion_pending),
        color = ico.signal,
        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Assertive },
    )
    Spacer(Modifier.height(20.dp))
    Text(
        stringResource(R.string.account_deletion_received),
        style = MaterialTheme.typography.headlineMedium,
        color = ico.ink,
        modifier = Modifier.semantics { heading() },
    )
    Spacer(Modifier.height(12.dp))
    Text(stringResource(R.string.account_deletion_stopped), color = ico.graphite)
    Spacer(Modifier.height(20.dp))
    state.deletion.nextSteps.forEach { step ->
        Text("• $step", style = MaterialTheme.typography.bodyLarge, color = ico.graphite)
        Spacer(Modifier.height(8.dp))
    }
    Spacer(Modifier.height(12.dp))
    Text(
        stringResource(R.string.account_deletion_close_app),
        style = MaterialTheme.typography.bodyLarge,
        color = ico.ink,
    )
}
