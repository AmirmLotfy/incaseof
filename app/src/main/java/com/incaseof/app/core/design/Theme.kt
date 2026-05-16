package com.incaseof.app.core.design

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = BrandInk,
    onPrimary = BrandIcy,
    primaryContainer = BrandCyan,
    onPrimaryContainer = BrandInk,
    secondary = BrandViolet,
    onSecondary = NeutralWhite,
    secondaryContainer = BrandCyan,
    onSecondaryContainer = BrandInk,
    tertiary = SafetyGreen,
    onTertiary = NeutralWhite,
    tertiaryContainer = SafetyGreenLight,
    onTertiaryContainer = BrandInk,
    error = DangerRed,
    onError = NeutralWhite,
    errorContainer = DangerRedLight,
    onErrorContainer = BrandInk,
    background = BrandIcy,
    onBackground = BrandInk,
    surface = NeutralWhite,
    onSurface = BrandInk,
    surfaceVariant = NeutralLightGray,
    onSurfaceVariant = NeutralDarkGray,
    outline = NeutralMediumGray,
    outlineVariant = NeutralLightGray
)

private val DarkColorScheme = darkColorScheme(
    primary = BrandIcy,
    onPrimary = BrandInk,
    primaryContainer = BrandCyan,
    onPrimaryContainer = BrandInk,
    secondary = BrandViolet,
    onSecondary = NeutralWhite,
    secondaryContainer = BrandCyan,
    onSecondaryContainer = BrandInk,
    tertiary = SafetyGreenLight,
    onTertiary = BrandInk,
    tertiaryContainer = SafetyGreen,
    onTertiaryContainer = NeutralWhite,
    error = DangerRedLight,
    onError = BrandInk,
    errorContainer = DangerRed,
    onErrorContainer = NeutralWhite,
    background = BrandInk,
    onBackground = BrandIcy,
    surface = NeutralNearBlack,
    onSurface = BrandIcy,
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
