"use client";

import { useState } from "react";

/**
 * Progressive context release. Build contract §80.
 *
 * Privacy shown rather than claimed. "Privacy-first" as a phrase means nothing; a control
 * that demonstrates location staying off at every stage means something.
 */
const TIERS = [
  {
    id: "normal",
    label: "Normal",
    note: "Nothing is shared. In Case of is doing nothing at all.",
    shared: [],
  },
  {
    id: "unresolved",
    label: "Check missed",
    note: "Only that a check went unanswered.",
    shared: ["Which check, and when it was expected"],
  },
  {
    id: "failed",
    label: "After a failed call",
    note: "Only the signals you turned on in advance.",
    shared: ["Which check, and when it was expected", "Last connection", "Battery"],
  },
] as const;

export function ContextTiers() {
  const [active, setActive] = useState(0);
  const tier = TIERS[active];

  return (
    <div style={{ marginTop: "2.5rem" }}>
      <div
        role="tablist"
        aria-label="What is shared at each stage"
        style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}
      >
        {TIERS.map((option, index) => {
          const selected = index === active;
          return (
            <button
              key={option.id}
              role="tab"
              type="button"
              aria-selected={selected}
              onClick={() => setActive(index)}
              style={{
                minHeight: "44px",
                padding: "0.5rem 1rem",
                borderRadius: "12px",
                font: "inherit",
                fontSize: "0.9375rem",
                cursor: "pointer",
                border: `1px solid ${selected ? "var(--ico-ink)" : "var(--ico-stone)"}`,
                background: selected ? "var(--ico-ink)" : "transparent",
                color: selected ? "var(--ico-background)" : "var(--ico-ink)",
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        aria-live="polite"
        style={{
          marginTop: "1.5rem",
          borderTop: "1px solid var(--ico-stone)",
          paddingTop: "1.5rem",
        }}
      >
        <p style={{ color: "var(--ico-graphite)" }}>{tier.note}</p>

        <ul style={{ listStyle: "none", padding: 0, margin: "1.25rem 0 0" }}>
          {tier.shared.length === 0 && (
            <li className="mono" style={{ color: "var(--ico-graphite)" }}>
              Nothing
            </li>
          )}
          {tier.shared.map((item) => (
            <li key={item} style={{ padding: "0.35rem 0" }}>
              {item}
            </li>
          ))}
          {/*
            Location is listed at every tier, always off. Stating it only where it is
            relevant would let somebody assume it appears later; showing it never appearing
            is the actual claim.
          */}
          <li
            style={{
              padding: "0.35rem 0",
              marginTop: "0.5rem",
              borderTop: "1px solid var(--ico-stone)",
              paddingTop: "0.85rem",
              color: "var(--ico-graphite)",
            }}
          >
            Location — <strong style={{ color: "var(--ico-ink)" }}>off</strong>, unless you
            add it to a plan yourself
          </li>
        </ul>
      </div>
    </div>
  );
}
