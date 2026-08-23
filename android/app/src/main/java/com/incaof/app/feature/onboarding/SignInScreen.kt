package com.incaof.app.feature.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.ui.components.PrimaryAction

/**
 * Sign in.
 *
 * Deliberately plain. Authentication is not where this product is interesting, and the
 * build contract is explicit that hackathon success must not depend on elaborate auth.
 *
 * The email field uses `rememberSaveable` so a rotation or a process death mid-typing does
 * not wipe what somebody entered.
 */
@Composable
fun SignInScreen(onSignIn: (String, String) -> Unit, error: String?, busy: Boolean, modifier: Modifier = Modifier) {
    var email by rememberSaveable { mutableStateOf("") }
    // Passwords are intentionally NOT saved across process death: restoring one from a
    // saved-state bundle writes it to disk.
    var password by remember { mutableStateOf("") }
    val ico = LocalIcoColors.current

    Column(
        modifier =
            modifier
                .fillMaxSize()
                .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            stringResource(R.string.app_name),
            style = MaterialTheme.typography.headlineMedium,
            color = ico.ink,
            modifier = Modifier.semantics { heading() },
        )
        Spacer(Modifier.height(4.dp))
        Text(stringResource(R.string.tagline), style = MaterialTheme.typography.bodyLarge, color = ico.graphite)

        Spacer(Modifier.height(48.dp))

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text(stringResource(R.string.email)) },
            singleLine = true,
            keyboardOptions =
                KeyboardOptions(
                    keyboardType = KeyboardType.Email,
                    imeAction = ImeAction.Next,
                ),
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(Modifier.height(12.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text(stringResource(R.string.password)) },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions =
                KeyboardOptions(
                    keyboardType = KeyboardType.Password,
                    imeAction = ImeAction.Done,
                ),
            modifier = Modifier.fillMaxWidth(),
        )

        error?.let {
            Spacer(Modifier.height(12.dp))
            Text(
                it,
                style = MaterialTheme.typography.bodyLarge,
                color = ico.critical,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Assertive },
            )
        }

        Spacer(Modifier.height(24.dp))
        PrimaryAction(
            label = stringResource(R.string.sign_in),
            onClick = { onSignIn(email.trim(), password) },
            enabled = !busy && email.isNotBlank() && password.isNotBlank(),
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SignInPreview() {
    InCaseOfTheme { SignInScreen(onSignIn = { _, _ -> }, error = null, busy = false) }
}
