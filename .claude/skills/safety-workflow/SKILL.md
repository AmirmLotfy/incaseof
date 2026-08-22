---
name: safety-workflow
description: Review escalation, alert-state, scheduling, or external-action code for idempotency, plan-version pinning, authorization and lease correctness. Use when touching workflows, Step Functions, schedulers, channel workers, or anything that transitions an Alert.
---

# Safety workflow review

## 1. State machine
Compare against `docs/PRODUCT-STATES.md` §2. Every transition must appear there.
- Terminal states (`RESOLVED`, `CANCELLED`, `ESCALATION_EXHAUSTED`) never transition out.
- Reaching a terminal state **cancels pending external actions**. Verify this, don't assume it.
- No transition is authored by the model.

## 2. Idempotency
```
idempotency_key = alert_id + escalation_step_id + attempt_number
```
- Guarded by a conditional write, not an `if exists` read followed by a write. That race is the
  whole point.
- Replayed scheduler delivery, replayed SQS delivery and Lambda retry must each produce **zero**
  additional external actions. There is a test for each.

## 3. Plan Version pinning
The Alert reads its ladder, responders, stop conditions and context policy from
`alert.plan_version_id` — never from the live plan. Editing a plan mid-Alert must not change what
that Alert is doing.

## 4. Lease correctness — the subtle one
- Claim is conditional on owner absent or expired. Two responders must not both believe they own it.
- Expiry resumes escalation **at the step it paused at**, never from the top.
- A lease expiring is normal, not an error.
- Acknowledged ≠ resolved. A claim alone never closes an Alert.

## 5. Stop conditions
Only §4 of `docs/PRODUCT-STATES.md` may close an Alert. Reject anything that treats a delivered
notification, an acknowledgement, phone movement, or a model opinion as resolution.

## 6. Degradation
Walk `docs/ARCHITECTURE.md` §7. For each failure, does escalation still continue? If any answer
depends on the model or the phone, that is a defect.
