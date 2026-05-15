package com.incaseof.app.navigation

import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.incaseof.app.features.about.AboutScreen
import com.incaseof.app.features.actionreview.ActionReviewScreen
import com.incaseof.app.features.casedetail.CaseDetailScreen
import com.incaseof.app.features.compiling.CompilingScreen
import com.incaseof.app.features.contactpicker.ContactPickerScreen
import com.incaseof.app.features.createcase.CreateCaseScreen
import com.incaseof.app.features.emergencylog.EmergencyLogScreen
import com.incaseof.app.features.home.HomeScreen
import com.incaseof.app.features.onboarding.OnboardingScreen
import com.incaseof.app.features.review.SafetyReviewScreen
import com.incaseof.app.features.settings.SettingsScreen
import com.incaseof.app.features.simulation.SimulationScreen
import com.incaseof.app.features.splash.SplashScreen

@Composable
fun NavGraph(
    navController: NavHostController,
    modifier: Modifier = Modifier,
    startDestination: String = Routes.Splash.route
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier,
        enterTransition = {
            slideInHorizontally(initialOffsetX = { it }, animationSpec = tween(300)) +
                fadeIn(animationSpec = tween(300))
        },
        exitTransition = {
            slideOutHorizontally(targetOffsetX = { -it / 3 }, animationSpec = tween(300)) +
                fadeOut(animationSpec = tween(200))
        },
        popEnterTransition = {
            slideInHorizontally(initialOffsetX = { -it / 3 }, animationSpec = tween(300)) +
                fadeIn(animationSpec = tween(300))
        },
        popExitTransition = {
            slideOutHorizontally(targetOffsetX = { it }, animationSpec = tween(300)) +
                fadeOut(animationSpec = tween(200))
        }
    ) {
        composable(Routes.Splash.route) {
            SplashScreen(
                onNavigateToOnboarding = {
                    navController.navigate(Routes.Onboarding.route) {
                        popUpTo(Routes.Splash.route) { inclusive = true }
                    }
                },
                onNavigateToHome = {
                    navController.navigate(Routes.Home.route) {
                        popUpTo(Routes.Splash.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.Onboarding.route) {
            OnboardingScreen(
                onComplete = {
                    navController.navigate(Routes.Home.route) {
                        popUpTo(Routes.Onboarding.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.Home.route) {
            HomeScreen(
                onCreateCase = { navController.navigate(Routes.CreateCase.route) },
                onCaseClick = { caseId -> navController.navigate(Routes.CaseDetail.createRoute(caseId)) },
                onViewLog = { navController.navigate(Routes.EmergencyLog.route) },
                onSettings = { navController.navigate(Routes.Settings.route) },
                onAbout = { navController.navigate(Routes.About.route) }
            )
        }

        composable(Routes.CreateCase.route) {
            CreateCaseScreen(
                onCompile = { condition, action ->
                    navController.navigate(Routes.Compiling.createRoute(condition, action))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.Compiling.route,
            arguments = listOf(
                navArgument("condition") { type = NavType.StringType },
                navArgument("action") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val condition = java.net.URLDecoder.decode(
                backStackEntry.arguments?.getString("condition") ?: "", "UTF-8"
            )
            val action = java.net.URLDecoder.decode(
                backStackEntry.arguments?.getString("action") ?: "", "UTF-8"
            )
            CompilingScreen(
                condition = condition,
                action = action,
                onComplete = { caseId ->
                    navController.navigate(Routes.Review.createRoute(caseId)) {
                        popUpTo(Routes.CreateCase.route) { inclusive = true }
                    }
                },
                onError = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.Review.route,
            arguments = listOf(navArgument("caseId") { type = NavType.StringType })
        ) {
            SafetyReviewScreen(
                onActivate = { caseId ->
                    navController.navigate(Routes.CaseDetail.createRoute(caseId)) {
                        popUpTo(Routes.Home.route)
                    }
                },
                onPickContact = { caseId ->
                    navController.navigate(Routes.ContactPicker.createRoute(caseId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.ContactPicker.route,
            arguments = listOf(navArgument("caseId") { type = NavType.StringType })
        ) {
            ContactPickerScreen(
                onContactSelected = { navController.popBackStack() },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.CaseDetail.route,
            arguments = listOf(navArgument("caseId") { type = NavType.StringType })
        ) {
            CaseDetailScreen(
                onSimulate = { caseId ->
                    navController.navigate(Routes.Simulation.createRoute(caseId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.Simulation.route,
            arguments = listOf(navArgument("caseId") { type = NavType.StringType })
        ) {
            SimulationScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.EmergencyLog.route) {
            EmergencyLogScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.Settings.route) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onAbout = { navController.navigate(Routes.About.route) }
            )
        }

        composable(Routes.About.route) {
            AboutScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.ActionReview.route,
            arguments = listOf(navArgument("caseId") { type = NavType.StringType })
        ) {
            ActionReviewScreen(
                onBack = { navController.popBackStack() },
                onDone = {
                    navController.navigate(Routes.Home.route) {
                        popUpTo(Routes.Home.route) { inclusive = true }
                    }
                }
            )
        }
    }
}
