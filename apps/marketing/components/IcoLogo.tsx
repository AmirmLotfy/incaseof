import React from "react";

export function IcoLogo({
  size = 40,
  showWordmark = true,
}: {
  size?: number;
  showWordmark?: boolean;
}) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "0.75rem" }}>
      <img
        src="/images/ico-logo.png"
        alt="In Case Of — ICO Logo"
        width={size}
        height={size}
        style={{
          borderRadius: "8px",
          border: "1px solid var(--ico-stone)",
          display: "block",
          objectFit: "cover",
        }}
      />
      {showWordmark && (
        <span
          style={{
            fontWeight: 700,
            letterSpacing: "-0.02em",
            fontSize: "1.125rem",
            color: "var(--ico-ink)",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          <span>in case of</span>
          <span
            style={{
              fontSize: "0.625rem",
              fontFamily: "var(--font-plex-mono)",
              background: "var(--ico-surface)",
              color: "var(--ico-graphite)",
              border: "1px solid var(--ico-stone)",
              padding: "0.15rem 0.4rem",
              borderRadius: "4px",
              fontWeight: 600,
              letterSpacing: "0.08em",
            }}
          >
            ICO
          </span>
        </span>
      )}
    </div>
  );
}
