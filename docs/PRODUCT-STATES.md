# In Case of — Product States (normative)

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

This document is the **single normative source** for Alert lifecycle. Code, tests, the Step
Functions definition and the agent's tool surface all derive from it. If an implementation
disagrees with this file, the implementation is wrong.

---

## 1. Alert state machine

```
SCHEDULED
    │
    ▼
DUE
    │
    ▼
GRACE
    │
    ▼
SELF_CONTACT
    │
    ├──── subject confirms ─────► RESOLVED
    │
    ▼
CIRCLE_ESCALATION
    │
    ├──── responder claims
    │          │
    │          ▼
    │       CHECKING
    │        /      \
    │       /        \
    │  verified    lease expired
    │      │             │
    │      ▼             ▼
    │  RESOLVED    CIRCLE_ESCALATION
    │
    ▼
ESCALATION_EXHAUSTED
```

Additional terminal state: `CANCELLED`.

**The agent cannot write these values.** State transitions occur only through domain services
invoked by the workflow or by an authenticated human action.

---

## 2. Transition table

| From | Event | To | Notes |
|---|---|---|---|
| `SCHEDULED` | due time reached | `DUE` | EventBridge Scheduler fires |
| `DUE` | grace configured | `GRACE` | No contact yet |
| `DUE` / `GRACE` | subject confirms | `RESOLVED` | Pre-escalation confirmation |
| `DUE` / `GRACE` | user cancels | `CANCELLED` | Only before escalation |
| `GRACE` | grace elapsed | `SELF_CONTACT` | First contact with subject |
| `SELF_CONTACT` | subject confirms okay | `RESOLVED` | Stop condition met |
| `SELF_CONTACT` | ladder exhausted for subject | `CIRCLE_ESCALATION` | |
| `CIRCLE_ESCALATION` | responder claims | `CHECKING` | Lease starts, backup paused |
| `CIRCLE_ESCALATION` | ladder exhausted | `ESCALATION_EXHAUSTED` | Terminal |
| `CHECKING` | responder verifies contact | `RESOLVED` | Trusted verification |
| `CHECKING` | responder reports unable | `CIRCLE_ESCALATION` | Resume immediately |
| `CHECKING` | **lease expires** | `CIRCLE_ESCALATION` | **Resume — this is the critical one** |
| any non-terminal | subject confirms okay | `RESOLVED` | Subject confirmation always wins |

---

## 3. Acknowledged ≠ Resolved

The most important semantic in the product.

Tapping **I'm checking** means:
```
responder temporarily owns the Alert
→ backup escalation pauses
→ 10-minute checking lease starts
```

It does **not** mean the person is safe. The responder must later explicitly choose
**Reached them — they're okay** or **I couldn't reach them**.

### Lease mechanics

- Default lease: **10 minutes** (configurable per Plan later).
- On claim: `owner = <person>`, `lease_expires_at = now + 10m`, escalation paused.
- At **2 minutes remaining**: "Are you still checking?" → *Extend 10 minutes* /
  *Couldn't reach them* / *Reached them*.
- On expiry with no response: ownership released, **escalation resumes** from where it paused.

A lease expiring is a normal, expected event — not an error.

---

## 4. Stop conditions

**Valid — the only ways an Alert closes successfully:**
- `SUBJECT_EXPLICIT_CONFIRMATION` — the subject said they are okay.
- `RESPONDER_VERIFIED_CONTACT` — an authorized responder confirms they reached the subject.
- `VERIFIED_CALL_RESPONSE` — subject responded through a verified channel (P1, IVR).
- `USER_CANCELLED_BEFORE_ESCALATION`.
- `PLAN_COMPLETION_SIGNAL` — plan-specific.

**Invalid — must never close an Alert:**
- The phone moved.
- The model "believes" the user is safe.
- A notification was *delivered*.
- A contact merely *acknowledged* the alert.

---

## 5. Resolution record

Every resolution records: **who · when · how · source · plan version · incident id**.

---

## 6. Invariants (assert these in tests)

1. A Moment produces **at most one** Alert.
2. An Alert is pinned to exactly one **Plan Version** for its entire life.
3. Terminal states (`RESOLVED`, `CANCELLED`, `ESCALATION_EXHAUSTED`) never transition out.
4. After an Alert reaches a terminal state, **all pending external actions are cancelled**.
5. An external action with an existing idempotency key is never dispatched twice.
6. Escalation resumes at the correct step after a lease expires — never restarts from the top.
7. No state transition is ever authored by the model.
