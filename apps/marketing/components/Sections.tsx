import type { ReactNode } from "react";

/** A full-width editorial row. Deliberately not a card — see build contract §78. */
export function Row({
  eyebrow,
  title,
  children,
  aside,
  flip = false,
}: {
  eyebrow?: string;
  title: string;
  children: ReactNode;
  aside?: ReactNode;
  flip?: boolean;
}) {
  return (
    <div
      style={{
        display: "grid",
        gap: "clamp(1.5rem, 4vw, 3.5rem)",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 22rem), 1fr))",
        alignItems: "start",
      }}
    >
      <div style={{ order: flip ? 2 : 1 }}>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h3>{title}</h3>
        <div style={{ marginTop: "0.75rem", color: "var(--ico-graphite)" }}>{children}</div>
      </div>
      {aside && <div style={{ order: flip ? 1 : 2 }}>{aside}</div>}
    </div>
  );
}

/** A quoted line, set as speech rather than as a pull-quote. */
export function Said({ children }: { children: ReactNode }) {
  return (
    <p
      style={{
        fontSize: "1.125rem",
        color: "var(--ico-ink)",
        borderLeft: "2px solid var(--ico-signal)",
        paddingLeft: "1rem",
      }}
    >
      {children}
    </p>
  );
}

/** Two lists side by side: what the product needs, and what it does not. */
export function Contrast({
  needs,
  doesNotNeed,
}: {
  needs: string[];
  doesNotNeed: string[];
}) {
  return (
    <div
      style={{
        display: "grid",
        gap: "clamp(1.5rem, 4vw, 3rem)",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 18rem), 1fr))",
        marginTop: "2.5rem",
      }}
    >
      <Column title="What In Case of needs" items={needs} marker="var(--ico-primary)" />
      <Column title="What it doesn’t" items={doesNotNeed} marker="var(--ico-stone)" muted />
    </div>
  );
}

function Column({
  title,
  items,
  marker,
  muted = false,
}: {
  title: string;
  items: string[];
  marker: string;
  muted?: boolean;
}) {
  return (
    <div>
      <p className="eyebrow">{title}</p>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {items.map((item) => (
          <li
            key={item}
            style={{
              display: "flex",
              gap: "0.75rem",
              alignItems: "baseline",
              padding: "0.5rem 0",
              borderTop: "1px solid var(--ico-stone)",
              color: muted ? "var(--ico-graphite)" : "var(--ico-ink)",
              textDecoration: muted ? "line-through" : "none",
              textDecorationColor: "var(--ico-stone)",
            }}
          >
            <span
              aria-hidden="true"
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: marker,
                flexShrink: 0,
                transform: "translateY(-2px)",
              }}
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The four steps of the mechanism. Build contract §77. */
export function Mechanism() {
  const steps = [
    ["Expect", "Tell In Case of what should happen."],
    ["Reach", "If the moment is missed, it starts with you."],
    ["Coordinate", "If uncertainty remains, the people you chose join in."],
    ["Resolve", "It stops only when the loop is actually closed."],
  ];

  return (
    <ol
      style={{
        listStyle: "none",
        margin: "2.5rem 0 0",
        padding: 0,
        display: "grid",
        gap: "clamp(1.5rem, 3vw, 2.5rem)",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 13rem), 1fr))",
      }}
    >
      {steps.map(([name, body], index) => (
        <li key={name} style={{ borderTop: "2px solid var(--ico-ink)", paddingTop: "1rem" }}>
          <p className="mono" style={{ fontSize: "0.75rem", color: "var(--ico-graphite)" }}>
            {String(index + 1).padStart(2, "0")}
          </p>
          <h3 style={{ marginTop: "0.5rem" }}>{name}</h3>
          <p style={{ marginTop: "0.5rem", color: "var(--ico-graphite)" }}>{body}</p>
        </li>
      ))}
    </ol>
  );
}
