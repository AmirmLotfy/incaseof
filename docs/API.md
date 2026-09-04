# In Case of — API Surface

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

API Gateway HTTP API. All `/v1/*` routes require a Cognito-authenticated principal except the
explicit signed-link operations under `/v1/r/*` and `/v1/i/*`, plus `/v1/demo/*` in the
isolated demo stack. Responder, invitation and demo sessions use separate narrow, expiring
token audiences. The machine-readable definition lives in `packages/contracts/openapi.yaml`.

---

## Plans

```
POST   /v1/plans/compile              natural language → validated CompiledPlan (preview only)
POST   /v1/plans                      create from a compiled plan
GET    /v1/plans
GET    /v1/plans/{planId}
GET    /v1/history                     terminal Alert history for the signed-in subject
POST   /v1/plans/{planId}/activate
POST   /v1/plans/{planId}/pause
POST   /v1/plans/{planId}/resume
POST   /v1/plans/{planId}/test        Drill Mode
```

`POST /v1/plans/compile` **never** creates or activates anything. It returns a `CompiledPlan` for
human preview. Activation is a separate, explicit call — this separation is a safety requirement,
not a convenience (`docs/AI-SAFETY.md` §5).

## Moments

```
GET    /v1/moments/next
GET    /v1/moments/{momentId}
POST   /v1/moments/{momentId}/confirm      "I'm okay"
POST   /v1/moments/{momentId}/extend       "Give me 30 more minutes"
POST   /v1/moments/{momentId}/cancel
```

## Circle

```
GET    /v1/circle
POST   /v1/circle/invitations
POST   /v1/circle/invitations/{id}/resend
DELETE /v1/circle/members/{id}
GET    /i/{signedToken}
POST   /v1/i/{signedToken}/accept
POST   /v1/i/{signedToken}/decline
```

## Devices

```text
POST   /v1/devices
DELETE /v1/devices/{deviceId}
```

## Alerts

```
GET    /v1/alerts/{alertId}
POST   /v1/alerts/{alertId}/claim
POST   /v1/alerts/{alertId}/release
POST   /v1/alerts/{alertId}/resolve
GET    /v1/alerts/{alertId}/timeline
```

## Responder (signed token, no account)

```
GET    /r/{signedToken}                web Incident Room
POST   /v1/r/{token}/claim
POST   /v1/r/{token}/extend
POST   /v1/r/{token}/unable
POST   /v1/r/{token}/resolve
```

## Public judge demo (synthetic tenant, demo stack only)

```text
POST   /v1/demo/session
POST   /v1/demo/plans/compile
POST   /v1/demo/plans
GET    /v1/demo/plans
POST   /v1/demo/plans/{planId}/test
GET    /v1/demo/moments/next
GET    /v1/demo/alerts/{alertId}
GET    /v1/demo/alerts/{alertId}/timeline
GET    /v1/demo/alerts/{alertId}/responder-link
```

Each session is isolated under a random synthetic subject, expires after 30 minutes and has
accepted fixture roles but no real contact endpoints. These routes return `404` outside the
demo environment. They still run the same compiler, repositories, Scheduler and workflow.

Voice is deferred and intentionally absent from the P0 public API. There is no placeholder
route implying that an unsupported channel exists.

---

## Conventions

- **Idempotency:** every state-changing authenticated endpoint that schedules work, sends an
  invitation or changes Alert ownership requires `Idempotency-Key`. Signed responder operations
  are scoped to one Alert and remain transition-idempotent.
- **Errors:** RFC 9457 `application/problem+json`. Authorization failures are `403` with a stable
  `reason_code`; they never explain *why* in a way that leaks another user's data.
- **Versioning:** `/v1` prefix. Responder routes are deliberately short (`/r/...`) because they are
  sent over SMS, where every character counts and the domain must stay recognisable for trust.
- **No endpoint ever returns a plaintext phone number.**
