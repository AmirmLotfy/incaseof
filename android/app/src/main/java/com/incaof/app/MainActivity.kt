package com.incaof.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.incaof.app.core.auth.AuthState
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.core.di.ViewModelFactory
import com.incaof.app.core.notifications.IcoNotifications
import com.incaof.app.core.notifications.PushRegistration
import com.incaof.app.feature.circle.CircleScreen
import com.incaof.app.feature.circle.CircleViewModel
import com.incaof.app.feature.history.HistoryScreen
import com.incaof.app.feature.history.HistoryViewModel
import com.incaof.app.feature.home.HomeScreen
import com.incaof.app.feature.home.HomeViewModel
import com.incaof.app.feature.onboarding.AuthViewModel
import com.incaof.app.feature.onboarding.SignInScreen
import com.incaof.app.feature.plans.PlanComposerScreen
import com.incaof.app.feature.plans.PlanDetailScreen
import com.incaof.app.feature.plans.PlansScreen
import com.incaof.app.feature.plans.PlansViewModel
import com.incaof.app.ui.Destination
import com.incaof.app.ui.IcoNavigationBar
import kotlinx.coroutines.launch

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
                var demoFactory by remember { mutableStateOf<ViewModelFactory?>(null) }
                var demoBusy by remember { mutableStateOf(false) }
                var demoError by remember { mutableStateOf<String?>(null) }
                val scope = rememberCoroutineScope()
                val notificationPermission =
                    rememberLauncherForActivityResult(
                        ActivityResultContracts.RequestPermission(),
                    ) { /* Delivery continues through the next rung when permission is denied. */ }

                LaunchedEffect(session) {
                    if (session is AuthState.SignedIn && BuildConfig.HAS_PUSH) {
                        if (
                            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                            !IcoNotifications.canNotify(this@MainActivity)
                        ) {
                            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                        }
                        PushRegistration.refresh(this@MainActivity, container.repository)
                    }
                }

                splash.setKeepOnScreenCondition { session is AuthState.Unknown }

                val activeDemoFactory = demoFactory
                if (activeDemoFactory != null) {
                    IcoApp(
                        factory = activeDemoFactory,
                        demoMode = true,
                        onExitDemo = { demoFactory = null },
                    )
                } else {
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
                                state = session,
                                onSignIn = auth::signIn,
                                onSignUp = auth::signUp,
                                onConfirm = auth::confirmSignUp,
                                onRequestReset = auth::requestPasswordReset,
                                onConfirmReset = auth::confirmPasswordReset,
                                onTryJudgeDemo = {
                                    demoBusy = true
                                    demoError = null
                                    scope.launch {
                                        container.startJudgeDemo().fold(
                                            onSuccess = { demoFactory = it },
                                            onFailure = {
                                                demoError = "The judge demo is unavailable. Try again in a moment."
                                            },
                                        )
                                        demoBusy = false
                                    }
                                },
                                error = demoError ?: error,
                                busy = busy || demoBusy,
                            )
                        }
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
private fun IcoApp(
    factory: ViewModelFactory,
    demoMode: Boolean = false,
    onExitDemo: () -> Unit = {},
) {
    val navController = rememberNavController()

    Scaffold(
        topBar = {
            if (demoMode) JudgeDemoBanner(onExitDemo)
        },
        bottomBar = { IcoNavigationBar(navController) },
    ) { insets ->
        NavHost(
            navController = navController,
            startDestination = Destination.HOME.route,
            modifier = Modifier.padding(insets),
        ) {
            composable(Destination.HOME.route) {
                val vm: HomeViewModel = viewModel(key = viewModelKey(demoMode, "home"), factory = factory)
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
                val vm: PlansViewModel = viewModel(key = viewModelKey(demoMode, "plans"), factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                val selected by vm.selected.collectAsStateWithLifecycle()
                val composer by vm.composer.collectAsStateWithLifecycle()
                val action by vm.action.collectAsStateWithLifecycle()
                var testingPlan by androidx.compose.runtime.remember {
                    androidx.compose.runtime.mutableStateOf<com.incaof.app.domain.Plan?>(null)
                }

                val drillPlan = testingPlan
                val plan = selected
                when {
                    composer.visible -> {
                        PlanComposerScreen(
                            state = composer,
                            onCompile = vm::compile,
                            onSave = vm::saveDraft,
                            onCancel = vm::cancelCreate,
                        )
                        androidx.activity.compose.BackHandler { vm.cancelCreate() }
                    }

                    drillPlan != null -> {
                        val drillVm =
                            androidx.compose.runtime.remember(drillPlan.id) {
                                factory.createDrillViewModel(drillPlan)
                            }
                        val drillState by drillVm.state.collectAsStateWithLifecycle()
                        com.incaof.app.feature.drill.DrillScreen(
                            state = drillState,
                            onFinish = { testingPlan = null },
                        )
                        androidx.activity.compose.BackHandler { testingPlan = null }
                    }

                    plan != null -> {
                        PlanDetailScreen(
                            plan = plan,
                            action = action,
                            onActivate = { vm.activate(plan.id) },
                            onPause = { vm.pause(plan.id) },
                            onResume = { vm.resume(plan.id) },
                            onTest = { testingPlan = plan },
                        )
                        androidx.activity.compose.BackHandler { vm.clearSelection() }
                    }

                    else -> {
                        PlansScreen(state = state, onSelect = vm::select, onCreate = vm::startCreate)
                    }
                }
            }

            composable(Destination.CIRCLE.route) {
                val vm: CircleViewModel = viewModel(key = viewModelKey(demoMode, "circle"), factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                val invite by vm.invite.collectAsStateWithLifecycle()
                CircleScreen(state = state, inviteState = invite, onInvite = vm::invite)
            }

            composable(Destination.HISTORY.route) {
                val vm: HistoryViewModel = viewModel(key = viewModelKey(demoMode, "history"), factory = factory)
                val state by vm.state.collectAsStateWithLifecycle()
                HistoryScreen(state = state)
            }
        }
    }
}

private fun viewModelKey(demoMode: Boolean, screen: String): String =
    "${if (demoMode) "demo" else "account"}-$screen"

@Composable
private fun JudgeDemoBanner(onExit: () -> Unit) {
    val ico = LocalIcoColors.current
    Surface(color = ico.signal) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Text("JUDGE DEMO", style = MaterialTheme.typography.labelMedium, color = ico.ink)
                Text(
                    "Synthetic tenant · safe delivery sink",
                    style = MaterialTheme.typography.bodySmall,
                    color = ico.ink,
                )
            }
            TextButton(onClick = onExit) { Text("Exit demo", color = ico.ink) }
        }
    }
}
