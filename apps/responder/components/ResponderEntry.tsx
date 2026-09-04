"use client";

import { useEffect, useState } from "react";
import { fetchIncident } from "@/lib/api";
import type { Incident, IncidentError } from "@/lib/incident";
import { IncidentRoom } from "./IncidentRoom";

export function ResponderEntry({ initialToken }: { initialToken: string }) {
  const [result, setResult] = useState<Incident | IncidentError | "LOADING">("LOADING");
  const token = typeof window === "undefined"
    ? initialToken
    : decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) ?? "");

  useEffect(() => {
    void fetchIncident(token).then(setResult);
  }, [token]);

  if (result === "LOADING") return <Message title="Opening this check…" body="Verifying the private link." />;
  if (result === "INVALID_LINK") return <Message title="This link isn’t valid" body="It may have expired, or the check it belonged to may already be resolved. If someone is expecting you, ask them to send a new one." />;
  if (result === "UNREACHABLE") return <Message title="Couldn’t load this" body="Something went wrong reaching In Case Of. Try again in a moment — the plan is still running either way." />;
  if (result.state === "RESOLVED" || result.state === "CANCELLED") return <Message title="This is closed" body={`${result.subjectName}’s check has been resolved. There’s nothing you need to do.`} />;
  return <IncidentRoom incident={result} token={token} />;
}

function Message({ title, body }: { title: string; body: string }) {
  return <main style={{ maxWidth: "var(--measure)", margin: "0 auto", padding: "4rem 1.25rem" }}><p className="wordmark">In Case Of</p><h1 className="headline" style={{ marginTop: "1.5rem" }}>{title}</h1><p style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>{body}</p></main>;
}
