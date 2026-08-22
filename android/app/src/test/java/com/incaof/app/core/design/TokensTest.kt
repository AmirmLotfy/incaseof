package com.incaof.app.core.design

import androidx.compose.ui.graphics.Color
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

/**
 * Guards the properties that the generator cannot enforce by itself.
 *
 * Tokens.kt is generated from packages/design-tokens/tokens.json, and CI fails on drift
 * between the two. What CI cannot catch is someone regenerating from a tokens.json that
 * has itself been changed in a way that breaks an accessibility rule. These assertions
 * encode the rules, so a bad palette change fails on Android too, not only on the web.
 */
class TokensTest {
    @Test
    fun `signal takes ink text, never white`() {
        // White on Signal Orange measures 3.52:1 and fails WCAG AA for normal text.
        // Ink on Signal Orange measures 4.98:1 and passes. This is not a taste call.
        assertEquals(Color(0xFF171A18), IcoOnColor.signal)
        assertNotEquals(Color(0xFFFFFFFF), IcoOnColor.signal)
    }

    @Test
    fun `light and dark palettes are actually different`() {
        assertNotEquals(IcoLightColors.background, IcoDarkColors.background)
        assertNotEquals(IcoLightColors.ink, IcoDarkColors.ink)
    }

    @Test
    fun `dark background is not pure black`() {
        assertNotEquals(Color(0xFF000000), IcoDarkColors.background)
    }

    @Test
    fun `every semantic colour is defined in both palettes`() {
        for (palette in listOf(IcoLightColors, IcoDarkColors)) {
            for (colour in listOf(
                palette.background,
                palette.surface,
                palette.ink,
                palette.graphite,
                palette.stone,
                palette.primary,
                palette.signal,
                palette.warning,
                palette.critical,
                palette.resolved,
            )) {
                assertNotEquals(Color.Unspecified, colour)
            }
        }
    }

    @Test
    fun `critical is distinct from signal`() {
        // A missed Moment is Signal Orange, not Brick. Missing means unresolved, not
        // emergency - collapsing the two would make the product shout at people.
        assertNotEquals(IcoLightColors.signal, IcoLightColors.critical)
        assertNotEquals(IcoDarkColors.signal, IcoDarkColors.critical)
    }
}
