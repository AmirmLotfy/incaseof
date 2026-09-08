# In Case of — Architecture

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

---

## 1. The governing boundary

```
                    HUMAN
                      │
                      ▼
             Natural-language input
                      │
                      ▼
                Strands Agent
                      │
          Amazon Nova 2 Lite via Bedrock
                      │
                   proposes
                      │
                      ▼
               Typed tool call
                      │
                      ▼
              AgentCore Gateway
                      │
                      ▼
                 Policy layer
                      │
               ALLOW / DENY
                      │
                      ▼
              Domain service
                      │
                      ▼
        Deterministic workflow / state
```

**Agent memory is context. DynamoDB is truth.** An LLM conversation never remembers who was
contacted, Alert status, whether somebody is safe, checking ownership, Plan version, or timers.
Those are application state.

---

## 2. Runtime topology

```
                    Android
                       │
                       ▼
                 Amazon Cognito
                       │
                       ▼
                 API Gateway (HTTP / WS)
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        Application API       Realtime
           Lambda              updates
             │
             ▼
          DynamoDB
             │
       ┌─────┴──────────┐
       ▼                ▼
 EventBridge        Step Functions
 Scheduler           (Standard)
       │                │
       └────────┬───────┘
                ▼
           Alert Engine
                │
       ┌────────┴─────────┐
       ▼                  ▼
  Strands Agent       Action Outbox
       │                  │
Nova via Bedrock          ▼
       │                 SQS
       ▼                  │
AgentCore Gateway         ▼
       │            channel workers
  Policy layer       /      |      \
       │           FCM     SMS   (Voice P1)
       ▼
Domain services
```

---

## 3. Service choices and the reason for each

| Concern | Service | Why |
|---|---|---|
| Identity | Amazon Cognito | Managed, hackathon-appropriate, no custom auth |
| Public API | API Gateway HTTP API | Not GraphQL — no need |
| Compute | Lambda | Account/Circle/Plan/Moment/Alert APIs, callbacks, workers |
| Agent hosting | AgentCore Runtime | Managed Strands compiler with IAM-authenticated Bedrock inference |
| Database | DynamoDB | Single-table, access-pattern driven |
| **Scheduling** | **EventBridge Scheduler** | **The phone must never own safety timers** |
| Durable orchestration | Step Functions **Standard** | Delay, retry, escalation, human callback, lease, fallback |
| Queue | SQS | All external communications |
| Push | FCM | Android device delivery |
| SMS | AWS End User Messaging / SNS | P0 external contact channel |
| Voice | Amazon Connect | **P1** — provisioning lead time, see PRD §12 |
| Secrets | Secrets Manager | Signing and provider credentials. The Bedrock model uses IAM, not an API key |
| Encryption | KMS | Phone endpoints, sensitive context, optional location |
| Infrastructure | AWS CDK | Reconstructable from Git. No console-managed resources |

---

## 4. Why Plan Version exists

A live Alert must never point at mutable Plan configuration.

```
21:00  Moment generated using Plan v4
21:03  user modifies tomorrow's plan → Plan v5 becomes active
       Current Alert remains pinned to v4
```

This removes a whole class of race conditions: an Alert's escalation ladder, responders, stop
conditions and context policy are frozen at the version that created its Moment.

---

## 5. Durable action / outbox pattern

Never call a provider directly from the workflow.

```
workflow → create ActionIntent → transactional write → outbox → SQS →
worker → provider → delivery callback
```

This makes retries predictable and keeps the workflow free of provider latency and failure modes.

---

## 6. Idempotency

Every external action carries:

```
idempotency_key = alert_id + escalation_step_id + attempt_number
```

Dispatch is guarded by a DynamoDB **conditional write**. If the key already exists, the worker
returns success *without sending again*.

**Target: duplicate external actions = 0.** This is tested explicitly (see `docs/PRODUCT-STATES.md`
and the reliability suite) by replaying scheduler and SQS deliveries.

---

## 7. Failure behaviour

