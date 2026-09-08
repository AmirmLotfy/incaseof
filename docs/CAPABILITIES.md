# In Case Of - capability and release evidence matrix

Updated: 2026-09-08. Branch: `codex/hackathon-final`.

In Case Of closes uncertainty; it does not decide whether someone is in danger.

## Active implementation checkpoint — 2026-09-08

Hackathon completion is the active release target. The Egypt/US production plan remains
recorded for later work. Hackathon and production acceptance remain separate, and the
hackathon release is not yet accepted.

**Public GitHub Pages site deployed with canonical HTTPS.** Commit `0702675`
corrects the scoped edge policy and reuses the existing API mapping. Protected run
`34178964642` proved ACM certificate, WAF, private buckets and CloudFront configuration,
then AWS rejected only distribution creation with its account-verification requirement and
rolled the stack back. Marketing, `/app`, `/demo`, account deletion and the signed APK are
published from the `gh-pages` branch with `incaof.com` configured as the custom domain.
Route 53 serves the four documented GitHub Pages A records and the `www` CNAME. GitHub
account-level ownership verification completed on 2026-09-08 through Route 53 change
`C00288122934L2G6SJOOW`; GitHub then issued a Let's Encrypt certificate for both
`incaof.com` and `www.incaof.com`, and HTTPS enforcement was enabled. Marketing, `/app`,
`/demo`, account deletion and the APK return HTTP 200 on the canonical host; `www` redirects
to the apex. `https://amirmlotfy.github.io/` remains an HTTPS fallback.

**Safety repair deployed and live verified.** The recovery review reproduced two provider calls for
one replayed SQS body, contact after consent withdrawal, a lost-action window before SQS
enqueue, and missing real subject recipients. The repair adds transactional outbox records,
a one-minute recovery relay, conditional worker ownership, explicit subject recipients,
pinned responder identities, strong authorization reads, atomic outcomes/audit events and
UNKNOWN provider outcomes. Worker sends with unknown outcomes are never blindly retried.
Existing legacy action locks require reconciliation, not replay.

The complete preflight now passes with 467 Python tests and 50 CDK assertions. Focused
regressions cover sequential and concurrent replay, enqueue failure, pre-provider failure,
ambiguous provider acceptance, worker death, consent withdrawal, recipient reassignment,
checking and resolution races, terminal-alert reconciliation, pagination, subject adapters,
outcome/audit atomicity, terminal Moment advancement, scheduler interruption, bounded recurring
cancellation, capacity-release recovery, and Step Functions identity across a pending-delivery wait. Protected
OIDC run `33991694814` deployed the relay and application functions without replacing or
modifying the AgentCore Runtime. A fresh live Drill on that commit completed the deterministic
path with four distinct durable ACCEPTED outcomes and 13 audit events.

**Production account foundation deployed; authentication boundary live verified.** Authenticated profile APIs now persist
Egypt/US country, Arabic/English locale, IANA timezone and lifecycle status in the person's
partition. Readiness reports endpoint booleans and bounded plan capacity without returning
contact values. Production starts with admissions closed, and activation refuses incomplete
profiles, unsupported configured markets, exhausted account capacity, unverified subject
channels, and responders missing consent, permission, membership, or a verified endpoint.

**Phone-verification foundation deployed; provider delivery remains blocked.** Three Cognito
routes now start, confirm and revoke subject phone verification. Candidate numbers are sealed with
KMS and kept separate from the active endpoint, so replacing a phone cannot disable the current
verified number before success. Challenge and exact candidate promotion is transactional;
cross-account lookup, country changes, endpoint replacement, expiry, five-attempt exhaustion,
one-minute cooldown and five-start UTC-day limits fail closed. Country changes revoke the active
phone. The demo deployment intentionally has no OTP application or origination identity, so starts
return `OTP_UNAVAILABLE` after authentication and cannot contact a carrier. AWS's built-in OTP
template supports English but not Arabic; an approved Arabic-capable registered route is still
required before Egypt production acceptance.

**Account deletion is deployed; its unauthenticated boundary is live verified.** The authenticated
API writes a durable deletion lock before returning, blocks normal account work, due-Moment opening
and queued delivery, and retries cleanup under a bounded worker lease. Cleanup disables Cognito
first, removes endpoints, timers, executions and all owner-linked data, then deletes the Cognito
principal last. Dependencies and ownership markers are erased in retry-safe order, including a
regression that interrupts cleanup mid-purge. Web and Android provide typed `DELETE` confirmation,
explicit monitoring-stopped progress, and a public deletion-request page. Protected run
`34167842407` deployed this milestone while preserving the quota-blocked AgentCore Runtime; the
canonical descriptor returns HTTP 200 and both deletion routes return HTTP 401 without Cognito.

