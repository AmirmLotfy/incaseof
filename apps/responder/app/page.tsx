/**
 * Phase 0 placeholder.
 *
 * The real surface here is the Incident Room, reached via a signed single-Alert link
 * (/r/{token}) that works without an account. It is built in Phase 6, after design
 * references are locked.
 */
export default function Home() {
  return (
    <main
      style={{
        maxWidth: "32rem",
        margin: "0 auto",
        padding: "var(--ico-space-7) var(--ico-space-4)",
      }}
    >
      <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>In Case of</h1>
      <p style={{ color: "var(--ico-graphite)", marginTop: "var(--ico-space-2)" }}>
        Responder links open a single alert. There is nothing to see here.
      </p>
      <p
        className="tabular"
        style={{
          marginTop: "var(--ico-space-6)",
          fontSize: "0.8125rem",
          color: "var(--ico-graphite)",
        }}
      >
        PHASE 0 · SCAFFOLD ONLY
      </p>
    </main>
  );
}
