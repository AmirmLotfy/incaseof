"use client";

import { useEffect, useState } from "react";
import { act } from "@/lib/api";
import {
  clockTime,
  countdown,
  relativeTime,
  type Incident,
} from "@/lib/incident";
import { copy, type Locale } from "@/lib/i18n";
import { LanguageToggle } from "./LanguageToggle";
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
export function IncidentRoom({ incident, token, locale, onLocaleChange }: { incident: Incident; token: string; locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  const [current, setCurrent] = useState(incident);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const claimed = current.leaseExpiresAt !== null;
  const words = copy[locale];

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
      <LanguageToggle locale={locale} onChange={onLocaleChange} />
      <p className="wordmark">In Case of</p>

      {current.state === "RESOLVED" || current.state === "CANCELLED" ? (
        <Closed incident={current} locale={locale} />
      ) : claimed ? (
        <Checking incident={current} busy={busy} onAct={run} locale={locale} />
      ) : (
        <Unclaimed incident={current} busy={busy} onAct={run} locale={locale} />
      )}

      {failed && (
        <p
          role="alert"
          style={{ color: "var(--ico-critical)", marginTop: "1.5rem" }}
        >
          {words.sendFailed(current.subjectName)}
        </p>
      )}
    </main>
  );
}

type Runner = (
  action: "claim" | "unable" | "resolve",
  next: (previous: Incident) => Incident,
) => void;

function Closed({ incident, locale }: { incident: Incident; locale: Locale }) {
  const words = copy[locale];
  return (
    <>
      <p className="section-label" style={{ marginTop: "2rem" }}>{words.resolved}</p>
      <h1 className="headline" style={{ marginTop: "0.75rem" }}>
        {words.checkClosed}
      </h1>
      <p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>
        {words.closedDetail(incident.subjectName)}
      </p>
      <hr className="rule" />
      <section aria-labelledby="resolved-timeline">
        <h2 id="resolved-timeline" className="section-label">{words.whatHappened}</h2>
        <Timeline entries={incident.tried} locale={locale} />
      </section>
    </>
  );
}

function Unclaimed({
  incident,
  busy,
  onAct,
  locale,
}: {
  incident: Incident;
  busy: boolean;
  onAct: Runner;
  locale: Locale;
}) {
  const words = copy[locale];
  return (
    <>
      {/*
        The person first, then the fact. Never speculation: this says somebody has not
        responded, and never that anything is wrong.
      */}
      <h1 className="headline" style={{ marginTop: "1.5rem" }}>
        {words.hasNotResponded(incident.subjectName)}
      </h1>

      <p style={{ color: "var(--ico-graphite)", marginTop: "0.75rem" }}>
        {incident.planLabel} · {words.expected}{" "}
        <span className="tabular">{clockTime(incident.expectedAt, locale)}</span>
      </p>

      <hr className="rule" />

      <section aria-labelledby="happened">
        <h2 id="happened" className="section-label">
          {words.whatsHappened}
        </h2>
        <Timeline entries={incident.tried} locale={locale} />
      </section>

      {incident.nextContact && (
        <section aria-labelledby="next" style={{ marginTop: "2rem" }}>
          <h2 id="next" className="section-label">
            {words.whatsNext}
          </h2>
          <p style={{ margin: 0 }}>
            {words.nextContact(
              incident.nextContact.name,
              relativeTime(incident.nextContact.at, new Date(), locale),
            )}
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
          {words.checking}
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
          {words.claimHelp(incident.subjectName)}
        </p>
      </div>
    </>
  );
}

function Checking({
  incident,
  busy,
  onAct,
  locale,
}: {
  incident: Incident;
  busy: boolean;
  onAct: Runner;
  locale: Locale;
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

  const words = copy[locale];
  const who = incident.ownerName ?? words.someone;
  const isSelf = incident.ownerName === "You";

  return (
    <>
      <h1 className="headline" style={{ marginTop: "1.5rem" }}>
        {isSelf ? words.youChecking : words.personChecking(who)}
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
        <span style={{ fontSize: "1rem", color: "var(--ico-graphite)" }}> {words.remaining}</span>
      </p>

      {/* The sentence the whole product turns on. */}
      <p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>
        {isSelf
          ? words.backupPausedSelf(incident.subjectName)
          : words.backupPausedOther(who, incident.subjectName)}
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
          {words.reached(incident.subjectName)}
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
          {words.unable}
        </button>
      </div>

      <p
        style={{
          color: "var(--ico-graphite)",
          fontSize: "0.9375rem",
          marginTop: "1.25rem",
        }}
      >
        {words.unableHelp}
      </p>
    </>
  );
}
