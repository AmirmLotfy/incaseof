package com.incaof.app.core.time

import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Times, as people read them.
 *
 * Everything is stored UTC and rendered in a zone. The zone is a parameter rather than a
 * global, because a plan carries its own IANA timezone and a deadline rendered in the
 * wrong one is a deadline in the wrong place.
 */
object TimeFormat {
    // Resolved per call, not held in a field. A formatter that captures the locale at
    // class-load time keeps formatting in the old language after the user changes theirs,
    // and the bug survives until the process restarts.
    private val clockTime get() = DateTimeFormatter.ofPattern("h:mm a", Locale.getDefault())
    private val dayName get() = DateTimeFormatter.ofPattern("EEEE", Locale.getDefault())
    private val dayAndMonth get() = DateTimeFormatter.ofPattern("d MMMM", Locale.getDefault())

    fun time(instant: Instant, zone: ZoneId = ZoneId.systemDefault()): String = clockTime.format(instant.atZone(zone))

    /** "Today", "Tomorrow", "Thursday", or a date once it is far enough out to need one. */
    fun day(instant: Instant, zone: ZoneId = ZoneId.systemDefault(), today: LocalDate = LocalDate.now(zone)): String {
        val date = instant.atZone(zone).toLocalDate()
        return when (date) {
            today -> "Today"
            today.plusDays(1) -> "Tomorrow"
            today.minusDays(1) -> "Yesterday"
            in today..today.plusDays(6) -> dayName.format(date)
            else -> dayAndMonth.format(date)
        }
    }

    fun dayAndTime(instant: Instant, zone: ZoneId = ZoneId.systemDefault()): String =
        "${day(instant, zone)} · ${time(instant, zone)}"

    /**
     * A ladder offset, as an interval.
     *
     * Relative rather than absolute, because what matters when reading a ladder is the gap
     * between rungs, not the clock time of each.
     */
    fun offset(seconds: Int): String =
        when {
            seconds == 0 -> "now"
            seconds < 60 -> "${seconds}s"
            seconds % 3600 == 0 -> "${seconds / 3600} hr"
            seconds < 3600 -> "${seconds / 60} min"
            else -> "${seconds / 3600} hr ${(seconds % 3600) / 60} min"
        }

    /** "in 7 minutes", for saying what happens next. Never a live countdown. */
    fun relative(from: Instant, to: Instant): String {
        val gap = Duration.between(from, to)
        if (gap.isNegative || gap.isZero) return "now"
        val minutes = gap.toMinutes()
        return when {
            minutes < 1 -> "in less than a minute"
            minutes == 1L -> "in 1 minute"
            minutes < 60 -> "in $minutes minutes"
            minutes < 120 -> "in about an hour"
            else -> "in ${gap.toHours()} hours"
        }
    }
}
