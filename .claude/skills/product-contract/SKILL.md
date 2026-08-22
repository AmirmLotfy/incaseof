---
name: product-contract
description: Check a proposed feature against the PRD scope and phase order before building it. Use when starting any new feature, when scope feels like it is growing, or when unsure whether something is P0, P1, or out of scope.
---

# Product contract check

Run this **before** writing feature code.

## 1. Is it in scope?

Read `docs/PRD.md` §12 (P0 table) and §11 (out of scope).

**Hard rejections** — say no and point at §11: diagnosis · medication compliance · medical advice ·
automatic emergency dispatch · emotion detection · distress or suicide-risk prediction · fall
detection · continuous voice or location · passive surveillance · family map · address-book
scraping · background WhatsApp automation.

**Do not build before submission** (§12): Wear OS · iOS · browser extension · calendar or email
integration · emergency-services APIs · payments · subscriptions · multi-tenant orgs.

## 2. Is it the right phase?

The order in §13 exists so that at any cut-off point what exists is a coherent working product
rather than a broad set of half-features.

> **The complete deterministic, non-AI vertical slice must work end to end before the model is
> added.** If Phase 4 is not done, do not start Phase 5.

## 3. Does it preserve the invariants?

- Does the AI stay out of state transitions, timers and authorization?
- Is every new external action idempotent?
- Is the Alert still pinned to a Plan Version?
- Does acknowledged still not mean resolved?
- Does it work when Gemini is down?

## 4. Does it change the schedule picture?

23 calendar days from Aug 22 to the Sept 14 deadline. If accepting this work makes a committed P0
item unreachable, **say so with the numbers** rather than absorbing it silently. Descoping is the
owner's decision, and they can only make it with real information.

## Output
A short verdict: in scope / out of scope / wrong phase, the section that decides it, and what to do
instead.
