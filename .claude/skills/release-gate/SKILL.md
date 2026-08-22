---
name: release-gate
description: Run every check required before marking a milestone or phase complete. Use at the end of a phase, before a demo, and before submission.
---

# Release gate

## 1. Everything must be green
```bash
./scripts/preflight.sh
```
Python tests + lint + format + types · web build + typecheck · design tokens · contracts ·
Android assemble + test + lint + ktlint · CDK synth · secret scan.

**Report real output, including failures.** A gate that reports success without running is worse
than no gate.

## 2. Definition of Done
Walk `docs/PRD.md` §15 line by line. Mark each ✓ only if it has actually been observed working —
not "the code looks right". The voice-call lines read against SMS + push in P0.

## 3. Safety invariants, demonstrated
- Duplicate scheduler/SQS delivery → **zero** duplicate external actions.
- Unauthorized Circle contact → rejected, recorded as DENY.
- Unauthorized context release → rejected.
- Gemini disabled → escalation timing unchanged.
- Lease expiry → escalation resumes at the correct step.

## 4. Schedule reality
Days remaining vs. remaining P0 surface. If they no longer fit, **say so with numbers**. That is
the owner's call to make, and silence removes their ability to make it.

## 5. Submission (final gate only)
Public repo · Apache-2.0 · README with architecture diagram · Strands Agents used · ≤5-min video
with demo **and** pitch · AWS Builder ID · track: Everyday Agents · $50 credits claimed by
**Sept 11 12pm PT** · deadline **Sept 14 5pm PT**.

No fake claims anywhere in the submission, the site, or the video.
