export interface Invitation {
  invitationId: string;
  ownerDisplayName: string;
  displayName: string;
  relationship: string | null;
  role: string | null;
  status: string;
  expiresAt: string;
  planCount: number;
  consentActive?: boolean;
}

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

export async function invitation(token: string): Promise<Invitation | null> {
  const api = await baseUrl();
  if (!api) return null;
  try {
    const response = await fetch(`${api}/i/${encodeURIComponent(token)}`, { cache: "no-store" });
    return response.ok ? (await response.json()) as Invitation : null;
  } catch {
    return null;
  }
}

export async function decideInvitation(token: string, action: "accept" | "decline"): Promise<Invitation | null> {
  const api = await baseUrl();
  if (!api) return null;
  try {
    const response = await fetch(`${api}/v1/i/${encodeURIComponent(token)}/${action}`, { method: "POST", cache: "no-store" });
    return response.ok ? (await response.json()) as Invitation : null;
  } catch {
    return null;
  }
}
