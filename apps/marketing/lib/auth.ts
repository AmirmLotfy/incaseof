import type { RuntimeConfig } from "./runtime";

const TOKEN_KEY = "ico.web.access-token";
const VERIFIER_KEY = "ico.oauth.verifier";
const STATE_KEY = "ico.oauth.state";

function base64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

export function token(): string | null {
  return typeof window === "undefined" ? null : sessionStorage.getItem(TOKEN_KEY);
}

export function signOut(config: RuntimeConfig): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  const query = new URLSearchParams({
    client_id: config.webClientId,
    logout_uri: `${window.location.origin}/`,
  });
  window.location.assign(`https://${config.cognitoDomain}/logout?${query}`);
}

export async function beginSignIn(config: RuntimeConfig): Promise<void> {
  const verifier = base64url(crypto.getRandomValues(new Uint8Array(48)));
  const challenge = base64url(
    new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))),
  );
  const state = base64url(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);

  const redirectUri = `${window.location.origin}/app/`;
  const query = new URLSearchParams({
    client_id: config.webClientId,
    response_type: "code",
    scope: "openid email",
    redirect_uri: redirectUri,
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
  });
  window.location.assign(`https://${config.cognitoDomain}/oauth2/authorize?${query}`);
}

export async function completeSignIn(config: RuntimeConfig): Promise<boolean> {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  if (!code) return Boolean(token());
  const state = url.searchParams.get("state");
  const expectedState = sessionStorage.getItem(STATE_KEY);
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!state || state !== expectedState || !verifier) throw new Error("The sign-in response is invalid.");

  const response = await fetch(`https://${config.cognitoDomain}/oauth2/token`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.webClientId,
      code,
      redirect_uri: `${window.location.origin}/app/`,
      code_verifier: verifier,
    }),
  });
  if (!response.ok) throw new Error("Sign-in could not be completed.");
  const body = (await response.json()) as { access_token?: string };
  if (!body.access_token) throw new Error("Cognito returned no access token.");
  sessionStorage.setItem(TOKEN_KEY, body.access_token);
  sessionStorage.removeItem(VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);
  window.history.replaceState({}, "", "/app/");
  return true;
}