**Durable launch capacity is implemented, locally verified, and deployed to demo.** Staging and production reserve an
active plan in one DynamoDB transaction across a unique plan row, a per-account counter, and a global
counter. Concurrent contenders cannot consume the same final slot. Activation and resume fail
closed; pause, one-time completion, and account deletion release reservations idempotently. The
production global limit and admissions flag both start closed at zero/false until measured fixed and
messaging costs prove a funded capacity within the $100 monthly target. Existing active escalation
is never stopped by this admission gate. Protected run `34170551661` deployed the same handlers and
storage contract to demo through scoped OIDC; demo remains intentionally exempt from production
admission limits so the judge flow stays available.

**Android launch copy is extracted for Arabic and English.** Auth, judge demo, Home, plans, Circle,
history, account deletion, Drill status/timeline, product vocabulary, accessibility descriptions and
relative time now resolve at composition from paired resources. View models retain language-neutral
message/status codes so a configuration change cannot leave cached English copy on screen. Both
catalogs contain the same 202 resource keys; unit tests, lint, ktlint and debug assembly pass on
commit `95ef600`. Rendered Arabic RTL and mixed-direction phone-number review remain device gates.

**Authenticated web, public deletion and signed responder flows now support Arabic and English.**
The web app, account deletion page and Incident Room select Arabic from an explicit language control,
`?lang=ar`, or browser preference; set document language/direction; translate lifecycle states,
actions, timeline events and relative time; isolate mixed-direction timestamps; and fit a 320px
viewport without horizontal overflow. All 19 browser/accessibility cases pass. The marketing home
page and public demo narrative still require Arabic extraction before production acceptance.

The first repair deployment run, `33990483025`, rolled back cleanly because the scoped
CloudFormation executor did not have `events:DescribeRule`. The recovery timer now uses the
already-authorized EventBridge Scheduler service; runs `33991066635` and `33991694814`
completed with no resource replacement and with the quota-blocked AgentCore Runtime preserved.

AWS login was restored on September 5. The configured session is root: provider
inspection only; deployments continue through protected scoped GitHub OIDC. Fresh
inspection confirms `IcoStack-demo=UPDATE_COMPLETE` and `Versions per Agent=0`.
AWS Support API inspection is unavailable under the current support subscription.

Next resumable actions: exercise account deletion with a disposable authenticated account; measure
fixed and per-message costs before assigning any funded production slots; refresh support cases
through the console; deploy the corrected AI runtime only after the version quota and artifact gates
pass; then rerun the public drill with the live model leg.
Arabic SMS coverage, provider registration, carrier receipts, capacity admission, Play delivery and
physical-country evidence remain outstanding.

Evidence states have precise meanings:

- **Implemented**: source exists and is internally consistent.
- **Locally verified**: a named local gate passed in this checkout.
- **Demo-only**: intentionally restricted to the synthetic judge environment.
- **Live verified**: exercised against the deployed demo environment and recorded in the release manifest.
- **Deferred**: absent, blocked by external input, or outside the hackathon slice.

Passing local tests is not evidence of deployment, provider delivery, device installation, DNS, or judge access.

