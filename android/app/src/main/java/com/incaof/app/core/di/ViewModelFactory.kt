package com.incaof.app.core.di

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.incaof.app.feature.circle.CircleViewModel
import com.incaof.app.feature.history.HistoryViewModel
import com.incaof.app.feature.home.HomeViewModel
import com.incaof.app.feature.onboarding.AuthViewModel
import com.incaof.app.feature.plans.PlansViewModel

/**
 * View models, constructed by hand.
 *
 * The alternative is a code generator and a compiler plugin for what is, here, five `when`
 * branches. When this stops fitting on a screen, that is the signal to reach for Hilt —
 * not before.
 */
class ViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        when {
            modelClass.isAssignableFrom(HomeViewModel::class.java) -> {
                HomeViewModel(container.repository)
            }

            modelClass.isAssignableFrom(PlansViewModel::class.java) -> {
                PlansViewModel(container.repository)
            }

            modelClass.isAssignableFrom(CircleViewModel::class.java) -> {
                CircleViewModel(container.repository)
            }

            modelClass.isAssignableFrom(HistoryViewModel::class.java) -> {
                HistoryViewModel(container.repository)
            }

            modelClass.isAssignableFrom(AuthViewModel::class.java) -> {
                AuthViewModel(container.auth)
            }

            else -> {
                error("Unknown view model ${modelClass.name}")
            }
        } as T
}
