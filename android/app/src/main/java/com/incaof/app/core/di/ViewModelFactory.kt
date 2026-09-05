package com.incaof.app.core.di

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.incaof.app.core.auth.AuthRepository
import com.incaof.app.data.IcoRepository
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
    private val auth: AuthRepository,
    private val repository: IcoRepository,
) : ViewModelProvider.Factory {
    constructor(container: AppContainer) : this(container.auth, container.repository)

    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        when {
            modelClass.isAssignableFrom(HomeViewModel::class.java) -> {
                HomeViewModel(repository)
            }

            modelClass.isAssignableFrom(PlansViewModel::class.java) -> {
                PlansViewModel(repository)
            }

            modelClass.isAssignableFrom(CircleViewModel::class.java) -> {
                CircleViewModel(repository)
            }

            modelClass.isAssignableFrom(HistoryViewModel::class.java) -> {
                HistoryViewModel(repository)
            }

            modelClass.isAssignableFrom(AuthViewModel::class.java) -> {
                AuthViewModel(auth)
            }

            else -> {
                error("Unknown view model ${modelClass.name}")
            }
        } as T

    fun createDrillViewModel(plan: com.incaof.app.domain.Plan): com.incaof.app.feature.drill.DrillViewModel =
        com.incaof.app.feature.drill
            .DrillViewModel(repository, plan)
}
