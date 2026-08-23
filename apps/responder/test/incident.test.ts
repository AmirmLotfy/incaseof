import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { clockTime, countdown, eventLabel, relativeTime } from "../lib/incident";

/**
 * The Incident Room's logic.
 *
 * Small surface, but every function here renders something somebody reads at 2am while
 * deciding whether to get out of bed. Wrong is worse than absent.
 */

const NOW = new Date("2026-08-26T21:00:00Z");

describe("relativeTime", () => {
  it("counts minutes while there are minutes to count", () => {
    assert.equal(relativeTime("2026-08-26T21:12:00Z", NOW), "in 12 minutes");
    assert.equal(relativeTime("2026-08-26T21:01:00Z", NOW), "in 1 minute");
  });

  it("does not flatten every long gap into 'about an hour'", () => {
    // The original bug: everything past 60 minutes read as "in about an hour", so a
    // contact seventeen hours away was described as imminent.
    assert.equal(relativeTime("2026-08-26T23:00:00Z", NOW), "in about 2 hours");
    assert.equal(relativeTime("2026-08-27T14:00:00Z", NOW), "in about 17 hours");
  });

  it("says 'about an hour' only when it is about an hour", () => {
    assert.equal(relativeTime("2026-08-26T22:00:00Z", NOW), "in about an hour");
    assert.equal(relativeTime("2026-08-26T22:10:00Z", NOW), "in about an hour");
  });

  it("never counts backwards", () => {
    // A rung whose time has passed says "shortly", not "in -4 minutes".
    assert.equal(relativeTime("2026-08-26T20:56:00Z", NOW), "shortly");
    assert.equal(relativeTime("2026-08-26T21:00:00Z", NOW), "shortly");
  });

  it("survives a malformed timestamp", () => {
    assert.equal(relativeTime("not-a-date", NOW), "shortly");
  });
});

describe("countdown", () => {
  it("renders a lease as fixed-width minutes and seconds", () => {
    assert.equal(countdown("2026-08-26T21:09:42Z", NOW), "09:42");
    assert.equal(countdown("2026-08-26T21:00:05Z", NOW), "00:05");
  });

  it("floors at zero rather than showing a negative lease", () => {
    assert.equal(countdown("2026-08-26T20:50:00Z", NOW), "00:00");
  });

  it("survives a malformed timestamp", () => {
    assert.equal(countdown("nonsense", NOW), "00:00");
  });
});

describe("eventLabel", () => {
  it("translates the events a responder actually sees", () => {
    assert.equal(eventLabel("MOMENT_DUE"), "Check requested");
    assert.equal(eventLabel("STATE_CIRCLE_ESCALATION"), "You were contacted");
    assert.equal(eventLabel("CHANNEL_UNAVAILABLE"), "Call unavailable");
  });

  it("never shows a raw constant when the backend adds an event type", () => {
    // Backends grow event types. An unrecognised one must degrade to something readable
    // rather than surfacing SCREAMING_SNAKE_CASE on somebody's lock screen.
    const rendered = eventLabel("SOME_NEW_BACKEND_EVENT");
    assert.ok(!rendered.includes("_"), rendered);
    assert.equal(rendered, "Some new backend event");
  });

  it("says nothing speculative", () => {
    const all = [
      "MOMENT_DUE",
      "ACTION_QUEUED",
      "ACTION_SENT",
      "CHANNEL_UNAVAILABLE",
      "STATE_CIRCLE_ESCALATION",
      "ALERT_CLAIMED",
      "RESPONDER_VERIFIED",
    ].map(eventLabel);

    for (const label of all) {
      for (const word of ["danger", "emergency", "risk", "urgent", "critical"]) {
        assert.ok(
          !label.toLowerCase().includes(word),
          `"${label}" speculates with "${word}"`,
        );
      }
    }
  });
});

describe("clockTime", () => {
  it("renders an hour and minute", () => {
    assert.match(clockTime("2026-08-26T21:00:00Z"), /\d{1,2}:\d{2}/);
  });

  it("returns nothing rather than 'Invalid Date'", () => {
    assert.equal(clockTime("nope"), "");
  });
});