| Failure | Behaviour |
|---|---|
| Model unavailable / invalid JSON / timeout | Escalation continues. UI falls back to deterministic buttons |
| App killed | Escalation continues — timers live in EventBridge, not the device |
| Lambda retry | No duplicate external action (idempotency key) |
| Channel provider fails | Fallback channel attempted; failure recorded as an ActionAttempt |
| Responder disappears | Checking lease expires, ownership released, workflow resumes |
| Step Functions retry | Safe — all steps idempotent |
| Carrier accepts but never delivers | Recorded as `ACTION_ACCEPTED`, never as delivered — see below |

**No safety-critical path is ever blocked behind the model.**

### Accepted is not delivered

A carrier returning a message id means it has taken custody of a message, not that a handset
received one. The two come apart in practice, and silently: an SNS account still in the SMS
sandbox returns an ordinary `MessageId` when publishing to an unverified number and delivers
nothing at all. This project's own dev account behaves exactly that way today.

So the system never infers arrival from a successful provider call:

| Event | Means | Evidence |
|---|---|---|
| `ACTION_QUEUED` | An intent is on the outbox | Our own write |
| `ACTION_ACCEPTED` | The carrier took the message, with a provider reference | Provider response |
| `ACTION_DELIVERED` | A handset received it | Carrier receipt only |
| `ACTION_UNDELIVERED` | The carrier gave up | Carrier receipt only |

`ACTION_DELIVERED` is never written by the send path — only by a delivery receipt. Both
clients label these separately, because a responder reads the timeline to decide whether
somebody has already been reached, and a timeline claiming contact that did not happen would
close the loop falsely. That is the single worst failure this product has.

**Not yet wired:** carrier receipts require production SNS access (the account is in the SMS
sandbox) and an SNS delivery-status IAM role. Until then the timeline stops at `ACCEPTED` and
says so, rather than rounding up to "delivered".

### Channels

A ladder may mix channels — push the subject, then text a sister — so a router maps each rung
to the provider that serves it. A channel with no provider bound reports
`CHANNEL_UNAVAILABLE`, never `ACTION_FAILED`: "nothing is wired to this" and "we tried and it
broke" are different facts, and reporting the second invites somebody to wait for a retry that
is never coming.

| Channel | Provider | Bound when |
|---|---|---|
| SMS | SNS | `ICO_KMS_KEY_ID` is set (endpoint encryption) |
| PUSH | FCM via SNS mobile push | `ICO_PUSH_PLATFORM_ARN` is set |
| CALL | Amazon Connect | P1 — reports `CHANNEL_UNAVAILABLE` by design |

Push goes through SNS rather than calling FCM directly, so the Firebase service-account
credential stays inside AWS: the platform application holds it, and no function in this system
ever loads, refreshes, or can leak it. What is stored per person is a platform endpoint ARN,
which is useless without the account it belongs to — a strictly weaker secret than a raw
registration token.

**A push carries no detail.** Notifications are readable on a locked screen, and in the
situation this product exists for, the person holding the phone is not reliably its owner. The
notification says a check is waiting; the app renders who and why after unlock.

---

## 8. The escalation workflow

A Standard workflow, shaped as a loop that holds no opinions:

```
NextAction ──► decision?
   ▲            ├── DISPATCH ──► Dispatch ──┐
   │            ├── WAIT ──────► Wait(n) ───┤
   └────────────┴── TERMINAL ──► Closed     │
                └───────────────────────────┘
```

Every decision is made in Python, where it is unit-testable in milliseconds. The state
machine only sequences and waits. `Dispatch` loops straight back rather than waiting,
because a ladder with two rungs at the same offset must fire both without a pause.

**Standard, not Express.** Escalation runs for hours, needs durable execution history for
the audit timeline, and waits on human callbacks. Express is cheaper and keeps no history,
which is the wrong trade when the history *is* the product.

`Dispatch` sends nothing. It writes an idempotency-guarded intent to SQS, and a worker
performs delivery — which is what makes a Step Functions retry harmless.

**Endpoint resolution happens in the worker and nowhere else.** By the time a message
reaches it, the recipient has already been authorized *by role*; the worker is the single
function in the system that ever turns a role into a phone number.

---

## 9. Environments

`local` · `dev` · `demo` · (`staging`, `prod` post-hackathon). Demo data never mixes with real
user data. Each environment is a separate CDK stack instance with its own table and schedules.
