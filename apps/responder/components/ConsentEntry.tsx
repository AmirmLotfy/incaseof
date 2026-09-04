"use client";

import { useEffect, useState } from "react";
import { decideInvitation, invitation, type Invitation } from "@/lib/invitation";

export function ConsentEntry({ initialToken }: { initialToken: string }) {
  const token = typeof window === "undefined" ? initialToken : decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) ?? "");
  const [value, setValue] = useState<Invitation | null | "LOADING">("LOADING");
  const [busy, setBusy] = useState(false);

  useEffect(() => { void invitation(token).then(setValue); }, [token]);

  if (value === "LOADING") return <Shell title="Opening this invitation…"><p>Verifying the private link.</p></Shell>;
  if (!value) return <Shell title="This link isn’t valid"><p>It may have expired or already been withdrawn. Ask the person who invited you for a new link.</p></Shell>;
  if (value.status === "ACCEPTED") return <Shell title="You’re in the Circle"><p>You agreed to help with {value.ownerDisplayName}’s plan. You can withdraw by asking them to remove you.</p></Shell>;
  if (value.status === "DECLINED" || value.status === "REVOKED") return <Shell title="This invitation is closed"><p>No contact permission is active.</p></Shell>;

  async function decide(action: "accept" | "decline") {
    setBusy(true);
    const updated = await decideInvitation(token, action);
    setValue(updated);
    setBusy(false);
  }

  return (
    <Shell title={`${value.ownerDisplayName} invited you`}>
      <p>You’re being asked to be {value.displayName}, the {value.role?.toLowerCase()} contact for {value.planCount || "future"} plan{value.planCount === 1 ? "" : "s"}.</p>
      <p className="consent-detail">ICO contacts you only when an expected moment remains unresolved. You are never asked to monitor a person continuously, and acknowledging is not resolving.</p>
      <div className="consent-actions">
        <button className="action action--resolve" disabled={busy} onClick={() => void decide("accept")}>Accept and consent</button>
        <button className="action action--quiet" disabled={busy} onClick={() => void decide("decline")}>Decline</button>
      </div>
    </Shell>
  );
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return <main style={{ maxWidth: "var(--measure)", margin: "0 auto", padding: "3rem 1.25rem 5rem" }}><p className="wordmark">In Case Of</p><p className="section-label" style={{ marginTop: "2rem" }}>Circle consent</p><h1 className="headline">{title}</h1><div style={{ color: "var(--ico-graphite)", marginTop: "1rem" }}>{children}</div></main>;
}
