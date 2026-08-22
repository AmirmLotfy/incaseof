// GENERATED FILE - edit packages/design-tokens/tokens.json instead.
package com.incaof.app.core.design

import androidx.compose.ui.graphics.Color

/**
 * In Case of colour tokens.
 *
 * Signal takes Ink text, never white: white on Signal Orange measures 3.52:1 and fails
 * WCAG AA. Stone is a decorative rule only and must never carry state.
 */
data class IcoColors(
    val background: Color = Color.Unspecified,
    val surface: Color = Color.Unspecified,
    val ink: Color = Color.Unspecified,
    val graphite: Color = Color.Unspecified,
    val stone: Color = Color.Unspecified,
    val primary: Color = Color.Unspecified,
    val signal: Color = Color.Unspecified,
    val warning: Color = Color.Unspecified,
    val critical: Color = Color.Unspecified,
    val resolved: Color = Color.Unspecified,
    val raised: Color = Color.Unspecified,
)

val IcoLightColors = IcoColors(
    background = Color(0xFFF6F5F0),
    surface = Color(0xFFFFFDF8),
    ink = Color(0xFF171A18),
    graphite = Color(0xFF626660),
    stone = Color(0xFFE4E4DE),
    primary = Color(0xFF205C47),
    signal = Color(0xFFE85B2A),
    warning = Color(0xFFD99A29),
    critical = Color(0xFFB44438),
    resolved = Color(0xFF39705A),
)

val IcoDarkColors = IcoColors(
    background = Color(0xFF101310),
    surface = Color(0xFF181C19),
    raised = Color(0xFF212622),
    ink = Color(0xFFF2F1EB),
    graphite = Color(0xFFA9AEA9),
    stone = Color(0xFF343934),
    primary = Color(0xFF8FC3AB),
    signal = Color(0xFFFF8055),
    warning = Color(0xFFE3B151),
    critical = Color(0xFFF29A90),
    resolved = Color(0xFF8FC3AB),
)

object IcoOnColor {
    val primary = Color(0xFFFFFFFF)
    val signal = Color(0xFF171A18)
    val warning = Color(0xFF171A18)
    val critical = Color(0xFFFFFFFF)
    val resolved = Color(0xFFFFFFFF)
}

object IcoShape {
    const val heroPanel = 20
    const val surface = 14
    const val input = 12
    const val button = 14
    const val bottomSheet = 24
    const val chip = 8
}
