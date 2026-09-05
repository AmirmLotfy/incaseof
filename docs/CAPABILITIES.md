# In Case Of - capability and release evidence matrix

Updated: 2026-09-05. Branch: `codex/hackathon-final`.

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
| Plans | Partially live verified | Create/list/get/activate/pause/resume/test routes and Android/web clients; the Android judge entry now mints an isolated session and routes its existing repository through the demo API; direct demo API created a real draft and started an accelerated Drill | Deploy the expanded demo routes, then verify Agent-backed compile and Android drill in demo AWS |
| Circle consent | Locally verified | Invite/resend/remove and signed accept/decline routes; Android invite UI; responder consent UI | Expiry, replay and cross-tenant tests on deployed URLs |
| Moment lifecycle | Partially live verified | The deployed Scheduler materialized a due Alert in the synthetic judge tenant; get/next/confirm/extend/cancel and recurring creation remain covered locally | Live confirm, extend, cancel and recurring-next-Moment evidence |
| Alert lifecycle | Partially live verified | A signed synthetic responder link was policy-gated until Circle escalation, then claim created `CHECKING` and explicit resolve produced `RESOLVED` | Private-window UI capture plus live release, extend, conflict and lease-expiry evidence |
| History | Locally verified | Owner-indexed terminal Alert query; API/Android mapping | Resolved deployed drill visible on clients |
| Workflow | Live verified without the model leg | A deployed accelerated Drill produced 11 audit events through Scheduler, Standard Step Functions, SQS, worker, responder lease and explicit resolution | Deployed execution ARN plus a complete AgentCore-to-workflow trace after model access is restored |
| Public judge demo | Demo-only; partially live verified | Fresh isolated sessions, draft creation and a complete deterministic Drill succeed on the direct API; web and Android use the same real handlers with no browser fixtures or local-data fallback; demo device registration is impossible | Deploy the expanded Android demo surface, Agent compile and public `/demo` edge hosting |
| Demo delivery | Demo-only; live verified | The deployed worker accepted real queued PUSH/SMS attempts and recorded redacted `safe-sink:` provider references in the audit timeline | Judge-facing UI capture after edge hosting |
| SMS | Implemented, not live verified | Worker is sole `sns:Publish` principal; endpoints resolved at dispatch | One permitted project-owned verified test number |
| FCM | Live verified on emulator | Isolated Firebase project/app, least-privilege service account in Secrets Manager, enabled SNS platform app, API registration, one enabled endpoint and one delivered API 37 notification with the real `I'M OKAY` action | One physical-device receipt |
| Android debug | Locally verified | `assembleDebug`, unit tests, Android lint and ktlint pass; all 3 connected accessibility tests pass on API 26 and API 37; the in-app judge session is route-isolated and token-tested | Deploy and exercise the in-app judge flow; physical-phone checks |
| Android release | Built and emulator verified | Signed `com.incaof.app` v0.2.0 APK; API 26-37; v2/v3 verification; no local repository/localhost marker; clean install and launch on API 26/API 37; Android 13+ permission request verified | One physical-phone install and notification pass; rebuild for the canonical API after edge hosting exists |
| Marketing/web/responder | Locally verified | Next.js 16 static exports, typecheck, lint, build, 14 browser/accessibility cases including configured web-app mutations and explicit responder terminal state | CloudFront URLs, TLS/security headers and Lighthouse evidence |
| Hosting | API live; edge blocked | Demo API, Cognito, DynamoDB, Scheduler, Step Functions, SQS, AgentCore and KMS are deployed. The registrar delegates `incaof.com` to the Route 53 zone; `api.incaof.com` has valid TLS, targets the demo API and returns the public product-boundary descriptor. CloudFront creation is blocked by AWS account verification | Deploy the edge resources; publish exports; verify apex/`www` DNS, TLS and headers globally |
| Observability | Provisioned and locally verified | `ico-demo-health` dashboard and eight alarms exist; all eight alarms report OK as of 2026-09-04 | Dashboard screenshot plus evidence during a complete drill |
| Architecture artifact | Locally verified | Nova-labelled 2400x1600 PNG, SVG source and visually checked one-page PDF | Upload preview on Devpost |
| Project image and screenshots | Deferred until live demo | Final compositor must use real captures | Complete deployed capture set; no synthetic UI |
| Demo video | Prepared, not produced | 4:30 script and shot plan | Approved Higgsfield budget, real captures, final master and public URL |
| Bonus posts | Three complete drafts | Markdown drafts cover product principle, governed AgentCore and idempotent workflow | Publish on builder.aws and record URLs |

## Current automated evidence

