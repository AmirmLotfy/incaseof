package com.incaof.app.core.time

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

class TimeFormatTest {
    private val amsterdam = ZoneId.of("Europe/Amsterdam")

    @Test
    fun `a ladder offset reads as an interval`() {
        assertEquals("now", TimeFormat.offset(0))
        assertEquals("10 min", TimeFormat.offset(600))
        assertEquals("25 min", TimeFormat.offset(1500))
        assertEquals("1 hr", TimeFormat.offset(3600))
        assertEquals("1 hr 15 min", TimeFormat.offset(4500))
    }

    @Test
    fun `times render in the zone they are asked for, not in UTC`() {
        // A deadline shown in the wrong zone is a deadline at the wrong time.
        val instant = Instant.parse("2026-08-26T19:00:00Z")
        assertTrue(TimeFormat.time(instant, amsterdam).startsWith("9:00"))
        assertTrue(TimeFormat.time(instant, ZoneId.of("UTC")).startsWith("7:00"))
    }

    @Test
    fun `nearby days get names rather than dates`() {
        val today = LocalDate.of(2026, 8, 26)
        val zone = ZoneId.of("UTC")

        fun at(day: Int) = Instant.parse("2026-08-${"%02d".format(day)}T12:00:00Z")

        assertEquals("Today", TimeFormat.day(at(26), zone, today))
        assertEquals("Tomorrow", TimeFormat.day(at(27), zone, today))
        assertEquals("Yesterday", TimeFormat.day(at(25), zone, today))
        assertEquals("Saturday", TimeFormat.day(at(29), zone, today))
    }

    @Test
    fun `distant days fall back to a date`() {
        val today = LocalDate.of(2026, 8, 26)
        val far = Instant.parse("2026-09-20T12:00:00Z")
        val rendered = TimeFormat.day(far, ZoneId.of("UTC"), today)
        assertTrue("expected a date, got $rendered", rendered.contains("20"))
    }

    @Test
    fun `relative times are approximate, never a live countdown`() {
        // A ticking countdown on a safety screen manufactures urgency; the product's job is
        // to reduce it.
        val now = Instant.parse("2026-08-26T21:00:00Z")
        assertEquals("in 7 minutes", TimeFormat.relative(now, now.plusSeconds(420)))
        assertEquals("in 1 minute", TimeFormat.relative(now, now.plusSeconds(60)))
        assertEquals("now", TimeFormat.relative(now, now))
        assertEquals("now", TimeFormat.relative(now, now.minusSeconds(60)))
    }
}
