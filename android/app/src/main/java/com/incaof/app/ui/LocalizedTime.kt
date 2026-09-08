package com.incaof.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import com.incaof.app.R
import com.incaof.app.core.time.TimeFormat
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

@Composable
fun localizedDay(
    instant: Instant,
    zone: ZoneId = ZoneId.systemDefault(),
    today: LocalDate = LocalDate.now(zone),
): String {
    val date = instant.atZone(zone).toLocalDate()
    return when (date) {
        today -> stringResource(R.string.time_today)
        today.plusDays(1) -> stringResource(R.string.time_tomorrow)
        today.minusDays(1) -> stringResource(R.string.time_yesterday)
        else -> TimeFormat.calendarDay(instant, zone, today)
    }
}

@Composable
fun localizedDayAndTime(instant: Instant, zone: ZoneId = ZoneId.systemDefault()): String =
    "${localizedDay(instant, zone)} · ${TimeFormat.time(instant, zone)}"

@Composable
fun localizedOffset(seconds: Int): String =
    when {
        seconds == 0 -> {
            stringResource(R.string.time_now)
        }

        seconds < 60 -> {
            pluralStringResource(R.plurals.time_seconds, seconds, seconds)
        }

        seconds % 3600 == 0 -> {
            val hours = seconds / 3600
            pluralStringResource(R.plurals.time_hours, hours, hours)
        }

        seconds < 3600 -> {
            val minutes = seconds / 60
            pluralStringResource(R.plurals.time_minutes, minutes, minutes)
        }

        else -> {
            val hours = seconds / 3600
            val minutes = (seconds % 3600) / 60
            stringResource(
                R.string.time_hours_minutes,
                pluralStringResource(R.plurals.time_hours, hours, hours),
                pluralStringResource(R.plurals.time_minutes, minutes, minutes),
            )
        }
    }

@Composable
fun localizedRelative(from: Instant, to: Instant): String {
    val gap = Duration.between(from, to)
    if (gap.isNegative || gap.isZero) return stringResource(R.string.time_now)
    val minutes = gap.toMinutes()
    return when {
        minutes < 1 -> {
            stringResource(R.string.time_relative_less_minute)
        }

        minutes == 1L -> {
            stringResource(R.string.time_relative_one_minute)
        }

        minutes < 60 -> {
            pluralStringResource(R.plurals.time_relative_minutes, minutes.toInt(), minutes)
        }

        minutes < 120 -> {
            stringResource(R.string.time_relative_about_hour)
        }

        else -> {
            val hours = gap.toHours().toInt()
            pluralStringResource(R.plurals.time_relative_hours, hours, hours)
        }
    }
}