- Unified preflight: all 19 gates pass on 2026-09-05.
- Python: Ruff format/lint, mypy and the full test suite pass.
- Contract parity: 53 method/path routes agree across OpenAPI, CDK and handler; authenticated and demo Android client routes are deployed in the correct environment templates.
- Infrastructure: 45 CDK assertions and synthesis pass, including exact Nova resources, runtime session lifecycle, AgentCore user-context invocation permissions, the demo-only quota-recovery guard and the single API-scoped Lambda invocation permission.
- Web: marketing and responder lint, typecheck and production static builds; 14 Playwright browser/accessibility cases.
- Android: unit tests, release lint, ktlint, R8, package/signature inspection and fail-closed configuration checks pass. All 3 connected accessibility tests pass on both API 26 and API 37.
- Android release identity: `com.incaof.app` v0.2.0 (`versionCode=2`), SHA-256 `db118074e6df54477212f2155674360a04a7b3eb69e2aacd168f6785d6cc60b3`, signing certificate SHA-256 `f12d1890545e420f5a2e10fa1475f21c2fa5463028f57fc3643daa1bc42bbd62`.
- Push delivery: API 37 created enabled endpoint `a36c1e9a-6dc4-32ba-b174-cbb37b76b64a`; SNS accepted message `c10723f5-9d2b-578c-91d1-40e145dc9104`; Android posted notification `1001` on channel `moments` with the `I'M OKAY` action. Protected credentials and the FCM token remain outside Git and logs.
- AWS core: `IcoStack-demo` is stable at `UPDATE_COMPLETE`; the API exposes all 53 explicit routes and uses one source-scoped invocation permission. The existing AgentCore Runtime remains deliberately preserved because the account's applied `Versions per Agent` quota is zero.
- AWS quota evidence: active AgentCore sessions were restored via approved request `451f1b8fde074b51bcb3aacaa2042ba8vNxnmcUj`; version request `b38dff125c3e4b1493e58c7fca4ed88bEgBdMI37` is `CASE_OPENED`.
- AWS account-verification evidence: support case `178838741100092` remains `UNASSIGNED`; a factual update is prepared but has not been sent without action-time confirmation.
- Public source evidence: commit `c7ff033f4fb5729a605b9354bb5f034bd90c3a54` is pushed to `codex/hackathon-final`; draft PR 15 has a fully green GitHub Actions run (`33962601126`) across Python, web, Android, guardrails and infrastructure, including exact Lambda and AgentCore artifact builds.
- Deployment identity: protected-environment run `33962736106` passed required review, exchanged GitHub OIDC for short-lived `ico-github-demo-deploy` credentials using the exact immutable repository subject, published exact assets, updated `IcoStack-demo` through the service-family-scoped `ico-demo-cfn-exec` role and verified the canonical API mapping. No long-lived AWS key or shared AdministratorAccess executor was used.
- Live deterministic Drill: after the scoped-role OIDC deployment, the canonical `api.incaof.com` verifier created synthetic plan `05b83895-b41d-4975-a06b-d7d762e2760c`, accelerated Moment `88071223-5461-58ec-a090-6d54cc9d0861`, and resolved Alert `b6c5c253-067b-41a6-8651-df67a4fe439e`. Eleven deployed audit events ended `RESPONDER_VERIFIED`; worker references were restricted to `safe-sink:`. The AgentCore compile was not part of this proof and still returns the designed 503 fallback.
- Release negative test: `assembleRelease` refuses to run without explicit backend and signing inputs.

## Hard blockers before a ready claim

1. Complete AWS account verification. CloudFront and every tested Bedrock model currently return account-level blocks.
2. Wait for AgentCore `Versions per Agent` case `178851871600399`, then deploy the corrected Nova runtime and 60-second idle lifecycle.
3. Add the currently blocked Nova/AgentCore compile leg to the now-proven live workflow, queue, responder lease and resolution path; record runtime, trace and execution identifiers.
4. Deploy edge hosting, publish both static clients, create apex/`www` records, and verify marketing, app, demo, consent and responder URLs globally. The canonical API descriptor is already live.
5. Finish one physical-phone FCM/install pass and rebuild the signed release for the canonical API after edge hosting exists.
6. Capture real deployed screenshots; only then generate the final 1800x1200 project image and demo video.
7. Publish the sub-five-minute video and builder.aws posts. The user supplies the public video URL and AWS Builder ID.
8. Merge the green draft PR only after the live acceptance gate passes, then tag that exact accepted commit and finalize `submission/release-evidence.json`.

## Explicitly deferred

- Voice, WhatsApp and automatic emergency dispatch.
- Production messaging access as a dependency for judge access.
- Deleting the legacy Gemini secret or changing root credentials before an alternate administrator path is proven and action-time approval is given.
