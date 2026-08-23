package com.incaof.app.ui

import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState
import com.incaof.app.R
import com.incaof.app.core.design.LocalIcoColors

/**
 * Four destinations. Build contract §52.
 *
 * There is no "AI" tab and no "Chat" tab, by design: the product surface never advertises
 * how it works internally.
 */
enum class Destination(
    val route: String,
    val labelRes: Int,
    val icon: ImageVector,
) {
    HOME("home", R.string.nav_home, Icons.home),
    PLANS("plans", R.string.nav_plans, Icons.plans),
    CIRCLE("circle", R.string.nav_circle, Icons.circle),
    HISTORY("history", R.string.nav_history, Icons.history),
}

@Composable
fun IcoNavigationBar(navController: NavHostController) {
    val ico = LocalIcoColors.current
    val backStack by navController.currentBackStackEntryAsState()
    val current = backStack?.destination

    NavigationBar(containerColor = ico.surface) {
        Destination.entries.forEach { destination ->
            val selected = current?.hierarchy?.any { it.route == destination.route } == true
            val label = stringResource(destination.labelRes)
            NavigationBarItem(
                selected = selected,
                onClick = {
                    navController.navigate(destination.route) {
                        // Single top with state restore: returning to Home should show the
                        // Home you left, not a fresh one, and the back stack should not
                        // accumulate a tab per tap.
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = { Icon(destination.icon, contentDescription = null) },
                // The label is always shown. An icon-only tab bar conveys meaning by shape
                // alone, which is exactly what the accessibility floor forbids.
                label = { Text(label) },
                alwaysShowLabel = true,
                colors =
                    NavigationBarItemDefaults.colors(
                        selectedIconColor = ico.primary,
                        selectedTextColor = ico.ink,
                        unselectedIconColor = ico.graphite,
                        unselectedTextColor = ico.graphite,
                        indicatorColor = ico.background,
                    ),
            )
        }
    }
}
