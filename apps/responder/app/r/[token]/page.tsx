import type { Metadata } from "next";
import { fetchIncident, isLive } from "@/lib/api";
import { IncidentRoom } from "@/components/IncidentRoom";

/**
 * /r/{token} — the Incident Room.
 *
 * No account, no sign-up, no cookie banner. Somebody arrives here from an SMS at 2am and
 * has to be able to act immediately.
 */
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "In Case of",
  // Never indexed. These URLs are credentials.
  robots: { index: false, follow: false },
};

export default async function IncidentPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const incident = await fetchIncident(token);

  if (incident === "INVALID_LINK") return <LinkNotValid />;
  if (incident === "UNREACHABLE") return <Unreachable />;

  if (incident.state === "RESOLVED" || incident.state === "CANCELLED") {
    return <AlreadyClosed name={incident.subjectName} />;
  }

  return (
    <>
      {!isLive && <LocalBanner />}
      <IncidentRoom incident={incident} token={token} />
    </>
  );
}

/**
 * One message for every reason a link can fail.
 *
 * Expired, forged, revoked and never-existed all read identically. Distinguishing them
 * tells somebody holding a guessed link which half of the guess was right.
 */
function LinkNotValid() {
  return (
    <Message
      title="This link isn’t valid"
      body="It may have expired, or the check it belonged to may already be resolved. If someone
      is expecting you, ask them to send a new one."
    />
  );
}

function Unreachable() {
  return (
    <Message
      title="Couldn’t load this"
      body="Something went wrong reaching In Case of. Try again in a moment — the plan is still
      running either way."
    />
  );
}

function AlreadyClosed({ name }: { name: string }) {
  return (
    <Message
      title="This is closed"
      body={`${name}’s check has been resolved. There’s nothing you need to do.`}
    />
  );
}

function Message({ title, body }: { title: string; body: string }) {
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
        {title}
      </h1>
      <p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>{body}</p>
    </main>
  );
}

/**
 * Says plainly that this is not connected to a real alert.
 *
 * The same principle as the demo-timing banner: a surface showing something other than
 * live data must say so, or it is misleading.
 */
function LocalBanner() {
  return (
    <p
      style={{
        margin: 0,
        padding: "0.625rem 1.25rem",
        background: "var(--ico-warning)",
        color: "var(--ico-on-warning)",
        fontSize: "0.875rem",
        textAlign: "center",
      }}
    >
      Sample incident — not connected to a live alert
    </p>
  );
}
