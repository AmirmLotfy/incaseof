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
import { enumLabel, webCopy, type Locale } from "@/lib/i18n";
import { LanguageToggle } from "./LanguageToggle";
import { useLocale } from "./useLocale";

type Status = "loading" | "unconfigured" | "signed-out" | "ready";

type AccountDeletion = {
  requestId: string;
  status: "PENDING" | "PROCESSING";
  requestedAt: string;
  monitoringStopped: true;
  nextSteps: string[];
};

export function WebApp() {
  const [locale, setLocale] = useLocale();
  const words = webCopy[locale];
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
  const [utterance, setUtterance] = useState("");
  const [preview, setPreview] = useState<CompileResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deletion, setDeletion] = useState<AccountDeletion | null>(null);

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
        try {
          await refresh(nextConfig, token() as string);
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 410) throw error;
          setDeletion(
            await api<AccountDeletion>(
              nextConfig,
              token() as string,
              "/v1/account/deletion",
            ),
          );
        }
        setStatus("ready");
      } catch (error) {
        setNotice(words.signInFailed);
        setStatus("signed-out");
      }
    })();
  }, [refresh, words.signInFailed]);

  async function run(operation: () => Promise<void>) {
    setBusy(true);
    setNotice("");
    try {
      await operation();
    } catch (error) {
      setNotice(words.requestFailed);
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading") return <State locale={locale} onLocaleChange={setLocale} title={words.openingPlans} body={words.checkingConfig} />;
  if (status === "unconfigured") {
    return <State locale={locale} onLocaleChange={setLocale} title={words.appNotDeployed} body={words.appNotDeployedBody} />;
  }
  if (status === "signed-out") {
    return (
      <State locale={locale} onLocaleChange={setLocale} title={words.plansWhenNeeded} body={words.signInBody}>
        <button className="cta app-button" onClick={() => config && void beginSignIn(config)}>
          {words.signIn}
        </button>
        {notice && <p role="alert" className="app-error">{notice}</p>}
      </State>
    );
  }

  const accessToken = token() as string;
  if (deletion) {
    return (
      <State
        locale={locale}
        onLocaleChange={setLocale}
        title={words.deletionProgress}
        body={words.deletionProgressBody}
      >
        <p className="mono app-deletion-status" role="status">
          {deletion.status} · {words.requested} {new Date(deletion.requestedAt).toLocaleString(locale === "ar" ? "ar-EG" : "en-US")}
        </p>
        <ol className="app-steps">
          {words.deletionSteps.map((step) => <li key={step}>{step}</li>)}
        </ol>
        <button className="app-link" onClick={() => config && signOut(config)}>{words.signOut}</button>
      </State>
    );
  }
  return (
    <>
      <LanguageToggle locale={locale} onChange={setLocale} />
      <div className="app-grid">
      <section className="app-pane" aria-labelledby="create-plan">
        <p className="eyebrow">{words.compiler}</p>
        <h2 id="create-plan">{words.whatShouldHappen}</h2>
        <label className="app-label" htmlFor="plan-description">{words.describeMoment}</label>
        <textarea id="plan-description" className="app-input" rows={5} value={utterance} placeholder={words.descriptionPlaceholder} onChange={(event) => setUtterance(event.target.value)} />
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
          {words.compilePreview}
        </button>

        {preview && (
          <div className="app-preview" aria-live="polite">
            <p className="eyebrow">{words.reviewFirst}</p>
            <h3>{preview.plan.label}</h3>
            <p>{enumLabel(preview.plan.type, locale)} · <bdi>{preview.plan.timezone}</bdi> · {words.minuteGrace(Math.round(preview.plan.graceSeconds / 60))}</p>
            <ol className="app-steps">
              {preview.plan.steps.map((step) => (
                <li key={step.sequence}><span className="mono">+{Math.round(step.offsetSeconds / 60)}m</span> {enumLabel(step.action, locale)}{step.targetRole ? ` — ${enumLabel(step.targetRole, locale)}` : ""}</li>
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
                setNotice(words.draftSaved(created.label));
                await refresh(config as RuntimeConfig, accessToken);
              })}
            >
              {words.saveDraft}
            </button>
          </div>
        )}
      </section>

      <aside className="app-pane" aria-labelledby="plans-heading">
        <div className="app-row">
          <div><p className="eyebrow">{words.yourAccount}</p><h2 id="plans-heading">{words.plans}</h2></div>
          <button className="app-link" onClick={() => config && signOut(config)}>{words.signOut}</button>
        </div>
        {moment ? (
          <div className="app-moment">
            <p className="eyebrow">{words.nextMoment}</p>
            <h3>{moment.planLabel}</h3>
            <p className="mono"><bdi>{new Date(moment.dueAt).toLocaleString(locale === "ar" ? "ar-EG" : "en-US")}</bdi></p>
            <p>{enumLabel(moment.alertState ?? moment.status, locale)}{moment.isDrill ? ` · ${words.drill}` : ""}</p>
            <div className="app-actions" aria-label={words.momentActions}>
              {moment.alertId && moment.alertState !== "RESOLVED" && moment.alertState !== "CANCELLED" && (
                <button
                  className="cta app-button"
                  disabled={busy}
                  onClick={() => run(async () => {
                    await api(config as RuntimeConfig, accessToken, `/v1/moments/${moment.momentId}/confirm`, {
                      method: "POST",
                      headers: { "idempotency-key": idempotencyKey() },
                    });
                    setNotice(words.confirmed);
                    await refresh(config as RuntimeConfig, accessToken);
                  })}
                >{words.imOkay}</button>
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
                  setNotice(words.extended);
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >{words.giveThirty}</button>
              <button
                className="app-link"
                disabled={busy || moment.status === "CANCELLED" || moment.status === "RESOLVED"}
                onClick={() => {
                  if (!window.confirm(words.cancelQuestion)) return;
                  void run(async () => {
                    await api(config as RuntimeConfig, accessToken, `/v1/moments/${moment.momentId}/cancel`, {
                      method: "POST",
                      headers: { "idempotency-key": idempotencyKey() },
                    });
                    setNotice(words.cancelled);
                    await refresh(config as RuntimeConfig, accessToken);
                  });
                }}
              >{words.cancelMoment}</button>
            </div>
          </div>
        ) : <p className="app-muted">{words.nothingExpected}</p>}
        <div className="app-plan-list">
          {plans.length === 0 ? <p className="app-muted">{words.noPlans}</p> : plans.map((plan) => (
            <article key={plan.planId} className="app-plan">
              <div><h3>{plan.label}</h3><p>{plan.active ? (plan.paused ? words.paused : words.active) : words.draft}</p></div>
              <button
                className="app-link"
                disabled={busy}
                onClick={() => run(async () => {
                  await api(config as RuntimeConfig, accessToken, `/v1/plans/${plan.planId}/test`, {
                    method: "POST",
                    headers: { "idempotency-key": idempotencyKey() },
                  });
                  setNotice(words.drillStarted);
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >{words.testPlan}</button>
              <button
                className="app-link"
                disabled={busy}
                onClick={() => run(async () => {
                  const action = !plan.active ? "activate" : plan.paused ? "resume" : "pause";
                  await api(config as RuntimeConfig, accessToken, `/v1/plans/${plan.planId}/${action}`, {
                    method: "POST",
                    headers: { "idempotency-key": idempotencyKey() },
                  });
                  setNotice(action === "activate" ? words.activated : action === "resume" ? words.resumed : words.pausedNotice);
                  await refresh(config as RuntimeConfig, accessToken);
                })}
              >{!plan.active ? words.activate : plan.paused ? words.resume : words.pause}</button>
            </article>
          ))}
        </div>

        <div className="app-section">
          <p className="eyebrow">{words.consentedResponders}</p>
          <h2>{words.circle}</h2>
          {circle.length === 0 ? <p className="app-muted">{words.noInvites}</p> : (
            <ul className="app-plan-list">
              {circle.map((member) => (
                <li key={member.memberId} className="app-plan">
                  <div><h3>{member.displayName}</h3><p>{member.relationship || words.circleMember} · {enumLabel(member.role, locale)}</p></div>
                  <div className="app-plan-actions">
                    <span className="mono">{member.status}</span>
                    {member.status !== "REMOVED" && (
                      <button
                        className="app-link"
                        disabled={busy}
                        onClick={() => {
                          if (!window.confirm(words.removeQuestion(member.displayName))) return;
                          void run(async () => {
                            await api(config as RuntimeConfig, accessToken, `/v1/circle/members/${member.memberId}`, {
                              method: "DELETE",
                              headers: { "idempotency-key": idempotencyKey() },
                            });
                            setNotice(words.removed(member.displayName));
                            await refresh(config as RuntimeConfig, accessToken);
                          });
                        }}
                      >{words.remove}</button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          <label className="app-label" htmlFor="invite-name">{words.inviteSomeone}</label>
          <input id="invite-name" className="app-input" value={inviteName} onChange={(event) => setInviteName(event.target.value)} placeholder={words.name} />
          <input className="app-input app-input--compact" value={inviteRelationship} onChange={(event) => setInviteRelationship(event.target.value)} placeholder={words.relationshipOptional} aria-label={words.relationship} />
          <select className="app-input app-input--compact" value={inviteRole} onChange={(event) => setInviteRole(event.target.value as CircleMemberSummary["role"])} aria-label={words.responderRole}>
            <option value="PRIMARY">{words.primary}</option><option value="BACKUP">{words.backup}</option><option value="TERTIARY">{words.tertiary}</option>
          </select>
          <button className="cta app-button" disabled={busy || !inviteName.trim()} onClick={() => run(async () => {
            const invitation = await api<InvitationSummary>(config as RuntimeConfig, accessToken, "/v1/circle/invitations", {
              method: "POST",
              headers: { "idempotency-key": idempotencyKey() },
              body: JSON.stringify({ displayName: inviteName.trim(), relationship: inviteRelationship.trim() || null, role: inviteRole }),
            });
            setInviteName(""); setInviteRelationship("");
            setPendingInvitation(invitation);
            setNotice(words.invitationCreated);
            await refresh(config as RuntimeConfig, accessToken);
          })}>{words.createInvitation}</button>
          {pendingInvitation && (
            <div className="app-invitation" aria-live="polite">
              <p className="app-muted">{words.consentLink}: <a href={pendingInvitation.inviteUrl} target="_blank" rel="noreferrer">{words.openInvitation}</a></p>
              <button className="app-link" disabled={busy} onClick={() => run(async () => {
                const refreshed = await api<InvitationSummary>(config as RuntimeConfig, accessToken, `/v1/circle/invitations/${pendingInvitation.invitationId}/resend`, {
                  method: "POST",
                  headers: { "idempotency-key": idempotencyKey() },
                });
                setPendingInvitation(refreshed);
                setNotice(words.refreshedLink);
              })}>{words.refreshLink}</button>
            </div>
          )}
        </div>

        <div className="app-section">
          <p className="eyebrow">{words.closedLoops}</p>
          <h2>{words.history}</h2>
          {history.length === 0 ? <p className="app-muted">{words.noHistory}</p> : (
            <ul className="app-plan-list">
              {history.map((entry) => (
                <li key={entry.id} className="app-plan">
                  <div><h3>{entry.planLabel}</h3><p>{entry.resolvedBy} · {entry.method}</p></div>
                  <time className="mono" dateTime={entry.resolvedAt}><bdi>{new Date(entry.resolvedAt).toLocaleDateString(locale === "ar" ? "ar-EG" : "en-US")}</bdi></time>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="app-section" id="delete-account">
          <p className="eyebrow">{words.account}</p>
          <h2>{words.deleteAccount}</h2>
          <p className="app-muted">
            {words.deleteBody}
          </p>
          <label className="app-label" htmlFor="delete-confirmation">
            {words.typeDelete}
          </label>
          <input
            id="delete-confirmation"
            className="app-input app-input--compact"
            value={deleteConfirmation}
            autoComplete="off"
            onChange={(event) => setDeleteConfirmation(event.target.value)}
          />
          <button
            className="app-link app-delete"
            disabled={busy || deleteConfirmation !== "DELETE"}
            onClick={() => run(async () => {
              const request = await api<AccountDeletion>(
                config as RuntimeConfig,
                accessToken,
                "/v1/account",
                {
                  method: "DELETE",
                  body: JSON.stringify({ confirmation: deleteConfirmation }),
                },
              );
              setDeletion(request);
            })}
          >
            {words.deleteAction}
          </button>
        </div>
        {notice && <p role="status" className="app-notice">{notice}</p>}
      </aside>
      </div>
    </>
  );
}

function State({ title, body, children, locale, onLocaleChange }: { title: string; body: string; children?: React.ReactNode; locale: Locale; onLocaleChange: (locale: Locale) => void }) {
  return <div className="app-state"><LanguageToggle locale={locale} onChange={onLocaleChange} /><p className="eyebrow">{webCopy[locale].webLabel}</p><h1>{title}</h1><p>{body}</p>{children}</div>;
}
