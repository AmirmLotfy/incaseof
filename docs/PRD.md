# In Case of — Product Requirements

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

**Product:** In Case of · **Domain:** incaof.com · **Package:** `com.incaof.app`
**Hackathon:** Agents for Humans 2026 · **Track:** Everyday Agents
**Core promise:** Someone notices. · **Product principle:** Monitor the plan, not the person.

---

## 1. Thesis

Millions of people spend meaningful periods alone. The existing options are two extremes:
**passive** (someone remembers to call) or **surveillance** (continuous location, cameras,
wearables, activity tracking).

There is a useful layer between them. A person can say *"this is what I expect to happen,"* and
if it does not happen, software can quietly start resolving the uncertainty.

> **In Case of is a contingency utility that watches for expected moments in someone's life and
> works to close the loop when one does not happen.**

It does **nothing** while everything is normal. When an expected event is unresolved it can:

```
ask the person → remind them → call them → understand their response →
contact an authorized Circle member → coordinate who is checking →
continue escalation if necessary → record explicit resolution
```

### Track justification

The hackathon FAQ states tracks are chosen by *who the primary user is*, not by what the agent
technically does. The primary user of In Case of is an individual managing their own life. That
is **Everyday Agents**, not Good Neighbor — Circle members are participants in one person's plan,
not a group being served.

---

## 2. The central abstraction: Expected Moment

This is **not** a reminder application. The canonical domain object is the **Expected Moment**:

> Something that should reasonably happen by a particular time.

It carries: what is expected · when it is expected · how long uncertainty is acceptable ·
how to first reach the subject · who may be contacted · when each person may be contacted ·
what information may be released · what counts as resolution.

Everything else in the system derives from this.

---

## 3. Vocabulary

Engineering names never leak into the product surface.

| Engineering | Product UI |
|---|---|
| SafetyPlan | Plan |
| ExpectedEvent | Moment |
| TrustedContacts | Circle |
| Incident | Alert |
| EscalationStep | Next step |
| OwnershipLease | Checking |
| Resolution | Resolved |
| ContextRelease | Shared if needed |
| ActionAttempt | Attempt |
| State machine | *never exposed* |

**Never display** in consumer UI: workflow, state machine, orchestration, LLM, agent loop,
prompt, tool call — unless the user explicitly opens Developer/Demo mode.

---

## 4. Principles (non-negotiable)

### 4.1 Monitor the plan, not the person
No continuous location. No continuous microphone. No permanent activity tracking. No map home
screen. No family surveillance dashboard. In Case of monitors an *expectation*.

### 4.2 Missing does not mean danger
A missed Moment means **unresolved**, not **emergency**. The product never panics immediately.

### 4.3 AI interprets humans. Software protects humans.
```
Human language → AI interpretation → Proposed action →
Deterministic authorization → Deterministic workflow → Real-world action
```
AI does not control timers. AI does not control authorization. AI does not decide who may receive
someone's location. AI does not determine that someone has a medical emergency.

### 4.4 Acknowledged does not equal resolved
A responder tapping **I'm checking** takes temporary ownership and pauses backup escalation for a
10-minute lease. It does **not** mean the person is safe. They must later explicitly choose
*Reached them — they're okay* or *I couldn't reach them*. If they disappear, the lease expires and
escalation resumes.

### 4.5 AI never silently changes protection
The agent may *suggest* a plan change. Changing the plan requires explicit human confirmation.

### 4.6 Every consequential action is explainable
The user must always be able to answer: What happened? Why? Who was contacted? What happens next?

### 4.7 Fail safely
If the AgentCore compiler fails, escalation continues. If the app is killed, escalation continues. If a Lambda
retries, nobody receives duplicate calls. If a channel fails, a fallback is attempted. If a
responder disappears, the workflow resumes.

---

## 5. Personas

**Primary — Independent individual.** Lives, travels, commutes or performs activities alone. Wants
reassurance without surveillance. Age 20–75+. *We do not design around "elderly people."*

**Secondary — Circle member.** Friend, sibling, child, parent, spouse, neighbour. Wants "tell me
when I actually need to do something," not "make me monitor their location all day."

**Tertiary (out of scope) — Organizer.** Care organisation, field team, university, travel operator.

---

## 6. Jobs to be done

- **Subject:** When I spend time alone, I want someone to notice if something expected fails to
  happen, without having to continuously share my life.
- **Circle member:** When someone I care about may need attention, tell me exactly what has already
  happened and what I need to do next.
- **Privacy-conscious user:** Let me decide in advance exactly which pieces of contextual
  information can become visible, and under which circumstances.

---

## 7. Plan templates

Four at launch, not seventeen. All compile to the same engine.

