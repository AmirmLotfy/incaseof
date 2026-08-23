# In Case of

## Mission

Build a privacy-preserving autonomous safety agent that monitors expected moments rather than
continuously monitoring people.

> **In Case of does not decide whether someone is in danger. It notices unresolved expectations
> and works to close the loop.**

## Source of truth

| Topic | File |
|---|---|
| Product, scope, Definition of Done | `docs/PRD.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Domain model | `docs/ERD.md` |
| **Alert states (normative)** | `docs/PRODUCT-STATES.md` |
| AI boundaries | `docs/AI-SAFETY.md` |
| Security | `docs/SECURITY.md` |
| API | `docs/API.md` |
| Design system | `docs/design/DESIGN.md` |
| Copy standards | `docs/design/COPY.md` |

If code and these documents disagree, the documents win — fix the code, or change the document
deliberately and say so.

## Non-negotiables

- AI never directly mutates Alert state.
- AI never controls timers.
- AI never receives arbitrary communication endpoints. It selects a **role**, never a person and
  never a phone number.
- No external action without policy validation.
- DynamoDB is authoritative state. Agent memory is context, not truth.
- Every external action is idempotent (`alert_id + step_id + attempt_number`).
- Every Alert uses a pinned Plan Version.
- **Acknowledged ≠ Resolved.**
- All safety workflows continue if the model is unavailable.
- No continuous location or microphone by default. Location is off, and P0 does not need it.
- Never invent metrics, testimonials, or product claims.

## Design

- No gradients. No glassmorphism. No AI icons, sparkles, or glowing orbs.
- No generic SaaS bento layouts. Not every section is a card.
- Consumer UI never exposes AI jargon (workflow, state machine, prompt, tool call, LLM).
- Signal Orange takes **Ink** text, never white — white measures 3.52:1 and fails WCAG AA.
- A missed Moment is **not red**. Missing means unresolved, not emergency.
- Colour tokens are generated from `packages/design-tokens/tokens.json`. Never hand-edit
  `tokens.css` or `Tokens.kt`; run `npm run tokens` and commit the result.
- **Refero research is required before any significant new user-facing surface.** Record locked
  references in `docs/design/REFERENCES.md` first. "Make it beautiful" with no references is how
  this becomes generic AI slop.

## Development

- Work in vertical slices, in the order in `docs/PRD.md`. The deterministic non-AI slice must work
  end-to-end before the model is added.
- Tests are part of the implementation, not a later phase.
- Never disable a failing test to make CI green.
- Never commit credentials. Never hardcode a phone number, even in a test — use the fixtures.
- Pin dependency versions exactly. No wildcard ranges.
- Do not deploy destructive infrastructure without explicit approval.
- Do not expand scope beyond P0 until the full deterministic slice works.

## Commands

```bash
uv sync                                   # Python deps
uv run pytest                             # domain + contract + eval-dataset tests
uv run ruff check . && uv run ruff format --check .
uv run mypy services

npm install
npm run build                             # marketing + responder
npm run typecheck
npm run tokens:check                      # design tokens: web and Android agree
npm run contracts:check                   # openapi.yaml agrees with docs/API.md

cd android && ./gradlew assembleDebug testDebugUnitTest lintDebug ktlintCheck
cd infra/cdk && npx cdk synth             # add -c env=demo for the demo stack

