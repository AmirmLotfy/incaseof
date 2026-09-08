import type { RuntimeConfig } from "./runtime";

export interface PlanStep {
  sequence: number;
  offsetSeconds: number;
  action: string;
  targetRole: string | null;
}

export interface PlanPreview {
  label: string;
  type: string;
  timezone: string;
  graceSeconds: number;
  steps: PlanStep[];
}

export interface CompileResult {
  compiledPlan: Record<string, unknown>;
  plan: PlanPreview;
  warnings: string[];
  trace: Record<string, unknown>;
}

export interface PlanSummary {
  planId: string;
  label: string;
  type: string;
  active: boolean;
  paused: boolean;
}

export interface MomentSummary {
  momentId: string;
  planId: string;
  planLabel: string;
  dueAt: string;
  graceUntil: string;
  status: string;
  isDrill: boolean;
  timeScale: number;
  alertId: string | null;
  alertState: string | null;
}

export interface CircleMemberSummary {
  memberId: string;
  displayName: string;
  relationship: string | null;
  role: "PRIMARY" | "BACKUP" | "TERTIARY";
  status: string;
}

export interface InvitationSummary {
  invitationId: string;
  status: string;
  inviteUrl: string;
}

export interface HistorySummary {
  id: string;
  alertId: string;
  planLabel: string;
  resolvedAt: string;
  resolvedBy: string;
  method: string;
  state: string;
}

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

export async function api<T>(
  config: RuntimeConfig,
  accessToken: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${config.apiUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      accept: "application/json",
      authorization: `Bearer ${accessToken}`,
      ...(init.body ? { "content-type": "application/json" } : {}),
      ...(init.headers ?? {}),
    },
  });
  const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok) {
    throw new ApiError(response.status, String(body.title ?? "The request could not be completed."));
  }
  return body as T;
}

export function idempotencyKey(): string {
  return crypto.randomUUID();
}
