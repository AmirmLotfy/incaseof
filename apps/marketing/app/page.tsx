/**
 * Phase 0 placeholder.
 *
 * The marketing site is deliberately NOT designed yet. Per the build contract, no
 * significant user-facing surface may be designed until docs/design/REFERENCES.md holds
 * locked visual references from Refero research. Designing first and researching later is
 * exactly how this drifts into generic AI-SaaS slop.
 *
 * This page exists only to prove the build, the fonts and the token pipeline work.
 */
export default function Home() {
  return (
    <main
      style={{
        maxWidth: "42rem",
        margin: "0 auto",
        padding: "var(--ico-space-7) var(--ico-space-4)",
      }}
    >
      <h1 style={{ fontSize: "1.75rem", fontWeight: 600, letterSpacing: "-0.01em" }}>
        In Case of
      </h1>
      <p style={{ color: "var(--ico-graphite)", marginTop: "var(--ico-space-2)" }}>
        Someone notices.
      </p>

      <hr
        style={{
          border: 0,
          borderTop: "1px solid var(--ico-stone)",
          margin: "var(--ico-space-6) 0",
        }}
      />

      <p style={{ lineHeight: 1.6 }}>
        In Case of does not decide whether someone is in danger. It notices unresolved
        expectations and works to close the loop.
      </p>

      <p
        className="tabular"
        style={{
          marginTop: "var(--ico-space-6)",
          fontSize: "0.8125rem",
          color: "var(--ico-graphite)",
        }}
      >
        PHASE 0 · SCAFFOLD ONLY · AWAITING DESIGN RESEARCH
      </p>
    </main>
  );
}
