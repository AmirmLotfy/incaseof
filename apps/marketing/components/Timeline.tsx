"use client";

import { useState } from "react";

/**
 * The brand device. Build contract §69, §74, §75.
 *
 * The product's own mechanism, rendered as the identity. It teaches what In Case of does
 * while somebody looks at it, which is worth more than any illustration — and it removes
 * the temptation to put a phone in a gradient cloud.
 *
 * Interactive on purpose: pressing "miss the check" walks the real escalation ladder. No
 * video, no autoplay, no animated typing. Somebody who wants to understand the product can
 * make it happen; somebody who doesn't sees a static, legible diagram.
 */

interface Rung {
  time: string;
  label: string;
  kind: "expected" | "subject" | "circle" | "resolved";
}

const LADDER: Rung[] = [
  { time: "12:00", label: "Expected home", kind: "expected" },
  { time: "12:10", label: "Check with you", kind: "subject" },
  { time: "12:20", label: "Message you", kind: "subject" },
  { time: "12:30", label: "Maya is contacted", kind: "circle" },
  { time: "12:40", label: "Omar is contacted", kind: "circle" },
];

export function TimelineDevice() {
  // How many rungs have happened. Starts at one: the expectation exists, nothing has failed.
  const [reached, setReached] = useState(1);
  const [resolved, setResolved] = useState(false);

  const done = resolved || reached >= LADDER.length;

  return (
    <div
      style={{
        border: "1px solid var(--ico-stone)",
        borderRadius: "20px",
        background: "var(--ico-surface)",
        padding: "1.75rem",
      }}
    >
      <p className="eyebrow" style={{ marginBottom: "1.5rem" }}>
        Tonight
      </p>

      <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {LADDER.map((rung, index) => {
          const active = index < reached;
          return (
            <li
              key={rung.time}
              style={{
                display: "grid",
                gridTemplateColumns: "3.75rem 1.25rem 1fr",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.55rem 0",
                opacity: active ? 1 : 0.35,
                transition: "opacity 240ms ease",
              }}
            >
              <span
                className="mono"
                style={{ fontSize: "0.875rem", color: "var(--ico-graphite)" }}
              >
                {rung.time}
              </span>

              {/* The marker. A line with a dot on it — the whole visual identity. */}
              <span
                aria-hidden="true"
                style={{
                  position: "relative",
                  display: "block",
                  height: "100%",
                  minHeight: "1.5rem",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: 0,
                    bottom: 0,
                    width: "1px",
                    transform: "translateX(-50%)",
                    background:
                      index === LADDER.length - 1 ? "transparent" : "var(--ico-stone)",
                  }}
                />
                <span
                  style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    width: active ? "11px" : "7px",
                    height: active ? "11px" : "7px",
                    borderRadius: "50%",
                    transform: "translate(-50%, -50%)",
                    background: markerColour(rung, active, resolved),
                    transition: "all 240ms ease",
                  }}
                />
              </span>

              <span style={{ fontSize: "0.9375rem" }}>{rung.label}</span>
            </li>
          );
        })}

        {resolved && (
          <li
            style={{
              display: "grid",
              gridTemplateColumns: "3.75rem 1.25rem 1fr",
              alignItems: "center",
              gap: "0.75rem",
              padding: "0.55rem 0",
            }}
          >
            <span className="mono" style={{ fontSize: "0.875rem", color: "var(--ico-graphite)" }}>
              12:34
            </span>
            <span aria-hidden="true" style={{ display: "block", textAlign: "center" }}>
              <span
                style={{
                  display: "inline-block",
                  width: "11px",
                  height: "11px",
                  borderRadius: "50%",
                  background: "var(--ico-resolved)",
                }}
              />
            </span>
            <span style={{ fontSize: "0.9375rem" }}>Maya confirmed — all okay</span>
          </li>
        )}
      </ol>

      <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        {!done && (
          <button
            type="button"
            onClick={() => setReached((n) => n + 1)}
            style={buttonStyle}
          >
            {reached === 1 ? "Miss the check →" : "What happens next →"}
          </button>
        )}
        {!done && reached > 1 && (
          <button type="button" onClick={() => setResolved(true)} style={buttonStyle}>
            Someone confirms
          </button>
        )}
        {done && (
          <button
            type="button"
            onClick={() => {
              setReached(1);
              setResolved(false);
            }}
            style={buttonStyle}
          >
            Start again
          </button>
        )}
      </div>

      {/* Announced so a screen-reader user is told what changed, not left to re-read. */}
      <p aria-live="polite" className="sr-only" style={srOnly}>
        {resolved
          ? "Resolved. Maya confirmed."
          : `Step ${reached} of ${LADDER.length}: ${LADDER[reached - 1].label}`}
      </p>
    </div>
  );
}

/**
 * Colour semantics, exactly as DESIGN.md §4 defines them.
 *
 * Unresolved is Signal Orange, never Brick — a missed check means unresolved, not
 * emergency, and turning the interface red because somebody hasn't tapped a button yet is
 * precisely the anxiety this product exists to avoid.
 */
function markerColour(rung: Rung, active: boolean, resolved: boolean): string {
  if (!active) return "var(--ico-stone)";
  if (resolved) return "var(--ico-resolved)";
  if (rung.kind === "expected") return "var(--ico-graphite)";
  return "var(--ico-signal)";
}

const buttonStyle: React.CSSProperties = {
  minHeight: "44px",
  padding: "0.55rem 1rem",
  borderRadius: "12px",
  border: "1px solid var(--ico-stone)",
  background: "transparent",
  color: "var(--ico-ink)",
  font: "inherit",
  fontSize: "0.9375rem",
  cursor: "pointer",
};

const srOnly: React.CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0,0,0,0)",
  whiteSpace: "nowrap",
  border: 0,
};
