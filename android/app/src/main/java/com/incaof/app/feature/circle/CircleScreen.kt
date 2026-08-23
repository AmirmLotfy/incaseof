package com.incaof.app.feature.circle

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
}

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
fun CircleScreen(state: CircleUiState, modifier: Modifier = Modifier) {
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
                items(state.members, key = { it.id }) { member ->
                    MemberRow(member)
                    HorizontalDivider(color = LocalIcoColors.current.stone)
                }
            }
        }
    }
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
