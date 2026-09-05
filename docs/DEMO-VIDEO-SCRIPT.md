# In Case Of - 4:30 hackathon demo

In Case Of closes uncertainty; it does not decide whether someone is in danger.

Every feature claim must be shown from the accepted deployed build. Higgsfield may supply
only the three short human-context plates and narration; it must not fabricate UI, AWS
traces, notifications or product behavior.

## Timeline and narration

### 0:00-0:20 - The human problem

**Picture:** Up to three short, non-alarmist human plates: living independently, a late
commute, and a solo outdoor activity. Total generated footage stays below 20 seconds.

**Narration:** "Independence should not require surveillance. She does not need a camera
watching her, or a panic button she may not be able to press. She needs one quiet promise:
if an expected moment passes, someone notices."

### 0:20-0:55 - Describe the plan

**Picture:** Real web app capture. Enter: "Mona checks in every evening at nine. If she
doesn't respond after ten minutes, ask Maya, then Omar." Show the deployed AgentCore trace
and the literal preview.

**Narration:** "This is ICO: In Case Of. Mona describes an expected moment in ordinary
language. A Strands agent on Amazon Bedrock AgentCore uses Claude Sonnet 4.6 to propose a
typed draft. It has no permission to schedule, message, or read contact endpoints."

### 0:55-1:20 - Review and activate

**Picture:** Review time, grace and role-only ladder. Show Circle consent. Activate only
after consent.

**Narration:** "The model's answer is never an action. Deterministic schema, time-zone,
consent and safety checks produce a preview. Mona reviews who may be contacted and when.
Only then can software create the schedule."

### 1:20-2:10 - The real accelerated Moment

**Picture:** Select **Test this plan**. Show EventBridge due event, Step Functions execution,
Alert state and audit timeline. Show the safe-sink label clearly.

**Narration:** "Drill Mode uses the deployed Scheduler, Standard Step Functions workflow,
DynamoDB state, SQS and worker on a compressed clock. Only the external delivery edge is
redirected to a named safe sink for judges. When Mona does not confirm, the Alert opens and
the approved ladder advances."

### 2:10-2:50 - Human judgment

**Picture:** Open the real signed responder link in a private window. Claim **I'm checking**,
show lease, then explicitly resolve **Reached her - she's okay**.

**Narration:** "Maya needs no account or install. Her expiring link is scoped to this Alert.
I'm checking creates a lease; it does not close anything. If Maya disappears, escalation
resumes. Only this explicit outcome resolves the Alert. Acknowledged is not resolved."

### 2:50-3:30 - Governed AWS agent

**Picture:** Redacted Developer Trace and architecture. Show runtime/model/schema/input hash,
Gateway role-only tool, Cedar ENFORCE decision and deterministic result. Demonstrate a
request containing an arbitrary phone number being denied.

**Narration:** "AWS credentials invoke the model; there is no model-provider key in
Lambda, the website or the APK. AgentCore Gateway tools accept roles, never phone numbers,
emails or URLs. Cedar is default deny and forbid wins. The target Lambda repeats tenant,
consent, version and state checks."

### 3:30-3:55 - Reliability

**Picture:** Test output for duplicate schedule events, queue retries, lease conflict, model
timeout and deterministic fallback. Do not scroll through unrelated output.

**Narration:** "Every boundary expects retries. Conditional writes prevent duplicate
contact. A stale plan version cannot change an open Alert. Model failure cannot authorize a
side effect; it returns a safe error while deterministic state remains intact."

### 3:55-4:20 - Privacy and impact

**Picture:** Android, web and responder montage using real captures. Briefly show no
location permission and the quiet all-clear state.

**Narration:** "ICO monitors the plan, not the person. It asks for no continuous location,
camera, or microphone access. Most days it does nothing. On the unusual day, it gives the
right people a calm, auditable way to close uncertainty."

### 4:20-4:30 - Close

**Picture:** ICO mark, "Someone notices", live demo and repository URLs.

**Narration:** "In Case Of. Someone notices. Try the live demo, inspect the public code, and
see how governed agents can support human judgment without replacing it."

## Capture rules

- Record 1920x1080 at a stable scale; keep the final master at 1080p.
- Redact AWS account IDs, phone numbers, email addresses, tokens and push payloads.
- Do not use a debug APK, browser fixtures, local repositories or synthetic AWS console UI.
- Keep narration neutral and non-alarmist. Music, if used, must have recorded license terms.
- Final duration must be under five minutes; target 4:30.
