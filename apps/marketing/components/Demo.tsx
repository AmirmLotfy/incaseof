"use client";

import { useEffect, useRef, useState } from "react";
import { idempotencyKey, type CompileResult, type MomentSummary } from "@/lib/api";
import { publicApiUrl } from "@/lib/runtime";
import { TraceInspector } from "@/components/TraceInspector";

interface DemoSession {
  sessionToken: string;
  expiresInSeconds: number;
  subjectDisplayName: string;
  synthetic: true;
}

interface CreatedPlan {
  planId: string;
  label: string;
}

interface TimelineEvent {
  at: string;
  actor: string;
  event: string;
  metadata: Record<string, unknown>;
}

type Stage = "unconfigured" | "idle" | "preview" | "draft" | "running" | "alert" | "failed";

export function Demo() {
  const [baseUrl, setBaseUrl] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [session, setSession] = useState<DemoSession | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [preview, setPreview] = useState<CompileResult | null>(null);
  const [plan, setPlan] = useState<CreatedPlan | null>(null);
  const [moment, setMoment] = useState<MomentSummary | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [responderUrl, setResponderUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    void publicApiUrl().then((url) => {
      setBaseUrl(url);
      setChecked(true);
      if (!url) setStage("unconfigured");
    });
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  async function request<T>(
    path: string,
    init: RequestInit = {},
    auth: string | null | undefined = session?.sessionToken,
  ): Promise<T> {
    if (!baseUrl) throw new Error("The live demo API is not configured.");
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        accept: "application/json",
        ...(auth ? { authorization: `Bearer ${auth}` } : {}),
        ...(init.body ? { "content-type": "application/json" } : {}),
        ...(init.headers ?? {}),
      },
    });
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) throw new Error(String(body.title ?? "The live demo request failed."));
    return body as T;
  }

  async function run(operation: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await operation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The live demo did not complete.");
      setStage("failed");
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    await run(async () => {
      const nextSession = await request<DemoSession>("/v1/demo/session", { method: "POST" }, null);
      setSession(nextSession);
      const compiled = await request<CompileResult>(
        "/v1/demo/plans/compile",
        {
          method: "POST",
          body: JSON.stringify({
            utterance: "Mona should check in every evening at 9 PM. Remind her, then ask Maya, then Omar.",
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          }),
        },
        nextSession.sessionToken,
      );
      setPreview(compiled);
      setStage("preview");
    });
  }

  async function saveDraft() {
    if (!preview) return;
    await run(async () => {
      const created = await request<CreatedPlan>("/v1/demo/plans", {
        method: "POST",
        body: JSON.stringify({ compiledPlan: preview.compiledPlan, ownerDisplayName: "Mona" }),
      });
      setPlan(created);
      setStage("draft");
    });
  }

  async function startDrill() {
    if (!plan) return;
    await run(async () => {
      const started = await request<{ moment: MomentSummary }>(`/v1/demo/plans/${plan.planId}/test`, {
        method: "POST",
        headers: { "idempotency-key": idempotencyKey() },
      });
      setMoment(started.moment);
      setStage("running");
      pollRef.current = window.setInterval(() => void poll(), 2000);
    });
  }

  async function poll() {
    try {
      const next = await request<MomentSummary>("/v1/demo/moments/next");
      setMoment(next);
      if (!next.alertId) return;
      const timeline = await request<{ events: TimelineEvent[] }>(`/v1/demo/alerts/${next.alertId}/timeline`);
      setEvents(timeline.events);
      setStage("alert");
      try {
        const link = await request<{ responderUrl: string }>(`/v1/demo/alerts/${next.alertId}/responder-link`);
        setResponderUrl(link.responderUrl);
      } catch {
        // The policy boundary may not yet have reached the Circle rung. Polling continues.
      }
    } catch {
      // Scheduler and workflow state converge asynchronously; retain the last verified state.
    }
  }

  if (!checked) return <DemoState title="Connecting to the demo environment…" />;
  if (stage === "unconfigured") {
    return (
      <DemoState
        title="The live judge demo is not deployed on this host."
        body="No browser simulation is substituted. Publish runtime-config.json after the demo stack is accepted."
      />
    );
  }

  return (
    <div>
      <p className="demo-banner">
        <strong>Live AWS demo.</strong> Data is synthetic and isolated per session. Every event below comes back from the deployed demo API.
      </p>
      <div className="app-grid" style={{ marginTop: "2.5rem" }}>
        <section className="app-pane">
          <p className="eyebrow">Mona’s evening check-in</p>
          <h2>Review before anything runs</h2>
          {stage === "idle" && (
            <button className="cta app-button" disabled={busy} onClick={() => void start()}>
              Compile the plan
            </button>
          )}
          {preview && (
            <div className="app-preview">
              <p className="eyebrow">AgentCore preview · not active</p>
              <h3>{preview.plan.label}</h3>
              <p>{preview.plan.type} · {preview.plan.timezone}</p>
              <ol className="app-steps">
                {preview.plan.steps.map((step) => (
                  <li key={step.sequence}>
                    <span className="mono">+{Math.round(step.offsetSeconds / 60)}m</span>{" "}
                    {step.action.replaceAll("_", " ")}{step.targetRole ? ` — ${step.targetRole}` : ""}
                  </li>
                ))}
              </ol>
              {stage === "preview" && <button className="cta app-button" disabled={busy} onClick={() => void saveDraft()}>Save this draft</button>}
              {stage === "draft" && <button className="cta app-button" disabled={busy} onClick={() => void startDrill()}>Test this plan</button>}
            </div>
          )}
          {(stage === "running" || stage === "alert") && moment && (
            <div className="app-moment" aria-live="polite">
              <p className="eyebrow">Real accelerated Moment</p>
              <h3>{moment.planLabel}</h3>
              <p>{moment.alertState ?? moment.status} · {new Date(moment.dueAt).toLocaleTimeString()}</p>
              {responderUrl && <a className="cta app-button" href={responderUrl} target="_blank" rel="noreferrer">Open responder link</a>}
            </div>
          )}
          {error && <p role="alert" className="app-error">{error}</p>}
        </section>

        <aside className="app-pane">
          <p className="eyebrow">Verified audit timeline</p>
          {events.length === 0 ? (
            <p className="app-muted">{stage === "running" ? "Waiting for EventBridge Scheduler and Step Functions…" : "No workflow events yet."}</p>
          ) : (
            <ol className="demo-timeline" aria-live="polite">
              {events.map((event, index) => (
                <li key={`${event.at}-${index}`}>
                  <span className="mono">{new Date(event.at).toLocaleTimeString()}</span>
                  <span>{event.event.replaceAll("_", " ")}</span>
                </li>
              ))}
            </ol>
          )}
          {preview && <TraceInspector trace={preview.trace} />}
        </aside>
      </div>
    </div>
  );
}

function DemoState({ title, body }: { title: string; body?: string }) {
  return <div className="app-state"><p className="eyebrow">Judge demo</p><h2>{title}</h2>{body && <p>{body}</p>}</div>;
}
