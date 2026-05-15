package com.incaseof.app.core.design

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = IndigoPrimary,
    onPrimary = NeutralWhite,
    primaryContainer = IndigoLight,
    onPrimaryContainer = NeutralWhite,
    secondary = CoralAccent,
    onSecondary = NeutralWhite,
    secondaryContainer = CoralLight,
    onSecondaryContainer = NeutralCharcoal,
    tertiary = SafetyGreen,
    onTertiary = NeutralWhite,
    tertiaryContainer = SafetyGreenLight,
    onTertiaryContainer = NeutralCharcoal,
    error = DangerRed,
    onError = NeutralWhite,
    errorContainer = DangerRedLight,
    onErrorContainer = NeutralCharcoal,
    background = NeutralOffWhite,
    onBackground = NeutralCharcoal,
    surface = NeutralWhite,
    onSurface = NeutralCharcoal,
    surfaceVariant = NeutralLightGray,
    onSurfaceVariant = NeutralDarkGray,
    outline = NeutralMediumGray,
    outlineVariant = NeutralLightGray
)

private val DarkColorScheme = darkColorScheme(
    primary = IndigoLight,
    onPrimary = NeutralWhite,
    primaryContainer = IndigoPrimary,
    onPrimaryContainer = NeutralWhite,
    secondary = CoralLight,
    onSecondary = NeutralBlack,
    secondaryContainer = CoralDark,
    onSecondaryContainer = NeutralWhite,
    tertiary = SafetyGreenLight,
    onTertiary = NeutralBlack,
    tertiaryContainer = SafetyGreenDark,
    onTertiaryContainer = NeutralWhite,
    error = DangerRedLight,
    onError = NeutralBlack,
    errorContainer = DangerRedDark,
    onErrorContainer = NeutralWhite,
    background = NeutralNearBlack,
    onBackground = NeutralWhite,
    surface = NeutralCharcoal,
    onSurface = NeutralWhite,
    surfaceVariant = NeutralCharcoal,
    onSurfaceVariant = NeutralMediumGray,
    outline = NeutralDarkGray,
    outlineVariant = NeutralCharcoal
)

@Composable
fun InCaseOfTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = InCaseOfTypography,
        shapes = InCaseOfShapes,
        content = content
    )
}
