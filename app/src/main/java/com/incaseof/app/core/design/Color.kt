package com.incaseof.app.core.design

import androidx.compose.ui.graphics.Color

// Brand Colors (Reconciled with Marketing Website)
val BrandIcy = Color(0xFFF4FAFF)
val BrandInk = Color(0xFF09051F)
val BrandCyan = Color(0xFF62E8FF)
val BrandViolet = Color(0xFF8B5CFF)
val BrandCoral = Color(0xFFFF7A5C)

// Neutrals
val NeutralWhite = Color(0xFFFFFFFF)
val NeutralLightGray = Color(0xFFE8E8EE)
val NeutralMediumGray = Color(0xFFB0B0C0)
val NeutralDarkGray = Color(0xFF6B6B80)
val NeutralCharcoal = Color(0xFF2A2A3C)
val NeutralNearBlack = Color(0xFF121220)

// Semantic colors
val DangerRed = Color(0xFFDC2626)
val DangerRedLight = Color(0xFFF87171)

val SafetyGreen = Color(0xFF4CAF82)
val SafetyGreenLight = Color(0xFF6FCF9E)
val SafetyGreenDark = Color(0xFF2E8B60)

val AmberWarning = Color(0xFFFFA726) // Added back for compatibility
val AmberWarningLight = Color(0xFFFFCC02)
val AmberWarningDark = Color(0xFFE08F00)

// Gradients (as pairs for Brush.linearGradient)
val GradientPrimary = listOf(BrandCyan, BrandViolet)
val GradientUrgent = listOf(BrandCoral, DangerRedLight)
val GradientDark = listOf(NeutralNearBlack, NeutralCharcoal)

// Glass
val GlassWhite = Color(0x1AFFFFFF)
val GlassDark = Color(0x1A000000)
val GlassBorder = Color(0x33FFFFFF)

// Aliases for compatibility with existing UI
val IndigoDeep = BrandInk
val IndigoPrimary = BrandViolet
val IndigoLight = BrandCyan
val IndigoSurface = NeutralCharcoal

val CoralAccent = BrandCoral
val CoralLight = BrandCoral
val CoralDark = DangerRed

val NeutralOffWhite = BrandIcy
val NeutralBlack = NeutralNearBlack


