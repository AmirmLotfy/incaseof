# Agents for Humans: Engineering an Idempotent Contingency Workflow on AWS

Retries are normal in distributed systems. In a contingency product, a duplicate retry can
become a duplicate message to a worried family member, while a dropped event can become no
message at all. ICO treats at-least-once delivery as a design input rather than an edge
case.

Amazon EventBridge Scheduler owns Expected Moment timers. When a moment is due, a Python
Lambda opens exactly one Alert and starts an AWS Step Functions Standard workflow. The
workflow asks deterministic domain code for the next decision: dispatch a rung, wait until
an offset or lease expiry, or close. It does not interpret language or resolve endpoints.

Dispatch writes a durable action intent to Amazon SQS. The worker is the only component
allowed to resolve an encrypted contact endpoint and call a provider. Each action is keyed
by Alert, sequence and attempt. DynamoDB conditional writes make repeated Scheduler events,
Step Functions retries and SQS redelivery converge on the same outcome instead of sending
again.

Provider truth is recorded carefully. An SNS message ID means AWS accepted a request; it
does not prove a handset received it. ICO records **ACTION_ACCEPTED** and reserves delivered
for a real carrier receipt. Missing providers and failed providers are different audit
events, so a responder does not wait for a retry that will never happen.

Human coordination is also modeled as a lease. **I'm checking** pauses backup escalation
for a bounded period without changing the Alert to resolved. Explicit resolution closes
the workflow and cancels pending schedules. Lease expiry simply returns the state machine
to its deterministic ladder.

For the public hackathon tenant, the same Scheduler, Step Functions, DynamoDB, SQS and
worker code runs on an accelerated clock. Only the last external delivery edge is replaced
by a named safe sink. That gives judges a fast, auditable workflow without sending test
messages to real people.

_Before publication: add the accepted execution ARN in redacted form, timeline screenshot,
test count from the tagged commit, and public repository/demo links._
