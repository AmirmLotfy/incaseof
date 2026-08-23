/**
 * What the Incident Room knows.
 *
 * Mirrors the responder view the API returns for `GET /r/{token}` — see
 * services/handlers/responding.py. Deliberately narrow: enough for somebody to decide
 * whether to act, and nothing about the subject's other plans, their Circle, or their
 * history.
 *
 * There is no field here for a phone number or a location, because the API returns
 * neither. A responder who wants to ring the person uses their own phone and their own
 * address book — the product does not hand out contact details, even to the people it is
 * asking for help.
 */
export interface Incident {
  alertId: string;
  subjectName: string;
  planLabel: string;
  expectedAt: string;
  state: string;
  tried: TimelineEntry[];
  ownerName: string | null;
  leaseExpiresAt: string | null;
  canClaim: boolean;
  canResolve: boolean;
  nextContact: NextContact | null;
}

export interface TimelineEntry {
  at: string;
  event: string;
}

export interface NextContact {
  name: string;
  at: string;
}

export type IncidentError = "INVALID_LINK" | "UNREACHABLE";

/**
 * Event names, translated.
 *
 * The same mapping as the Android app's Vocabulary.kt, for the same reason: engineering
 * names never reach a screen. Nothing here speculates — the page says what was tried, never
 * what it might mean.
 */
const EVENT_LABELS: Record<string, string> = {
  MOMENT_DUE: "Check requested",
  ACTION_QUEUED: "Reminder sent",
  ACTION_SENT: "Message sent",
  CHANNEL_UNAVAILABLE: "Call unavailable",
  ACTION_SUPPRESSED: "Not sent — already resolved",
  STATE_CIRCLE_ESCALATION: "You were contacted",
  ALERT_CLAIMED: "Someone started checking",
  RESPONDER_VERIFIED: "Confirmed",
};

export function eventLabel(event: string): string {
  return (
    EVENT_LABELS[event] ??
    event.toLowerCase().replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())
  );
}

/** 9:00 PM. Times are the page's core content, so they are rendered with tabular figures. */
export function clockTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

/** "09:42" — how long a lease has left. */
export function countdown(toIso: string, from: Date = new Date()): string {
  const remaining = new Date(toIso).getTime() - from.getTime();
  if (Number.isNaN(remaining) || remaining <= 0) return "00:00";
  const total = Math.floor(remaining / 1000);
  const minutes = String(Math.floor(total / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

/** "in 12 minutes". Approximate on purpose — a ticking countdown manufactures urgency. */
export function relativeTime(toIso: string, from: Date = new Date()): string {
  const gap = new Date(toIso).getTime() - from.getTime();
  if (Number.isNaN(gap) || gap <= 0) return "shortly";

  const minutes = Math.round(gap / 60000);
  if (minutes < 1) return "in less than a minute";
  if (minutes === 1) return "in 1 minute";
  if (minutes < 60) return `in ${minutes} minutes`;
  if (minutes < 90) return "in about an hour";

  const hours = Math.round(minutes / 60);
  return hours === 1 ? "in about an hour" : `in about ${hours} hours`;
}
