import type { Incident, IncidentError } from "./incident";

/**
 * Talking to the API.
 *
 * When no API is configured — which is the state of the world until the stack is deployed —
 * this serves a local incident so the surface can be built, reviewed and tested. That is a
 * data source, not a second product: every component, state and interaction below is the
 * same code the deployed API drives.
 */
const BASE_URL = process.env.NEXT_PUBLIC_ICO_API_URL ?? "";

export const isLive = BASE_URL.length > 0;

export async function fetchIncident(token: string): Promise<Incident | IncidentError> {
  if (!isLive) return localIncident(token);

  try {
    const response = await fetch(`${BASE_URL}/r/${encodeURIComponent(token)}`, {
      // Never cached. A responder returning to the page must see the current state, not
      // whether somebody was checking four minutes ago.
      cache: "no-store",
      headers: { accept: "application/json" },
    });
    if (response.status === 403 || response.status === 404 || response.status === 410) {
      return "INVALID_LINK";
    }
    if (!response.ok) return "UNREACHABLE";
    return (await response.json()) as Incident;
  } catch {
    return "UNREACHABLE";
  }
}

export async function act(
  token: string,
  action: "claim" | "extend" | "unable" | "resolve",
): Promise<boolean> {
  if (!isLive) return true;
  try {
    const response = await fetch(
      `${BASE_URL}/v1/r/${encodeURIComponent(token)}/${action}`,
      { method: "POST", cache: "no-store" },
    );
    return response.ok;
  } catch {
    return false;
  }
}

/** The worked example from build contract §21, so the surface renders without a backend. */
function localIncident(token: string): Incident | IncidentError {
  if (token === "expired" || token === "invalid") return "INVALID_LINK";

  // Anchored to now rather than to a fixed hour, so the sample reads as something in
  // progress: the check was 23 minutes ago and the backup is 12 minutes away.
  const now = Date.now();
  const expected = new Date(now - 23 * 60_000);
  const at = (minutes: number) =>
    new Date(expected.getTime() + minutes * 60_000).toISOString();

  return {
    alertId: "alert-demo",
    subjectName: "Mona",
    planLabel: "Evening check",
    expectedAt: expected.toISOString(),
    state: "CIRCLE_ESCALATION",
    tried: [
      { at: at(0), event: "MOMENT_DUE" },
      { at: at(10), event: "ACTION_QUEUED" },
      { at: at(20), event: "CHANNEL_UNAVAILABLE" },
      { at: at(23), event: "STATE_CIRCLE_ESCALATION" },
    ],
    ownerName: null,
    leaseExpiresAt: null,
    canClaim: true,
    canResolve: false,
    nextContact: { name: "Omar", at: at(35) },
  };
}
