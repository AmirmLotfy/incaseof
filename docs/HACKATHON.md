# In Case Of - ICO: Devpost submission copy

In Case Of closes uncertainty; it does not decide whether someone is in danger.

> Release gate: this copy may be pasted only after the live evidence fields in
> `docs/CAPABILITIES.md` pass. Until then, URLs describe intended canonical destinations.

## General information

**Project name:** In Case Of - ICO

**Elevator pitch:** ICO quietly watches expected moments, takes safe action through governed AWS agents, and asks for human judgment only when it matters.

**Track:** Everyday Agents

**Code:** https://github.com/AmirmLotfy/incaseof

**Live demo:** https://incaof.com/demo

**Android:** https://incaof.com/downloads/in-case-of.apk

## About the project

### Inspiration

Independence should not require surveillance. People live alone, recover at home, commute late and take solo trips without wanting a camera, live-location feed or emergency button watching them all day. ICO began with a quieter promise: **monitor the plan, not the person**. If an expected moment passes unresolved, someone notices.

### What it does

Someone describes an expected moment in ordinary language. ICO turns it into a literal preview: when the check is due, how long grace lasts, who may be contacted and in what order. Nothing activates until the subject reviews it and every required Circle member consents.

At the due time, deterministic software opens an Alert. The subject can confirm or extend. A responder can claim **I'm checking**, which creates a temporary lease but does not resolve the Alert. Only an explicit outcome closes the loop; an expired lease resumes escalation. Every transition is recorded in a truthful timeline.

### How we built it

The Android client uses Kotlin and Jetpack Compose. The marketing site, authenticated web app, public judge demo and zero-install responder experience use Next.js 16 static exports behind private Amazon S3 origins and Amazon CloudFront.

Amazon Cognito authenticates subjects. Amazon API Gateway exposes an explicit route list to Python 3.12 AWS Lambda handlers. Amazon DynamoDB stores versioned Plans, Moments, Alerts, consent and audit events. Amazon EventBridge Scheduler owns due times; AWS Step Functions Standard and Amazon SQS drive retried, idempotent escalation.

Natural language is interpreted by a Strands agent running in Amazon Bedrock AgentCore Runtime with Amazon Nova 2 Lite through Amazon Bedrock. AWS execution-role credentials replace model API keys. The runtime has no DynamoDB, Scheduler, SQS, SNS or contact permission. AgentCore Gateway accepts only abstract roles, and an AgentCore Policy Engine evaluates Cedar policies in ENFORCE mode. Typed schema, time-zone, consent and safety validators re-check every draft before it can be saved.

### Challenges we ran into

The hardest problem was not contacting someone; it was preserving meaning through retries and uncertainty. We had to make duplicate events harmless, distinguish provider acceptance from delivery, pin Alerts to immutable Plan Versions, and ensure **acknowledged is not resolved**. Signed responder links needed to be narrow, expiring and tenant-safe without forcing a worried friend to create an account. The model/system separation had to be structural rather than prompt-based.

### Accomplishments that we're proud of

We built one governed vertical slice from language to explicit resolution across native Android, authenticated web and responder web surfaces. The agent can propose a role but has no vocabulary for phone numbers, emails or arbitrary URLs. A synthetic judge tenant runs the real schedule, workflow, queue, worker, lease and audit code with only the final delivery redirected to a clearly named safe sink. OpenAPI, CDK, handlers and the Android client are checked for route parity.

### What we learned

Unresolved does not mean danger. The useful action is to close uncertainty without inventing conclusions. AI is good at translating how people speak into a candidate structure; deterministic software must authorize and own safety state. Privacy improves when capability is removed, not merely promised.

### What's next for In Case Of

After carefully reviewed pilots, we would add scoped context snapshots and additional channels such as voice and WhatsApp. Those channels must preserve the same consent, role-only addressing, idempotency and explicit-resolution rules. ICO will not become automatic emergency dispatch.

## Built with

Python, TypeScript, Kotlin, Jetpack Compose, Next.js, Strands Agents SDK, Amazon Bedrock, Amazon Bedrock AgentCore, Amazon Nova 2 Lite, AWS Lambda, AWS Step Functions, Amazon API Gateway, Amazon DynamoDB, Amazon Cognito, Amazon EventBridge Scheduler, Amazon SQS, Amazon SNS, Amazon CloudFront, Amazon S3, AWS KMS, AWS Secrets Manager, AWS CDK, Amazon CloudWatch, Playwright, Pytest

## Testing instructions

1. Open https://incaof.com/demo and choose **Mona's evening check-in**.
2. Compile the description and review every proposed step.
3. Save the draft, then choose **Test this plan**.
4. Let the accelerated Moment pass and watch the deployed audit timeline update.
5. Open the generated responder link in a private window.
6. Choose **I'm checking**, observe that the Alert remains open under a lease, then resolve **Reached her - she's okay**.
7. Open Developer Trace to inspect the redacted AgentCore, model, tool, policy and deterministic decisions.
8. Optionally install the signed APK and choose **Try judge demo**.

No payment or personal phone number is required. Demo identities are synthetic, delivery is redirected to a safe sink, and tokens shown in Developer Trace are redacted.