| Template | Example |
|---|---|
| **Routine** | "Check on me every evening." |
| **Journey** | "I should arrive before midnight." |
| **Solo** | "I'm hiking until six." |
| **Recovery** | "I'm alone tonight. Check periodically." |

---

## 8. The Plan model

**Trigger** — recurring (`every day at 21:00`), one-time (`August 26 at 18:00`), or relative
(`90 minutes from now`).

**Grace** — acceptable uncertainty window before escalation begins.

**Escalation** — an ordered ladder of offsets and actions:
```
21:00  check with me      21:25  notify Maya
21:10  remind me          21:35  call Maya
21:20  call me            21:45  notify Omar
```

**Stop conditions** — *allowed:* subject explicitly confirms okay · authorized responder verifies
direct contact · user cancels before escalation · plan-specific completion signal.
***Not allowed:*** phone moved · model "believes" user is safe · notification delivered ·
contact merely acknowledged the alert.

**Context release** — per-signal policy, e.g. `location: NEVER`,
`battery: AFTER_SUBJECT_CALL_FAILED`, `last connection: CIRCLE_ESCALATION_ONLY`.

---

## 9. Natural-language Plan creation

The agent's showcase capability. Input:

> "I'm hiking tomorrow. I expect to be back around six. Give me half an hour because I might be
> late. If I don't respond, call me. Then tell Maya. If she doesn't do anything for ten minutes,
> call Omar."

The result must **not** remain a chat message. It becomes structured, reviewable UI showing the
compiled ladder, the context policy, and an **Activate plan** action. This conversion from
language to deterministic interface is the core differentiator.

**Compilation pipeline — the preview step is never skipped:**
```
Model output → schema validation → semantic validation → contact authorization validation →
safety validation → simulation → human preview → explicit confirmation → Plan Version created
```

The canonical compiled form is defined by `packages/domain-schemas/compiled-plan.schema.json`,
with the worked example in `packages/test-fixtures/`.

---

## 10. Functional scope

**Authentication (P0):** email via Cognito, profile, timezone and locale. *Later:* passkeys,
phone sign-in and Google sign-in. Hackathon success must not depend on complex auth.

**Circle:** display name, relationship label, priority, verified phone, supported channels,
accepted status, plan permissions, context permissions.

**Circle consent:** nobody becomes a safety contact accidentally. Acceptance records timestamp,
source, permissions, relevant Plan, and policy version.

**Responders need no app.** Hard requirement. Channels: SMS, WhatsApp (P1), voice (P1), and a
signed web link that works without sign-up for that one Alert.

**Resolution methods:** explicit self-confirmation · explicit trusted verification. Every
resolution records who, when, how, source, plan version, incident id.

**Drill Mode:** *Test this plan* runs the **same deployed workflow engine** with an accelerated
schedule. There is no fake demo code path — see `docs/DEMO.md`.

**Plan Health:** objective facts only (`2/2 Circle members verified`, `Push tested Aug 20`).
Never an AI score like "Safety 92/100."

---

## 11. Out of scope — reject feature creep

diagnosis · medication compliance · medical advice · automatic emergency-services dispatch ·
emotion detection · distress prediction · suicide-risk prediction · fall detection · continuous
voice monitoring · continuous location · passive surveillance · CCTV · family map · unauthorized
contacts · scraping address books · background Android automation of personal WhatsApp.

These belong to separate future risk reviews, not to this product.

---

## 12. P0 scope

Committed in full. See "Schedule risk" below.

| Feature | P0 |
|---|:--:|
| Android app | ✓ |
| Authentication | ✓ |
| Circle | ✓ |
| Consent | ✓ |
| One-time Plan | ✓ |
| Recurring Plan | ✓ |
| Natural language compilation | ✓ |
| Strands on AgentCore with Amazon Nova 2 Lite through Bedrock | ✓ |
| Strands Agent | ✓ |
| AgentCore Runtime | ✓ |
| AgentCore Gateway / Policy | ✓ |
| EventBridge schedule | ✓ |
| Step Functions escalation | ✓ |
| FCM | ✓ |
| **Real external contact channel** | ✓ **— satisfied by FCM push + SMS. See below.** |
| Responder web | ✓ |
| Alert claim | ✓ |
| Checking lease | ✓ |
| Resolution | ✓ |
| Audit timeline | ✓ |
| Drill Mode | ✓ |
| Marketing site | ✓ |
| Live browser demo | ✓ |
| Developer trace | ✓ |

### Decision: the voice leg

**Amazon Connect telephony and the IVR are P1, not P0.** Claiming a phone number can require
identity verification with multi-day lead time — an external dependency that build speed cannot
recover. P0 proves real external contact via **FCM push and SMS** (AWS End User Messaging / SNS),
which provision in minutes.

