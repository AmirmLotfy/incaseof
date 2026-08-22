package com.incaof.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors

/**
 * Phase 0 scaffold.
 *
 * Real screens are built in Phase 3, after docs/design/REFERENCES.md holds locked visual
 * references. This exists to prove the build, the theme and the generated tokens work.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            InCaseOfTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { insets ->
                    ScaffoldNotice(modifier = Modifier.padding(insets))
                }
            }
        }
    }
}

@Composable
private fun ScaffoldNotice(modifier: Modifier = Modifier) {
    val ico = LocalIcoColors.current
    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = "In Case of",
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        Text(
            text = "Someone notices.",
            style = MaterialTheme.typography.bodyLarge,
            color = ico.graphite,
        )
        Text(
            text = "Phase 0 · scaffold only",
            style = MaterialTheme.typography.labelSmall,
            color = ico.graphite,
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun ScaffoldNoticePreview() {
    InCaseOfTheme { ScaffoldNotice() }
}
