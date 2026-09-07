package com.incaof.app.feature.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.incaof.app.R
import com.incaof.app.core.auth.AuthState
import com.incaof.app.core.design.InCaseOfTheme
import com.incaof.app.core.design.LocalIcoColors
import com.incaof.app.ui.components.PrimaryAction

private enum class AuthMode {
    SIGN_IN,
    SIGN_UP,
    CONFIRM_SIGN_UP,
    RESET_REQUEST,
    RESET_CONFIRM,
}

/** Complete Cognito self-service entry: sign-in, sign-up, confirmation and recovery. */
@Composable
fun SignInScreen(
    state: AuthState,
    onSignIn: (String, String) -> Unit,
    onSignUp: (String, String) -> Unit,
    onConfirm: (String, String) -> Unit,
    onRequestReset: (String) -> Unit,
    onConfirmReset: (String, String, String) -> Unit,
    onTryJudgeDemo: () -> Unit,
    error: String?,
    busy: Boolean,
    modifier: Modifier = Modifier,
) {
    var mode by rememberSaveable { mutableStateOf(AuthMode.SIGN_IN) }
    var email by rememberSaveable { mutableStateOf("") }
    var code by rememberSaveable { mutableStateOf("") }
    // Passwords are intentionally not saveable: they never enter a saved-state bundle.
    var password by remember { mutableStateOf("") }
    val ico = LocalIcoColors.current

    LaunchedEffect(state) {
        if (state is AuthState.NeedsConfirmation) {
            email = state.email
            mode = AuthMode.CONFIRM_SIGN_UP
        }
    }

    Column(
        modifier = modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Row(
            modifier =
                Modifier.clearAndSetSemantics {
                    contentDescription = "ICO"
                },
        ) {
            Text("I", style = MaterialTheme.typography.headlineLarge, color = ico.ink)
            Text("C", style = MaterialTheme.typography.headlineLarge, color = ico.signal)
            Text("O", style = MaterialTheme.typography.headlineLarge, color = ico.ink)
        }
        Spacer(Modifier.height(12.dp))
        Text(
            stringResource(R.string.app_name),
            style = MaterialTheme.typography.headlineMedium,
            color = ico.ink,
            modifier = Modifier.semantics { heading() },
        )
        Spacer(Modifier.height(4.dp))
        Text(
            when (mode) {
                AuthMode.SIGN_IN -> stringResource(R.string.tagline)
                AuthMode.SIGN_UP -> "Create your private plan space"
                AuthMode.CONFIRM_SIGN_UP -> "Confirm the code sent to your email"
                AuthMode.RESET_REQUEST -> "Request a password reset code"
                AuthMode.RESET_CONFIRM -> "Choose a new password"
            },
            style = MaterialTheme.typography.bodyLarge,
            color = ico.graphite,
        )
        Spacer(Modifier.height(36.dp))

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text(stringResource(R.string.email)) },
            singleLine = true,
            enabled = mode != AuthMode.CONFIRM_SIGN_UP,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
            modifier = Modifier.fillMaxWidth(),
        )

        if (mode in setOf(AuthMode.SIGN_IN, AuthMode.SIGN_UP, AuthMode.RESET_CONFIRM)) {
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = {
                    Text(
                        if (mode ==
                            AuthMode.RESET_CONFIRM
                        ) {
                            "New password"
                        } else {
                            stringResource(R.string.password)
                        },
                    )
                },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                modifier = Modifier.fillMaxWidth(),
            )
        }

        if (mode == AuthMode.CONFIRM_SIGN_UP || mode == AuthMode.RESET_CONFIRM) {
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = code,
                onValueChange = { code = it.filter(Char::isDigit) },
                label = { Text("Confirmation code") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Done),
                modifier = Modifier.fillMaxWidth(),
            )
        }

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
            label =
                when (mode) {
                    AuthMode.SIGN_IN -> "Sign in"
                    AuthMode.SIGN_UP -> "Create account"
                    AuthMode.CONFIRM_SIGN_UP -> "Confirm account"
                    AuthMode.RESET_REQUEST -> "Send reset code"
                    AuthMode.RESET_CONFIRM -> "Set new password"
                },
            onClick = {
                val cleanEmail = email.trim()
                when (mode) {
                    AuthMode.SIGN_IN -> {
                        onSignIn(cleanEmail, password)
                    }

                    AuthMode.SIGN_UP -> {
                        onSignUp(cleanEmail, password)
                    }

                    AuthMode.CONFIRM_SIGN_UP -> {
                        onConfirm(cleanEmail, code)
                    }

                    AuthMode.RESET_REQUEST -> {
                        onRequestReset(cleanEmail)
                        mode = AuthMode.RESET_CONFIRM
                    }

                    AuthMode.RESET_CONFIRM -> {
                        onConfirmReset(cleanEmail, code, password)
                    }
                }
            },
            enabled =
                !busy && email.isNotBlank() &&
                    when (mode) {
                        AuthMode.SIGN_IN, AuthMode.SIGN_UP -> password.length >= 12
                        AuthMode.CONFIRM_SIGN_UP -> code.length >= 6
                        AuthMode.RESET_REQUEST -> true
                        AuthMode.RESET_CONFIRM -> code.length >= 6 && password.length >= 12
                    },
        )

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TextButton(onClick = { mode = if (mode == AuthMode.SIGN_UP) AuthMode.SIGN_IN else AuthMode.SIGN_UP }) {
                Text(if (mode == AuthMode.SIGN_UP) "I already have an account" else "Create account")
            }
            TextButton(onClick = { mode = AuthMode.RESET_REQUEST }) { Text("Forgot password?") }
        }
        Spacer(Modifier.height(12.dp))
        TextButton(onClick = onTryJudgeDemo, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (busy) "Opening safe demo…" else "Try judge demo")
        }
        Text(
            "Runs an isolated synthetic demo in this app. It never contacts real people.",
            style = MaterialTheme.typography.bodySmall,
            color = ico.graphite,
        )
    }
}

@Preview(showBackground = true)
@Composable
private fun SignInPreview() {
    InCaseOfTheme {
        SignInScreen(
            state = AuthState.SignedOut,
            onSignIn = { _, _ -> },
            onSignUp = { _, _ -> },
            onConfirm = { _, _ -> },
            onRequestReset = {},
            onConfirmReset = { _, _, _ -> },
            onTryJudgeDemo = {},
            error = null,
            busy = false,
        )
    }
}
