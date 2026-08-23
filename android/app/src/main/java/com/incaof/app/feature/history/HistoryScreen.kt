package com.incaof.app.feature.history

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
import com.incaof.app.core.time.TimeFormat
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.ResolvedMoment
import com.incaof.app.feature.home.userMessage
import com.incaof.app.ui.components.Notice
import com.incaof.app.ui.components.StatusMarker
import com.incaof.app.ui.components.TabularLabel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant

class HistoryViewModel(
    private val repository: IcoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<HistoryUiState>(HistoryUiState.Loading)
    val state: StateFlow<HistoryUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.value =
                repository.history().fold(
                    onSuccess = { HistoryUiState.Content(it) },
                    onFailure = { HistoryUiState.Failed(it.userMessage()) },
                )
        }
    }
}

sealed interface HistoryUiState {
    data object Loading : HistoryUiState

    data class Content(
        val entries: List<ResolvedMoment>,
    ) : HistoryUiState

    data class Failed(
        val message: String,
    ) : HistoryUiState
}

/**
 * History. Build contract §24.
 *
 * Reassuring rather than forensic: what resolved, when, and who closed it. The full audit
 * trail is one tap in, not the default view.
 *
 * Deliberately absent: streaks, adherence percentages, charts. Gamifying a safety record
 * creates pressure to maintain a streak, which is exactly the wrong incentive to attach to
 * whether somebody says they are okay.
 */
@Composable
fun HistoryScreen(state: HistoryUiState, modifier: Modifier = Modifier) {
    when (state) {
        HistoryUiState.Loading -> {
            Column(
                modifier.fillMaxSize(),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) { CircularProgressIndicator() }
        }

        is HistoryUiState.Failed -> {
            Notice(state.message, modifier.padding(24.dp))
        }

        is HistoryUiState.Content -> {
            if (state.entries.isEmpty()) {
                Notice(stringResource(R.string.history_empty), modifier.padding(24.dp))
            } else {
                LazyColumn(
                    modifier = modifier.fillMaxSize(),
                    contentPadding = PaddingValues(24.dp),
                ) {
                    items(state.entries, key = { it.id }) { entry ->
                        HistoryRow(entry)
                        HorizontalDivider(color = LocalIcoColors.current.stone)
                    }
                }
            }
        }
    }
}

@Composable
private fun HistoryRow(entry: ResolvedMoment) {
    val ico = LocalIcoColors.current
    Column(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 16.dp)
            .semantics {
                contentDescription =
                    "${entry.planLabel}, resolved ${TimeFormat.dayAndTime(entry.resolvedAt)}, " +
                    entry.method
            },
    ) {
        TabularLabel(TimeFormat.day(entry.resolvedAt).uppercase())
        Spacer(Modifier.height(8.dp))
        Text(entry.planLabel, style = MaterialTheme.typography.titleMedium, color = ico.ink)
        Spacer(Modifier.height(4.dp))
        StatusMarker(
            label = "${stringResource(R.string.resolved)} · ${TimeFormat.time(entry.resolvedAt)}",
            color = ico.resolved,
        )
        Spacer(Modifier.height(4.dp))
        Text(entry.method, style = MaterialTheme.typography.bodyLarge, color = ico.graphite)
    }
}

@Preview(showBackground = true)
@Composable
private fun HistoryPreview() {
    InCaseOfTheme {
        HistoryScreen(
            HistoryUiState.Content(
                listOf(
                    ResolvedMoment("1", "Evening check", Instant.now(), "You", "You confirmed"),
                    ResolvedMoment("2", "Journey home", Instant.now(), "Maya", "Maya verified contact"),
                ),
            ),
        )
    }
}