./scripts/preflight.sh                    # everything above, in order
```

## Agent tooling (installed, not aspirational)

- **AWS skills and MCP** come from `aws configure agent-toolkit --yes`, not from a
  `/plugin` command. 19 skills in `~/.claude/skills`, MCP registered in `~/.claude.json`.
  Needs a region set first. Use them rather than reasoning about AWS from training data.
- **Refero** is installed standalone via `npx skills add`. Its craft references work
  offline; live style and screen research needs the MCP in `.mcp.json` and a browser
  sign-in.
- `skills-lock.json` pins the Refero skill by content hash. Commit changes to it
  deliberately.

## Toolchain notes (verified at scaffold time — do not "fix" these)

- **AGP 9 compiles Kotlin natively.** Applying `org.jetbrains.kotlin.android` is an error. The
  Compose compiler plugin is still applied separately, and `kotlin { compilerOptions { } }` sits
  outside the `android { }` block.
- **compileSdk/targetSdk 37** (Android 17). AndroidX requires 37+; 36 fails the build.
- **Material3 1.4.0 / Compose BOM 2026.08.00** are current stable. 1.5.x is alpha — do not adopt.
- **Detekt is deliberately absent**: its newest release predates Kotlin 2.4 and AGP 9 built-in
  Kotlin. Android Lint plus ktlint 14.2.0 cover this until detekt catches up.
- **mypy, not ty**: `ty` is at 0.0.x and pre-1.0. A release gate should not be a preview tool.
- Python is `uv`-managed 3.12. The system interpreter is 3.9 and cannot run this project.
- **ktlint's code style comes from `.editorconfig`**, not from the Gradle plugin's `android`
  flag — that flag does not reach ktlint's own config resolution.
- **Amplify requires `isCoreLibraryDesugaringEnabled`.** Without it the build fails at
  `checkDebugAarMetadata`, not at compile.
- **Adaptive icons must stay in `mipmap-anydpi-v26`** even at minSdk 26. Plain `anydpi` does
  not resolve and AAPT fails outright; `ObsoleteSdkInt` is disabled for that reason.
- **Material3 does not bundle icons.** `material-icons-core` is a separate dependency.
- Hilt, KSP and Room are deliberately absent — see `android/gradle/libs.versions.toml`.

## Phase state

**Phase 0 complete**: contracts, schemas, scaffold, guardrails, CI.
**Phase 1 complete**: deterministic domain core. Pure — no AWS, no model, no ambient clock.
`docs/PRODUCT-STATES.md` is enforced by a parity test that reads the document.
**Phase 2 complete**: infrastructure. DynamoDB adapters with conditional writes, EventBridge
Scheduler, Step Functions escalation, SQS outbox, Cognito, HTTP API. Synthesised and asserted;
**not yet deployed** — that needs the AWS CLI, credentials and explicit approval.
**Phase 3 complete**: the Android shell — Cognito auth, Home (all-clear and action-needed),
Plans, Plan detail, Circle, History, notifications with a working "I'M OKAY" action, four-tab
navigation. Runs against a local data source until the stack is deployed.
**Phase 4 complete**: the deterministic vertical slice. Plan → Moment → missed → Alert →
Circle contacted → claimed → resolved, proven end to end by `services/tests/slice/`, which
drives the real handlers, domain, policy layer and DynamoDB semantics. Only EventBridge,
SQS and Step Functions are played by the driver, and only because they exist to move time
and messages. Drill Mode runs the same engine compressed.

**Not yet proven, and blocked on deployment**: a Moment firing while the phone is off, real
FCM/SMS delivery, and the live demo. Those need the AWS CLI, credentials and an explicit
decision to deploy.

**Phase 5 complete**: Strands + Gemini behind the policy layer. One agent, eight tools, none
of which can name a person or an endpoint. Every proposal is recorded as an `AGENT_DECISION`
with ALLOW/DENY, denials included. Model output is validated twice — Pydantic for shape, then
the JSON Schema contract — before the existing semantic and safety layers run. Any model
failure degrades to explicit buttons; escalation timing is unaffected because the timers are
in EventBridge.

**Not yet run against the real model**: `GEMINI_API_KEY` is not set, so the live eval suite
has never executed. The suite and harness exist and the boundary is proven structurally.

**Phase 6 complete**: the web. The responder Incident Room at `/r/{token}` — no account,
no sign-up, one action, and an explicit sentence that claiming is not resolving. The
marketing site with the product's own timeline as the brand device, all nine sections from
§73–§84. A judge walkthrough at `/demo`.

**Not connected to a live backend**: both apps run against a labelled local data source
until the stack is deployed. The banner says so on every surface that shows one.

**Phase 7 is next**: polish — real channels, Drill Mode in the app, the trace UI, motion,
error states, performance, screenshots.
