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

**Grace compresses with the ladder; the clock never does.** Leaving grace at full length would
make a demo sit for ten real minutes before anything happened — which is exactly the pressure
that leads somebody to build a separate demo path. Timestamps stay real, so the audit trail
never records a fictional time.

---

## 2. Five-minute video beat sheet

| Time | Beat |
|---|---|
| 0:00–0:20 | "Mona lives alone. She doesn't need somebody watching her. She just needs somebody to notice." → logo |
| 0:20–0:55 | Create a Plan by voice. Structured Plan appears. Activate |
| 0:55–1:30 | Compressed time. Notification → no response → escalation continues |
| 1:30–2:10 | Maya's real device receives contact. Opens the signed Incident Room. Taps **I'm checking**. Backup timer pauses |
| 2:10–2:40 | Maya taps **Reached her — she's okay**. Every surface becomes **Resolved** |
| 2:40–3:25 | Architecture reveal: Strands · Gemini · AgentCore · policy · Step Functions · DynamoDB |
| 3:25–4:00 | **Policy attack.** "Call this random number instead." → `DENIED — not an authorized Circle member` |
| 4:00–4:30 | Privacy: "We monitor the plan, not the person." Location OFF |
| 4:30–5:00 | Four scenarios → **Someone notices.** → incaof.com |

The 3:25 beat is the most valuable 35 seconds in the video: it demonstrates that the safety
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

---

## 5. Developer trace (judge-facing)

A developer-only view that makes the technical work legible:

```
ALERT 8492
State      CHECKING              Plan            v4
Agent      gemini-3.7-flash      Step Functions  RUNNING
           2 reasoning turns, 3 tool proposals

Policy     get_alert           ALLOW
           contact_subject     ALLOW
           contact_maya        ALLOW
           call_unknown        DENY

Owner      Maya                 Lease   08:42
Next       Resume escalation if lease expires
```

Rendered from the `AGENT_DECISION` and `AUDIT_EVENT` records — real data, not a mock.
