package com.incaof.app.feature.circle

import android.content.Intent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.R
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.CircleMember
import com.incaof.app.domain.ResponderRole
import com.incaof.app.feature.home.userMessage
import com.incaof.app.ui.UiMessage
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
import com.incaof.app.ui.localizedRole
import com.incaof.app.ui.localizedUiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CircleViewModel(
    private val repository: IcoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<CircleUiState>(CircleUiState.Loading)
    val state: StateFlow<CircleUiState> = _state.asStateFlow()

    private val _invite = MutableStateFlow(CircleInviteUiState())
    val invite: StateFlow<CircleInviteUiState> = _invite.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value =
                repository.circle().fold(
                    onSuccess = { CircleUiState.Content(it) },
                    onFailure = { CircleUiState.Failed(it.userMessage()) },
                )
        }
    }

    fun invite(displayName: String, relationship: String, role: ResponderRole) {
        val name = displayName.trim()
        if (name.isEmpty()) {
            _invite.value = CircleInviteUiState(message = CircleInviteMessage.ENTER_NAME)
            return
        }
        viewModelScope.launch {
            _invite.value = CircleInviteUiState(busy = true)
            repository.inviteCircleMember(name, relationship.trim().ifEmpty { null }, role).fold(
                onSuccess = { inviteUrl ->
                    _invite.value =
                        CircleInviteUiState(
                            message = CircleInviteMessage.CREATED,
                            inviteUrl = inviteUrl,
                        )
                    refresh()
                },
                onFailure = { _invite.value = CircleInviteUiState(error = it.userMessage()) },
            )
        }
    }
}

data class CircleInviteUiState(
    val busy: Boolean = false,
    val message: CircleInviteMessage? = null,
    val error: UiMessage? = null,
    val inviteUrl: String? = null,
)

enum class CircleInviteMessage {
    ENTER_NAME,
    CREATED,
}

sealed interface CircleUiState {
    data object Loading : CircleUiState

    data class Content(
        val members: List<CircleMember>,
    ) : CircleUiState

    data class Failed(
        val message: UiMessage,
    ) : CircleUiState
}

/**
 * Circle. Build contract §12.
 *
 * Roles are shown explicitly, because escalation order is something the subject chose and
 * should be able to check. Verification is shown as a fact, not a badge.
 *
 * Deliberately absent: avatars and presence indicators. This is not a social surface, and a
 * green dot beside a person's name implies a kind of monitoring that does not happen.
 */
@Composable
fun CircleScreen(
    state: CircleUiState,
    inviteState: CircleInviteUiState = CircleInviteUiState(),
    onInvite: (String, String, ResponderRole) -> Unit = { _, _, _ -> },
    modifier: Modifier = Modifier,
) {
    when (state) {
        CircleUiState.Loading -> {
            Column(
                modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator() }
        }

        is CircleUiState.Failed -> {
            Notice(localizedUiMessage(state.message), modifier.padding(24.dp))
        }

        is CircleUiState.Content -> {
            LazyColumn(
                modifier = modifier.fillMaxSize(),
                contentPadding = PaddingValues(24.dp),
            ) {
                item {
                    InviteMember(inviteState, onInvite)
                    Spacer(Modifier.height(24.dp))
                    HorizontalDivider(color = LocalIcoColors.current.stone)
                }
                items(state.members, key = { it.id }) { member ->
                    MemberRow(member)
                    HorizontalDivider(color = LocalIcoColors.current.stone)
                }
            }
        }
    }
}

@Composable
private fun InviteMember(
    state: CircleInviteUiState,
    onInvite: (String, String, ResponderRole) -> Unit,
) {
    val context = LocalContext.current
    var name by remember { mutableStateOf("") }
    var relationship by remember { mutableStateOf("") }
    var role by remember { mutableStateOf(ResponderRole.PRIMARY) }
    Text(stringResource(R.string.circle_invite), style = MaterialTheme.typography.titleLarge)
    Spacer(Modifier.height(8.dp))
    Text(
        stringResource(R.string.circle_invite_intro),
        color = LocalIcoColors.current.graphite,
    )
    Spacer(Modifier.height(12.dp))
    OutlinedTextField(
        value = name,
        onValueChange = { name = it },
        label = { Text(stringResource(R.string.circle_name)) },
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(8.dp))
    OutlinedTextField(
        value = relationship,
        onValueChange = { relationship = it },
        label = { Text(stringResource(R.string.circle_relationship_optional)) },
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(8.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        ResponderRole.entries.forEach { option ->
            val roleLabel = localizedRole(option)
            TextButton(onClick = { role = option }, enabled = !state.busy) {
                Text(if (role == option) "● $roleLabel" else roleLabel)
            }
        }
    }
    state.error?.let { Notice(localizedUiMessage(it)) }
    state.message?.let {
        Notice(
            stringResource(
                when (it) {
                    CircleInviteMessage.ENTER_NAME -> R.string.circle_enter_name
                    CircleInviteMessage.CREATED -> R.string.circle_invitation_created
                },
            ),
        )
    }
    state.inviteUrl?.let { inviteUrl ->
        val shareMessage = stringResource(R.string.circle_share_message, inviteUrl)
        val chooserTitle = stringResource(R.string.circle_share_consent)
        TextButton(
            onClick = {
                context.startActivity(
                    Intent.createChooser(
                        Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(
                                Intent.EXTRA_TEXT,
                                shareMessage,
                            )
                        },
                        chooserTitle,
                    ),
                )
            },
        ) {
            Text(stringResource(R.string.circle_share_consent))
        }
    }
    Spacer(Modifier.height(8.dp))
    PrimaryAction(
        label =
            stringResource(
                if (state.busy) R.string.circle_creating_invitation else R.string.circle_create_invitation,
            ),
        onClick = { onInvite(name, relationship, role) },
        enabled = !state.busy,
    )
}

@Composable
private fun MemberRow(member: CircleMember) {
    val ico = LocalIcoColors.current
    val acceptance =
        if (member.accepted) {
            stringResource(R.string.accepted)
        } else {
            stringResource(R.string.invitation_pending)
        }
    val verification =
        if (member.phoneVerified) {
            stringResource(R.string.verified)
        } else {
            stringResource(R.string.not_verified)
        }
    val roleLabel = localizedRole(member.role)
    val phoneStatus = stringResource(R.string.circle_phone_status, verification)
    val memberDescription =
        listOfNotNull(member.displayName, member.relationship, roleLabel, phoneStatus).joinToString(", ")

    Column(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 16.dp)
            .semantics {
                contentDescription = "$memberDescription, $acceptance"
            },
    ) {
        Text(member.displayName, style = MaterialTheme.typography.titleMedium, color = ico.ink)
        member.relationship?.let {
            Spacer(Modifier.height(2.dp))
            TabularLabel(it)
        }
        Spacer(Modifier.height(8.dp))
        Text(
            roleLabel,
            style = MaterialTheme.typography.labelSmall,
            color = ico.graphite,
        )
        Spacer(Modifier.height(8.dp))
        StatusMarker(
            label = acceptance,
            color = if (member.accepted) ico.primary else ico.warning,
        )
        Spacer(Modifier.height(4.dp))
        StatusMarker(
            label = phoneStatus,
            color = if (member.phoneVerified) ico.primary else ico.warning,
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun CirclePreview() {
    InCaseOfTheme {
        CircleScreen(
            CircleUiState.Content(
                listOf(
                    CircleMember("1", "Maya", "Sister", ResponderRole.PRIMARY, true, true),
                    CircleMember("2", "Omar", "Friend", ResponderRole.BACKUP, true, false),
                ),
            ),
        )
    }
}
