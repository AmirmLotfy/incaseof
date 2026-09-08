"use client";

import { useEffect, useState } from "react";
import { fetchIncident } from "@/lib/api";
import type { Incident, IncidentError } from "@/lib/incident";
import { copy, type Locale } from "@/lib/i18n";
import { IncidentRoom } from "./IncidentRoom";
import { LanguageToggle } from "./LanguageToggle";
import { useResponderLocale } from "./useResponderLocale";

export function ResponderEntry({ initialToken }: { initialToken: string }) {
  const [locale, setLocale] = useResponderLocale();
  const words = copy[locale];
  const [result, setResult] = useState<Incident | IncidentError | "LOADING">("LOADING");
  const token = typeof window === "undefined"
    ? initialToken
    : decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) ?? "");

  useEffect(() => {
    void fetchIncident(token).then(setResult);
  }, [token]);

  if (result === "LOADING") return <Message locale={locale} onLocaleChange={setLocale} title={words.openingCheck} body={words.verifyingLink} />;
  if (result === "INVALID_LINK") return <Message locale={locale} onLocaleChange={setLocale} title={words.invalidLink} body={words.invalidCheck} />;
  if (result === "UNREACHABLE") return <Message locale={locale} onLocaleChange={setLocale} title={words.unreachable} body={words.unreachableBody} />;
  if (result.state === "RESOLVED" || result.state === "CANCELLED") return <Message locale={locale} onLocaleChange={setLocale} title={words.closed} body={words.closedCheck(result.subjectName)} />;
  return <IncidentRoom incident={result} token={token} locale={locale} onLocaleChange={setLocale} />;
}

function Message({ title, body, locale, onLocaleChange }: { title: string; body: string; locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  return <main style={{ maxWidth: "var(--measure)", margin: "0 auto", padding: "4rem 1.25rem" }}><LanguageToggle locale={locale} onChange={onLocaleChange} /><p className="wordmark">In Case Of</p><h1 className="headline" style={{ marginTop: "1.5rem" }}>{title}</h1><p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>{body}</p></main>;
}