| Capability | State | Current evidence | Release evidence still required |
|---|---|---|---|
| Natural-language plan preview | Submission-capable fallback; live model blocked | Typed AgentCore adapter/runtime tests; deterministic revalidation; the canonical judge flow exposes and labels the deterministic safe-template fallback when AgentCore is unavailable | Optional score improvement: deploy the corrected Nova artifact after the AgentCore version quota is restored, then record a bounded canary |
| Model and credentials | Implemented; live blocked | Source is locked to AWS-native `us.amazon.nova-2-lite-v1:0`; IAM/SigV4; no model API key in clients. A direct Nova canary currently returns account-level `Operation not allowed`. Claude was rejected after Bedrock returned an unsupported-country restriction for this account | AWS account verification, invocation ID, model ID, latency, token usage and redacted trace |
| Agent authorization | Provisioned; locally verified | Runtime, Gateway, role-only Lambda target and Cedar Policy Engine exist in `us-east-1`; Gateway is ENFORCE; CDK assertions pass | Permitted and denied live Gateway calls after account verification |
| Account profile and readiness | Deployed to demo; auth boundary live verified | Authenticated profile/readiness routes, Dynamo adapter, EG/US and ar/en validation, IANA timezone validation, endpoint-safe responses, exact-plan channel gates, and atomic account/global reservations; production admissions and funded capacity start closed | Authenticated live profile/readiness exercise, cost-backed positive capacity, verified phone lifecycle, then staging/production deployment |
| Account deletion | Deployed; auth boundary live verified | Durable per-account lock; idempotent request/status APIs; leased retry worker; Cognito disable/delete; timer, workflow, endpoint, reservation and owner-data cleanup; mid-purge and post-purge retry tests; authenticated web/Android flows; public request page; both live routes return 401 without Cognito | Authenticated request/status and worker cleanup exercise with a disposable account, then staging/production verification |
| Phone ownership | Deployed foundation; provider blocked | Cognito start/confirm/revoke routes; strict EG/US E.164 validation; KMS candidate storage; atomic exact-endpoint promotion; cooldown, daily and attempt limits; country-change revocation; all three deployed routes return 401 without Cognito | Registered EG and US origins, Arabic-capable Egypt verification SMS, authenticated live start/confirm/revoke, carrier receipt and physical-handset evidence |
| Plans | Partially live verified | Create/list/get/activate/pause/resume/test routes and Android/web clients; the Android judge entry now mints an isolated session and routes its existing repository through the demo API; direct demo API created a real draft and started an accelerated Drill | Deploy the expanded demo routes, then verify Agent-backed compile and Android drill in demo AWS |
| Circle consent | Locally verified | Invite/resend/remove and signed accept/decline routes; Android invite UI; responder consent UI | Expiry, replay and cross-tenant tests on deployed URLs |
| Moment lifecycle | Partially live verified | The deployed Scheduler materialized a due Alert in the synthetic judge tenant; deterministic version+due successor identity makes due, resolution, cancellation and retries converge on one recurring Moment; one-time and bounded completion/cancellation deactivate and release capacity; scheduler and release interruptions recover locally | Deploy this checkpoint, then capture live confirm, extend, cancel and recurring-next-Moment evidence |
| Alert lifecycle | Partially live verified | A signed synthetic responder link was policy-gated until Circle escalation, then claim created `CHECKING` and explicit resolve produced `RESOLVED` | Private-window UI capture plus live release, extend, conflict and lease-expiry evidence |
| History | Locally verified | Owner-indexed terminal Alert query; API/Android mapping | Resolved deployed drill visible on clients |
| Workflow | Live verified without the model leg | Commit `864a168` produced 13 audit events through Scheduler, Standard Step Functions, SQS, durable outbox, worker, responder lease and explicit resolution; execution `alert-84d3d2cd-1c6a-4abc-ac7e-a517f6f6cc37` preserved identity across delivery waits and finished `SUCCEEDED` at 2026-09-05T21:13:54.357Z | Complete AgentCore-to-workflow trace after model access is restored |
| Public judge demo | Demo-only; partially live verified | Fresh isolated sessions, draft creation and a complete deterministic Drill succeed on the direct API; web and Android use the same real handlers with no browser fixtures or local-data fallback; demo device registration is impossible | Deploy the expanded Android demo surface, Agent compile and public `/demo` edge hosting |
| Demo delivery | Demo-only; live verified | The deployed worker accepted real queued PUSH/SMS attempts and recorded redacted `safe-sink:` provider references in the audit timeline | Judge-facing UI capture after edge hosting |
| SMS | Implemented, not live verified | Worker is sole `sns:Publish` principal; endpoints resolved at dispatch | One permitted project-owned verified test number |
| FCM | Live verified on emulator | Isolated Firebase project/app, least-privilege service account in Secrets Manager, enabled SNS platform app, API registration, one enabled endpoint and one delivered API 37 notification with the real `I'M OKAY` action | One physical-device receipt |
| Android debug | Locally verified | `assembleDebug`, unit tests, Android lint and ktlint pass; account deletion sends a tested DELETE body and has typed-confirmation state tests; 202-key English/Arabic catalogs cover all launch flows, product vocabulary, messages and relative time; all 3 connected accessibility tests pass on API 26 and API 37; the in-app judge session is route-isolated and token-tested | Authenticated deletion/device exercise, rendered Arabic RTL and mixed-number review, deploy and exercise the judge flow, physical-phone checks |
| Android release | Built and emulator verified | Signed `com.incaof.app` v0.2.0 APK; API 26-37; v2/v3 verification; no local repository/localhost marker; clean install and launch on API 26/API 37; Android 13+ permission request verified; exact protected-build APK completed the live Drill against `api.incaof.com` | One physical-phone install and notification pass |
| Marketing/web/responder | Canonical HTTPS live | Next.js 16 static exports, typecheck, lint, build, 19 browser/accessibility cases; authenticated web, public deletion and responder flows support Arabic RTL at 320px; marketing, `/app`, `/demo`, signed `/r` and `/i` shells, and APK are published on GitHub Pages. `incaof.com` and `www.incaof.com` have a valid certificate, HTTPS is enforced, canonical routes return HTTP 200, and `www` redirects to the apex | Capture final judge-facing evidence on the canonical host |
| Hosting | API and canonical static site live | Demo API, Cognito, DynamoDB, Scheduler, Step Functions, SQS, AgentCore and KMS are deployed. `api.incaof.com` has valid TLS and returns the public descriptor. GitHub Pages serves the public site at `https://incaof.com` with enforced HTTPS. The scoped AWS edge reached distribution creation before account verification blocked it | AWS CloudFront remains externally blocked; it is not required for the hackathon site |
| Observability | Provisioned and locally verified | `ico-demo-health` dashboard and eight alarms exist; all eight alarms report OK as of 2026-09-04 | Dashboard screenshot plus evidence during a complete drill |
| Architecture artifact | Locally verified | Nova-labelled 2400x1600 PNG, SVG source and visually checked one-page PDF | Upload preview on Devpost |
| Project image and screenshots | Canonical submission package complete | Twelve real browser/Android captures cover the public site, validated deterministic preview, deployed audit timeline, signed responder claim/lease/resolution and signed Android release Drill. Signed paths are redacted in provenance. A 1800×1200 image is composed from those captures | Optional score improvement: repeat the preview/trace captures after AgentCore is available |
| Demo video | 4:35 submission master produced | A 1920×1080 H.264/AAC master, local narration, synchronized SRT/VTT files, 1280×720 thumbnail, editable FFmpeg timeline and capture-hash provenance are complete. The narration and visible UI truthfully disclose the AgentCore quota block and deterministic fallback | Complete end-to-end playback review and upload publicly to YouTube or Vimeo |
| Bonus posts | Three complete drafts | Markdown drafts cover product principle, governed AgentCore and idempotent workflow | Optional bonus: publish on builder.aws and record URLs |

