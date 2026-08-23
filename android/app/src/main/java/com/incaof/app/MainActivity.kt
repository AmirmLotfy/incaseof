package com.incaof.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.incaof.app.core.auth.AuthState
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.di.ViewModelFactory
import com.incaof.app.feature.circle.CircleScreen
import com.incaof.app.feature.circle.CircleViewModel
import com.incaof.app.feature.history.HistoryScreen
import com.incaof.app.feature.history.HistoryViewModel
import com.incaof.app.feature.home.HomeScreen
import com.incaof.app.feature.home.HomeViewModel
import com.incaof.app.feature.onboarding.AuthViewModel
import com.incaof.app.feature.onboarding.SignInScreen
import com.incaof.app.feature.plans.PlanDetailScreen
import com.incaof.app.feature.plans.PlansScreen
import com.incaof.app.feature.plans.PlansViewModel
import com.incaof.app.ui.Destination
import com.incaof.app.ui.IcoNavigationBar

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // Held until the auth state is known, so the app never flashes a sign-in form at
        // somebody who is already signed in.
        val splash = installSplashScreen()
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        val container = (application as IcoApplication).container
        val factory = ViewModelFactory(container)

        setContent {
            InCaseOfTheme {
                val auth: AuthViewModel = viewModel(factory = factory)
                val session by auth.session.collectAsStateWithLifecycle()

                splash.setKeepOnScreenCondition { session is AuthState.Unknown }

                when (session) {
                    AuthState.Unknown -> {
                        Loading()
                    }

                    is AuthState.SignedIn -> {
                        IcoApp(factory)
                    }

                    else -> {
                        val error by auth.error.collectAsStateWithLifecycle()
                        val busy by auth.busy.collectAsStateWithLifecycle()
                        SignInScreen(
                            onSignIn = auth::signIn,
                            error = error,
                            busy = busy,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Loading() {
    Column(
        Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) { CircularProgressIndicator() }
}

@Composable
private fun IcoApp(factory: ViewModelFactory) {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = { IcoNavigationBar(navController) },
    ) { insets ->
        NavHost(
            navController = navController,
            startDestination = Destination.HOME.route,
            modifier = Modifier.padding(insets),
        ) {
            composable(Destination.HOME.route) {
                val vm: HomeViewModel = viewModel(factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                HomeScreen(
                    state = state,
                    onConfirm = vm::confirm,
                    onExtend = vm::extend,
                    onNeedSomeone = { navController.navigate(Destination.CIRCLE.route) },
                    onRetry = vm::refresh,
                )
            }

            composable(Destination.PLANS.route) {
                val vm: PlansViewModel = viewModel(factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                val selected by vm.selected.collectAsStateWithLifecycle()

                val plan = selected
                if (plan == null) {
                    PlansScreen(state = state, onSelect = vm::select)
                } else {
                    PlanDetailScreen(plan = plan, onTest = {})
                    androidx.activity.compose.BackHandler { vm.clearSelection() }
                }
            }

            composable(Destination.CIRCLE.route) {
                val vm: CircleViewModel = viewModel(factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                CircleScreen(state = state)
            }

            composable(Destination.HISTORY.route) {
                val vm: HistoryViewModel = viewModel(factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                HistoryScreen(state = state)
            }
        }
    }
}
