# In Case of — API Surface

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

API Gateway HTTP API. All `/v1/*` routes require a Cognito-authenticated principal except the
`/r/*` responder routes, which authenticate with a signed single-Alert token
(`docs/SECURITY.md` §2). The machine-readable definition lives in `packages/contracts/openapi.yaml`.

---

## Plans

```
POST   /v1/plans/compile              natural language → validated CompiledPlan (preview only)
POST   /v1/plans                      create from a compiled plan
GET    /v1/plans
GET    /v1/plans/{planId}
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

## Voice (P1)

```
POST   /v1/voice/session
```

---

## Conventions

- **Idempotency:** every mutating endpoint accepts `Idempotency-Key`. Replays return the original
  result rather than acting twice.
- **Errors:** RFC 9457 `application/problem+json`. Authorization failures are `403` with a stable
  `reason_code`; they never explain *why* in a way that leaks another user's data.
- **Versioning:** `/v1` prefix. Responder routes are deliberately short (`/r/...`) because they are
  sent over SMS, where every character counts and the domain must stay recognisable for trust.
- **No endpoint ever returns a plaintext phone number.**
