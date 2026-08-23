package com.incaof.app.feature.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaof.app.data.ConfirmSource
import com.incaof.app.data.IcoRepository
import com.incaof.app.domain.Moment
import com.incaof.app.domain.Plan
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Home.
 *
 * All state is derived from the backend and re-read on entry. Nothing about an Alert is
 * decided or cached as truth here, so process death costs a reload and nothing else —
 * which is the behaviour the Alert-survives-process-death requirement actually needs.
 */
class HomeViewModel(
    private val repository: IcoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow<HomeUiState>(HomeUiState.Loading)
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { current ->
                if (current is HomeUiState.Content) current.copy(refreshing = true) else current
            }
            val moment = repository.nextMoment()
            val plans = repository.plans()

            _state.value =
                moment.fold(
                    onSuccess = { next ->
                        HomeUiState.Content(
                            moment = next,
                            activePlan = plans.getOrNull()?.firstOrNull { it.active },
                        )
                    },
                    onFailure = { HomeUiState.Failed(it.userMessage()) },
                )
        }
    }

    /**
     * "I'm okay."
     *
     * The key is derived from the Moment, so a double tap, or a retry after the first
     * attempt appeared to fail, confirms the same Moment once.
     */
    fun confirm() {
        val content = _state.value as? HomeUiState.Content ?: return
        val moment = content.moment ?: return

        viewModelScope.launch {
            _state.value = content.copy(submitting = true, error = null)
            repository
                .confirmMoment(
                    momentId = moment.id,
                    idempotencyKey = "confirm-${moment.id}",
                    source = ConfirmSource.APP,
                ).fold(
                    onSuccess = { refresh() },
                    onFailure = { error ->
                        // Stay on the screen with the action still available. Someone who was
                        // not heard needs another way to be heard, not an error page.
                        _state.value = content.copy(submitting = false, error = error.userMessage())
                    },
                )
        }
    }

    fun extend(seconds: Int) {
        val content = _state.value as? HomeUiState.Content ?: return
        val moment = content.moment ?: return

        viewModelScope.launch {
            _state.value = content.copy(submitting = true, error = null)
            repository.extendMoment(moment.id, seconds).fold(
                onSuccess = { refresh() },
                onFailure = { error ->
                    _state.value = content.copy(submitting = false, error = error.userMessage())
                },
            )
        }
    }
}

sealed interface HomeUiState {
    data object Loading : HomeUiState

    data class Content(
        val moment: Moment?,
        val activePlan: Plan?,
        val submitting: Boolean = false,
        val refreshing: Boolean = false,
        val error: String? = null,
    ) : HomeUiState {
        /** True when In Case of is waiting on this person right now. */
        val needsAction: Boolean get() = moment?.isWaitingOnMe == true
    }

    data class Failed(
        val message: String,
    ) : HomeUiState
}

/**
 * Errors, in the product's voice.
 *
 * Never a stack trace, never a status code, and never speculation about what went wrong
 * elsewhere. What the person needs is what to do next.
 */
internal fun Throwable.userMessage(): String =
    when (this) {
        is java.net.UnknownHostException, is java.net.SocketTimeoutException -> {
            "Couldn't reach In Case of. Your plan is still running."
        }

        else -> {
            "Something went wrong. Try again."
        }
    }
