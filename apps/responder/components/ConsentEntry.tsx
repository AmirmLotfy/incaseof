"use client";

import { useEffect, useState } from "react";
import { decideInvitation, invitation, type Invitation } from "@/lib/invitation";
import { copy, roleLabel, type Locale } from "@/lib/i18n";
import { LanguageToggle } from "./LanguageToggle";
import { useResponderLocale } from "./useResponderLocale";

export function ConsentEntry({ initialToken }: { initialToken: string }) {
  const [locale, setLocale] = useResponderLocale();
  const words = copy[locale];
  const token = typeof window === "undefined" ? initialToken : decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) ?? "");
  const [value, setValue] = useState<Invitation | null | "LOADING">("LOADING");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void invitation(token).then(setValue); }, [token]);

  if (value === "LOADING") return <Shell locale={locale} onLocaleChange={setLocale} title={words.openingInvitation}><p>{words.verifyingLink}</p></Shell>;
  if (!value) return <Shell locale={locale} onLocaleChange={setLocale} title={words.invalidLink}><p>{words.invalidInvitation}</p></Shell>;
  if (value.status === "ACCEPTED") return <Shell locale={locale} onLocaleChange={setLocale} title={words.invitationAccepted}><p>{words.invitationAcceptedBody(value.ownerDisplayName)}</p></Shell>;
  if (value.status === "DECLINED" || value.status === "REVOKED") return <Shell locale={locale} onLocaleChange={setLocale} title={words.invitationClosed}><p>{words.noPermission}</p></Shell>;

  async function decide(action: "accept" | "decline") {
    setBusy(true);
    const updated = await decideInvitation(token, action);
    setValue(updated);
    setBusy(false);
  }

  return (
    <Shell locale={locale} onLocaleChange={setLocale} title={words.invitedYou(value.ownerDisplayName)}>
      <p>{words.invitationSummary(value.displayName, roleLabel(value.role, locale), value.planCount)}</p>
      <p className="consent-detail">{words.consentDetail}</p>
      <div className="consent-actions">
        <button className="action action--resolve" disabled={busy} onClick={() => void decide("accept")}>{words.accept}</button>
        <button className="action action--quiet" disabled={busy} onClick={() => void decide("decline")}>{words.decline}</button>
      </div>
    </Shell>
  );
}

function Shell({ title, children, locale, onLocaleChange }: { title: string; children: React.ReactNode; locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  return <main style={{ maxWidth: "var(--measure)", margin: "0 auto", padding: "3rem 1.25rem 5rem" }}><LanguageToggle locale={locale} onChange={onLocaleChange} /><p className="wordmark">In Case Of</p><p className="section-label" style={{ marginTop: "2rem" }}>{copy[locale].circleConsent}</p><h1 className="headline">{title}</h1><div style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>{children}</div></main>;
}
