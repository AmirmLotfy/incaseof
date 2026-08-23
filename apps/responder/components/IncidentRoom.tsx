"use client";

import { useEffect, useState } from "react";
import { act } from "@/lib/api";
import {
  clockTime,
  countdown,
  relativeTime,
  type Incident,
} from "@/lib/incident";
import { Timeline } from "./Timeline";

/**
 * The Incident Room. Build contract §21.
 *
 * Two states, and they look different on purpose.
 *
 * *Unclaimed*: who, what, what was tried, what happens next, one action.
 * *Claimed*: who is checking, how long is left, and an explicit sentence saying backup
 * contact is paused — because the single most common misunderstanding this product has to
 * prevent is somebody believing that acknowledging an alert has resolved it.
 *
 * The resolution copy deliberately diverges from §21's "I REACHED HER". The system does not
 * know anybody's pronouns and must not guess one from a name, so the phrasing avoids the
 * question rather than answering it wrongly on somebody's lock screen.
 */
export function IncidentRoom({ incident, token }: { incident: Incident; token: string }) {
  const [current, setCurrent] = useState(incident);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const claimed = current.leaseExpiresAt !== null;

  async function run(
    action: "claim" | "unable" | "resolve",
    next: (previous: Incident) => Incident,
  ) {
    setBusy(true);
    setFailed(false);
    const ok = await act(token, action);
    if (ok) {
      setCurrent(next);
    } else {
      // Say so rather than failing silently. Somebody who tapped "I'm checking" and was not
      // heard needs to know the backup contact may still be called.
      setFailed(true);
    }
    setBusy(false);
  }

  return (
    <main
      style={{
        maxWidth: "var(--measure)",
        margin: "0 auto",
        padding: "2rem 1.25rem 4rem",
      }}
    >
      <p className="wordmark">In Case of</p>

      {claimed ? (
        <Checking incident={current} busy={busy} onAct={run} />
      ) : (
        <Unclaimed incident={current} busy={busy} onAct={run} />
      )}

      {failed && (
        <p
          role="alert"
          style={{ color: "var(--ico-critical)", marginTop: "1.5rem" }}
        >
          That didn&rsquo;t send. Check your connection and try again — {current.subjectName}
          &rsquo;s plan is still running.
        </p>
      )}
    </main>
  );
}

type Runner = (
  action: "claim" | "unable" | "resolve",
  next: (previous: Incident) => Incident,
) => void;

function Unclaimed({
  incident,
  busy,
  onAct,
}: {
  incident: Incident;
  busy: boolean;
  onAct: Runner;
}) {
  return (
    <>
      {/*
        The person first, then the fact. Never speculation: this says somebody has not
        responded, and never that anything is wrong.
      */}
      <h1 className="headline" style={{ marginTop: "1.5rem" }}>
        {incident.subjectName} hasn&rsquo;t responded
      </h1>

      <p style={{ color: "var(--ico-graphite)", marginTop: "0.75rem" }}>
        {incident.planLabel} · Expected{" "}
        <span className="tabular">{clockTime(incident.expectedAt)}</span>
      </p>

      <hr className="rule" />

      <section aria-labelledby="happened">
        <h2 id="happened" className="section-label">
          What&rsquo;s happened
        </h2>
        <Timeline entries={incident.tried} />
      </section>

      {incident.nextContact && (
        <section aria-labelledby="next" style={{ marginTop: "2rem" }}>
          <h2 id="next" className="section-label">
            What&rsquo;s next
          </h2>
          <p style={{ margin: 0 }}>
            {incident.nextContact.name} will be contacted{" "}
            {relativeTime(incident.nextContact.at)}.
          </p>
        </section>
      )}

      <div style={{ marginTop: "2.5rem", display: "grid", gap: "0.75rem" }}>
        <button
          type="button"
          className="action action--attention"
          disabled={busy || !incident.canClaim}
          onClick={() =>
            onAct("claim", (previous) => ({
              ...previous,
              ownerName: "You",
              leaseExpiresAt: new Date(Date.now() + 10 * 60_000).toISOString(),
              canClaim: false,
              canResolve: true,
            }))
          }
        >
          I&rsquo;m checking
        </button>

        {/*
          Not a link to a phone number. The product never hands out contact details, even
          to the people it is asking for help — a responder uses their own address book.
        */}
        <p
          style={{
            color: "var(--ico-graphite)",
            fontSize: "0.9375rem",
            textAlign: "center",
            margin: "0.25rem 0 0",
          }}
        >
          Tapping this pauses the next contact for 10 minutes. It doesn&rsquo;t mean{" "}
          {incident.subjectName} is okay.
        </p>
      </div>
    </>
  );
}

function Checking({
  incident,
  busy,
  onAct,
}: {
  incident: Incident;
  busy: boolean;
  onAct: Runner;
}) {
  const [remaining, setRemaining] = useState(() =>
    incident.leaseExpiresAt ? countdown(incident.leaseExpiresAt) : "00:00",
  );

  useEffect(() => {
    if (!incident.leaseExpiresAt) return;
    const id = setInterval(
      () => setRemaining(countdown(incident.leaseExpiresAt as string)),
      1000,
    );
    return () => clearInterval(id);
  }, [incident.leaseExpiresAt]);

  const who = incident.ownerName ?? "Someone";

  return (
    <>
      <h1 className="headline" style={{ marginTop: "1.5rem" }}>
        {who === "You" ? "You’re checking" : `${who} is checking`}
      </h1>

      {/*
        Announced politely rather than assertively: a screen reader should not interrupt
        every second, but somebody should be told when the state changed.
      */}
      <p
        className="tabular"
        aria-live="polite"
        style={{ fontSize: "2rem", marginTop: "0.5rem" }}
      >
        {remaining}
        <span style={{ fontSize: "1rem", color: "var(--ico-graphite)" }}> remaining</span>
      </p>

      {/* The sentence the whole product turns on. */}
      <p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>
        Backup contact is paused while {who === "You" ? "you check" : `${who} checks`} on{" "}
        {incident.subjectName}. If nothing happens before the time runs out, contacting
        resumes automatically.
      </p>

      <hr className="rule" />

      <div style={{ display: "grid", gap: "0.75rem" }}>
        <button
          type="button"
          className="action action--resolve"
          disabled={busy || !incident.canResolve}
          onClick={() =>
            onAct("resolve", (previous) => ({
              ...previous,
              state: "RESOLVED",
              leaseExpiresAt: null,
              canClaim: false,
              canResolve: false,
            }))
          }
        >
          I reached {incident.subjectName} — all okay
        </button>

        <button
          type="button"
          className="action action--quiet"
          disabled={busy}
          onClick={() =>
            onAct("unable", (previous) => ({
              ...previous,
              ownerName: null,
              leaseExpiresAt: null,
              canClaim: true,
              canResolve: false,
            }))
          }
        >
          I couldn&rsquo;t reach them
        </button>
      </div>

      <p
        style={{
          color: "var(--ico-graphite)",
          fontSize: "0.9375rem",
          marginTop: "1.25rem",
        }}
      >
        &ldquo;I couldn&rsquo;t reach them&rdquo; isn&rsquo;t a failure. It starts the next
        contact straight away instead of waiting.
      </p>
    </>
  );
}
