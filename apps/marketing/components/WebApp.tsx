"use client";

import { useCallback, useEffect, useState } from "react";
import { completeSignIn, beginSignIn, signOut, token } from "@/lib/auth";
import {
  api,
  ApiError,
  idempotencyKey,
  type CompileResult,
  type CircleMemberSummary,
  type HistorySummary,
  type InvitationSummary,
  type MomentSummary,
  type PlanSummary,
} from "@/lib/api";
import { runtimeConfig, type RuntimeConfig } from "@/lib/runtime";

type Status = "loading" | "unconfigured" | "signed-out" | "ready";

export function WebApp() {
  const [status, setStatus] = useState<Status>("loading");
  const [config, setConfig] = useState<RuntimeConfig | null>(null);
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [moment, setMoment] = useState<MomentSummary | null>(null);
  const [circle, setCircle] = useState<CircleMemberSummary[]>([]);
  const [history, setHistory] = useState<HistorySummary[]>([]);
  const [inviteName, setInviteName] = useState("");
  const [inviteRelationship, setInviteRelationship] = useState("");
  const [inviteRole, setInviteRole] = useState<CircleMemberSummary["role"]>("PRIMARY");
  const [pendingInvitation, setPendingInvitation] = useState<InvitationSummary | null>(null);
  const [utterance, setUtterance] = useState("Check on me every evening at 9 PM.");
  const [preview, setPreview] = useState<CompileResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async (nextConfig: RuntimeConfig, accessToken: string) => {
    const [planResult, momentResult, circleResult, historyResult] = await Promise.all([
      api<{ plans: PlanSummary[] }>(nextConfig, accessToken, "/v1/plans"),
      api<MomentSummary>(nextConfig, accessToken, "/v1/moments/next").catch((error) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }),
      api<{ members: CircleMemberSummary[] }>(nextConfig, accessToken, "/v1/circle"),
      api<{ history: HistorySummary[] }>(nextConfig, accessToken, "/v1/history"),
    ]);
    setPlans(planResult.plans);
    setMoment(momentResult);
    setCircle(circleResult.members);
    setHistory(historyResult.history);
  }, []);

  useEffect(() => {
    void (async () => {
      const nextConfig = await runtimeConfig();
      if (!nextConfig) return setStatus("unconfigured");
      setConfig(nextConfig);
      try {
        const authenticated = await completeSignIn(nextConfig);
        if (!authenticated || !token()) return setStatus("signed-out");
        await refresh(nextConfig, token() as string);
        setStatus("ready");
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "Sign-in failed.");
        setStatus("signed-out");
      }
    })();
  }, [refresh]);

  async function run(operation: () => Promise<void>) {
    setBusy(true);
    setNotice("");
    try {
      await operation();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "That did not complete.");
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading") return <State title="Opening your plans" body="Checking the secure app configuration…" />;
  if (status === "unconfigured") {
    return <State title="The web app isn’t deployed yet" body="No API or Cognito runtime configuration is published on this host. No sample data has been substituted." />;
  }
  if (status === "signed-out") {
    return (
      <State title="Your plans, when you need them" body="Sign in securely with Amazon Cognito. The same screen also lets you create an account, confirm it, or recover access.">
        <button className="cta app-button" onClick={() => config && void beginSignIn(config)}>
          Sign in or create account
        </button>
        {notice && <p role="alert" className="app-error">{notice}</p>}
      </State>
    );
  }

  const accessToken = token() as string;
  return (
    <div className="app-grid">
      <section className="app-pane" aria-labelledby="create-plan">
        <p className="eyebrow">Plan compiler</p>
        <h2 id="create-plan">What should happen?</h2>
        <label className="app-label" htmlFor="plan-description">Describe one expected moment</label>
        <textarea id="plan-description" className="app-input" rows={5} value={utterance} onChange={(event) => setUtterance(event.target.value)} />
        <button
          className="cta app-button"
          disabled={busy || utterance.trim().length < 8}
          onClick={() => run(async () => {
            setPreview(await api<CompileResult>(config as RuntimeConfig, accessToken, "/v1/plans/compile", {
              method: "POST",
              body: JSON.stringify({ utterance, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone }),
            }));
          })}
        >
          Compile a safe preview
        </button>

        {preview && (
          <div className="app-preview" aria-live="polite">
            <p className="eyebrow">Not active — review first</p>
            <h3>{preview.plan.label}</h3>
            <p>{preview.plan.type} · {preview.plan.timezone} · {Math.round(preview.plan.graceSeconds / 60)} minute grace</p>
            <ol className="app-steps">
              {preview.plan.steps.map((step) => (
                <li key={step.sequence}><span className="mono">+{Math.round(step.offsetSeconds / 60)}m</span> {step.action.replaceAll("_", " ")}{step.targetRole ? ` — ${step.targetRole}` : ""}</li>
              ))}
            </ol>
            <button
              className="cta app-button"
              disabled={busy}
              onClick={() => run(async () => {
                const created = await api<PlanSummary>(config as RuntimeConfig, accessToken, "/v1/plans", {
                  method: "POST",
                  body: JSON.stringify({ compiledPlan: preview.compiledPlan }),
                });
                setPreview(null);
                setNotice(`${created.label} is saved as a draft. Add required Circle consent before activation.`);
                await refresh(config as RuntimeConfig, accessToken);
              })}
            >
              Save draft
            </button>
          </div>
        )}
      </section>

      <aside className="app-pane" aria-labelledby="plans-heading">
        <div className="app-row">
          <div><p className="eyebrow">Your account</p><h2 id="plans-heading">Plans</h2></div>
          <button className="app-link" onClick={() => config && signOut(config)}>Sign out</button>
        </div>
        {moment ? (
          <div className="app-moment">
            <p className="eyebrow">Next expected moment</p>
            <h3>{moment.planLabel}</h3>
            <p className="mono">{new Date(moment.dueAt).toLocaleString()}</p>
            <p>{moment.alertState ?? moment.status}{moment.isDrill ? " · Drill" : ""}</p>
            <div className="app-actions" aria-label="Expected moment actions">
              {moment.alertId && moment.alertState !== "RESOLVED" && moment.alertState !== "CANCELLED" && (
                <button
                  className="cta app-button"
                  disabled={busy}
                  onClick={() => run(async () => {
                    await api(config as RuntimeConfig, accessToken, `/v1/moments/${moment.momentId}/confirm`, {
                      method: "POST",
                      headers: { "idempotency-key": idempotencyKey() },
                    });
                    setNotice("You confirmed this moment. The Alert is resolved.");
                    await refresh(config as RuntimeConfig, accessToken);
                  })}
                >I’m okay</button>
              )}
              <button
                className="app-link"
                disabled={busy || moment.status === "CANCELLED" || moment.status === "RESOLVED"}
                onClick={() => run(async () => {
                  await api(config as RuntimeConfig, accessToken, `/v1/moments/${moment.momentId}/extend`, {
                    method: "POST",
                    headers: { "idempotency-key": idempotencyKey() },
                    body: JSON.stringify({ seconds: 1800 }),
                  });
                  setNotice("This moment was moved 30 minutes. The plan itself did not change.");
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >Give me 30 minutes</button>
              <button
                className="app-link"
                disabled={busy || moment.status === "CANCELLED" || moment.status === "RESOLVED"}
                onClick={() => {
                  if (!window.confirm("Cancel this expected moment? This does not delete or pause the plan.")) return;
                  void run(async () => {
                    await api(config as RuntimeConfig, accessToken, `/v1/moments/${moment.momentId}/cancel`, {
                      method: "POST",
                      headers: { "idempotency-key": idempotencyKey() },
                    });
                    setNotice("This expected moment was cancelled. The plan remains available.");
                    await refresh(config as RuntimeConfig, accessToken);
                  });
                }}
              >Cancel this moment</button>
            </div>
          </div>
        ) : <p className="app-muted">Nothing is expected right now.</p>}
        <div className="app-plan-list">
          {plans.length === 0 ? <p className="app-muted">No plans yet.</p> : plans.map((plan) => (
            <article key={plan.planId} className="app-plan">
              <div><h3>{plan.label}</h3><p>{plan.active ? (plan.paused ? "Paused" : "Active") : "Draft"}</p></div>
              <button
                className="app-link"
                disabled={busy}
                onClick={() => run(async () => {
                  await api(config as RuntimeConfig, accessToken, `/v1/plans/${plan.planId}/test`, {
                    method: "POST",
                    headers: { "idempotency-key": idempotencyKey() },
                  });
                  setNotice("Real Drill started. The due event will use the deployed Scheduler and workflow.");
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >Test this plan</button>
              <button
                className="app-link"
                disabled={busy}
                onClick={() => run(async () => {
                  const action = !plan.active ? "activate" : plan.paused ? "resume" : "pause";
                  await api(config as RuntimeConfig, accessToken, `/v1/plans/${plan.planId}/${action}`, {
                    method: "POST",
                    headers: { "idempotency-key": idempotencyKey() },
                  });
                  setNotice(action === "activate" ? "Plan activated." : action === "resume" ? "Plan resumed." : "Plan paused.");
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >{!plan.active ? "Activate" : plan.paused ? "Resume" : "Pause"}</button>
            </article>
          ))}
        </div>

        <div className="app-section">
          <p className="eyebrow">Consented responders</p>
          <h2>Circle</h2>
          {circle.length === 0 ? <p className="app-muted">No one has been invited.</p> : (
            <ul className="app-plan-list">
              {circle.map((member) => (
                <li key={member.memberId} className="app-plan">
                  <div><h3>{member.displayName}</h3><p>{member.relationship || "Circle member"} · {member.role}</p></div>
                  <div className="app-plan-actions">
                    <span className="mono">{member.status}</span>
                    {member.status !== "REMOVED" && (
                      <button
                        className="app-link"
                        disabled={busy}
                        onClick={() => {
                          if (!window.confirm(`Remove ${member.displayName} from your Circle? Their active consent will be withdrawn.`)) return;
                          void run(async () => {
                            await api(config as RuntimeConfig, accessToken, `/v1/circle/members/${member.memberId}`, {
                              method: "DELETE",
                              headers: { "idempotency-key": idempotencyKey() },
                            });
                            setNotice(`${member.displayName} was removed and their active consent was withdrawn.`);
                            await refresh(config as RuntimeConfig, accessToken);
                          });
                        }}
                      >Remove</button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <label className="app-label" htmlFor="invite-name">Invite someone</label>
          <input id="invite-name" className="app-input" value={inviteName} onChange={(event) => setInviteName(event.target.value)} placeholder="Name" />
          <input className="app-input app-input--compact" value={inviteRelationship} onChange={(event) => setInviteRelationship(event.target.value)} placeholder="Relationship (optional)" aria-label="Relationship" />
          <select className="app-input app-input--compact" value={inviteRole} onChange={(event) => setInviteRole(event.target.value as CircleMemberSummary["role"])} aria-label="Responder role">
            <option value="PRIMARY">Primary</option><option value="BACKUP">Backup</option><option value="TERTIARY">Tertiary</option>
          </select>
          <button className="cta app-button" disabled={busy || !inviteName.trim()} onClick={() => run(async () => {
            const invitation = await api<InvitationSummary>(config as RuntimeConfig, accessToken, "/v1/circle/invitations", {
              method: "POST",
              headers: { "idempotency-key": idempotencyKey() },
              body: JSON.stringify({ displayName: inviteName.trim(), relationship: inviteRelationship.trim() || null, role: inviteRole }),
            });
            setInviteName(""); setInviteRelationship("");
            setPendingInvitation(invitation);
            setNotice("Invitation created. Share the scoped link; consent is still pending.");
            await refresh(config as RuntimeConfig, accessToken);
          })}>Create invitation</button>
          {pendingInvitation && (
            <div className="app-invitation" aria-live="polite">
              <p className="app-muted">Consent link: <a href={pendingInvitation.inviteUrl} target="_blank" rel="noreferrer">Open or copy invitation</a></p>
              <button className="app-link" disabled={busy} onClick={() => run(async () => {
                const refreshed = await api<InvitationSummary>(config as RuntimeConfig, accessToken, `/v1/circle/invitations/${pendingInvitation.invitationId}/resend`, {
                  method: "POST",
                  headers: { "idempotency-key": idempotencyKey() },
                });
                setPendingInvitation(refreshed);
                setNotice("A fresh seven-day consent link is ready. The previous link no longer needs to be shared.");
              })}>Refresh consent link</button>
            </div>
          )}
        </div>

        <div className="app-section">
          <p className="eyebrow">Closed loops</p>
          <h2>History</h2>
          {history.length === 0 ? <p className="app-muted">No resolved moments yet.</p> : (
            <ul className="app-plan-list">
              {history.map((entry) => (
                <li key={entry.id} className="app-plan">
                  <div><h3>{entry.planLabel}</h3><p>{entry.resolvedBy} · {entry.method}</p></div>
                  <time className="mono" dateTime={entry.resolvedAt}>{new Date(entry.resolvedAt).toLocaleDateString()}</time>
                </li>
              ))}
            </ul>
          )}
        </div>
        {notice && <p role="status" className="app-notice">{notice}</p>}
      </aside>
    </div>
  );
}

function State({ title, body, children }: { title: string; body: string; children?: React.ReactNode }) {
  return <div className="app-state"><p className="eyebrow">In Case Of web</p><h1>{title}</h1><p>{body}</p>{children}</div>;
}
