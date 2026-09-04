# In Case Of - capability and release evidence matrix

Updated: 2026-09-04. Branch: `codex/hackathon-final`.

In Case Of closes uncertainty; it does not decide whether someone is in danger.

Evidence states have precise meanings:

- **Implemented**: source exists and is internally consistent.
- **Locally verified**: a named local gate passed in this checkout.
- **Demo-only**: intentionally restricted to the synthetic judge environment.
- **Live verified**: exercised against the deployed demo environment and recorded in the release manifest.
- **Deferred**: absent, blocked by external input, or outside the hackathon slice.

Passing local tests is not evidence of deployment, provider delivery, device installation, DNS, or judge access.

| Capability | State | Current evidence | Release evidence still required |
|---|---|---|---|
| Natural-language plan preview | Locally verified; live blocked | Typed AgentCore adapter/runtime tests; deterministic revalidation; deployed v1 process exposed and fixed an artifact-only import defect | Deploy the corrected Nova artifact after the AgentCore version quota is restored, then record a bounded canary |
| Model and credentials | Implemented; live blocked | Source is locked to `us.amazon.nova-2-lite-v1:0`; IAM/SigV4; no model API key in clients. Direct Bedrock calls currently return account-level `Operation not allowed` | AWS account verification, invocation ID, model ID, latency, token usage and redacted trace |
| Agent authorization | Provisioned; locally verified | Runtime, Gateway, role-only Lambda target and Cedar Policy Engine exist in `us-east-1`; Gateway is ENFORCE; CDK assertions pass | Permitted and denied live Gateway calls after account verification |
| Plans | Locally verified | Create/list/get/activate/pause/resume/test routes and Android/web clients | Authenticated web and Android drill in demo AWS |
| Circle consent | Locally verified | Invite/resend/remove and signed accept/decline routes; Android invite UI; responder consent UI | Expiry, replay and cross-tenant tests on deployed URLs |
| Moment lifecycle | Locally verified | Get/next/confirm/extend/cancel, schedules and recurring moment creation | Scheduler invocation and cancellation in demo AWS |
| Alert lifecycle | Locally verified | Get/claim/release/resolve/timeline with checking lease semantics | Responder private-window claim, lease and resolution |
| History | Locally verified | Owner-indexed terminal Alert query; API/Android mapping | Resolved deployed drill visible on clients |
| Workflow | Locally verified | Standard Step Functions definition, retries, SQS worker, idempotent state tests | Deployed execution ARN and successful end-to-end trace |
| Public judge demo | Demo-only; partially live verified | Fresh synthetic sessions succeed on the direct demo API; accelerated timing, real handlers, no browser fixtures | Agent compile and complete drill; public `/demo` still needs edge hosting |
| Demo delivery | Demo-only, locally verified | `SAFE_SINK` is accepted only when `ICO_ENV=demo`; action audit remains real | Worker log and timeline reference beginning `safe-sink:` |
| SMS | Implemented, not live verified | Worker is sole `sns:Publish` principal; endpoints resolved at dispatch | One permitted project-owned verified test number |
| FCM | Live verified on emulator | Isolated Firebase project/app, least-privilege service account in Secrets Manager, enabled SNS platform app, API registration, one enabled endpoint and one delivered API 37 notification with the real `I'M OKAY` action | One physical-device receipt |
| Android debug | Locally verified | `assembleDebug`, unit tests, Android lint and ktlint pass; all 3 connected accessibility tests pass on API 26 and API 37 against the latest source | Physical-phone checks |
| Android release | Built and emulator verified | Signed `com.incaof.app` v0.2.0 APK; API 26-37; v2/v3 verification; no local repository/localhost marker; clean install and launch on API 26/API 37; Android 13+ permission request verified | One physical-phone install and notification pass; rebuild for the canonical API after edge hosting exists |
| Marketing/web/responder | Locally verified | Next.js 16 static exports, typecheck, lint, build, 12 accessibility cases | CloudFront URLs, TLS/security headers and Lighthouse evidence |
| Hosting | Core provisioned; edge blocked | Demo API, Cognito, DynamoDB, Scheduler, Step Functions, SQS, AgentCore and KMS are deployed. Private S3/CloudFront/WAF/certificate/DNS source passes synth, but CloudFront creation is blocked by AWS account verification | Deploy edge resources; publish exports; verify apex/`www`/API DNS, TLS and headers globally |
| Observability | Provisioned and locally verified | `ico-demo-health` dashboard and eight alarms exist; all eight alarms report OK as of 2026-09-04 | Dashboard screenshot plus evidence during a complete drill |
| Architecture artifact | Locally verified | Nova-labelled 2400x1600 PNG, SVG source and visually checked one-page PDF | Upload preview on Devpost |
| Project image and screenshots | Deferred until live demo | Final compositor must use real captures | Complete deployed capture set; no synthetic UI |
| Demo video | Prepared, not produced | 4:30 script and shot plan | Approved Higgsfield budget, real captures, final master and public URL |
| Bonus posts | Three complete drafts | Markdown drafts cover product principle, governed AgentCore and idempotent workflow | Publish on builder.aws and record URLs |

