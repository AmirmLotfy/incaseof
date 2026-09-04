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
import com.incaof.app.domain.Vocabulary
import com.incaof.app.feature.home.userMessage
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.PrimaryAction
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
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
            _invite.value = CircleInviteUiState(error = "Enter the person’s name.")
            return
        }
        viewModelScope.launch {
            _invite.value = CircleInviteUiState(busy = true)
            repository.inviteCircleMember(name, relationship.trim().ifEmpty { null }, role).fold(
                onSuccess = { inviteUrl ->
                    _invite.value =
                        CircleInviteUiState(
                            notice =
                                "Invitation created. Share the scoped link; " +
                                    "they must accept before any plan can rely on them.",
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
    val notice: String? = null,
    val error: String? = null,
    val inviteUrl: String? = null,
)

sealed interface CircleUiState {
    data object Loading : CircleUiState

    data class Content(
        val members: List<CircleMember>,
    ) : CircleUiState

    data class Failed(
        val message: String,
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
            Notice(state.message, modifier.padding(24.dp))
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
    Text("Invite someone", style = MaterialTheme.typography.titleLarge)
    Spacer(Modifier.height(8.dp))
    Text(
        "They receive a scoped consent link. Their contact details are never exposed to the agent.",
        color = LocalIcoColors.current.graphite,
    )
    Spacer(Modifier.height(12.dp))
    OutlinedTextField(
        value = name,
        onValueChange = { name = it },
        label = { Text("Name") },
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(8.dp))
    OutlinedTextField(
        value = relationship,
        onValueChange = { relationship = it },
        label = { Text("Relationship (optional)") },
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth(),
    )
    Spacer(Modifier.height(8.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        ResponderRole.entries.forEach { option ->
            TextButton(onClick = { role = option }, enabled = !state.busy) {
                Text(if (role == option) "● ${Vocabulary.role(option)}" else Vocabulary.role(option))
            }
        }
    }
    state.error?.let { Notice(it) }
    state.notice?.let { Notice(it) }
    state.inviteUrl?.let { inviteUrl ->
        TextButton(
            onClick = {
                context.startActivity(
                    Intent.createChooser(
                        Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(
                                Intent.EXTRA_TEXT,
                                "I’d like you to join my In Case Of Circle. Review and accept here: $inviteUrl",
                            )
                        },
                        "Share consent link",
                    ),
                )
            },
        ) {
            Text("Share consent link")
        }
    }
    Spacer(Modifier.height(8.dp))
    PrimaryAction(
        label = if (state.busy) "Creating invitation…" else "Create invitation",
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

    Column(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 16.dp)
            .semantics {
                contentDescription =
                    buildString {
                        append(member.displayName)
                        member.relationship?.let { append(", $it") }
                        append(", ${Vocabulary.role(member.role)}")
                        append(", $acceptance, phone $verification")
                    }
            },
    ) {
        Text(member.displayName, style = MaterialTheme.typography.titleMedium, color = ico.ink)
        member.relationship?.let {
            Spacer(Modifier.height(2.dp))
            TabularLabel(it)
        }
        Spacer(Modifier.height(8.dp))
        Text(
            Vocabulary.role(member.role),
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
            label = "Phone $verification",
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
