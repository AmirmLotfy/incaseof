import type { Incident, IncidentError } from "./incident";

/**
 * Talking to the API.
 *
 * Runtime configuration is loaded from the deployed static origin. Missing configuration
 * fails closed; a responder must never see a convincing fixture while a real Alert runs.
 */
let cachedBaseUrl: Promise<string | null> | null = null;

async function baseUrl(): Promise<string | null> {
  cachedBaseUrl ??= (async () => {
    const embedded = process.env.NEXT_PUBLIC_ICO_API_URL ?? "";
    if (embedded) return embedded.replace(/\/$/, "");
    try {
      const response = await fetch("/runtime-config.json", { cache: "no-store" });
      if (!response.ok) return null;
      const config = (await response.json()) as { apiUrl?: string };
      return config.apiUrl?.replace(/\/$/, "") ?? null;
    } catch {
      return null;
    }
  })();
  return cachedBaseUrl;
}

export async function fetchIncident(token: string): Promise<Incident | IncidentError> {
  const api = await baseUrl();
  if (!api) return "UNREACHABLE";

  try {
    const response = await fetch(`${api}/r/${encodeURIComponent(token)}`, {
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
  const api = await baseUrl();
  if (!api) return false;
  try {
    const response = await fetch(
      `${api}/v1/r/${encodeURIComponent(token)}/${action}`,
      { method: "POST", cache: "no-store" },
    );
    return response.ok;
  } catch {
    return false;
  }
}