## Current automated evidence

- Unified preflight: all 17 gates pass on 2026-09-04.
- Python: Ruff format/lint, mypy, 375 passing tests.
- Contract parity: 42 method/path routes agree across OpenAPI, CDK and handler; Android client routes are deployed in the template.
- Infrastructure: 43 CDK assertions and synthesis pass, including exact Nova resources, runtime session lifecycle and AgentCore user-context invocation permissions.
- Web: marketing and responder lint, typecheck and production static builds; 12 Playwright accessibility cases.
- Android: unit tests, release lint, ktlint, R8, package/signature inspection and fail-closed configuration checks pass. All 3 connected accessibility tests pass on both API 26 and API 37.
- Android release identity: `com.incaof.app` v0.2.0 (`versionCode=2`), SHA-256 `db118074e6df54477212f2155674360a04a7b3eb69e2aacd168f6785d6cc60b3`, signing certificate SHA-256 `f12d1890545e420f5a2e10fa1475f21c2fa5463028f57fc3643daa1bc42bbd62`.
- Push delivery: API 37 created enabled endpoint `a36c1e9a-6dc4-32ba-b174-cbb37b76b64a`; SNS accepted message `c10723f5-9d2b-578c-91d1-40e145dc9104`; Android posted notification `1001` on channel `moments` with the `I'M OKAY` action. Protected credentials and the FCM token remain outside Git and logs.
- AWS core: `IcoStack-demo` is stable at `UPDATE_ROLLBACK_COMPLETE`; 157 resources were originally created. A rejected Nova update was safely rolled back because the account's applied `Versions per Agent` quota is zero.
- AWS quota evidence: active AgentCore sessions were restored via approved request `451f1b8fde074b51bcb3aacaa2042ba8vNxnmcUj`; version request `b38dff125c3e4b1493e58c7fca4ed88bEgBdMI37` is `CASE_OPENED`.
- Release negative test: `assembleRelease` refuses to run without explicit backend and signing inputs.

## Hard blockers before a ready claim

1. Complete AWS account verification. CloudFront and every tested Bedrock model currently return account-level blocks.
2. Wait for AgentCore `Versions per Agent` case `178851871600399`, then deploy the corrected Nova runtime and 60-second idle lifecycle.
3. Create an IAM Identity Center or durable least-privileged deployment path. Successful deployments used narrowly scoped, ephemeral IAM users that were deleted immediately afterward; the interactive session is still root.
4. Run and record the full live drill through Nova, AgentCore, workflow, queue, responder lease and resolution.
5. Deploy and publish both static clients, create apex/`www` records, and verify marketing, app, demo, consent, responder and API URLs globally.
6. Finish one physical-phone FCM/install pass and rebuild the signed release for the canonical API after edge hosting exists.
7. Capture real deployed screenshots; only then generate the final 1800x1200 project image and demo video.
8. Publish the sub-five-minute video and builder.aws posts. The user supplies the public video URL and AWS Builder ID.
9. Review the dirty baseline, push a clean accepted commit, tag it, and finalize `submission/release-evidence.json`.

## Explicitly deferred

- Voice, WhatsApp and automatic emergency dispatch.
- Production messaging access as a dependency for judge access.
- Deleting the legacy Gemini secret or changing root credentials before an alternate administrator path is proven and action-time approval is given.
