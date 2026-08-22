---
description: Testing standards
globs: ["**/tests/**", "**/*_test.py", "**/*Test.kt", "evals/**"]
---

# Testing rules

## Priority order
1. **Domain unit tests** — plan compiler, validation, Moment creation, Alert transitions, leases,
   resolution, context release, retries, idempotency. Highest value; no cloud needed.
2. **Agent evals** — separate from application tests (`evals/`).
3. **AWS integration** — scheduler, Step Functions, SQS, callbacks, conditional writes.
4. **Android** — ViewModel, repository, Compose UI, notification actions, process death.
5. **Web** — unit, component, Playwright, accessibility, responsive.

## Rules
- Never disable or skip a failing test to make CI green. Fix it or fix the code.
- A test must be able to fail. A negative test that passes for the wrong reason proves nothing —
  this is why `load_fixture` strips `_why` before validating.
- Assert on behaviour, not implementation detail.
- No real phone numbers, no real people's names, no live network calls in unit tests.

## Reliability suite (must exist before submission)
duplicate scheduler delivery · duplicate SQS delivery · Lambda retry · provider timeout ·
provider 500 · FCM unavailable · late response · response exactly as the lease expires ·
Dynamo conditional conflict · Gemini unavailable · invalid Gemini JSON · Gemini timeout ·
Step Functions retry.

**The system must degrade predictably.** Each of these has a defined correct behaviour in
`docs/ARCHITECTURE.md` §7.
