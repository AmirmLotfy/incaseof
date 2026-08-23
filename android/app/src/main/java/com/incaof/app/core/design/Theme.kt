package com.incaof.app.core.design

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat

/**
 * Semantic colours that Material3's ColorScheme has no slot for.
 *
 * [signal] is unresolved-attention and [resolved] is a closed loop. Neither maps onto
 * Material's error/primary vocabulary without lying about what they mean, so they travel
 * alongside it.
 */
val LocalIcoColors = staticCompositionLocalOf { IcoLightColors }

/**
 * Type scale from docs/design/DESIGN.md.
 *
 * Times use tabular figures wherever the platform supports them: this product's core
 * content is clock times, and digits that reflow as they tick read as unstable.
 */
private val IcoTypography =
    Typography(
        displayLarge = TextStyle(fontSize = 42.sp, fontWeight = FontWeight.Medium),
        headlineLarge = TextStyle(fontSize = 30.sp, fontWeight = FontWeight.Medium),
        headlineMedium = TextStyle(fontSize = 26.sp, fontWeight = FontWeight.SemiBold),
        titleMedium = TextStyle(fontSize = 19.sp, fontWeight = FontWeight.Medium),
        bodyLarge = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Normal),
        labelLarge = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Medium),
        labelSmall = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Medium),
    )

@Composable
fun InCaseOfTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val ico = if (darkTheme) IcoDarkColors else IcoLightColors

    // Deliberately NOT dynamic colour. A safety surface must look the same on every
    // device: "orange means unresolved" cannot be true only on some wallpapers.
    val scheme =
        if (darkTheme) {
            darkColorScheme(
                primary = ico.primary,
                onPrimary = IcoOnColor.primary,
                background = ico.background,
                onBackground = ico.ink,
                surface = ico.surface,
                onSurface = ico.ink,
                surfaceVariant = ico.raised,
                onSurfaceVariant = ico.graphite,
                error = ico.critical,
                onError = IcoOnColor.critical,
                outline = ico.stone,
            )
        } else {
            lightColorScheme(
                primary = ico.primary,
                onPrimary = IcoOnColor.primary,
                background = ico.background,
                onBackground = ico.ink,
                surface = ico.surface,
                onSurface = ico.ink,
                onSurfaceVariant = ico.graphite,
                error = ico.critical,
                onError = IcoOnColor.critical,
                outline = ico.stone,
            )
        }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            WindowCompat
                .getInsetsController(window, view)
                .isAppearanceLightStatusBars = !darkTheme
        }
    }

    CompositionLocalProvider(LocalIcoColors provides ico) {
        MaterialTheme(
            colorScheme = scheme,
            typography = IcoTypography,
            content = content,
        )
    }
}

/** Style for clock times. Never let digits reflow as they change. */
@Composable
fun momentTimeStyle(color: Color = MaterialTheme.colorScheme.onBackground): TextStyle =
    MaterialTheme.typography.displayLarge.copy(
        color = color,
        textAlign = TextAlign.Start,
    )
