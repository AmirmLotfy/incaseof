package com.incaseof.app.features.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.incaseof.app.core.preferences.AppPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val appPreferences: AppPreferences
) : ViewModel() {

    private val _currentPage = MutableStateFlow(0)
    val currentPage = _currentPage.asStateFlow()

    val totalPages = 3

    fun nextPage() {
        if (_currentPage.value < totalPages - 1) {
            _currentPage.value += 1
        }
    }

    fun previousPage() {
        if (_currentPage.value > 0) {
            _currentPage.value -= 1
        }
    }

    fun setPage(page: Int) {
        _currentPage.value = page.coerceIn(0, totalPages - 1)
    }

    fun completeOnboarding() {
        viewModelScope.launch {
            appPreferences.setOnboardingCompleted()
        }
    }
}