## Current automated evidence

- Unified preflight: all 19 gates pass on 2026-09-08 at implementation commit `5f48122`.
- Python: Ruff format/lint, mypy and all 467 tests pass.
- Contract parity: 61 method/path routes agree across OpenAPI, CDK and handler; authenticated and demo Android client routes are deployed in the correct environment templates.
- Infrastructure: 50 CDK assertions and synthesis pass, including the bounded account-deletion worker and narrow Cognito, Scheduler, Step Functions, SNS, KMS and DynamoDB permissions; production-closed admissions and bounded account capacity; complete least-privilege OTP configuration; exact Nova resources; runtime session lifecycle; the one-minute outbox recovery schedule; the six-timeout SQS visibility window; the demo-only quota-recovery guard and the single API-scoped Lambda invocation permission.
- Web: marketing and responder lint, typecheck and production static builds; 19 Playwright browser/accessibility cases, including Arabic RTL authenticated, deletion and responder flows at 320px.
- Android: unit tests, release lint, ktlint, R8, package/signature inspection and fail-closed configuration checks pass. All 3 connected accessibility tests pass on both API 26 and API 37.
- Android release identity: protected run `34188760450` built `com.incaof.app` v0.2.0 (`versionCode=2`) from commit `a3e0d0c`, SHA-256 `4119a4993a44e38a11bdb37e2523f527d4364f84b524933e1ff3b63ec1054258`, signing certificate SHA-256 `f12d1890545e420f5a2e10fa1475f21c2fa5463028f57fc3643daa1bc42bbd62`. The installed signed release started the deployed Drill and rendered live Scheduler, workflow, queue and worker audit events on API 37.
- Submission media: twelve canonical/browser and signed-Android captures, 1800×1200 project image, 4:35 1920×1080 master, WAV narration, SRT/VTT captions, 1280×720 thumbnail, editable timeline and complete capture hashes are present. The canonical deterministic fallback is explicitly disclosed in the UI and narration.
- Push delivery: API 37 created enabled endpoint `a36c1e9a-6dc4-32ba-b174-cbb37b76b64a`; SNS accepted message `c10723f5-9d2b-578c-91d1-40e145dc9104`; Android posted notification `1001` on channel `moments` with the `I'M OKAY` action. Protected credentials and the FCM token remain outside Git and logs.
- AWS core: `IcoStack-demo` is stable at `UPDATE_COMPLETE`; the API exposes all 61 explicit routes and uses one source-scoped invocation permission. The existing AgentCore Runtime remains deliberately preserved because the account's applied `Versions per Agent` quota is zero.
- AWS quota evidence: active AgentCore sessions were restored via approved request `451f1b8fde074b51bcb3aacaa2042ba8vNxnmcUj`. AWS asked why automated version request `b38dff125c3e4b1493e58c7fca4ed88bEgBdMI37` requested 1,001 versions; case `178851871600399` was answered on 2026-09-08 clarifying that the applied value is zero and the demo needs only the minimum non-zero value of one. It is awaiting AWS.
- AWS account-verification evidence: support case `178838741100092` was refreshed on 2026-09-08 with current CloudFront, Nova 2 Lite and AgentCore failures plus the September 14 deadline. It is awaiting AWS; no remaining identity or payment prerequisite has been identified to us yet.
- Public source evidence: edge recovery checkpoint `0702675` is pushed to `codex/hackathon-final`; reliability checkpoint `5f48122` has fully green run `34177296272` across Python, web, Android, guardrails and infrastructure. Android localization commit `95ef600`, signed responder localization `971b683`, and authenticated web/public deletion localization `67afcd5` are preserved in the same branch.
- Deployment identity: protected-environment runs `34170361557` and `34170551661` passed required review, exchanged GitHub OIDC for short-lived `ico-github-demo-deploy` credentials using the exact immutable repository subject, published exact assets, updated `IcoStack-demo` through the service-family-scoped `ico-demo-cfn-exec` role and verified the canonical API mapping. No long-lived AWS key or shared AdministratorAccess executor was used. The AgentCore Runtime was preserved because the account quota remains zero. The canonical descriptor remains HTTP 200; unauthenticated profile, readiness, all three phone-lifecycle routes and both deletion routes return HTTP 401.
- Live deterministic Drill: after that scoped-role OIDC deployment, the direct API verifier created synthetic plan `8870c8dc-3c80-40ec-a189-c64afa5ab84a`, accelerated Moment `36c1810a-380f-5d27-8273-8a62c64f367e`, and resolved Alert `84d3d2cd-1c6a-4abc-ac7e-a517f6f6cc37`. Thirteen deployed audit events include four distinct ACTION_QUEUED/ACTION_ACCEPTED pairs, Circle escalation, responder claim and `RESPONDER_VERIFIED`; all four outbox rows are terminal ACCEPTED and worker references are restricted to `safe-sink:`. After the in-progress lease wait elapsed, the Standard workflow re-read the terminal Alert and finished `SUCCEEDED`. The AgentCore compile was not part of this proof and still returns the designed 503 fallback.
- Release negative test: `assembleRelease` refuses to run without explicit backend and signing inputs.

## Hackathon submission blockers

The official rules require a working Strands-based project, public source, architecture diagram,
a public video of at most five minutes, and the participant's AWS Builder ID. AgentCore deployment,
a live demo, and builder.aws posts can improve scoring but are optional. Physical-device and real SMS
evidence remain production acceptance work rather than hackathon eligibility gates.

1. Re-capture the canonical judge flow in submission mode and seal the final image/video provenance.
2. Upload the sub-five-minute video to YouTube or Vimeo and record its public URL.
3. Record the participant's AWS Builder ID.
4. Merge the green draft PR, tag the exact accepted commit, and finalize `submission/release-evidence.json`.

AWS account verification and AgentCore quota case `178851871600399` remain active score-improvement
work. If AWS restores access before judging, deploy the corrected Nova runtime and capture the model
invocation and trace identifiers without changing the deterministic workflow guarantee.

## Explicitly deferred

- Voice, WhatsApp and automatic emergency dispatch.
- Production messaging access as a dependency for judge access.
- Deleting the legacy Gemini secret or changing root credentials before an alternate administrator path is proven and action-time approval is given.
