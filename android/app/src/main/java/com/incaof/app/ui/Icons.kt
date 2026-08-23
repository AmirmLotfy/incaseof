package com.incaof.app.ui

import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Person
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.material.icons.Icons as MaterialIcons

/**
 * Navigation icons.
 *
 * Plain Material glyphs. No sparkles, no robots, no brains, no magic wands — the anti-slop
 * list is not decoration advice, it is what keeps this from reading as an AI product.
 */
object Icons {
    val home: ImageVector = MaterialIcons.Filled.Home
    val plans: ImageVector = MaterialIcons.Filled.List
    val circle: ImageVector = MaterialIcons.Filled.Person
    val history: ImageVector = MaterialIcons.Filled.DateRange
}
