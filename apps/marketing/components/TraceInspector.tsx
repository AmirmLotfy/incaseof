"use client";

interface TraceInspectorProps {
  trace: Record<string, unknown> | null | undefined;
}

const PRIVATE_KEY = /(account|tenant|subject|person|phone|email|token|secret|endpoint|contact)/i;
const AWS_ACCOUNT = /(arn:aws:[^:]+:[^:]*:)[0-9]{12}:/g;

function redact(value: unknown, key = ""): unknown {
  if (PRIVATE_KEY.test(key)) return "[REDACTED]";
  if (typeof value === "string") return value.replace(AWS_ACCOUNT, "$1[account]:");
  if (Array.isArray(value)) return value.map((item) => redact(item));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) => [
        childKey,
        redact(childValue, childKey),
      ]),
    );
  }
  return value;
}

/**
 * A deliberately literal presenter for backend-supplied compile evidence.
 *
 * It never derives AWS state from browser state and never invents an ARN, policy decision,
 * model result, or workflow event. If the deployed API provides no trace, judges see that
 * absence rather than a simulation. Sensitive identifiers are redacted recursively.
 */
export function TraceInspector({ trace }: TraceInspectorProps) {
  return (
    <details className="demo-trace">
      <summary>Developer Trace</summary>
      {trace ? (
        <>
          <p>Redacted evidence returned by the deployed compile API.</p>
          <pre>{JSON.stringify(redact(trace), null, 2)}</pre>
        </>
      ) : (
        <p>No deployed trace evidence is available for this run.</p>
      )}
    </details>
  );
}
