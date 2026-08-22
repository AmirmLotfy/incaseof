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
              Gemini 3.7 Flash
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
Gemini 3.7 Flash          ▼
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
| Agent hosting | AgentCore Runtime | Container-based, so a Gemini-backed Strands agent runs fine |
| Database | DynamoDB | Single-table, access-pattern driven |
| **Scheduling** | **EventBridge Scheduler** | **The phone must never own safety timers** |
| Durable orchestration | Step Functions **Standard** | Delay, retry, escalation, human callback, lease, fallback |
| Queue | SQS | All external communications |
| Push | FCM | Android device delivery |
| SMS | AWS End User Messaging / SNS | P0 external contact channel |
| Voice | Amazon Connect | **P1** — provisioning lead time, see PRD §12 |
| Secrets | Secrets Manager | Gemini key, provider creds, signing secrets. Never in the APK |
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
| Gemini unavailable / invalid JSON / timeout | Escalation continues. UI falls back to deterministic buttons |
| App killed | Escalation continues — timers live in EventBridge, not the device |
| Lambda retry | No duplicate external action (idempotency key) |
| Channel provider fails | Fallback channel attempted; failure recorded as an ActionAttempt |
| Responder disappears | Checking lease expires, ownership released, workflow resumes |
| Step Functions retry | Safe — all steps idempotent |

**No safety-critical path is ever blocked behind the model.**

---

## 8. Environments

`local` · `dev` · `demo` · (`staging`, `prod` post-hackathon). Demo data never mixes with real
user data. Each environment is a separate CDK stack instance with its own table and schedules.