The state machine in `docs/PRODUCT-STATES.md` and the escalation ladder are **unchanged**; only the
channel binding differs. `CALL_SUBJECT` / `CALL_RESPONDER` steps remain first-class in the schema
and compile normally — they dispatch through the channel abstraction, which reports
`CHANNEL_UNAVAILABLE` until Connect is wired. Adding Connect in P1 requires no domain change.

Definition of Done items 8 and 13 below are therefore read against SMS + push in P0.

### P1 — only after the vertical slice works
conversational voice · Amazon Connect + IVR · WhatsApp · progressive device context ·
AppFunctions · richer exceptions · plan recommendations · dark mode refinement · advanced
multi-Circle permissions.

### Known gaps, deliberately deferred

Recorded when found rather than left implicit:

- **Interval plans have no end bound.** `intervalSeconds` anchors a chain to `timeOfDay` and
  repeats indefinitely, so "check every three hours tonight" keeps checking tomorrow. A bounded
  night is currently expressed as a `RELATIVE` or `ONE_TIME` plan, or by pausing. Adding an
  explicit `until` to the schema is a Phase 5 change, once natural-language compilation shows
  how people actually phrase the bound.

### Do not build before submission
Wear OS · iOS · browser extension · smartwatch detection · fall detection · calendar integration ·
email integration · emergency-services APIs · payments · subscriptions · multi-tenant orgs.

---

## 13. Schedule risk (accepted, tracked)

Full P0 was chosen over a trimmed scope with the risk stated. Recorded so it stays visible:

**Submission closes Sept 14 2026, 5:00pm PT. From Aug 22 that is 23 calendar days — roughly 20
build days after the video and submission package.** The table above is a large product surface
for a solo builder.

Mitigations built into the process rather than into wishful estimates:

1. **Vertical-slice order is enforced** (`.claude/skills/product-contract`). The deterministic,
   non-AI slice must work end-to-end before the model is added. At any cut-off point what exists
   is a coherent working product, not a broad set of half-features.
2. **`DEMO_TIME_SCALE` is designed in from day one**, so the demo runs the real workflow engine and
   no fake demo path is ever needed under deadline pressure.
3. **Phase-boundary checkpoints.** If the remaining P0 surface stops fitting the remaining days,
   that is surfaced with real numbers so descoping remains an informed decision, made deliberately.

---

## 14. Metrics

**North star — Resolved Uncertainty Rate:** `resolved Alerts / opened Alerts`.

Supporting: median self-resolution time · median Circle takeover time · nuisance escalation rate ·
notification delivery success · Circle acceptance rate · drill completion · exhausted Alert rate.

**Hard engineering targets:**
```
duplicate external actions:      0
unauthorized tool executions:    0
```

---

## 15. Definition of Done

The project is not done until **all** of these are true:

```
✓ User can create a Plan using natural language.
✓ AgentCore output becomes validated structured data.
✓ User sees exactly what will happen before activation.
✓ Expected Moment fires if the Android app is terminated.
✓ Android check notification works.
✓ "I'm okay" resolves the correct Moment.
✓ Missing the Moment creates one and only one Alert.
✓ Real external contact works.                      [P0: SMS + push]
✓ Circle member can access Alert without installing the app.
✓ Circle member can claim it.
✓ Claim pauses backup escalation.
✓ Claim expiration resumes backup escalation.
✓ Circle member can verify resolution.              [P0: SMS + web link]
✓ Pending actions stop after resolution.
✓ Duplicate event delivery does not duplicate external actions.
✓ Unauthorized Circle contact is rejected.
✓ Unauthorized context release is rejected.
✓ Model outage does not prevent deterministic escalation.
✓ Full audit timeline is available.
✓ Drill Mode runs the same production workflow.
✓ Android app passes accessibility review.
✓ Responder web passes accessibility review.
✓ Marketing website has no fake claims.
✓ Marketing site passes responsive visual QA.
✓ Agent eval suite passes agreed thresholds.
✓ CDK can reconstruct the environment.
✓ Public repo contains required license.
✓ Live demo works.
✓ Five-minute submission story works with no explanation gaps.
```

---

## 16. Submission requirements

| Requirement | Detail |
|---|---|
| Deadline | **Sept 14 2026, 5:00pm PT** |
| Project age | Newly created during the submission period; pre-existing work disclosed |
| Framework | **Strands Agents SDK — required** |
| AgentCore | Encouraged, strengthens Technical Implementation, not required |
| Repository | Public, MIT or Apache licence → **Apache-2.0** |
| Also required | README · architecture diagram · ≤5-minute video (demo **and** pitch) · AWS Builder ID |
| Optional | Live demo link · builder.aws blog post |
| **AWS credits** | **$50, claimed via the hackathon form by Sept 11, 12pm PT, while supplies last** |
| Judging | Technological Implementation · Design · Potential Impact · Creativity & Originality · Presentation |
