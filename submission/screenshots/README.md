# Required live screenshot set

Capture only after the demo release manifest passes. Keep the browser and Android status
bars clean and redact accounts, tokens, contact endpoints and personal notifications.

Required files:

1. `marketing-desktop.png` - 1440px-wide canonical homepage.
2. `marketing-mobile.png` - 390px-wide homepage and navigation.
3. `web-plan-preview.png` - authenticated compiled plan preview.
4. `android-home.png` - physical or API 37 device home.
5. `android-create.png` - natural-language creation and literal preview.
6. `android-circle.png` - invitation/consent state with synthetic names.
7. `android-drill.png` - visible demo timing and live Alert state.
8. `responder-claim.png` - unclaimed signed link in a private window.
9. `responder-lease.png` - checking lease; Alert still open.
10. `responder-resolved.png` - explicit resolution.
11. `audit-timeline.png` - deployed end-to-end timeline.
12. `developer-trace-redacted.png` - AgentCore/model/tool/Cedar/deterministic evidence.

`scripts/build-devpost-image.sh` refuses to write the final project image until its four
required source captures are present.

## Live browser capture

After the canonical deployment and AgentCore canary pass, run:

```bash
npm run capture:submission
```

The capture runner reads the canonical marketing URL from `submission/release-evidence.json`,
requires HTTPS on `incaof.com`, refuses to run in final mode before the AgentCore canary passes,
uses no network interception or fixtures, and records SHA-256 provenance. It captures the two
marketing views, web preview, redacted Developer Trace, audit timeline, and all three responder
states. Android captures remain a physical/emulator-device procedure.

`ICO_CAPTURE_MODE=rehearsal ICO_CAPTURE_BASE_URL=http://127.0.0.1:3000` may be used only to
debug selectors. Rehearsal files are not submission evidence and must never be recorded in the
accepted manifest.

The project-image compositor intentionally does not require `status: ACCEPTED`; that would create
a circular gate because the final image itself is required before acceptance. Instead it requires
the live AgentCore canary, resolved deployed Drill, reachable canonical URLs, and real source
captures before writing anything.

## Android capture

For each Android state, navigate the signed `com.incaof.app` release to the intended screen,
then require a unique visible phrase while capturing it:

```bash
ICO_EXPECT_TEXT='Someone notices' ./scripts/capture-android-screen.sh android-home
ICO_EXPECT_TEXT='Review before activating' ./scripts/capture-android-screen.sh android-create
ICO_EXPECT_TEXT='Circle' ./scripts/capture-android-screen.sh android-circle
ICO_EXPECT_TEXT='Drill' ./scripts/capture-android-screen.sh android-drill
```

The script refuses a debug package, a background app, ambiguous device selection, missing
expected text, and visible local/sample markers. It hashes the device serial before recording
provenance and never writes the raw serial.
