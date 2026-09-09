# Title

In Case Of — ICO

## One-line Summary

ICO quietly watches expected moments, takes safe action through governed AWS agents, and asks for human judgment only when it matters.

## Problem

People who live alone, recover at home, commute late, or take solo trips often want one simple assurance: if an expected moment passes unresolved, someone they trust should notice. Existing options commonly require continuous location, cameras, microphones, panic buttons, or a premature assumption that uncertainty means danger.

## Solution

In Case Of monitors the plan rather than the person. A subject describes an expected moment in ordinary language. ICO turns it into a literal draft containing the due time, grace period, approved recipients, channels, and escalation order. Nothing starts until the subject reviews the draft, every required responder consents, the channels are ready, and the subject explicitly activates it.

At the due time, deterministic AWS services open an Alert and advance the approved escalation ladder. A responder can claim “I’m checking,” creating an expiring lease that keeps the Alert open. Only an explicit outcome resolves it. Every transition is recorded in an audit trail.

## Why This Matters

Uncertainty affects both independence and peace of mind. ICO gives people a quiet safety net while preserving privacy and human judgment. The model helps translate intent; it never decides that someone is in danger, chooses an unapproved recipient, or controls the safety state.

## How We Used AI

ICO implements a Strands agent targeting Amazon Bedrock AgentCore Runtime and Amazon Nova 2 Lite. The agent converts natural language into a typed candidate Plan. Its tools accept abstract roles rather than raw phone numbers, email addresses, or arbitrary URLs. Cedar policy, schema validation, consent, time-zone rules, channel readiness, pinned Plan Versions, and deterministic state transitions authorize every later action.

AWS account verification and an applied zero AgentCore-version quota currently prevent deployment of the corrected model runtime. The public judge flow labels and uses the same validated deterministic fallback. Scheduler, Step Functions, SQS, the durable delivery worker, responder leases, and explicit resolution still run live in AWS. No model trace is fabricated.

## How We Used Codex

Codex helped recover and audit the project, reproduce four delivery-ordering defects, implement a transactional outbox and durable worker outcomes, add regression tests for replay, consent withdrawal, enqueue failure, provider uncertainty, and subject delivery, repair Android release serialization, localize the launch flows, harden infrastructure permissions, build the public judge flow, and maintain evidence that separates local, CI, emulator, provider, and deployed claims. Protected GitHub workflows use short-lived OIDC credentials and a project-scoped CloudFormation execution role.

## Key Features

- Natural-language Plan compilation with a literal preview before activation.
- Consent-gated Circle recipients and channel readiness checks.
- Durable, idempotent delivery intents with reconciliation for uncertain provider outcomes.
- EventBridge Scheduler, Step Functions Standard, SQS, DynamoDB, and a single authorized delivery worker.
- Expiring responder links, claim leases, conflict handling, and explicit resolution.
- Public isolated judge demo plus authenticated web and signed Android clients.
- English and Arabic resources with RTL-ready web and mobile surfaces.
- Redacted developer trace and auditable workflow timeline.

## Architecture

The Android client uses Kotlin and Jetpack Compose. The marketing site, authenticated web app, public judge demo, deletion route, and zero-install responder experience use Next.js 16 static exports. Amazon Cognito authenticates subjects. API Gateway exposes 61 explicit routes to Python 3.12 Lambda handlers. DynamoDB stores Plan Versions, Moments, Alerts, consent, outbox records, durable delivery outcomes, and audit events. EventBridge Scheduler owns due times; Step Functions Standard advances the approved ladder; SQS carries delivery intents. SNS adapters support push and SMS, while the judge flow redirects final delivery to a clearly labeled safe sink.

AgentCore Runtime hosts the Strands compiler, AgentCore Gateway exposes only role-based tools, and AgentCore Policy Engine evaluates Cedar policies in ENFORCE mode. The runtime has no DynamoDB, Scheduler, SQS, SNS, or contact permission.

Architecture diagram: `submission/architecture/in-case-of-architecture.png`

## Testing Instructions

1. Open https://incaof.com/demo and choose **Mona’s evening check-in**.
2. Compile the description and review every proposed step.
3. Save the draft, then choose **Test this plan**.
4. Let the accelerated Moment pass and watch the deployed audit timeline update.
5. Open the generated responder link in a private window.
6. Choose **I’m checking** and confirm the Alert remains open under a lease.
7. Resolve **Reached her — she’s okay** and verify the audit timeline closes explicitly.
8. Open **Developer Trace** to inspect the redacted model, tool, policy, and deterministic decisions.
9. Optionally install the signed APK and choose **Try judge demo**.

No payment or personal phone number is required. Demo identities are synthetic, provider delivery is redirected to a safe sink, and signed tokens are redacted from evidence.

## Public Demo Link

https://incaof.com/demo

## Public Repository Link

https://github.com/AmirmLotfy/incaseof

## Demo Video

https://youtu.be/hDcBwr9dFsY — 2:17 public YouTube demo with Marcus, a conversational male Higgsfield Qwen voice, original project-authored score, live public web workflow, deployed AWS audit timeline, responder resolution, signed Android client, architecture, and the current AgentCore limitation. Timed English captions are published, and YouTube reports no copyright or Community Guidelines issues.

## Screenshot Shot List

1. Public marketing page.
2. Validated Plan preview.
3. Deployed workflow and audit timeline.
4. Responder claim, active lease, and explicit resolution.
5. Signed Android home, create, Circle, and deployed Drill screens.
6. Redacted developer trace.

Canonical captures and hashes are recorded in `submission/screenshots/README.md` and `submission/release-evidence.json`.

## Submission Readiness Notes

- Public repository, Apache 2.0 license, README, architecture diagram, live demo, signed Android APK, project image, and sub-five-minute public video are ready.
- The current branch has green Python, web, Android, infrastructure, and guardrail checks.
- The **In Case Of — ICO** entry is verified live as submitted to Agents for Humans.
- The participant’s AWS Builder ID is supplied in the authenticated Devpost form.

## Known Limitations

- AWS account verification and the applied zero AgentCore-version quota block the corrected live Nova/AgentCore compiler deployment. The fallback is labeled in the UI and film.
- Physical-phone push and carrier SMS are outside hackathon acceptance and remain unverified.
- Production admissions are closed; the public surface is an isolated judge demo.

## Official Form Fields

- Submitter Type (`27729`): Individual
- Country of Residence (`27730`): Egypt
- Track (`27732`): Everyday Agents
- Public code repository (`27733`): https://github.com/AmirmLotfy/incaseof
- Architecture diagram (`27734`): `submission/architecture/in-case-of-architecture.png`
- AWS Builder ID (`27735`): supplied in the authenticated Devpost form
- Optional live demo (`27736`): https://incaof.com/demo
- Testing instructions (`28191`): use the Testing Instructions section above
- Optional builder.aws post (`27737`): three verified short content URLs, covering all three public posts

## Devpost Assets

- Project thumbnail: `submission/devpost/in-case-of-project-1800x1200.png`
- Architecture upload: `submission/architecture/in-case-of-architecture.png`
- Video thumbnail: `submission/video/final/ico-youtube-thumbnail.png`
- GPT Image 2 provenance: `submission/devpost/gpt-image-generation-provenance.json`
