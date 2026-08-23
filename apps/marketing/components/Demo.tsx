"use client";

import { useCallback, useState } from "react";

/**
 * The judge demo. Build contract §86.
 *
 * An honest thing to be clear about: this is a **browser walkthrough of the mechanism**, not
 * the product running. The real Drill Mode runs the production workflow server-side on a
 * compressed clock — see docs/DEMO.md and services/tests/slice/test_drill_mode.py. That
 * needs a deployed stack; this needs a browser.
 *
 * What it does share with the product is the sequence: the same ladder, the same states, the
 * same rule that acknowledging is not resolving. The banner says what it is, because a
 * surface showing something other than live data and not saying so is misleading.
 */

type Phase =
  | "idle"
  | "waiting"
  | "self_contact"
  | "circle"
  | "checking"
  | "resolved"
  | "exhausted";

interface Event {
  time: string;
  label: string;
  actor: "system" | "you" | "circle";
}

const LADDER = [
  { at: 0, label: "Check requested", actor: "system" as const },
  { at: 10, label: "Reminder sent", actor: "system" as const },
  { at: 20, label: "Message sent", actor: "system" as const },
  { at: 25, label: "Maya contacted", actor: "system" as const },
  { at: 40, label: "Omar contacted", actor: "system" as const },
];

export function Demo() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [events, setEvents] = useState<Event[]>([]);
  const [rung, setRung] = useState(0);

  const stamp = useCallback((minutes: number) => {
    const base = new Date();
    base.setHours(21, 0, 0, 0);
    return new Date(base.getTime() + minutes * 60_000).toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  }, []);

  const add = useCallback(
    (label: string, actor: Event["actor"], minutes: number) =>
      setEvents((previous) => [...previous, { time: stamp(minutes), label, actor }]),
    [stamp],
  );

  function activate() {
    setPhase("waiting");
    setEvents([]);
    setRung(0);
  }

  function advance() {
    const next = LADDER[rung];
    if (!next) return;
    add(next.label, next.actor, next.at);
    const upcoming = rung + 1;
    setRung(upcoming);
    if (upcoming >= LADDER.length) setPhase("exhausted");
    else if (upcoming >= 4) setPhase("circle");
    else setPhase("self_contact");
  }

  function confirm() {
    add("You confirmed — resolved", "you", 22);
    setPhase("resolved");
  }

  function claim() {
    add("Maya is checking — backup paused", "circle", 27);
    setPhase("checking");
  }

  function verify() {
    add("Maya confirmed — resolved", "circle", 31);
    setPhase("resolved");
  }

  const closed = phase === "resolved" || phase === "exhausted";

  return (
    <div>
      <Banner />

      <div
        style={{
          display: "grid",
          gap: "clamp(1.5rem, 4vw, 3rem)",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 20rem), 1fr))",
          marginTop: "2.5rem",
          alignItems: "start",
        }}
      >
        <div>
          <p className="eyebrow">Step 1 — the plan</p>
          <p style={{ color: "var(--ico-graphite)" }}>
            An evening check at 9:00 PM. If it goes unanswered: you, then you again, then a
            message, then Maya, then Omar.
          </p>

          <div style={{ marginTop: "1.5rem", display: "grid", gap: "0.75rem" }}>
            {phase === "idle" && (
              <Action onClick={activate} kind="primary">
                Activate the plan
              </Action>
            )}

            {phase === "waiting" && (
              <>
                <p className="eyebrow" style={{ marginBottom: 0 }}>
                  Step 2 — miss it
                </p>
                <Action onClick={advance} kind="attention">
                  9:00 arrives, nobody answers
                </Action>
              </>
            )}

            {(phase === "self_contact" || phase === "circle") && (
              <>
                <Action onClick={advance} kind="attention">
                  Let it continue
                </Action>
                {phase === "self_contact" && (
                  <Action onClick={confirm} kind="primary">
                    Tap “I’m okay”
                  </Action>
                )}
                {phase === "circle" && (
                  <Action onClick={claim} kind="primary">
                    Maya taps “I’m checking”
                  </Action>
                )}
              </>
            )}

            {phase === "checking" && (
              <>
                {/* The distinction the whole product turns on, made visible. */}
                <p
                  style={{
                    padding: "0.85rem 1rem",
                    border: "1px solid var(--ico-stone)",
                    borderRadius: "12px",
                    color: "var(--ico-graphite)",
                    fontSize: "0.9375rem",
                  }}
                >
                  Maya has acknowledged, not resolved. Omar is paused for ten minutes. If
                  Maya goes quiet, contacting resumes where it left off.
                </p>
                <Action onClick={verify} kind="primary">
                  Maya: “I reached Mona — all okay”
                </Action>
              </>
            )}

            {closed && (
              <Action onClick={() => setPhase("idle")} kind="quiet">
                Run it again
              </Action>
            )}
          </div>
        </div>

        <div
          style={{
            border: "1px solid var(--ico-stone)",
            borderRadius: "20px",
            background: "var(--ico-surface)",
            padding: "1.75rem",
            minHeight: "18rem",
          }}
        >
          <p className="eyebrow">What’s happened</p>

          {events.length === 0 ? (
            <p style={{ color: "var(--ico-graphite)" }}>
              Nothing yet. Activate the plan to begin.
            </p>
          ) : (
            <ol style={{ listStyle: "none", margin: 0, padding: 0 }} aria-live="polite">
              {events.map((event, index) => (
                <li
                  key={`${event.time}-${index}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "5rem 1fr",
                    gap: "0.85rem",
                    padding: "0.45rem 0",
                  }}
                >
                  <span className="mono" style={{ color: "var(--ico-graphite)" }}>
                    {event.time}
                  </span>
                  <span
                    style={{
                      color:
                        event.actor === "system" ? "var(--ico-ink)" : "var(--ico-resolved)",
                    }}
                  >
                    {event.label}
                  </span>
                </li>
              ))}
            </ol>
          )}

          {phase === "exhausted" && (
            <p style={{ marginTop: "1.5rem", color: "var(--ico-graphite)" }}>
              Everyone on the plan was contacted and nobody confirmed. In Case of records
              that plainly — it does not decide what it means.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function Banner() {
  return (
    <p
      style={{
        margin: 0,
        padding: "0.75rem 1rem",
        borderRadius: "12px",
        background: "var(--ico-warning)",
        color: "var(--ico-on-warning)",
        fontSize: "0.9375rem",
      }}
    >
      <strong>Walkthrough.</strong> This runs in your browser and contacts nobody. The real
      Drill Mode runs the production workflow on a compressed clock.
    </p>
  );
}

function Action({
  children,
  onClick,
  kind,
}: {
  children: React.ReactNode;
  onClick: () => void;
  kind: "primary" | "attention" | "quiet";
}) {
  const palette = {
    primary: { background: "var(--ico-primary)", color: "var(--ico-on-primary)", border: "none" },
    // Ink on Signal Orange. White measures 3.52:1 and fails AA.
    attention: { background: "var(--ico-signal)", color: "var(--ico-on-signal)", border: "none" },
    quiet: {
      background: "transparent",
      color: "var(--ico-ink)",
      border: "1px solid var(--ico-stone)",
    },
  }[kind];

  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        minHeight: "52px",
        padding: "0.85rem 1.25rem",
        borderRadius: "14px",
        font: "inherit",
        fontWeight: 500,
        cursor: "pointer",
        textAlign: "left",
        ...palette,
      }}
    >
      {children}
    </button>
  );
}
