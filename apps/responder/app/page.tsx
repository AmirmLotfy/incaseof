/**
 * The responder app has no home page worth having.
 *
 * Every real entry point is a signed single-Alert link. Somebody arriving at the root
 * either mistyped a URL or is looking around, and neither warrants a marketing page here.
 */
export const metadata = {
  title: "In Case of",
  robots: { index: false, follow: false },
};

export default function Root() {
  return (
    <main
      style={{
        maxWidth: "var(--measure)",
        margin: "0 auto",
        padding: "4rem 1.25rem",
      }}
    >
      <p className="wordmark">In Case of</p>
      <h1 className="headline" style={{ marginTop: "1.5rem" }}>
        Nothing to see here
      </h1>
      <p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>
        In Case of sends a private link when somebody needs you. This page isn&rsquo;t one.
      </p>
      <p style={{ marginTop: "2rem" }}>
        <a href="https://incaof.com" style={{ color: "var(--ico-primary)" }}>
          What is In Case of?
        </a>
      </p>
    </main>
  );
}
