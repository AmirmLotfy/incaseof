export interface RuntimeConfig {
  apiUrl: string;
  cognitoDomain: string;
  webClientId: string;
}

let cached: Promise<RuntimeConfig | null> | null = null;
let cachedApi: Promise<string | null> | null = null;

export function runtimeConfig(): Promise<RuntimeConfig | null> {
  cached ??= load();
  return cached;
}

export function publicApiUrl(): Promise<string | null> {
  cachedApi ??= loadApi();
  return cachedApi;
}

async function loadApi(): Promise<string | null> {
  const embedded = process.env.NEXT_PUBLIC_ICO_API_URL ?? "";
  if (embedded) return embedded.replace(/\/$/, "");
  try {
    const response = await fetch("/runtime-config.json", { cache: "no-store" });
    if (!response.ok) return null;
    const candidate = (await response.json()) as Partial<RuntimeConfig>;
    return candidate.apiUrl ? candidate.apiUrl.replace(/\/$/, "") : null;
  } catch {
    return null;
  }
}

async function load(): Promise<RuntimeConfig | null> {
  const embedded = {
    apiUrl: process.env.NEXT_PUBLIC_ICO_API_URL ?? "",
    cognitoDomain: process.env.NEXT_PUBLIC_ICO_COGNITO_DOMAIN ?? "",
    webClientId: process.env.NEXT_PUBLIC_ICO_WEB_CLIENT_ID ?? "",
  };
  if (Object.values(embedded).every(Boolean)) return normalize(embedded);

  try {
    const response = await fetch("/runtime-config.json", { cache: "no-store" });
    if (!response.ok) return null;
    const candidate = (await response.json()) as Partial<RuntimeConfig>;
    if (!candidate.apiUrl || !candidate.cognitoDomain || !candidate.webClientId) return null;
    return normalize(candidate as RuntimeConfig);
  } catch {
    return null;
  }
}

function normalize(config: RuntimeConfig): RuntimeConfig {
  return {
    apiUrl: config.apiUrl.replace(/\/$/, ""),
    cognitoDomain: config.cognitoDomain.replace(/^https?:\/\//, "").replace(/\/$/, ""),
    webClientId: config.webClientId,
  };
}
