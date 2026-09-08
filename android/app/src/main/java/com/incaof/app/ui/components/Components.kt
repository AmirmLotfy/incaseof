package com.incaof.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.incaof.app.core.design.IcoOnColor
import com.incaof.app.core.design.LocalIcoColors

/** Minimum touch target. Non-negotiable — see .claude/rules/android.md. */
private val MinTouchTarget = 48.dp

/**
 * OpenType tabular figures.
 *
 * Every digit occupies the same width, so a clock does not jitter as it counts. Set as
 * a raw feature tag because Compose exposes no typed constant for it.
 */
private const val TABULAR_FIGURES = "tnum"

/**
 * A clock time.
 *
 * Tabular figures, always. This product's core content is times, and digits that reflow as
 * they tick read as instability in exactly the surface that should feel steady.
 */
@Composable
fun MomentTime(text: String, modifier: Modifier = Modifier, color: Color = MaterialTheme.colorScheme.onBackground) {
    Text(
        text = text,
        modifier = modifier,
        color = color,
        style =
            MaterialTheme.typography.displayLarge.copy(
                fontFeatureSettings = TABULAR_FIGURES,
            ),
    )
}

/** A small monospaced-feeling label. Used for times inside lists. */
@Composable
fun TabularLabel(text: String, modifier: Modifier = Modifier, color: Color = LocalIcoColors.current.graphite) {
    Text(
        text = text,
        modifier = modifier,
        color = color,
        style =
            MaterialTheme.typography.labelSmall.copy(
                fontFeatureSettings = TABULAR_FIGURES,
            ),
    )
}

/**
 * A section heading with a rule under it.
 *
 * A rule rather than a card. Not every section is a card — that habit is what produces
 * bento-grid slop (DESIGN.md §7).
 */
@Composable
fun SectionHeading(text: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = LocalIcoColors.current.graphite,
            modifier = Modifier.semantics { heading() },
        )
        Spacer(Modifier.height(8.dp))
        HorizontalDivider(color = LocalIcoColors.current.stone)
    }
}

/**
 * The one big action on a screen.
 *
 * Height is 56dp rather than the 48dp floor: this is the control someone taps at 2am, half
 * awake, and the extra margin is the difference between reassurance and a mis-tap.
 */
@Composable
fun PrimaryAction(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    description: String? = null,
    enabled: Boolean = true,
    container: Color = MaterialTheme.colorScheme.primary,
    content: Color = IcoOnColor.primary,
) {
    val haptic = LocalHapticFeedback.current
    Button(
        onClick = {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
            onClick()
        },
        enabled = enabled,
        shape = RoundedCornerShape(14.dp),
        colors =
            ButtonDefaults.buttonColors(
                containerColor = container,
                contentColor = content,
            ),
        modifier =
            modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .then(
                    if (description != null) {
                        Modifier.semantics { contentDescription = description }
                    } else {
                        Modifier
                    },
                ),
    ) {
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

/** A quieter action. Still meets the 48dp floor. */
@Composable
fun SecondaryAction(label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    TextButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = MinTouchTarget),
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelLarge,
            color = LocalIcoColors.current.graphite,
        )
    }
}

/**
 * State, shown as a marker *and* a word.
 *
 * Never colour alone. A dot that means "unresolved" is invisible to a colour-blind user and
 * to a screen reader, so the word carries the meaning and the marker only reinforces it.
 */
@Composable
fun StatusMarker(label: String, color: Color, modifier: Modifier = Modifier, description: String? = null) {
    Row(
        modifier =
            modifier.semantics {
                contentDescription = description ?: label
            },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Box(
            Modifier
                .size(10.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(color)
                .clearAndSetSemantics { },
        )
        Text(
            text = label,
            style =
                MaterialTheme.typography.labelSmall.copy(
                    fontWeight = FontWeight.Medium,
                    letterSpacing = 0.08.sp,
                ),
            color = LocalIcoColors.current.ink,
        )
    }
}

/**
 * One rung of the escalation ladder.
 *
 * Rendered as a literal sequence rather than prose, because "who gets contacted and when"
 * is the thing a person most needs to be able to check at a glance.
 */
@Composable
fun LadderRung(time: String, action: String, modifier: Modifier = Modifier, emphasised: Boolean = false) {
    val ico = LocalIcoColors.current
    Row(
        modifier =
            modifier
                .fillMaxWidth()
                .heightIn(min = MinTouchTarget)
                .padding(vertical = 4.dp)
                .semantics { contentDescription = "$time, $action" },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TabularLabel(
            text = time,
            modifier = Modifier.width(64.dp),
            color = if (emphasised) ico.ink else ico.graphite,
        )
        Spacer(Modifier.width(12.dp))
        Text(
            text = action,
            style = MaterialTheme.typography.bodyLarge,
            color = if (emphasised) ico.ink else ico.graphite,
        )
    }
}

/** Full-width message for empty and error states. Says what happened, plainly. */
@Composable
fun Notice(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text,
        modifier = modifier.fillMaxWidth().padding(vertical = 24.dp),
        style = MaterialTheme.typography.bodyLarge,
        color = LocalIcoColors.current.graphite,
        textAlign = TextAlign.Start,
    )
}
