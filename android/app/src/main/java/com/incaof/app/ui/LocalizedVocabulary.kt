package com.incaof.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import com.incaof.app.R
import com.incaof.app.domain.AlertState
import com.incaof.app.domain.PlanType
import com.incaof.app.domain.ReleaseLevel
import com.incaof.app.domain.ResponderRole
import com.incaof.app.domain.StepAction

@Composable
fun localizedExplanation(state: AlertState?, subjectName: String? = null): String =
    when (state) {
        null, AlertState.SCHEDULED -> {
            stringResource(R.string.explanation_clear)
        }

        AlertState.DUE, AlertState.GRACE -> {
            stringResource(R.string.explanation_waiting)
        }

        AlertState.SELF_CONTACT -> {
            stringResource(
                R.string.explanation_self_contact,
                subjectName ?: stringResource(R.string.subject_you),
            )
        }

        AlertState.CIRCLE_ESCALATION -> {
            stringResource(R.string.explanation_circle)
        }

        AlertState.CHECKING -> {
            stringResource(R.string.explanation_checking)
        }

        AlertState.RESOLVED -> {
            stringResource(R.string.explanation_resolved)
        }

        AlertState.CANCELLED -> {
            stringResource(R.string.explanation_cancelled)
        }

        AlertState.ESCALATION_EXHAUSTED -> {
            stringResource(R.string.explanation_exhausted)
        }
    }

@Composable
fun localizedAction(action: StepAction): String =
    stringResource(
        when (action) {
            StepAction.PUSH_SUBJECT -> R.string.action_push_subject
            StepAction.SMS_SUBJECT -> R.string.action_sms_subject
            StepAction.CALL_SUBJECT -> R.string.action_call_subject
            StepAction.MESSAGE_RESPONDER -> R.string.action_message_responder
            StepAction.CALL_RESPONDER -> R.string.action_call_responder
        },
    )

@Composable
fun localizedRole(role: ResponderRole): String =
    stringResource(
        when (role) {
            ResponderRole.PRIMARY -> R.string.role_primary
            ResponderRole.BACKUP -> R.string.role_backup
            ResponderRole.TERTIARY -> R.string.role_tertiary
        },
    )

@Composable
fun localizedRelease(level: ReleaseLevel): String =
    stringResource(
        when (level) {
            ReleaseLevel.NEVER -> R.string.release_never
            ReleaseLevel.ON_ALERT_OPEN -> R.string.release_alert_open
            ReleaseLevel.AFTER_SUBJECT_CALL_FAILED -> R.string.release_subject_call_failed
            ReleaseLevel.CIRCLE_ESCALATION -> R.string.release_circle_escalation
        },
    )

@Composable
fun localizedPlanType(type: PlanType): String =
    stringResource(
        when (type) {
            PlanType.ROUTINE -> R.string.plan_type_routine
            PlanType.JOURNEY -> R.string.plan_type_journey
            PlanType.SOLO -> R.string.plan_type_solo
            PlanType.RECOVERY -> R.string.plan_type_recovery
        },
    )

@Composable
fun localizedTimelineEvent(event: String): String {
    val resource =
        when (event) {
            "MOMENT_DUE" -> R.string.timeline_moment_due
            "ACTION_QUEUED" -> R.string.timeline_action_queued
            "ACTION_ACCEPTED" -> R.string.timeline_action_accepted
            "ACTION_DELIVERED" -> R.string.timeline_action_delivered
            "ACTION_UNDELIVERED" -> R.string.timeline_action_undelivered
            "ACTION_FAILED" -> R.string.timeline_action_failed
            "ACTION_SUPPRESSED" -> R.string.timeline_action_suppressed
            "CHANNEL_UNAVAILABLE" -> R.string.timeline_channel_unavailable
            "CONTACT_DENIED" -> R.string.timeline_contact_denied
            "SUBJECT_CONFIRMED" -> R.string.timeline_subject_confirmed
            "ALERT_CLAIMED" -> R.string.timeline_alert_claimed
            "RESPONDER_VERIFIED" -> R.string.timeline_responder_verified
            "STATE_CIRCLE_ESCALATION" -> R.string.timeline_circle_escalation
            "STATE_CHECKING" -> R.string.timeline_state_checking
            "STATE_RESOLVED" -> R.string.timeline_state_resolved
            else -> null
        }
    return resource?.let { stringResource(it) }
        ?: event.lowercase().replace('_', ' ').replaceFirstChar { it.uppercase() }
}
