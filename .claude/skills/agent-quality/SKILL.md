---
name: agent-quality
description: Review Strands agent code, tool definitions, prompts and model integration for typed output, tool-surface safety, prompt-injection resistance and fallback behaviour. Use when adding or changing any agent tool, prompt, or model call.
---

# Agent quality review

## 1. The tool surface is the security boundary
For every tool, ask: **could a fully compromised model cause harm through this signature?**

- ❌ Any parameter that accepts a phone number, email, URL, or free-form target.
- ✅ Parameters that name a **role** or an **id the backend re-authorizes**.

`contact_circle_member(alert_id, circle_member_id, requested_channel)` — never
`send_sms(number, text)`. The defence is that the unsafe action cannot be *expressed*, not that the
prompt asks nicely.

Every tool re-verifies server-side: active Alert · member on the pinned Plan Version · consent
ACTIVE · current step permits this contact · channel permitted · endpoint verified.

## 2. Typed output
- Output validated against `packages/domain-schemas/compiled-plan.schema.json`.
- Invalid JSON, schema failure, or timeout → deterministic fallback, never a retry loop that
  blocks resolution.
- The human preview step is never skipped, including in Drill Mode and the demo.

## 3. State
The model never remembers who was contacted, Alert status, ownership, or timers. If a prompt
carries that as context, it must be re-read from DynamoDB at decision time.

## 4. Fallback
With the model unavailable the user still sees `I'M OKAY` / `NEED SOMEONE` / `GIVE ME MORE TIME`,
and escalation timing is unchanged. Verify by disabling the model, not by reading the code.

## 5. Evals
New capability → new eval cases, including adversarial ones. Check
`evals/test_datasets.py::test_adversarial_dataset_covers_every_required_attack` still passes.

Ambiguity rule: `AMBIGUOUS` never resolves an Alert. Not once, not "probably", not "sounds fine".
