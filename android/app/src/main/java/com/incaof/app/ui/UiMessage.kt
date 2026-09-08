package com.incaof.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.incaof.app.R

enum class UiMessage {
    OFFLINE,
    GENERIC,
    AUTH_SIGN_IN,
    AUTH_SIGN_UP,
    AUTH_CONFIRMATION,
    AUTH_RESET_REQUEST,
    AUTH_RESET_CONFIRM,
    PLAN_DESCRIPTION_REQUIRED,
    PLAN_UPDATED,
    DEMO_UNAVAILABLE,
}

@Composable
fun localizedUiMessage(message: UiMessage): String =
    stringResource(
        when (message) {
            UiMessage.OFFLINE -> R.string.error_offline
            UiMessage.GENERIC -> R.string.error_generic
            UiMessage.AUTH_SIGN_IN -> R.string.error_auth_sign_in
            UiMessage.AUTH_SIGN_UP -> R.string.error_auth_sign_up
            UiMessage.AUTH_CONFIRMATION -> R.string.error_auth_confirmation
            UiMessage.AUTH_RESET_REQUEST -> R.string.error_auth_reset_request
            UiMessage.AUTH_RESET_CONFIRM -> R.string.error_auth_reset_confirm
            UiMessage.PLAN_DESCRIPTION_REQUIRED -> R.string.error_plan_description
            UiMessage.PLAN_UPDATED -> R.string.notice_plan_updated
            UiMessage.DEMO_UNAVAILABLE -> R.string.error_demo_unavailable
        },
    )
