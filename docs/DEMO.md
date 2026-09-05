# In Case of — Demo & Submission

> **In Case of does not decide whether someone is in danger. It notices unresolved
> expectations and works to close the loop.**

---

## 1. Demo time compression — the rule that keeps the demo honest

A realistic plan escalates over tens of minutes. A demo has five. The temptation is a fake demo
path. **We never do that.**

```
DEMO_TIME_SCALE     production: 1.0     demo: 0.02
10 minutes → 12 seconds
```

Only the **schedule** is scaled. The same state machine, the same Step Functions workflow, the same
policy checks, the same idempotency guarantees, the same channels. Drill Mode uses this mechanism,
so the "Test this plan" button in the product and the hackathon demo are the same code path.

Any environment with `DEMO_TIME_SCALE != 1.0` shows a persistent banner:

> **Demo timing enabled**

**Never** build a demo-only branch in domain logic. If a demo needs behaviour the product does not
have, the product is wrong, not the demo.

`services/tests/slice/test_drill_mode.py` is what keeps this honest. It runs the full slice
compressed and asserts it reaches the same states, contacts the same people, enforces the same
consent checks and suppresses the same duplicates as a real run. A shortcut added for the demo
would make the two diverge and fail there.

The deployed deterministic path has a separate guarded acceptance command. It creates only an
isolated synthetic tenant, never prints its token, requires an explicit mutation flag, and verifies
the safe-sink audit records as well as the lease and terminal state:

```bash
ICO_DEMO_API_URL=https://api.incaof.com \
ICO_ACCEPT_SYNTHETIC_MUTATION=1 \
./scripts/verify-live-demo-drill.sh
```

This command deliberately starts from a structured plan. The Bedrock/AgentCore compilation canary
is a distinct release gate so a working deterministic workflow cannot conceal a model outage.

**Grace compresses with the ladder; the clock never does.** Leaving grace at full length would
make a demo sit for ten real minutes before anything happened — which is exactly the pressure
that leads somebody to build a separate demo path. Timestamps stay real, so the audit trail
never records a fictional time.

---

## 2. Four-minute-thirty-second video beat sheet

| Time | Beat |
|---|---|
| 0:00–0:20 | Human problem and **Someone notices** |
| 0:20–0:55 | Type a Plan description; AgentCore returns a literal structured preview |
| 0:55–1:20 | Review schedule, grace and consent; explicitly activate |
| 1:20–2:10 | Real accelerated Moment, safe-sink delivery and deployed audit timeline |
| 2:10–2:50 | Open the signed responder link; claim a lease; explicitly resolve |
| 2:50–3:30 | Strands, AgentCore, Gateway and Cedar trace; arbitrary-contact request denied |
| 3:30–3:55 | Retry, idempotency, lease conflict and model-failure evidence |
| 3:55–4:20 | Privacy, Android/web/responder montage and impact |
| 4:20–4:30 | ICO mark, **Someone notices**, live demo and repository URLs |

The governed-agent beat is the most valuable 40 seconds in the video: it demonstrates that the safety
property is real and enforced, not asserted.

---

## 3. Pitch requirements

The video must contain a working demo **and** a pitch covering: the problem solved, the target
audience, and why it matters.

---

## 4. Submission checklist

```
[ ] Public repository, Apache-2.0                    [ ] Video ≤ 5:00, demo + pitch
[ ] README with architecture diagram                 [ ] AWS Builder ID registered
[ ] Built with Strands Agents SDK                    [ ] Track: Everyday Agents
[ ] Text description of features                     [ ] Optional: live demo link
[ ] $50 AWS credits claimed by Sept 11, 12pm PT      [ ] Optional: builder.aws blog post
```

**Deadline: September 14 2026, 5:00pm PT.**

Judging: Technological Implementation · Design · Potential Impact · Creativity & Originality ·
Presentation.

The final go/no-go command is intentionally stricter than local preflight:

```bash
./scripts/verify-submission-ready.sh
```

It checks the accepted public commit/tag, canonical live URLs, signed APK and checksum, physical
device evidence, AgentCore/model canary, resolved live Drill, architecture uploads, all real
screenshots, the 3:2 project image, public video, Builder ID and at least one builder.aws post.
Local tests alone cannot make this command pass.

---

## 5. Developer trace (judge-facing)

A developer-only view that makes the technical work legible:

The panel renders only redacted fields returned by the deployed API. The compile view may show
`modelId`, `schemaVersion`, `runtimeSessionId` and `traceId`. Alert policy and workflow facts may
appear only when an actual `AGENT_DECISION` or `AUDIT_EVENT` record contains them. If the backend
does not return a field, the UI says evidence is unavailable; it never derives an ARN, policy
decision, model result or terminal state from elapsed browser/device time.
